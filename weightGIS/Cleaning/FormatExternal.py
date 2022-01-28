from ..Cleaning import Standardise, FormatNames, RelationalDatabase

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

    def standardise_names(self, data_directory: Union[str, Path], name_i: int, data_start_i: int) -> None:

        # Initialise the FormatNames class
        name_qc = FormatNames(self._splitter, self._matcher, name_i, data_start_i, self._write_directory,
                              self._data_name)

        # Standardise each name within the provided data directory
        [name_qc.standardise_names(Path(data_directory, file)) for file in directory_iterator(data_directory)]

        # Write the file and log to disk
        name_qc.write()

    def relational_database(self) -> None:

        RelationalDatabase(self._matcher, self._data_name, self._write_directory)()

