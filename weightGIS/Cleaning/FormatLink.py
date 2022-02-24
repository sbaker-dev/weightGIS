from miscSupports import directory_iterator, write_json, terminal_time
from csvObject import CsvObject
from pathlib import Path


class FormatLink:
    def __init__(self, match_data):
        # Construct a GID: name matcher as in this case we already have formatted GIDs
        self.matcher = {match.gid: match.name for match in match_data.matcher.values()}

        # Initialise the database
        self.database = {}

    def __call__(self, data_dir, write_dir, database_name):
        [self._run(CsvObject(Path(data_dir, file)), i) for i, file in enumerate(directory_iterator(data_dir))]
        print(f"Linked Data {terminal_time()}")

        write_json(self.database, write_dir, f'Cleaned_{database_name}')
        print(f"Written Data {terminal_time()}")

    def _run(self, csv_file, index):
        """Link the data to the database"""
        file_name = csv_file.file_name
        if index % 100 == 0:
            print(f"Linked {index} files up to {file_name}")

        self.database[file_name] = {self.matcher[row[0]]: {h: row[i + 1] for i, h in enumerate(csv_file.headers[1:])}
                                    for row in csv_file.row_data}
