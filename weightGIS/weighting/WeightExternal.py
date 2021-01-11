from miscSupports import load_json, write_json, flatten
from collections import Counter
from csvObject import write_csv
import sys


class WeightExternal:
    def __init__(self, external_data_path, weights_path, date_max, json_data=True):
        self.database, self.searcher, self.attributes = self._load_external(external_data_path, json_data)
        self._weights_dates = load_json(weights_path)
        self._user_end_date = date_max
        self._master = {}
        self._non_common = []

    def weight_external(self, write_path, write_name="Weighted"):
        """
        This will use all the places and weights from the weights be dates file, and use it to weight an external data
        source.
        """
        for place_name in self._weights_dates:
            print(place_name)

            # See how many changes exist for this place
            dates_range = [date for date in self._weights_dates[place_name].keys()]

            # If there is only one date, we have no weighting to do as the place remains unchanged from its first state
            if (len(dates_range) == 1) and self.extract_data(place_name):
                self._master[place_name] = self.extract_data(place_name)

            # Otherwise we need to weight the data, and potentially consider non-common dates across places
            else:
                self._master[place_name] = self._weight_place(place_name, dates_range)

        # Write out the weighted data
        write_json(self._master, write_path, write_name)
        if len(self._non_common) > 0:
            write_csv(write_path, "NonCommonDates", [], self._non_common)

    def _weight_place(self, place_name, dates_range):
        """
        If a place changes over time, then we need to weight data based on those changes. If there is only a single
        place, for example a place used to be 50% larger so in a previous change it represents 50% of the values, then
        we just need to weight all the values by that weight. If the place used to made up of multiple places, then we
        need to weight each place by that weight, and then sum the values. The later has more problems associated with
        it, as you need data in ALL of the places otherwise you end up with uncommon dates where you cannot weight a
        certain district because you don't have all the data you need.
        """
        place_dict = {attr: {"Dates": [], "Values": []} for attr in self.attributes}

        # For each change that occurs in this place
        for index, date in enumerate(dates_range, 1):

            # Set the date range for this change
            date_min, date_max = self._set_min_max_date(index, date, dates_range)

            # If there is only one place for this change, then we just need to weight the values relevant to the dates
            if len(self._weights_dates[place_name][date]) == 1:
                self._weight_single(place_name, date, place_dict, date_min, date_max)

            # Otherwise we have to make sure all places, have all dates, and sum weighted values appropriately .
            else:
                self._weight_multiple(place_name, date, place_dict, date_min, date_max)

        # Flatten the lists
        for attr in place_dict:
            place_dict[attr]["Dates"] = flatten(place_dict[attr]["Dates"])
            place_dict[attr]["Values"] = flatten(place_dict[attr]["Values"])

        return place_dict

    def _weight_single(self, place_name, date, place_dict, date_min, date_max):
        """
        If there is only a single place, then we don't need to worry about non-common dates across weight places and we
        can just weight the values of each attribute and append them to our place dict as long as the database contains
        information about this place
        """
        place, weight = self._extract_weight_place(self._weights_dates[place_name][date])

        # If the database contains information about this place, extract that information and set it against the
        # current place
        if self.extract_data(place):
            attr_values = [self.weight_attribute(attr, place, weight, date_min, date_max) for attr in self.attributes]

            for attr, dates, values in attr_values:
                place_dict[attr]["Dates"].append(dates)
                place_dict[attr]["Values"].append(values)
        else:
            print(f"Warning: No data found for {self._search_name(place)}")

    def _weight_multiple(self, place_name, date, place_dict, date_min, date_max):
        """
        If there are multiple places in this change peroid, then we need to extract the data and check that we have the
        same dates for each place in this change. If we do we can then just sum the weighted values to create a weighted
        value set that can be appended for each date.
        """

        # Extract the places and weights involved in this change
        places, weights = self._extract_weight_place(self._weights_dates[place_name][date])

        # Determine if we have data for each place
        all_valid = [self.extract_data(place) for place in places if self.extract_data(place)]

        # If we have data for both places
        if len(all_valid) == len(places):

            for attr in self.attributes:
                dates_list = self._extract_usable_dates(attr, date_min, date_max, places, weights)
                weight_values = [self._weight_summation(date, attr, places, weights) for date in dates_list]

                place_dict[attr]["Dates"].append(dates_list)
                place_dict[attr]["Values"].append(weight_values)

        else:
            print(f"Warning only found data for {len(all_valid)} of the expected {len(places)} places for "
                  f"{[self._search_name(place) for place in places]}")

    def _extract_usable_dates(self, attr, date_min, date_max, places, weights):
        """
        If we have multiple places, not all places may have the same dates. We cannot create a weighted value from
        multiple places if some of those places are missing. So in these cases, nothing is written to the dataset, and
        a line explaining what was missing is written out to a csv file.

        If we do have common dates dates for a given place, then we return these dates which will be indexed to extract
        the values associated with them
        """

        dates_list = [self.weight_attribute(attr, place, weight, date_min, date_max, dates_return=True)
                      for place, weight in zip(places, weights)]

        # Count each occurrence of a date to insure we have the same number in all places
        dates_dict = Counter(flatten(dates_list))

        # If we have any non_common dates, we can't use this date for weighting as we won't have data in all of the
        # places involved in the weight
        non_common_dates = [date for date in dates_dict if dates_dict[date] != len(places)]
        if len(non_common_dates) > 0:
            # Write out this information for users so they can fix their raw data
            self._non_common.append(flatten([[date, attr] + places for date in non_common_dates]))
            print(f"Warning: Non Common dates found for {attr} in {places}")

        # Return common dates list
        return sorted([date for date in dates_dict if date not in non_common_dates])

    def _search_name(self, place_name):
        """
        Extract the key from a place_name, and use that to get the data key from the using this place_name as key in the
        search_key dict
        """
        return self.searcher[place_name.split("__")[0]]

    @staticmethod
    def _extract_weight_place(date_data):
        """
        Extract the places and weights for a given date for a given place in weight_dates
        """
        weight_places = [place for place in date_data.keys()]
        weight_list = [weight for weight in date_data.values()]

        if (len(weight_places) == 1) and (len(weight_list) == 1):
            return weight_places[0], weight_list[0]
        else:
            return weight_places, weight_list

    def weight_attribute(self, attr, place, weight, date_min, date_max, dates_return=False, value_return=False):
        """
        For a given attribute, extract the attribute values and if they are between the min and max dates weight them.
        Return the attribute key, the dates of the weight values as a list, and the weighted value as a list

        NOTE
        ---------

        This is horrible, and needs refactoring
        """
        try:
            data = self.database[self._search_name(place)][attr]
            values = [self.calculate_weight(value, weight) for date, value in zip(data["Dates"], data["Values"])
                      if date_min <= int(date) < date_max]
            dates = [date for date in data["Dates"] if date_min <= int(date) < date_max]

            if not dates_return and not value_return:
                return attr, dates, values
            elif dates_return:
                return dates
            elif value_return:
                return values
            else:
                sys.exit("No valid return")

        except KeyError:
            values = []
            dates = []

            if not dates_return and not value_return:
                return attr, dates, values
            elif dates_return:
                return dates
            elif value_return:
                return values
            else:
                sys.exit("No valid return")

    def extract_data(self, place):
        """
        Check to see if the database contains a given place
        """
        try:
            return self.database[self._search_name(place)]
        except KeyError:
            return None

    @staticmethod
    def _load_external(database_path, json_data):
        """
        Load weights and external data
        """
        print("Loading External Data")
        if json_data:
            data = load_json(database_path)
            search_key = {place.split("__")[0]: place for place in data.keys()}
            attributes = list(set([attr for place in data.keys() for attr in data[place].keys()
                                   if isinstance(data[place][attr], dict)]))

        else:
            print("CSV DATA NOT YET INITALISED")
            sys.exit()

        return data, search_key, attributes

    def _set_min_max_date(self, index, date, dates_range):
        """
        If we have reached the last date provided, then set max date to be the max provided by the user, otherwise
        create a time period from the current date and the next date
        """
        if index < len(dates_range):
            return int(date), int(dates_range[index])
        else:
            return int(date), int(self._user_end_date)

    @staticmethod
    def calculate_weight(value, weight):
        """
        A weight value is equal to the value * (percentage weight / 100)
        """
        if isinstance(value, str):
            return value
        else:
            return value * (weight / 100)

    def _date_index(self, date, attr, place):
        """
        Use the date to extract the index position that date is in this places attribute, and the use that index to
        parse the value that is associated with it from values

        Note
        --------------
        The original data set was set as Dates list [] value_list [] but wouldn't it make more sense to have date: v?

        """
        return self.extract_data(place)[attr]["Values"][self.extract_data(place)[attr]["Dates"].index(date)]

    def _weight_summation(self, date, attr, places, weights):
        """
        Create a summed value from all the weights of the places
        """
        values = [self.calculate_weight(self._date_index(date, attr, p), w) for p, w in zip(places, weights)]

        if all(isinstance(v, (int, float)) for v in values):
            return sum(values)
        else:
            return "NA"
