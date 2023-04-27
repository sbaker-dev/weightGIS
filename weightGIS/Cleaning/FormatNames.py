from weightGIS.Errors import AmbiguousIsolates, AmbiguousIsolatesAlternatives, OrderError, UnexpectedQCName, \
    UnexpectedQCDate
from weightGIS.Cleaning import FormatStandardise

from miscSupports import find_duplicates, parse_as_numeric, simplify_string, write_json, terminal_time, load_yaml
from typing import List, Union
from csvObject import CsvObject
from pathlib import Path
import numpy as np


class FormatNamesLog:
    def __init__(self, qc_validation: Union[Path, str]):

        self._qc = load_yaml(qc_validation)

        self.log = {"Deleted": {}, "Ambiguous": {}}

    def _validated_qc(self, name, date, qc_type):
        """Validate the quality control measure that has been applied"""
        if name not in self._qc:
            raise UnexpectedQCName(name, date, qc_type)
        elif self._qc[name]['years'] and (int(date) not in self._qc[name]['years']):
            raise UnexpectedQCDate(name, date, qc_type)
        else:
            return 0

    def delete_name(self, name, date):
        """Log any deleted places"""
        # Add date to deleted if it doesn't exist
        if date not in self.log['Deleted']:
            self.log['Deleted'][date] = []

        self.log['Deleted'][date].append(name)
        print(f"Deleted: {name}")

        # Validate that this QC is expected
        self._validated_qc(name, date, 'deletion')

    def ambiguous(self, duplicate_name, data, date):
        """Log each duplicate that exists that has been merged"""
        # Add date to ambiguous if it doesn't exist
        if date not in self.log['Ambiguous']:
            self.log['Ambiguous'][date] = {}

        duplicate_data = [row for row in data if duplicate_name == row[0]]
        self.log['Ambiguous'][date][duplicate_name] = duplicate_data

        print(f"Found non perfect duplicates for {duplicate_name}")
        for dup in duplicate_data:
            print(f"\t{dup}")

        # Validate that this QC is expected
        self._validated_qc(duplicate_name, date, 'ambiguous')

    def write(self, database_name, out_directory):
        """Write log to disk"""
        write_json(self.log, out_directory, f"{database_name}_QC_Log")


