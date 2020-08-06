import json
import sys


class WeightExternal:
    def __init__(self, external_data_path, weights_path, date_max, json_data=True):
        self.database, self.searcher, self.attributes = self._load_external(external_data_path, json_data)
        self._weights_dates = self._load_json(weights_path)
        self._user_end_date = date_max
        self._master = {}


    def weight_external(self):
        for place_name in self._weights_dates:
            print(place_name)
            # See how many changes exist for this place
            dates_range = [date for date in self._weights_dates[place_name].keys()]

            # If there is only one date, we have no weighting to do as the place remains unchanged from its first state
            if (len(dates_range) == 1) and self.check_database(self._search_name(place_name)):
                self._master[place_name] = self.check_database(self._search_name(place_name))

            # # Otherwise we need to weight the data, and potentially consider non-common dates across places
            # else:
            #     place_dict = {place_name: {attr: {"Dates": [], "Values": []} for attr in attributes}}
            #     for index, date in enumerate(dates_range, 1):
            #         date_min, date_max = self._set_min_max_date(index, date, dates_range, user_date_max)
            #
            #         # If there is only one place, then we just need to weight the values relevant to the dates
            #         if len(self._weights_dates[place_name][date]) == 1:
            #             self._single_weight(place_name, date, database, search_key, date_min, date_max, attributes,
            #                                 place_dict)
            #         # Otherwise we have to make sure all places, have all dates.
            #         else:
            #             places, weights = self._extract_weight_place(self._weights_dates[place_name][date])
            #
            #             print(date_min, date_max)
            #             print(self._weights_dates[place_name][date])
            #             print(places, weights)
            #             all_valid = [self.check_database(database, self._search_name(search_key, place)) for place in places
            #                          if self.check_database(database, self._search_name(search_key, place))]
            #
            #             # If we have data for both places
            #             if len(all_valid) == len(places):
            #                 for attr in attributes:
            #                     print(attr)
            #                     dates_list = [self.weight_attribute(attr, database, search_key, place, weight, date_min, date_max, dates_return=True)
            #                                   for place, weight in zip(places, weights)]
            #
            #                     value_list = [self.weight_attribute(attr, database, search_key, place, weight, date_min, date_max, value_return=True)
            #                                   for place, weight in zip(places, weights)]
            #
            #                     common_dates_dict = (Counter(self.flatten_list(dates_list)))
            #                     non_common_dates = [date for date in common_dates_dict if
            #                                         common_dates_dict[date] != len(places)]
            #
            #
            #
            #                     if len(non_common_dates) > 0:
            #                         print("Non Common Dates that need writing out here")
            #                     # todo if there are non common dates then we need to isolate dates that are not common
            #                     #  from the list.
            #
            #                     else:
            #                         # todo otherwise we need to use the common dates dict to extract a date. We probably
            #                         #  want to extract this from the database as that is a dict so we don't reconstruct
            #                         #  it for the sack of it
            #
            #                         for d, v in dates_list, value_list:
            #                             print(d)
            #                             print(v)
            #
            #                         break
            #
            #
            #
            #
            #
            #
            #
            #
            #
            #
            #
            #
            #     break

    def _single_weight(self, place_name, date, database, search_key, date_min, date_max, attributes, place_dict):
        """
        If there is only a single place, then we don't need to worry about non-common dates across weight places and we
        can just weight the values of each attribute and append them to our place dict as long as the database contains
        information about this place
        """
        place, weight = self._extract_weight_place(self._weights_dates[place_name][date])

        # If the database contains information about this place, extract that information and set it against the
        # current place
        if database[self._search_name(search_key, place)]:
            attribute_values = [self.weight_attribute(attr, database, search_key, place, weight, date_min, date_max)
                                for attr in attributes]

            for attr, dates, values in attribute_values:
                place_dict[place_name][attr]["Dates"].append(dates)
                place_dict[place_name][attr]["Values"].append(values)

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

    def weight_attribute(self, attr, database, search_key, place, weight, date_min, date_max, dates_return=False, value_return=False):
        """
        For a given attribute, extract the attribute values and if they are between the min and max dates weight them.
        Return the attribute key, the dates of the weight values as a list, and the weighted value as a list
        """
        attr_data = database[self._search_name(search_key, place)][attr]
        values = [self.construct_weight(value, weight) for date, value in zip(attr_data["Dates"], attr_data["Values"])
                  if date_min <= int(date) < date_max]
        dates = [date for date in attr_data["Dates"] if date_min <= int(date) < date_max]

        if not dates_return and not value_return:
            return attr, dates, values
        elif dates_return:
            return dates
        elif value_return:
            return values
        else:
            sys.exit("No valid return")

    def check_database(self, place):
        """
        Check to see if the database contains a given place
        """
        try:
            return self.database[place]
        except KeyError:
            return None

    def _load_external(self, database_path, json_data):
        """
        Load weights and external data
        """
        print("Loading External Data")
        if json_data:
            data = self._load_json(database_path)
            search_key = {place.split("__")[0]: place for place in data.keys()}
            attributes = list(set([attr for place in data.keys() for attr in data[place].keys()
                                   if isinstance(data[place][attr], dict)]))

        else:
            print("CSV DATA NOT YET INITALISED")
            sys.exit()

        return data, search_key, attributes

    @staticmethod
    def _set_min_max_date(index, date, dates_range, max_date):
        """
        If we have reached the last date provided, then set max date to be the max provided by the user, otherwise
        create a time period from the current date and the next date
        """
        if index < len(dates_range):
            return int(date), int(dates_range[index])
        else:
            return int(date), int(max_date)

    @staticmethod
    def construct_weight(value, weight):
        """
        A weight value is equal to the value * (percentage weight / 100)
        """

        return value * (weight / 100)

    @staticmethod
    def flatten_list(list_of_lists):
        """
        This is designed to flatten a list of lists into a single list

        :param list_of_lists: A list of other lists
        :type list_of_lists: list

        :return: A list with one level of sub-lists flattened
        :rtype: list
        """

        return [item for sublist in list_of_lists for item in sublist]

    @staticmethod
    def _load_json(path):
        """
        Load a json file at a given path
        """
        with open(path) as j:
            return json.load(j)
