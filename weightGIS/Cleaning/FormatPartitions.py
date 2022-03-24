from miscSupports import validate_path, load_yaml, load_json, directory_iterator, simplify_string, parse_as_numeric, \
    flatten
from csvObject import CsvObject, write_csv
from typing import Optional, Union
from pathlib import Path
import numpy as np
import re


class FormatPartitions:
    def __init__(self, root: Union[Path, str], out: Union[Path, str], merged_list: Union[Path, str],
                 population: Optional[Union[Path, str]], file_index: Optional[int] = None):
        self.root = validate_path(root)
        self.out = validate_path(out)
        self.merge_list = load_yaml(validate_path(merged_list))
        self.pop = self._load_population(population)
        self.file_indexer = file_index

    @staticmethod
    def _load_population(population_path):
        """Load the population if it was set"""
        if population_path:
            return load_json(population_path)
        return None

    def __call__(self):
        """Partition all files in root"""
        [self._partition_file(Path(self.root, file)) for file in directory_iterator(self.root)]

    def _partition_file(self, file_path: Path):
        """Partition a given file"""
        # Load the csv
        csv_obj = CsvObject(file_path, set_columns=True)

        # Isolate the {place names: Values} as a dict
        place_names = {simplify_string(row[0]): [
            parse_as_numeric(re.sub(r"\D", "", v), int) for v in row[1:]] for row in csv_obj.row_data}

        # Correct rows that require correction
        corrected_rows = flatten([self._correct_rows(place_names, merge, correction, csv_obj.file_name)
                                  for merge, correction in self.merge_list.items() if merge in place_names.keys()])

        # Construct the non-altered rows and add any corrected rows if required
        rows = [[name] + row for name, row in place_names.items() if name not in self.merge_list.keys()]
        if len(corrected_rows) > 0:
            rows = rows + corrected_rows

        # Write out
        write_csv(self.out, csv_obj.file_name, csv_obj.headers, rows)

    def _name_as_date(self, file_name: str):
        """Isolate the date from the filename via indexing if it was set"""
        if not self.file_indexer:
            return file_name
        else:
            return file_name[:self.file_indexer]

    def _correct_rows(self, place_names, merge, correction, file_name):
        """
        Correct a row that has multiple place names within by partitioning it by population if it exists or equally
        otherwise
        """
        # Isolate the merged rows from place_names as numpy array (for multiplication)
        merged_rows = np.array(place_names[merge])

        # Isolate the population, or equally divided each place equally if we do not have it
        pops, total = self._construct_pops(file_name, correction)
        if not total or total == 0:
            pops = self._inferred_population(merged_rows, merge, file_name, correction)

        # Construct a corrected row by splitting the merged_row for each place as a percentage of the total
        return [[c] + (merged_rows * (p / total)).tolist() for c, p in pops.items()]

    def _construct_pops(self, file_name: str, correction: dict):
        """Isolate the population if we have it, and total the population count; otherwise return None"""
        # If we do not have any population return None
        if not self.pop:
            return None, None

        # Isolate the population counts relevant for this year
        pops = {n: self.pop[f"{c}{self._name_as_date(file_name)}"]
                for c, n in zip(correction['Pops'], correction['Names'])}
        return pops, sum(pops.values())

    @staticmethod
    def _inferred_population(merged_rows, merge, file, correction):
        """If we do not have populations we can use to partition the total, just evenly divide the unemployment"""
        print(f"Warning: No Population found for {merge} in {file}: Each place set to equally be weighted")
        total = sum(merged_rows)
        return {n: total / len(correction['Names']) for n in correction['Names']}
