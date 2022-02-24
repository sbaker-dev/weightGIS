from miscSupports import flatten, directory_iterator, terminal_time
from typing import List
from csvObject import CsvObject, write_csv
from pathlib import Path


class FormatCombine:
    def __init__(self, unique_id, data_start, root_directory, write_directory, date):
        print("Combining...")
        self.unique_id_index = unique_id
        self.data_start = data_start
        self.root = root_directory
        self.write_dir = write_directory
        self.date = date

        self.unique_ids = self._isolate_unique_ids()
        self.data_dicts = self._data_as_dict()
        self.data_lengths = self._data_lengths()

    def __call__(self):
        """Isolate the values for each unique location and save as a combined csv"""
        out_list = [[ids] + flatten(self._isolate_id_values(ids)) for ids in self.unique_ids]
        write_csv(self.write_dir, self.date, self._headers(), out_list)
        print(f"...Finished {terminal_time()}")

    def _isolate_unique_ids(self) -> List:
        """Isolate the unique ID column from each resource"""
        return sorted(list(set(flatten([CsvObject(Path(self.root, file), set_columns=True)[self.unique_id_index]
                                        for file in directory_iterator(self.root)]))))

    def _data_as_dict(self) -> dict:
        """Return the file: data as a dict"""
        return {file: self._file_as_dict(file) for file in directory_iterator(self.root)}

    def _file_as_dict(self, file: str) -> dict:
        """Construct the file dict as the uniqueID: row_data[data_start:]"""
        return {row[self.unique_id_index]: row[self.data_start:] for row in CsvObject(Path(self.root, file)).row_data}

    def _data_lengths(self) -> dict:
        """Isolate the length of each file for if we encounter missing data"""
        return {file: CsvObject(Path(self.root, file)).row_length for file in directory_iterator(self.root)}

    def _headers(self) -> List:
        """Isolate the headers for the file"""
        return ['GID'] + flatten([CsvObject(Path(self.root, file)).headers[self.data_start:]
                                  for file in directory_iterator(self.root)])

    def _isolate_id_values(self, ids: str) -> List:
        """Isolate any values that match ids in each of the files"""
        return [self._isolate(file, ids) for file in directory_iterator(self.root)]

    def _isolate(self, file:str, ids: str) -> List:
        """Isolate the row that match's the ID if it exists, else return an empty list"""
        try:
            return self.data_dicts[file][ids]
        except KeyError:
            return ["" for _ in range(self.data_lengths[file])]
