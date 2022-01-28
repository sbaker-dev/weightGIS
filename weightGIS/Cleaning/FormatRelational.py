from weightGIS.Cleaning import Standardise

from miscSupports import write_json, load_json, terminal_time, validate_path
from typing import Union
from pathlib import Path


class RelationalDatabase:
    def __init__(self, matcher: Standardise, data_name: str, write_directory: Union[Path, str]):

        self._std = matcher
        self._data_name = data_name
        self._write_directory = write_directory

        self._database = load_json(validate_path(Path(write_directory, f"Cleaned_{data_name}.txt")))
        self.reformatted_database = {}

    def __call__(self):
        """
        Create a json file for place that contains all the information across time from the standardised data
        """

        for call_index, place in enumerate(self._std.matcher.values(), 1):
            if call_index % 100 == 0:
                print(f"{call_index} / {len(self._std.matcher.values())}")

            # Set the output stub for this place's json database
            place_data = {"GID": place.gid}

            # Isolate any data pertaining to this place from this file and add them to the place_data dict
            for date in self._database:
                self._process_relation_data(date, place.name, place_data)

            self.reformatted_database[place.name] = place_data

        write_json(self.reformatted_database, self._write_directory, f"Relational_{self._data_name}")
        print(f"Finished at {terminal_time()}")

    def _process_relation_data(self, date: str, place: str, place_data: dict) -> None:
        """
        Set the attribute values to the date of this file's data.

        Each place should now be unique after going through the cleaning procedures. This isolates all the headers that
        are not places, and if they are not already, sets them as attributes to out json place_data dict. The values
        are then set in a date: value dict per attribute for the current date
        """
        # If this place does not exist at this date, return none and stop
        if place not in self._database[date]:
            return None

        # Add headers to the place data dict if it does not already exist
        for header in self._database[date][place].keys():
            if header not in place_data:
                place_data[header] = {}

        # Update the attributes, assigning them as floats if possible.
        for attribute, value in self._database[date][place].items():
            try:
                place_data[attribute][int(date)] = float(value)
            except ValueError:
                place_data[attribute][int(date)] = value
