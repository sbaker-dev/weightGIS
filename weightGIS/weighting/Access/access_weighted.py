from miscSupports import flatten, terminal_time, load_json, validate_path
from csvObject import write_csv
from typing import List
from pathlib import Path


def access_weighted(data_extraction_set, data_requested):
    """
    This will use a set of keys to extract data from a weightGIS json database so that i can be written out or used in
    applications or processes.

    Note
    -----
    This requires the json dict to follow the weightGIS v0.9 or above json format of the following for each entry:

    gid__place: {attribute1: {date1:value1 ... dateN:valueN} ... attributeN: {date1:value1 ... dateN:valueN}

    :param data_extraction_set: The loaded json database
    :type data_extraction_set: dict

    :param data_requested: The attributes you would like to extract from each place
    :type data_requested: list

    """
    all_dates = []
    for place, attributes in zip(data_extraction_set.keys(), data_extraction_set.values()):
        place_dates = []

        # Isolate each elements keys, which should be the dates, as long as the data exists and is a dict
        for data in data_requested:
            if data in attributes.keys() and isinstance(attributes[data], dict):
                place_dates.append(list(attributes[data].keys()))

        all_dates.append(flatten(place_dates))

    common_dates = sorted(list(set(flatten(all_dates))))

    row_data = []
    for place, d_attr in zip(data_extraction_set.keys(), data_extraction_set.values()):

        # The place name will be a gid__place which we want to extract here
        place_names = place.split("__")
        gid, place = place_names[0], "_".join([p for i, p in enumerate(place_names) if i != 0])

        # Then for each date we setup our first two columns of place-date
        for date in common_dates:
            date_values = [gid, place, date]

            # And for each attribute requested, we extract the value if the date is valid, else NA
            for attr in data_requested:
                if (attr in d_attr.keys()) and (isinstance(d_attr[attr], dict) and (date in d_attr[attr].keys())):
                    date_values.append(d_attr[attr][date])
                else:
                    date_values.append("NA")
            row_data.append(date_values)

    print(f"Retrieved Weighted Data {terminal_time()}")
    return row_data


class DatabaseToCsv:
    def __init__(self, database_path: [Path, str]):
        print("...Loading")
        self.database = load_json(validate_path(database_path))

        self._attrs = self._set_headers()
        self._dates = self._set_unique_dates()

    def __call__(self, working_directory, write_name):
        print("...Isolating")
        row_data = [self._extract_place(place, p_values)
                    for place, p_values in zip(self.database.keys(), self.database.values())]

        write_csv(working_directory, write_name, ['GID', 'Place', 'Date'] + self._attrs, row_data)
        print(f"...Finished {terminal_time()}")

    def _set_headers(self) -> List[str]:
        """Extract the unique headers that exist in all locations"""
        return sorted(list(set(flatten([list(v.keys()) for v in self.database.values()]))))

    def _set_unique_dates(self) -> List[str]:
        """Extract the unique dates"""
        dates = flatten([flatten([list(vv.keys()) for kk, vv in v.items() if kk != 'GID'])
                         for v in self.database.values()])
        return sorted(list(set(dates)))

    def _extract_place(self, place: str, p_values: dict) -> List[str]:
        """Extract the place, and the attribute values, for that place"""

        return flatten([self._format_names(place, date) + [self._extract_value(attr, date, p_values)
                                                           for attr in self._attrs]
                        for date in self._dates])

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


if __name__ == '__main__':
    DatabaseToCsv(r"I:\Work\BIO-HGIS\Waves\Census1971\QCed\Census1971_Weighted.txt")(
        r"I:\Work\BIO-HGIS\Releases\BIO-HGIS-1.5", 'Census1971_Weighted')
