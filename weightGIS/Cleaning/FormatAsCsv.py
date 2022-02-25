from miscSupports import flatten, terminal_time, load_json, validate_path
from csvObject import write_csv
from typing import List, Union
from pathlib import Path


class FormatAsCsv:
    def __init__(self, database_path: [Path, str]):
        print("...Loading")
        self.database = load_json(validate_path(database_path))

        self._attrs = self._set_headers()
        self._dates = self._set_unique_dates()

    def __call__(self, working_directory: Union[Path, str], write_name: str):
        """Reformat a database into a csv"""
        print("...Isolating")
        row_data = flatten([self._extract_place(place, p_values)
                            for place, p_values in zip(self.database.keys(), self.database.values())])

        write_csv(working_directory, write_name, ['GID', 'Place', 'Date'] + self._attrs, row_data)
        print(f"...Finished {write_name} at {terminal_time()}")

    def _set_headers(self) -> List[str]:
        """Extract the unique headers that exist in all locations"""
        return sorted(list(set(flatten([list(v.keys()) for v in self.database.values()]))))

    def _set_unique_dates(self) -> List[str]:
        """Extract the unique dates"""
        dates = flatten([flatten([list(vv.keys()) for kk, vv in v.items() if kk != 'GID'])
                         for v in self.database.values()])
        return sorted(list(set(dates)))

    def _extract_place(self, place: str, p_values: dict) -> List[List[str]]:
        """Extract the place, and the attribute values, for that place"""
        return [self._format_names(place, date) + [self._extract_value(attr, date, p_values) for attr in self._attrs]
                for date in self._dates]

    @staticmethod
    def _format_names(place: str, date: str) -> List[str]:
        """For the CSV, split the GID / place name into their own columns"""
        place_names = place.split("__")
        return [place_names[0], "_".join([p for i, p in enumerate(place_names) if i != 0]), date]

    @staticmethod
    def _extract_value(attr, date, p_values) -> str:
        """Extract the value if present, else return NA"""
        if (attr in p_values.keys()) and (isinstance(p_values[attr], dict) and (date in p_values[attr].keys())):
            return str(p_values[attr][date])
        else:
            return 'NA'
