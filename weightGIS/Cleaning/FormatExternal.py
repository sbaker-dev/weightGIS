from ..Cleaning import FormatSetup, FormatNames, RelationalDatabase

from miscSupports import directory_iterator
from typing import Optional, Union, List
from pathlib import Path


class FormatExternal(FormatSetup):
    def __init__(self, place_reference: Union[str, Path], data_name: str, write_directory: Union[Path, str],
                 correction_path: Optional[Union[Path, str]] = None, place_order: Optional[List[int]] = None,
                 alternate_matches: Optional[List[int]] = None, splitter: str = "__",):
        super().__init__(place_reference, correction_path, alternate_matches, place_order)

        # Set delimiters for complex names and the database name
        self._data_name = data_name
        self._splitter = splitter

    def standardise_names(self, data_directory: Union[str, Path], name_i: int, data_start_i: int,
                          write_directory: Union[str, Path]):

        # Initialise the FormatNames class
        name_qc = FormatNames(self._splitter, self.order, self.matcher, self.corrections, name_i, self.alternate,
                              data_start_i, write_directory, self._data_name)

        # Standardise each name within the provided data directory
        [name_qc.standardise_names(Path(data_directory, file)) for file in directory_iterator(data_directory)]

        # Write the log
        name_qc.write()

    def relational_database(self, cleaned_directory: Union[Path, str], write_directory: Union[Path, str], cpu_cores=1):

        RelationalDatabase(self.matcher, self._data_name, write_directory, cleaned_directory)(cpu_cores)

        return

