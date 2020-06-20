import json
from csvObject import CsvObject, write_csv


class AssignWeights:
    def __init__(self, weights_path, dates_path, shapefile_years, write_directory, file_name):
        """
        This class contains the methods needed to actually assign the weights to a usable database

        :param weights_path: The path to the bases weights calculated via ConstructWeights
        :param dates_path: The path to the dates of changes
        :param shapefile_years: A list of type year month day, (yyyymmdd) eg [19511231], that represents the time period
            of each shapefile
        :param write_directory: The directory to write too
        :param file_name: The name of the file to write
        """
        self.weights, self.dates = self._load_data(weights_path, dates_path)
        self.dates_indexes = self._set_date_indexes()
        self.shapefile_years = shapefile_years
        self.write_directory = write_directory
        self.file_name = file_name

    def assign_weights(self):
        """
        This takes all the weights that have occurred, and a file given by the user that contains information on when
        places change in terms of dates, and writes out the weights by the dates they occur.

        :return: Nothing, just write out the file
        :rtype: None
        """

        weights_list = []
        for place_over_time in self.weights:
            # Extract the place information
            gid, district = place_over_time[0][:2]

            # Determine if any changes occur to this place
            changes = self._extract_relevant_changes(gid)
            if len(changes) == 0:
                # If there are no changes just extract the first entry and add the min census year as it is always valid
                weights_list.append([gid, district] + [[min(self.shapefile_years)] + place_over_time[0][2:]])
            else:
                # else we need to write out the weights that we observe by the date of the observed change
                weights_list.append([gid, district] + self._assigned_dates_to_weights(
                    place_over_time, self._observed_dates(changes)))

        with open(f"{self.write_directory}/{self.file_name}.txt", "w", encoding="utf-8") as json_saver:
            json.dump(weights_list, json_saver, ensure_ascii=False, indent=4, sort_keys=True)

    def _set_date_indexes(self, ref_name="Changes"):
        """
        This just isolates the columns within the dates csv that have dates within them and returns a list of indexes
        where each index is a respective column.

        :param ref_name: The common name within the dates columns to isolate them
        :type ref_name: str

        :return: List of indexes, where each index is a column to load
        :rtype: list
        """
        return [index for index, head in enumerate(self.dates.headers) if ref_name in head]

    def _extract_relevant_changes(self, current_gid, passer="-"):
        """
        If the GID is within the a given row of data from dates file then we want to extract the date columns from that
        row by using the dates_indexes as an indexer. The format that is used is yyyymmdd so we then want to invert
        these proper dates and only keep the ones that are within the range of our census years

        :param current_gid: The current GID of the current place
        :type: str

        :param passer: The character used as the blank
        :type passer: str

        :return: A list of relevant dates of changes in the format of [yyyymmdd, ... yyyymmdd]
        :rtype: list
        """
        changes = [place[i] for place in self.dates.row_data if str(current_gid) in place for i in range(len(place))
                   if i in self.dates_indexes and place[i] != passer]

        return [int(c) for c in self._invert_dates(changes)
                if min(self.shapefile_years) <= int(c) <= max(self.shapefile_years)]

    def _observed_dates(self, changes):
        """
        Multiple changes can occur in a census period but only the latest can be observed. This groups the changes by
        census period and the returns a list of dates that can actually be observed

        :param changes: list of changes in yyyymmdd format
        :type changes: list

        :return: A list of observed dates in the form of [yyyymmdd ... yyyymmdd]
        :rtype: list
        """

        census_year_groupings = []
        for change_date in changes:
            for index in range(len(self.shapefile_years)):
                if (self.shapefile_years[index] < change_date <= self.shapefile_years[index + 1]) and \
                        (index < len(self.shapefile_years) - 1):
                    census_year_groupings.append([self.shapefile_years[index + 1], change_date])

        return self._select_latest(census_year_groupings)

    @staticmethod
    def _select_latest(grouped_census_dates):
        """
        This will selected the latest year between a given census period, as only the latest can be observed in the
        shapefile

        :param grouped_census_dates: List of dates in the form of [[census_year, date]] where both dates are in yyyymmdd
        :type grouped_census_dates: list

        :return: A list of observed dates in the form of [yyyymmdd ... yyyymmdd]
        :rtype: list
        """
        memory = []
        observed_dates = []
        for census_year, date in grouped_census_dates:
            if census_year not in memory:
                memory.append(census_year)
                observed_dates.append(max([match_date for match_year, match_date in grouped_census_dates
                                           if match_year == census_year]))

        return observed_dates

    @staticmethod
    def _invert_dates(dates_list, delimiter="/"):
        """
        Returns dates in an inverted manner as dates may be in a ddmmyyyy but we need it to be yyyymmdd so this
        reorganises them.

        :param dates_list: List of dates to invert
        :type dates_list: list[str]

        :return: list of inverted dates
        :rtype: list[str]
        """
        return [date.split(delimiter)[2] + date.split(delimiter)[1] + date.split(delimiter)[0] for date in dates_list]

    @staticmethod
    def _load_data(weights_path, dates_path):
        """
        Load the data into memory
        """
        with open(weights_path) as j:
            weights = json.load(j)

        return weights, CsvObject(dates_path)

    def _assigned_dates_to_weights(self, place_over_time, dates_observed):
        """
        Purpose
        --------
        This assigns the date to the change that has been observed in the shapefile.

        Example
        -------
        | For a given shape that represents a region, lets call it Otley, we have 4 census year shapefiles we observe
         in 1931, 1951, 1961 and 1971. We want to weight on 1951 so we take that year as our reference and apply this to
         the other years and we get the following weights based on our reference in 1951:
        |
        | A [01, "OTLEY_UD", [01, "OTLEY_UD", 60, 60], [00, "AIREDALE_RD", 20, 50]
        | B [01, "OTLEY_UD", [01, "OTLEY_UD", 100, 100]"
        | C [01, "OTLEY_UD", [01, "OTLEY_UD", 90, 78], [02, "BRADFORD_CB, 10.2, 1.4]"
        | D [01, "OTLEY_UD", [01, "OTLEY_UD", 70, 40], [02, "BRADFORD_CB, 15, 3]"
        |
        | Now by loading in our dates file we know that changes to OTLEY's structure occurred in 1934, 56, 62 and 65.
         However, we can only observe the last change that occurs within a shapefile, as constructed by
         construct_observed_dates, so only 1934, 56, and 65 will be used. Regardless of which reference year is chosen,
         the system works chronologically for this process.
        |
        | The first Census year is 1931, given it is not our reference year it does not need to be 100% weight, and as
         such the weight for our 1951 shape in 1931 can be of multiple places. The weight we observe in this case is
         the weight before any changes have occurred as its the first observable date in our sample. As such it is
         always loaded by taking index = 0 and setting the 'change' date to the first census year.
        |
        | From this point forth changes may have occurred. The 1934 change is the last change that occurs between the
         1931 shapefile and the 1951 shapefile. So the weights we observe in 1951, are the reflection of the change that
         occurred in 1934. By searching dates with index-1, we are isolating the 1931, with index calling 1951.So we use
         index to then parse the correct observed weights from our place_over_time to this date.
        |
        | This then continues. So in this case B's weight is applied to the date of 1934, C's weight to 1956 and D's
         weight to 1965; as we cannot observe the change that occurs in 1962. The constructed weight for our reference
         shape is therefore going to take the form of the following
        |
        | [01, "OTLEY_UD", [19310401, [01, "OTLEY_UD", 60, 60], [00, "AIREDALE_RD", 20, 50]]...[date_of_change,
          [WeightA, WeightB]]

        Parameters
        ----------
        :param dates_observed: The dates that we observed for this place
        :type dates_observed: list

        :param place_over_time: The current Places weight changes from census years
        :type place_over_time: list

        :return: A list for all the weights changes that occur to a given place by the date of which the change occurs
            in the form of list[date1[gid, district_name, area_weight, pop_weight]... dateN[gid, district_name,
             area_weight, pop_weight]]
        :rtype: list
        """

        weights_by_date = []
        for index, weight in enumerate(place_over_time):
            if index == 0:
                weights_by_date.append([min(self.shapefile_years)] + place_over_time[index][2:])
            else:
                for date in dates_observed:
                    if self.shapefile_years[index - 1] < date <= self.shapefile_years[index]:
                        weights_by_date.append([date] + place_over_time[index][2:])

        return weights_by_date


