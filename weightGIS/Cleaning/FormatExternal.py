from ..Cleaning import Standardise, FormatNames, RelationalDatabase, FormatLink, FormatCombine
from weightGIS import WeightExternal

from miscSupports import directory_iterator
from typing import Optional, Union, List
from pathlib import Path


class FormatExternal:
    def __init__(self, place_reference: Union[str, Path], data_name: str, write_directory: Union[Path, str],
                 correction_path: Optional[Union[Path, str]] = None, place_order: Optional[List[int]] = None,
                 alternate_matches: Optional[List[int]] = None, splitter: str = "__",):

        self._matcher = Standardise(place_reference, correction_path, alternate_matches, place_order)

        # Set delimiters for complex names, the database name, and the write_directory
        self._data_name = data_name
        self._splitter = splitter
        self._write_directory = write_directory

    def standardise_names(self, data_directory: Union[str, Path], name_i: int, data_start_i: int,
                          qc_validation: Union[Path, str], process_i: int = 0) -> None:
        """Standardise the names of places within external data"""
        # Initialise the FormatNames class
        name_qc = FormatNames(self._splitter, self._matcher, name_i, data_start_i, self._write_directory,
                              self._data_name, qc_validation)

        # Standardise each name within the provided data directory
        files = directory_iterator(data_directory)
        file_count = len(files) - process_i
        [name_qc.standardise(Path(data_directory, file), i, file_count) for i, file in enumerate(files[process_i:], 1)]

        # Write the file and log to disk
        name_qc.write()

    def link_names(self, data_directory: Union[str, Path]):
        """Link a cleaned file based on its unique ID to the full name and then construct the database"""
        FormatLink(self._matcher)(data_directory, self._write_directory, self._data_name)

    def relational_database(self) -> None:
        """Reformat Cleaned database of Date: Place: Attribute: Value -> Place: Attribute: Date: Value """
        RelationalDatabase(self._matcher, self._data_name, self._write_directory)()

    def weight_database(self, weights_path, date_max):
        WeightExternal(Path(self._write_directory, f"Relational_{self._data_name}.txt"), weights_path, date_max
                       ).weight_external(self._write_directory, f"{self._data_name}_Weighted")

    @staticmethod
    def combine_data_sources(unique_id, data_start, data_directory, write_directory, date):
        """Combine data sources into a single file if you have multiple files for the same data source and date"""
        FormatCombine(unique_id, data_start, data_directory, write_directory, date)()
