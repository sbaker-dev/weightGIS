from ..Cleaning import Match, Correction

from miscSupports import validate_path, simplify_string, string_contains_numbers
from csvObject import CsvObject
from typing import Optional, Union, List
from pathlib import Path


class FormatSetup:
    def __init__(self, place_reference: Union[str, Path], data_name: str,
                 correction_path: Optional[Union[Path, str]] = None, cpu_cores: int = 1,
                 alternate_matches: Optional[List[int]] = None, place_order: Optional[List[int]] = None):

        # Set the standardised name reference from a path to its csv
        self._reference = CsvObject(validate_path(place_reference), set_columns=True)

        # # The name for this particular sub set of data
        # self._data_name = data_name
        #
        # # Number of cores to use for multi-core enabled methods
        # self._cpu_cores = cpu_cores

        # Match lists to standardise names to, set the number of match types, -1 is from removing GID
        self.matcher, self._reference_types = self._construct_match_list()
        self.alternate = alternate_matches
        self._match_types = len(self._reference_types) - 1

        # If there is a correction file, validate it exists, then load it; else None.
        self.corrections = self._set_corrections(correction_path)

        # Set the order of any split elements
        self.order = self._set_ordering(place_order)

    def _construct_match_list(self):
        """
        Take the relations provided in the place reference and construct lists of matches for each place type to match
        names against
        """
        # Isolate the place types within the reference file, which represent column headers without numbers
        reference_types = [header for header in self._reference.headers
                           if "GID" not in header and not string_contains_numbers(header)]

        match_list = {}
        [self._match_name(match_list, place_names, reference_types) for place_names in self._reference.row_data]
        return match_list, ["GID"] + reference_types

    def _match_name(self, match_list, place_names, reference_types):
        """For each row of standardised names, map each alternated base map to the standardised, and link
        supporting names and gid"""

        # Clean the names from place reference
        names = [self._place_type_names(place_names, self._isolate_area_indexes(ref)) for ref in reference_types]

        # The first set of isolates from reference types will be the base names
        base_names = names[0]
        for name in base_names:
            # For each name in the base set, map all alternated names back to base_names[0]. Also store the GID and
            # alternated names
            match_list[f"{place_names[0]}__{name}"] = Match(place_names[0], base_names[0], names[1:])

    def _isolate_area_indexes(self, area):
        """Isolate the indexes associated with a given area index"""
        return [index for index, header in enumerate(self._reference.headers) if area in header]

    @staticmethod
    def _place_type_names(place_names: str, type_indexes: List[int]) -> List[str]:
        """
        Isolates all the valid names from a list of place names this place type by isolating the indexes
        """
        return [simplify_string(place_names[i]) for i in type_indexes if place_names[i] != ""]

    @staticmethod
    def _set_corrections(correction_path: Optional[Union[str, Path]]) -> Optional[dict]:
        """
        Set the correction dict for error: correction. If the name is invalid or needs removing, the delete flag will be
        true, and it will instead be set to none.
        """
        # If there are no corrections return None
        if not correction_path:
            return None

        # Otherwise, construct an error: correction / None dict, where None occurs if the name is to be deleted
        return {simplify_string(error): Correction(correction, alt_names, year, delete)
                for error, alt_names, correction, year, delete, _ in CsvObject(validate_path(correction_path)).row_data}

    def _set_ordering(self, place_order):
        if place_order:
            return place_order
        else:
            # Otherwise set the place_map to be just an ordered list of ints of range equal to the place types
            return [i for i in range(self._match_types)]
