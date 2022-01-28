from ..Cleaning import FormatSetup, FormatNames

from miscSupports import directory_iterator, find_duplicates, parse_as_numeric, simplify_string
from csvObject import CsvObject, write_csv
from typing import Optional, Union, List
from pathlib import Path
import numpy as np
import sys


class FormatExternal(FormatSetup):
    def __init__(self, place_reference: Union[str, Path], data_name: str, log_directory: Union[str, Path],
                 correction_path: Optional[Union[Path, str]] = None, cpu_cores: int = 1, splitter: str = "__",
                 alternate_matches: Optional[List[int]] = None, place_order: Optional[List[int]] = None):
        super().__init__(place_reference, data_name, correction_path, cpu_cores, alternate_matches, place_order)

        # Set delimiters for complex names
        self._splitter = splitter

        # Log directory for this process
        self._log_directory = log_directory

    def standardise_names(self, data_directory: Union[str, Path], name_i: int, data_start_i: int,
                          write_directory: Union[str, Path]):

        # Initialise the FormatNames class
        name_qc = FormatNames(self._splitter, self.order, self.matcher, self.corrections, name_i, self.alternate,
                              data_start_i, write_directory, self._log_directory)

        # Standardise each name within the provided data directory
        [name_qc.standardise_names(Path(data_directory, file)) for file in directory_iterator(data_directory)]
