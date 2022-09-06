from miscSupports import validate_path, load_yaml, load_json, write_json, simplify_string, parse_as_numeric, flatten
from typing import Optional, Union
from csvObject import write_csv
from pathlib import Path
import numpy as np
import re


class FormatPartitions:
    def __init__(self, data_path: Union[Path, str], out: Union[Path, str], qc_directory: Union[Path, str],
                 merged_list: Union[Path, str], population: Union[Path, str], splitter: str,
                 file_index: Optional[int] = None, name_index: int = 1):

        self.out = validate_path(out)
        self.qc_directory = qc_directory
        self._database = load_json(validate_path(data_path))
        self.merge_list = load_yaml(validate_path(merged_list))
        self.pop = self._load_population(population)

        self.file_indexer = file_index
        self.splitter = splitter
        self.name_index = name_index
        self.headers = self._set_headers()

        self.merge_record = {date: [] for date in self._database.keys()}

    @staticmethod
    def _load_population(population_path):
        """Load the population if it was set"""
        if population_path:
            return load_json(population_path)
        return None

    def _set_headers(self):
        headers = [tuple(values.keys()) for place_values in self._database.values() for values in place_values.values()]
        headers = sorted(list(set(headers)))
        if len(headers) != 1:
            raise Exception(f"Expected to find a single set of headers, yet found {len(headers)}: {headers}")
        return ['place'] + list(headers[0]) + ['SID', 'SIDClass']

    def __call__(self):
        """Partition all files in root"""
        [self._partition_file(date, place_values) for date, place_values in self._database.items()]
        write_json(self.merge_record, self.qc_directory, 'Partitions')

    def _partition_file(self, date: str, place_values: dict):
        """Partition a given file"""
        # Isolate the {place names: Values} as a dict
        place_names = {simplify_string(place.split(self.splitter)[self.name_index]): {
            'values': [parse_as_numeric(re.sub(r"\D", "", v), int) for v in values.values()],
            'original': [f"{self.splitter}".join([p for p in simplify_string(place).split(self.splitter)][1:])]
            } for place, values in place_values.items()}

        # Correct rows that require correction
        corrected_rows = flatten([self._correct_rows(place_names[merge]['values'], merge, correction, date)
                                  for merge, correction in self.merge_list.items() if merge in place_names.keys()])

        # Construct the non-altered rows and add any corrected rows if required
        rows = [row['original'] + row['values'] + [0, 0] for name, row in place_names.items()
                if name not in self.merge_list.keys()]
        if len(corrected_rows) > 0:
            rows = rows + corrected_rows

        # Write out
        write_csv(self.out, date, self.headers, rows)

    def _name_as_date(self, file_name: str):
        """Isolate the date from the filename via indexing if it was set"""
        if not self.file_indexer:
            return file_name
        else:
            return file_name[:self.file_indexer]

    def _correct_rows(self, merge_places, merge, correction, date):
        """
        Correct a row that has multiple place names within by partitioning it by population if it exists or equally
        otherwise
        """
        self.merge_record[date].append(merge)

        # Isolate the merged rows from place_names as numpy array (for multiplication)
        merged_rows = np.array(merge_places)

        # Isolate the population, or equally divided each place equally if we do not have it
        pops, total, data_class = self._construct_pops(merge, date, correction)

        # TODO: this might now be too specific...
        # Construct a corrected row by splitting the merged_row for each place as a percentage of the total. Note the
        # SID group and the class of partition
        return [[pop_name] + (merged_rows * (pop_values / total)).tolist() + [correction['sid'], data_class]
                for pop_name, pop_values in pops.items()]

    def _construct_pops(self, merge: str, file_date: str, correction: dict):
        """Isolate the population if we have it, and total the population count; otherwise return None"""
        # Isolation population date
        date = self._isolate_merge_date(correction, file_date, merge)

        # Isolate the population counts relevant for this year for this set of corrections
        pops = {name: self._assign_population(name, file_date, merge) for name in correction['dates'][date]['places']}

        # Return this population dict, the summation of the values, and the data class of this type
        return pops, sum(pops.values()), correction['dates'][date]['class']

    @staticmethod
    def _isolate_merge_date(correction, file_date, merge):
        """Isolate the last date we have a correction for"""
        try:
            return [date for date in correction['dates'].keys() if int(file_date) >= int(date)][-1]
        except IndexError:
            raise Exception(f"Failed to find a valid date for {merge} with {list(correction['dates'].keys())} for"
                            f" file data: {file_date}")

    def _assign_population(self, name, file_date, merge):
        """Attempt to assign the population, unless we lack a valid case, raise exception in that case"""
        try:
            return self.pop[f"{name}{self._name_as_date(file_date)}"]
        except KeyError:
            raise Exception(f"Failed to find a valid date for {merge} in file {file_date} split part: "
                            f"'{name} - {self._name_as_date(file_date)}'")
