from miscSupports import directory_iterator, find_duplicates, chunk_list, write_json
from csvObject import CsvObject, write_csv
from multiprocessing import Process
from pathlib import Path
import numpy as np
import re


class FormatExternal:
    def __init__(self, place_reference, data_name, correction_path=None, cpu_cores=1, splitter="__", name_index=0,
                 place_map=None):
        # Set the standardised name reference from a path to its csv
        assert Path(place_reference), "Path to place reference not valid"
        self._reference = CsvObject(place_reference)

        # The name for this particular sub set of data
        self._data_name = data_name

        # Number of cores to use for multi-core enabled methods
        self._cpu_cores = cpu_cores

        # Match lists to standardise names to, set the number of match types, -1 is from removing GID
        self._matcher, self._reference_types = self._construct_match_list()
        self._match_types = len(self._matcher[0]) - 1

        # If there is a correction file, validate it exists, then load it; else None.
        if correction_path:
            self._corrections = self._set_corrections(correction_path)
        else:
            self._corrections = None

        # How to break names into chunks and the column index of names in the reformatted data
        self._splitter = splitter
        self._name_index = name_index

        if place_map:
            # If names need to be remapped then assert there are as many maps as places in the matcher
            assert self._match_types == len(place_map)
            self.order = place_map
        else:
            # Otherwise set the place_map to be just an ordered list of ints of range equal to the place types
            self.order = [i for i in range(len(self._matcher[0]) - 1)]

    def _construct_match_list(self):
        """
        Take the relations provided in the place reference and construct lists of matches for each place type to match
        names against

        :return: A list of lists, where sub lists contain the gid of the place, and then sub lists of strings for each
            place type
        """

        # Isolate the place types within the reference file
        reference_types = [header for header in self._reference.headers if "GID" not in header and "Alt" not in header]
        reference_types = [header.split("_Name")[0] for header in reference_types]

        # Set the indexes for each area
        type_indexes = [[index for index, header in enumerate(self._reference.headers) if area in header]
                        for area in reference_types]

        validation = []
        for place in self._reference.row_data:
            validation.append([place[0]] + [self._place_type_names(place, place_type) for place_type in type_indexes])

        return validation, ["GID"] + reference_types

    def _place_type_names(self, place, indexes):
        """
        Isolates all the valid names for this place type

        :param place: The current place we want to find equivalent names for
        :type place: str

        :param indexes: A list of indexes that represents the columns to isolate for this row that are valid for this
            place type
        :type indexes: list

        :return: A list of all the valid places for this type
        :rtype: list
        """
        return [self._simplify_string(place[i]) for i in range(min(indexes), max(indexes) + 1) if place[i] != ""]

    @staticmethod
    def _simplify_string(string_to_simplify):
        """
        strip a string of all non alphanumeric characters, white space, as well as underscore

        :param string_to_simplify: String to simplify
        :type string_to_simplify: str

        :return: String stripped of all non alphanumeric characters, white space and underscores
        :rtype: str
        """
        # This seems rather specific?
        string_to_simplify = string_to_simplify.replace("&", "and")
        return re.sub(r"[\W_\s]", "", string_to_simplify).lower()

    def _set_corrections(self, correction_path):
        """
        Set the correction list for changing names after reformatting

        This is designed to change names when names occur via spelling mistakes in the original source material. You
        could clean these in the reformatting stage, but if you have multiple dataset's where the spelling errors occur
        but the formatting is different then this allows for a standardised approach to fixing the error.

        :param correction_path: A path to the correction file, which contains as many rows as twice the number of types,
            + 1 for the operator column.
        :type correction_path: str | Path

        :return: A list of length match_type + 1, where the addtional is from the operator column so we know to delete
            or replace a value.
        """

        # Load the data into memory
        assert Path(correction_path).exists(), "Path to corrections not valid"
        correction_data = CsvObject(correction_path)

        # Assert there are as many rows as twice the number of types, + 1 for the operator column
        assert (self._match_types * 2) + 1 == correction_data.row_length

        # Create the original, correction rows
        original_i, new_i = [[i * self._match_types, (i * self._match_types) + self._match_types] for i in range(2)]

        correction_list = []
        for row in correction_data.row_data:
            # Isolate the original names and the replacements
            originals = [self._simplify_string(name) for name in row[original_i[0]:original_i[1]]]
            corrections = [self._simplify_string(name) for name in row[new_i[0]:new_i[1]]]

            # Append this to a list with the operator column; the last one hence -1
            correction_list.append([originals, corrections, row[-1]])

        return correction_list

    def standardise_names(self, data_directory, write_directory):
        """
        Standardise each place name to a single name if it has multiple

        If working with time series data places may change their names over time which can lead to a lot of merge errors
        or difficulty in linking data. This will standardise all names to a single entry, ensuring that regardless of
        the actual name of the place in that year that all data from that place is grouped to a single entry.

        :param data_directory: Directory containing csv files named in a yyyymmdd format
        :type data_directory: Path | str

        :param write_directory: Output directory
        :type write_directory: Path | str

        :return: Nothing, write out the data for each file found in the data_directory and then stop
        :rtype: None
        """
        for file in directory_iterator(data_directory):
            print(file)

            # Load the data into memory.
            data = CsvObject(Path(data_directory, file), set_columns=True)

            # Standardise the name via the matcher
            rows = []
            for i, name in enumerate(data.column_data[self._name_index], 0):
                reformatted = self._convert_names(name, i, data)
                if reformatted:
                    rows.append(reformatted)

            # Set the headers of the output file then write the file of the same name to the write_directory
            headers = self._reference_types + data.headers[1:]
            write_csv(write_directory, data.file_path.stem, headers, rows)

    def _convert_names(self, name, index, data):
        """
        Convert a name to a standardised representation from _matcher loaded via a PlaceReference output file

        Names may not be standardised over time. Names are stored in the reformatted file with a _splitter separating
        the geo-levels. The names are split, stripped of all non-characters and set to be lower case. The names are
        then correct for spelling or deletion requests if required via _corrections. If the data is not deleted, we then
        look to match the name to our reference. If we do so successfully, then the name is merged with the row_data and
        then return; otherwise a IndexError from _match_to_reference will be raised.

        :param name: Current place name
        :type name: str

        :param index: Current row index for parsing out the row_data
        :type index: int

        :param data: The csvObject of the current file
        :type data: CsvObject

        :return: The row's standardised names with GID and the row_data in a list
        :rtype: list
        """
        # Split the names on the _splitter and order them based on the original order or that provided by the user.
        ordered_names = np.array(name.split(self._splitter))[self.order].tolist()

        # Simplify each name
        simplified = [self._simplify_string(name) for name in ordered_names]

        # Isolate the row data for this file
        row_data = [row for i, row in enumerate(data.row_data[index]) if i != self._name_index]

        # Correct the names if required
        place_names = self._correct_data(simplified)
        if place_names:
            # If we are not deleting the row, standardise the names
            return self._match_to_reference(place_names) + row_data
        else:
            return None

    def _correct_data(self, simplified):
        """
        Correct or delete the names if required

        If corrections are required, validate that the name is not within the correction list. If it is and it's flag
        is set to FALSE, then accept the correction name. If it is match to the corrections but the FLAG is not FALSE
        (Ideally set to TRUE) then it will return None and this entry will not be brought across.

        :param simplified: Simplified names
        :type simplified: list

        :return: The original names if corrections are not set, or if the current names where not matched. If matched
            and flag of FALSE it returns the correction names from the correction file. Otherwise None
        :rtype: list | None
        """
        if self._corrections:
            for errors, corrections, flag in self._corrections:
                if simplified == errors:
                    if flag == "FALSE":
                        return corrections
                    else:
                        return None

            return simplified
        else:
            return simplified

    def _match_to_reference(self, place_names):
        """
        Match the place to a PlaceReference from _matcher.

        This will iterate though each row in the matcher until it finds a match for all place types and then return the
        first element of the reference as the standardised name. Raises and IndexError if it fails.

        :param place_names: The simplified and corrected place names for this place
        :type place_names: list

        :return: The standardised place names for this place
        :rtype: list

        :raises IndexError: If the place names are not successfully matched.
        """
        for row in self._matcher:

            # See if we can match each place type to a a group in an a given row in the matcher.
            checked_row = [True if match in match_group else False for match, match_group in zip(place_names, row[1:])]

            # If all are true, isolate the first element as the standardised name.
            if all(checked_row):
                return self._set_standardised_place(row)

        # If we fail raise an index error
        raise IndexError(f"{place_names} was not matched. Please update your Place Reference file accordingly.")

    @staticmethod
    def _set_standardised_place(place_groups):
        """Extract the GID from the first entry, and the first name of each group for all others"""
        return [place if i == 0 else place[0] for i, place in enumerate(place_groups)]

    def solve_ambiguity(self, standardised_directory, write_directory):
        """
        Remove perfect duplicates and combine non perfect duplicates so that all GIDs are unique.

        Some places may end up being duplicated, in the raw data or after standardisation. This method will remove
        perfect duplicates, and combine non perfect duplicates into a single entry. Keep in mind, that if this is not
        desirable, that the system will print out each non-perfect duplication merge it has done. You may wish to alter
        your original data set, or change your place reference to avoid this from happening.

        :param standardised_directory: The data directory of the output from standardise_names
        :type standardised_directory: str | Path

        :param write_directory: The output directory
        :type write_directory: str | Path
        """
        for file in directory_iterator(standardised_directory):
            print(file)

            # Load the original file and look for duplicate GIDs; which should be unique
            data = CsvObject(Path(standardised_directory, file), set_columns=True)
            duplicate_list = find_duplicates(data.column_data[0])

            # Isolate any row that does not suffer from duplication as the base of the write return
            reset_row = [row for row in data.row_data if row[0] not in duplicate_list]

            for dup in duplicate_list:
                # Isolate the row names
                row_names = data.row_data[data.column_data[0].index(dup)][:len(self._reference_types)]

                # Isolate the values for each duplicate name
                sub_list = [[float(rr) for rr in r[len(self._reference_types):]] for r in data.row_data if dup == r[0]]

                # Isolate unique lists, to remove duplicates
                unique_sub_lists = [list(x) for x in set(tuple(x) for x in sub_list)]

                # Warn the user that some values have been combined.
                if len(unique_sub_lists) > 1:
                    print(f"Found and combined multiple entries that where not perfect duplicates for {row_names}")

                # Add the combined values or singular entry of duplicate values to the reset list
                reset_row.append(row_names + [sum(i) for i in zip(*unique_sub_lists)])

            write_csv(write_directory, data.file_path.stem, data.headers, reset_row)

    def relational_database(self, cleaned_directory, write_directory):
        """
        Create a json file for place that contains all the information across time from the standardised data via sub
        processing to speed up the process. Loads the names from the PlaceReference file set to _matcher

        At present we have multiple files, one file for each entry of data. This method will standardise all the data
        from a given place into a single dict so that we can easily combine multiple dataset's.

        Note
        ----
        This is normally quite a slow process, hence allow for multi-core functionality, but also it will NOT over-write
        files. This is so you can fix smaller areas and not have to regenerate the whole list. Keep in mind therefore
        that if you do wish to re-run the program you will need an empty write_directory.

        :param cleaned_directory: The files that have been standardised and then checked for ambiguity
        :type cleaned_directory: Path | str

        :param write_directory: The output directory
        :type write_directory: Path | str

        :return: Nothing, write each json file out and then stop
        :rtype: None
        """

        chunked = chunk_list([i for i in range(len(self._matcher))], int(len(self._matcher) / self._cpu_cores))
        processes = [Process(target=self.relational_subprocess,
                             args=(index_list, index, cleaned_directory, write_directory))
                     for index, index_list in enumerate(chunked, 1)]

        for process in processes:
            process.start()

        for process in processes:
            process.join()

    def relational_subprocess(self, index_list, index_of_process, data_directory, write_directory):
        """
        This sub process is run via a call from relational_database via Process

        Each process is set a sub selection of indexes from the PlaceReference loaded into _matcher. Each process will
        then isolate this name and create a output json database for it by extracting any matching entries attributes
        from the data directory.

        :param index_list: A list of indexes to load from the PlaceReference for this process
        :type index_list: list[int]

        :param index_of_process: Which process thread this is
        :type index_of_process: int

        :param data_directory: Load directory the of standardised, cleaned, and correct data
        :type data_directory: str | Path

        :param write_directory: Write Directory for the json database
        :type write_directory: str | Path

        :return: Nothing, write a json database for each location that has been indexed from the PlaceReference.
        :rtype: None
        """

        # Currently processed files in the output directory
        current_files = [f for f in directory_iterator(write_directory)]

        for call_index, place_index in enumerate(index_list, 1):
            print(f"{call_index} / {len(index_list)} for process {index_of_process}")

            # Create the unique name from the groups and isolate the gid for parsing the csv
            unique_name = "__".join(self._set_standardised_place(self._matcher[place_index]))
            gid = self._matcher[place_index][0]

            # Set the output stub for this place's json database
            place_data = {"Place_Name": unique_name, "GID": gid}

            # If the data has not already been processed
            if self._not_processed(unique_name, current_files):
                for file in directory_iterator(data_directory):

                    # Load the data into memory
                    data = CsvObject(Path(data_directory, file), set_columns=True)

                    # Isolate any data pertaining to this place from this file and add them to the place_data dict
                    self._process_relation_data(data, gid, place_data)

                write_json(place_data, write_directory, f"{unique_name}_{self._data_name}")

    def _not_processed(self, unique_name, current_files):
        """
        If a file doesn't exist, then we want to process it.
        """
        if f"{unique_name}_{self._data_name}.txt" not in current_files:
            return True
        else:
            print(f"Already processed {unique_name}")

    def _process_relation_data(self, data, gid, place_data):
        """
        Set the attribute values to the date of this file's data.

        Each place should now be unique after going through the cleaning procedures. This isolates all the headers that
        are not places, and if they are not already, sets them as attributes to out json place_data dict. The values
        are then set in a date: value dict per attribute, where the date is isolated from the data's filename.

        :param data: A CsvObject of the current file's data
        :type data: CsvObject

        :param gid: The unique number for this location

        :param place_data: Output json data dict
        :type place_data: dict

        :return: Nothing, update the json data dict's attributes then stop or do not process if the place is not present
        :rtype: None

        :raises KeyError: If the gid is not unique
        """

        # Isolate the non place name headers to be used as attribute keys
        header_keys = data.headers[len(self._reference_types):]

        # Count the occurrences of the GID
        gid_count = data.column_data[0].count(gid)

        # If it happens more than once, raise an KeyError as it should be unique
        if gid_count > 1:
            raise KeyError(f"ERROR: {gid} found twice in {data.file_name}")

        # If it is less than 1 then return none and stop, this place doesn't exist at this point in time
        elif gid_count < 1:
            return None

        # Otherwise extract the data for this place.
        else:
            # Add headers to the place data dict if it does not already exist
            for header in header_keys:
                if header not in place_data:
                    place_data[header] = {}

            # Isolate the data from this file relating to this GID
            row_isolate = data.row_data[(data.column_data[0].index(gid))][len(self._reference_types):]

            # Update the attributes, assigning them as floats if possible.
            for attribute, value in zip(header_keys, row_isolate):
                try:
                    place_data[attribute][int(data.file_path.stem)] = float(value)
                except ValueError:
                    place_data[attribute][int(data.file_path.stem)] = value