class FormatNames:
    def __init__(self, splitter: str, matcher: FormatStandardise, name_i: int, data_start_i: int,
                 write_directory: Union[Path, str], database_name: str, qc_validation: Union[Path, str],
                 merge_ambiguity: bool):

        # Initialise the matcher
        self._std = matcher

        # How to split the names and the database name
        self._splitter = splitter
        self._database_name = database_name

        # The indexes to isolate from the files
        self._name_i = name_i
        self._data_i = data_start_i
        self._splitter = splitter
        self._merge_ambiguity = merge_ambiguity

        # Setup the output write directory, the logging subclass, and the database holder
        self._write_directory = write_directory
        self.log = FormatNamesLog(qc_validation)
        self.database = {}

    def write(self):
        """Write the database and the log to disk"""
        write_json(self.database, self._write_directory, f'Cleaned_{self._database_name}')
        self.log.write(self._database_name, self._write_directory)

    def standardise(self, csv_path: Path, file_index: int, total_files: int):
        """Standardise all names within this csv"""
        # Load the csv file
        raw_csv = CsvObject(csv_path, set_columns=True)

        # Isolate unique names and simplify them for matching
        unique_names = sorted([simplify_string(place) for place in list(set(raw_csv[self._name_i]))])

        # Map all the unique names to a standardised name
        place_dict = {place: self._match_place(place, raw_csv.file_name) for place in unique_names}

        # rename all locations
        cleaned = [[place_dict[simplify_string(row[self._name_i])]] + row[self._data_i:] for row in raw_csv.row_data]

        # Remove any ambiguity if required
        if self._merge_ambiguity:
            cleaned = self._solve_ambiguity(cleaned, raw_csv.file_name)

        # Add this dates values to the database
        self.database[raw_csv.file_name] = {row[0]: {h: row[i+1] for i, h in enumerate(raw_csv.headers[self._data_i:])}
                                            for row in cleaned}
        print(f"Processed {file_index} / {total_files}: {raw_csv.file_name} at {terminal_time()}")

    def _match_place(self, place, year):
        """
        Names from the town level data are not linkable to districts, attempt to do so via this method.
        """
        # Isolate the root name and the alternate names
        root_name, alternated_names = self._set_place_name(place)

        # Correct the root_name if there are spelling mistakes, continue if this element was to be deleted.
        root_name = self._correct_root_name(root_name, alternated_names, year)
        if not root_name:
            self.log.delete_name(place, year)
            return None

        # Isolate the standardised name from matches
        return self._isolate_standardised_name(root_name, alternated_names)

    def _set_place_name(self, place):
        """Split the names on the _splitter and order them based on the original order or that provided by the user"""
        split_place = place.split(self._splitter)

        if len(self._std.order) != len(split_place):
            raise OrderError(split_place, place, self._splitter, self._std.order)

        names = np.array(split_place)[self._std.order].tolist()
        return names[0], names[1:]

    def _correct_root_name(self, root: str, alternated_names: str, year: str) -> str:
        """Correct the root name if root exists in corrections"""
        if not self._std.corrections:
            return root
        try:
            return self._std.corrections[root].validate_correction(root, alternated_names, year)
        except KeyError:
            return root

    def _isolate_standardised_name(self, root_name, alternate_names):
        """
        Depending on whether we are using alternate names or otherwise, attempt to isolate a standardised name for
        root_name
        """
        # Isolate all the potential names, by comparing root name to the 2nd component of name (1st is GID)
        potential_matches = [name for name in self._std.matcher.keys() if root_name == name.split("__")[1]]

        # If we found no potential matches, then raise an index error
        if len(potential_matches) == 0:
            # TODO: Make an exception error class
            if len(alternate_names) > 0:
                raise IndexError(f"Failed to find {root_name}. Alternate names: {alternate_names}")
            else:
                raise IndexError(f"Failed to find {root_name}")

        # If we find at least one potential match, and have alternative names, validate the match is consistent with the
        # expected alternative names
        if len(potential_matches) > 1 and self._std.alternate:
            for place in [self._std.matcher[match] for match in potential_matches]:

                # If we find a place that successfully validates with alternate names, return that match
                if place.validate_alternate(alternate_names):
                    return place.name

            # If we fail to find a match that meets the alternative names, warn the end using by raise
            raise AmbiguousIsolatesAlternatives(potential_matches, root_name, alternate_names)

        # If we don't have alternative names, but find more than a single entry, then we have an ambitious merge, raise
        elif len(potential_matches) > 1:
            raise AmbiguousIsolates(potential_matches, root_name)

        # Otherwise we found exactly a single match, so return that match
        else:
            return self._std.matcher[potential_matches[0]].name

    def _solve_ambiguity(self, data: List[List[str]], date: str):
        """Remove any ambiguities rows that have occurred as a result of standardisation"""
        # Isolate names and search for duplicates
        names = [row[0] for row in data if row[0]]
        duplicate_list = find_duplicates(names)

        # Isolate any row that does not suffer from duplication as the base of the write return
        reset_row = [row for row in data if row[0] not in duplicate_list and row[0]]

        # Merge the duplicates
        return reset_row + [self._merge_duplicates(data, duplicate, date) for duplicate in duplicate_list]

    def _merge_duplicates(self, data, duplicated, date) -> List[str]:
        """Merge any duplicated entries together"""
        # Isolate the values for each duplicate name
        sub_list = [[parse_as_numeric(rr, float) for rr in row[1:]] for row in data if duplicated == row[0]]

        # Isolate unique lists, to remove duplicates
        unique_sub_lists = [list(x) for x in set(tuple(x) for x in sub_list)]

        # Warn the user that some values have been combined, then return the merged data
        if len(unique_sub_lists) > 1:
            self.log.ambiguous(duplicated, data, date)
        return [duplicated] + [str(sum(i)) for i in zip(*unique_sub_lists)]
