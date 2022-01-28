from miscSupports import find_duplicates, parse_as_numeric, simplify_string
from csvObject import CsvObject, write_csv
from typing import List, Optional, Union
from pathlib import Path
import numpy as np
import sys


class FormatNames:
    def __init__(self, splitter: str, order: List[int], matcher: dict, corrections: dict, name_i: int,
                 alternate_matches: Optional[List[int]],  data_start_i: int, write_directory: Union[str, Path]):

        # How to split the names, and the ordering of the items that have been split
        self._splitter = splitter
        self._order = order

        # The standardisation and correction dictionaries
        self._matcher = matcher
        self._corrections = corrections
        self._alternate = alternate_matches

        # The indexes to isolate from the files
        self._name_i = name_i
        self._data_i = data_start_i

        # Write directory
        self._write_directory = write_directory

    def standardise_names(self, csv_path: Path):

        # Load the csv file
        raw_csv = CsvObject(csv_path, set_columns=True)

        # Isolate unique names and simplify them for matching
        unique_names = sorted([simplify_string(place) for place in list(set(raw_csv[self._name_i]))])

        # Map all the unique names to a standardised name
        place_dict = {place: self._match_place(place, raw_csv.file_name) for place in unique_names}

        # rename all locations
        renamed = [[place_dict[simplify_string(row[self._name_i])]] + row[self._data_i:] for row in raw_csv.row_data]

        # Remove any ambiguity
        cleaned = self.solve_ambiguity(renamed)

        # Write the file
        write_csv(self._write_directory, raw_csv.file_name, ["Place"] + raw_csv.headers[self._data_i:], cleaned)

        sys.exit()

    def _match_place(self, place, year):
        """
        Names from the town level data are not linkable to districts, attempt to do so via this method.
        """
        # Isolate the root name and the alternate names
        root_name, alternated_names = self._set_place_name(place)

        # Correct the root_name if there are spelling mistakes, continue if this element was to be deleted.
        root_name = self._correct_root_name(root_name, alternated_names, year)
        if not root_name:
            print(f"Deleted: {place}")
            return None

        # Isolate the standardised name from matches
        return self._isolate_standardised_name(root_name, alternated_names)

    def _set_place_name(self, place):
        """Split the names on the _splitter and order them based on the original order or that provided by the user"""
        split_place = place.split(self._splitter)

        if len(self._order) != len(split_place):
            raise Exception(f"Attempted to order {len(split_place)} place names within {place.split(self._splitter)} "
                            f"with {len(self._order)} orderings of {self._order}")

        names = np.array(split_place)[self._order].tolist()
        return names[0], names[1:]

    def _correct_root_name(self, root: str, alternated_names: str, year: str) -> str:
        """Correct the root name if root exists in corrections"""
        if not self._corrections:
            return root
        try:
            return self._corrections[root].validate_correction(root, alternated_names, year)
        except KeyError:
            return root

    def _isolate_standardised_name(self, root_name, alternate_names):

        potential_matches = [name for name in self._matcher.keys() if root_name == name.split("__")[1]]

        if len(potential_matches) == 0:
            raise IndexError(f"Failed to find {root_name}")

        if len(potential_matches) > 1 and self._alternate:
            for place in [self._matcher[match] for match in potential_matches]:
                if place.validate_alternate(alternate_names):
                    return place.name
            # TODO: Create error
            raise Exception(f"Found the following potential matches {potential_matches} for root '{root_name}' but "
                            f"could not uniquely identify them with {alternate_names}")

        elif len(potential_matches) > 1:
            raise Exception(f"Found the following potential matches {potential_matches} for root '{root_name}' but "
                            "could not uniquely identify them")

        else:
            return self._matcher[potential_matches[0]].name

    def solve_ambiguity(self, data: List[List[str]]):

        # Isolate names and search for duplicates
        names = [row[0] for row in data if row[0]]
        duplicate_list = find_duplicates(names)

        # Isolate any row that does not suffer from duplication as the base of the write return
        reset_row = [row for row in data if row[0] not in duplicate_list and row[0]]

        # Merge the duplicates
        return reset_row + [self._merge_duplicates(data, duplicate) for duplicate in duplicate_list]

    @staticmethod
    def _merge_duplicates(data, duplicated) -> List[str]:
        # Isolate the values for each duplicate name
        sub_list = [[parse_as_numeric(rr, float) for rr in row[1:]] for row in data if duplicated == row[0]]

        # Isolate unique lists, to remove duplicates
        unique_sub_lists = [list(x) for x in set(tuple(x) for x in sub_list)]

        # Warn the user that some values have been combined.
        if len(unique_sub_lists) > 1:
            # TODO: Setup a warning class?
            print(f"Found non perfect duplicates for {duplicated}")
            for dup in [row for row in data if duplicated == row[0]]:
                print(f"\t{dup}")
        return [duplicated] + [str(sum(i)) for i in zip(*unique_sub_lists)]