def write_out_changes(weights_path, write_out_path, name_class=True):
    """
    To be able to write the weight file we need to know when the changes occur, not just how many changes occur. To
    do this we need a list of names and the expected number of changes. The assumption is, that a place will not
    change more than once between census years but when this is not the case we need to be explict about this so we
    can work of the change manually if need be.

    :param weights_path: The weights that have been calculated for the base shape
    :type weights_path: str

    :param write_out_path: The path to write the file to
    :type write_out_path: str

    :param name_class: If names have additional information associated with them
    :type name_class: bool

    :return: Nothing, just write out the csv file with the number of expected changes and support search terms
    :rtype: None
    """

    # Load the weights
    with open(weights_path) as j:
        base_weights = json.load(j)

    # if our unit have a class, then we need to write out this information
    if name_class:
        headers = ["GID", "Place_Name", "Place_Type", "Expected Changes"]
    else:
        headers = ["GID", "Place_Name", "Expected Changes"]

    write_holder = []
    for weight_group in base_weights:

        # Find all the unique changes, long panel data may have lot's of duplication if district's don't change
        non_duplication = []
        for i in range(len(weight_group)):
            change_log = weight_group[i][2:]
            change_log.sort(key=lambda x: int(x[0]))
            if weight_group[i][:2] + change_log not in non_duplication:
                non_duplication.append(weight_group[i][:2] + change_log)

        # If there are more than three elements in the list then there are guaranteed to be changes, although if
        # individuals have allowed for changing exterior bounds it is also possible that the same district may be
        # smaller so we also need to just the 3rd element's area weight to see if it changed
        changes_from_base = []
        for unique_year_change in non_duplication:
            if len(unique_year_change) > 3 or unique_year_change[2][3] != 100:
                changes_from_base.append(unique_year_change)

        # Then write the information to a list to be written out on completion of the loop the information
        expect_number_of_changes = len(changes_from_base)
        if name_class:
            write_holder.append([non_duplication[0][0], non_duplication[0][1].split("_")[0],
                                 non_duplication[0][1].split("_")[-1], expect_number_of_changes])
        else:
            write_holder.append([non_duplication[0][0], non_duplication[0][1].split("_")[0], expect_number_of_changes])

    write_csv(write_out_path, "ChangeLog", headers, write_holder)
