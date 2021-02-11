from miscSupports import directory_iterator
from csvObject import CsvObject, write_csv
from shapeObject import ShapeObject
from pathlib import Path
import re
import os


class PlaceReference:
    def __init__(self, working_directory, sub_unit_name="Sub_Unit", match_unit_name="Match_Unit"):
        self._working_dir = working_directory
        self._ambiguous = []
        self._cut_off = 100
        self._sub_name = sub_unit_name
        self._match_name = match_unit_name

    def link_places(self, sub_unit_directory, matching_unit_directory, sub_gid, sub_name, match_name, sub_type=None):
        """
        This will link to geo-levels together, files must have a numeric component and each sub_unit must be matched
        with a match-unit file with the same numeric component

        Example
        --------
        District and county shapefiles must have the dates within the names and there must be a matching shapefile for
        each district. So if you have 1931 districts you must have a 1931 county. The actual names doesn't matter as
        long as the dates match. Whilst the defaults column indexes for gid, name and type for districts and name for
        county may work, you should check it against the column indexes you have in your download.
        """

        # Reset ambiguous holder and load shapefiles
        self._ambiguous = []
        sub_units = self._load_shapefiles(sub_unit_directory)
        match_units = self._load_shapefiles(matching_unit_directory)

        # For each file we want to match
        for sub_file in sub_units:
            # Determine the current year for this sub unit and use it to load in the correct match file of the same year
            year = re.sub(r"[\D]", "", sub_file.file_name)
            match_file = self._set_match_file(match_units, year)

            # Set a match unit for each sub unit
            relations = [self._link_locations(place, rec, match_file, year, sub_gid, sub_name, sub_type, match_name)
                         for place, rec in zip(sub_file.polygons, sub_file.records)]

            # Once set, write out the relations for this district file then repeat
            headers = ["GID", f"{self._sub_name}"] + \
                      [f"{self._match_name}{i}" for i in range(max([len(relation) for relation in relations]) - 2)]
            write_csv(self._working_dir, f"{year}_relation", headers, relations)

        # If we have ambiguous relations we need to write those out
        if len(self._ambiguous) > 0:
            headers = ["Match_File", "GID", self._sub_name] + \
                      [f"{self._match_name}_{i}" for i in range(max([len(relation)
                                                                     for relation in self._ambiguous]) - 3)]
            write_csv(self._working_dir, "Ambiguous_Relations", headers, self._ambiguous)
            print(f"Please validate the {len(self._ambiguous)} ambiguous relations before proceeding by creating a file"
                  f"called 'SetAmbiguous.csv' where there is now only a single relation for each ambiguous link")
        else:
            print("No problems detected, please move to _write_linked_unique next but set ambiguity to False")

    @staticmethod
    def _set_match_file(match_files, year):
        """
        This takes a given list of match files and matches them against the same year of the county shape files
        and returns the ShapeObject object of the match.

        :param year: The current year
        :type year: str

        :return: Matching county ShapeObject
        :rtype: ShapefileHelper.ShapeObject.ShapeObject

        :raises IndexError: If no match is found
        """
        for match in match_files:
            if year == re.sub(r"[\D]", "", match.file_name):
                return match

        raise IndexError(f"Failed to find a match file for {year}")

    def _link_locations(self, place, rec, match_file, year, sub_gid, sub_name, sub_type, match_name):
        """
        Set the relationship for a given district to a county. If there is more than one county, append to a list so it
        can be fixed
        """
        county_overlaps = self._district_county_overlap(place, match_file, match_name)
        if sub_type:
            name = rec[sub_name] + rec[sub_type]
        else:
            name = rec[sub_name]

        if len(county_overlaps) > 1:
            self._ambiguous.append([year, rec[sub_gid], name] + county_overlaps)
            print(f"Ambiguous Relationship found for {name} in {year} for {self._match_name} {county_overlaps}")

        return [rec[sub_gid], name] + county_overlaps

    def _district_county_overlap(self, district_shape, county, county_name):
        """
        A district will be overlapped by a county, but it may have multiple relations which we would need to sort out
        manually. To construct the list of relations and check for ambiguity the system iterates through each polygon
        within a district and sees which county overlaps.

        :param district_shape: The current district shape

        :param county: The current county ShapeObject
        :type county: ShapeObject

        :return: County relationships for this given district
        """
        county_relationships = []
        for county, rec in zip(county.polygons, county.records):
            if district_shape.intersection(county).area > self._cut_off:
                if rec[county_name] not in county_relationships:
                    county_relationships.append(rec[county_name])
        return county_relationships

    def write_linked_unique(self, ambiguity=True, ambiguity_file_name="SetAmbiguous.csv"):
        """
        Load in the relation files, and construct the lookup

        :param ambiguity: If there is ambiguity in the file system
        :param ambiguity_file_name: THe name of the fix file
        """
        # Load the files for each shapefile that where written by link_districts_counties as well as the user ambiguous
        # file named ambiguity_file_name
        ambiguity_file = self._ambiguity_setter(ambiguity, ambiguity_file_name)
        relation_files = [CsvObject(f"{self._working_dir}/{file}")
                          for file in directory_iterator(self._working_dir) if "_relation" in file]

        # Construct a list of all the names without any ambiguity
        name_list = [self._fix_row_ambiguity(row, ambiguity_file, re.sub(r"[\D]", "", file.file_name))
                     for file in relation_files for row in file.row_data]

        # Construct the unique lists of districts, counties, and relationships
        unique_match = list(set([county for gid, district, county in name_list]))
        unique_sub = list(set([district for gid, district, county in name_list]))
        unique_relations = list({tuple(i) for i in name_list})

        # If the files do not already exist, to prevent the case where individuals keep their project files here so
        # overwriting may destroy work, write out
        if not os.path.isfile(f"{self._working_dir}/LookupBase.csv"):
            write_csv(self._working_dir, "LookupBase", ["GID", self._sub_name, self._match_name],
                      [list(relation) for relation in unique_relations])
        if not os.path.isfile(f"{self._working_dir}/Unique_{self._match_name}.csv"):
            write_csv(self._working_dir, f"Unique_{self._match_name}", [self._match_name], unique_match)
        if not os.path.isfile(f"{self._working_dir}/Unique_{self._sub_name}.csv"):
            write_csv(self._working_dir, f"Unique_{self._sub_name}", [self._sub_name], unique_sub)
        print("Finished Writing out base lookup")

    def _ambiguity_setter(self, ambiguity, ambiguity_file_name):
        """
        If there is ambiguity, load the fix file
        """
        if ambiguity:
            try:
                return CsvObject(f"{self._working_dir}/{ambiguity_file_name}")
            except FileNotFoundError:
                raise FileNotFoundError(f"Ambiguity specified but no fix file named {ambiguity_file_name} found")
        else:
            return None

    def _fix_row_ambiguity(self, row, ambiguity_file, year):
        """
        If there is any ambiguity in a row then it will have more than three entries, if the ambiguity file is correctly
        written then it will have 4 rows, and this method matches the conditions if they are correct and returns the
        row without any ambiguity
        """
        append_row = [r for r in row if r != ""]

        if len(append_row) == 3:
            return append_row
        else:
            ambiguity_row = self._get_ambiguous_row(ambiguity_file, row[0], year)
            if len(ambiguity_row) == 4:
                return ambiguity_row[1:]
            else:
                raise IndexError("Row should contain Date, GID, sub_unit_name, and matching name yet found length"
                                 f"{len(ambiguity_row)}")

    @staticmethod
    def _get_ambiguous_row(ambiguity_file, match, year):
        """
        Compare the year and row GID to the rows in the ambiguity file and return the match. Crash if fails
        """

        for row in ambiguity_file.row_data:
            if (match in row) and (year in row):
                return row

        raise IndexError(f"Failed to find a {match} file for {ambiguity_file.file_name}")

    def construct_reference(self, base_weights_name="LookupBase"):
        """
        Take in the base set of relations from the shapefiles, and a set of unique names of counties and districts, and
        construct a lookup file which allows our weighting program to find alternative names to the shapefiles names to
        ensure a match
        """
        base_relation = CsvObject(f"{self._working_dir}/{base_weights_name}.csv")

        alt_sub, sub_num = self._set_alternative(CsvObject(f"{self._working_dir}/Unique_{self._sub_name}.csv"))
        alt_match, match_num = self._set_alternative(CsvObject(f"{self._working_dir}/Unique_{self._match_name}.csv"))

        reformat = [self._assign_alternative(row, alt_sub, sub_num, alt_match, match_num)
                    for row in base_relation.row_data]

        header = base_relation.headers[:2] + [f"Alt_{self._sub_name}_{i + 1}" for i in range(sub_num - 1)]
        header = header + base_relation.headers[2:3] + [f"Alt_{self._match_name}_{i + 1}" for i in range(match_num - 1)]
        write_csv(self._working_dir, "PlaceReference", header, reformat)

    @staticmethod
    def _set_alternative(alt):
        """
        Extract alternative names from a list of type [base_name, possible alternative1, ...possible alternativeN)

        :param alt: Alternative names, such as county or districts, CsvObjected
        :return: standardised list of alternative names if there are alternative names in the file, None otherwise
        :rtype: list or None
        """
        if len(alt.column_data) > 1:
            alt_names = [[r for r in row if r != ""] for row in alt.row_data if len([r for r in row if r != ""]) > 1]
            name_lengths = [len(name) for name in alt_names]
            alt_places = [r + ["" for _ in range(max(name_lengths) - len(r))] for r in alt_names]
            return alt_places, max([len(d) for d in alt_places])
        else:
            return [[row] for row in alt.column_data[0]], 1

    def _assign_alternative(self, row, alt_sub_unit, sub_unit_length, alt_match, match_num):
        """
        Assign alternative sub-units and match units for the current row
        """
        current_row = self._construct_row(alt_sub_unit, row, sub_unit_length, 1)
        return self._construct_row(alt_match, current_row, match_num, 2 + sub_unit_length - 1)

    @staticmethod
    def _construct_row(alt_names, current_row, length_of_alt, row_index):
        """
        Look for a match within alternative names. If there is no match just return the row with a set of blanks equal
        to the max length of alternative names
        """

        for r in alt_names:
            if current_row[row_index] in r:
                return current_row[:row_index] + r + current_row[row_index + 1:]

        return current_row[0:row_index + 1] + ["" for _ in range(length_of_alt - 1)] + current_row[row_index + 1:]

    @staticmethod
    def _load_shapefiles(path):
        """
        Load the shapefiles into memory
        """
        return [ShapeObject(f"{path}/{file}") for file in directory_iterator(path) if Path(path, file).suffix == ".shp"]
