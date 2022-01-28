from ..Cleaning import FormatSetup

from miscSupports import directory_iterator, find_duplicates, parse_as_numeric, simplify_string
from csvObject import CsvObject, write_csv
from typing import Optional, Union, List
from pathlib import Path
import numpy as np
import sys


class FormatExternal(FormatSetup):
    def __init__(self, place_reference: Union[str, Path], data_name: str,
                 correction_path: Optional[Union[Path, str]] = None, cpu_cores: int = 1, splitter: str = "__",
                 alternate_matches: Optional[List[int]] = None, place_order: Optional[List[int]] = None):
        super().__init__(place_reference, data_name, correction_path, cpu_cores, splitter, alternate_matches,
                         place_order)

    def standardise_names(self, data_directory: Union[str, Path], name_i: int, data_start_i: int,
                          write_directory: Union[str, Path]):

        [self._search_for_names(file, data_directory, name_i, data_start_i, write_directory)
         for file in directory_iterator(data_directory)]

    def _search_for_names(self, csv_file, data_directory, name_i, data_start_i, write_directory):

        # Load the csv file
        raw_csv = CsvObject(Path(data_directory, csv_file), set_columns=True)

        # Isolate unique names and simplify them for matching
        unique_names = sorted([simplify_string(place) for place in list(set(raw_csv[name_i]))])

        # Map all the unique names to a standardised name
        place_dict = {place: self._match_place(place, raw_csv.file_name) for place in unique_names}

        # rename all locations
        renamed = [[place_dict[simplify_string(row[name_i])]] + row[data_start_i:] for row in raw_csv.row_data]

        # Remove any ambiguity
        cleaned = self.solve_ambiguity(renamed)

        # Write the file
        write_csv(write_directory, raw_csv.file_name, ["Place"] + raw_csv.headers[data_start_i:], cleaned)

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

        if len(potential_matches) > 1 and self.alternate:
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