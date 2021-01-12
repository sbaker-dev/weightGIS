from miscSupports import load_json, write_json
from csvObject.csvWriter import write_csv


class AdjustWeights:
    def __init__(self, working_directory, weights_path):
        self._working_dir = working_directory
        self._weights = load_json(weights_path)

    def replace_assigned_weight(self, fixed_json_path, name):
        """
        In some situations you may find a complex problem or a mistake and want to replace a given place rather than
        have to - rerun the whole constructor. This allows you to replace a given place by its key in the base_weights
        file you made on all your data, and a new smaller update file. The changes between the update and the master
        will be logged and then the master file will be updated.
        """
        # Load the fix file
        fixed = load_json(fixed_json_path)

        # Create the restructured values for the named place
        key_list = self._replacement_keys(name, fixed)
        restructured = {str(year): self._replacement_values(fixed, name, year, new) for year, new in key_list}

        # Write out the new json
        write_data = self._weights
        write_data[name] = restructured
        write_json(write_data, self._working_dir, "BaseWeights")

    def _replacement_keys(self, name, fixed):
        """
        This Creates a true false list of keys, where True means that the values will be taken from then fixed file and
        false from the original
        """
        original_keys = [int(key) for key in self._weights[name].keys()]
        key_list = [[key, False] for key in original_keys] + \
                   [[new, True] for new in [int(key) for key in fixed[name].keys()] if new not in original_keys]
        key_list.sort(key=lambda x: x[0])
        return key_list

    def _replacement_values(self, fixed, name, year, new):
        """
        Assign attribute data from the new, or old data based on where the data is.
        """
        if new:
            return fixed[name][str(year)]
        else:
            return self._weights[name][str(year)]

    def write_out_changes(self, write_name, population_weights=True):
        """
        To be able to write the weight file we need to know when the changes occur, not just how many changes occur. To
        do this we need a list of names and the expected number of changes. The assumption is, that a place will not
        change more than once between census years but when this is not the case we need to be explict about this so we
        can work of the change manually if need be.

        :return: Nothing, just write out the csv file with the number of expected changes and support search terms
        :rtype: None
        """
        write_holder = [[weight_group, len(self._determine_changes(weight_group, population_weights)) - 1]
                        for weight_group in self._weights]

        write_csv(self._working_dir, write_name, ["Place", "Expected_Changes"], write_holder)
        print("Written out changes!")

    def _determine_changes(self, weight_group, population_weights):
        """
        Check to see if any changes occur for the current places's weight_group within the base weights

        :param weight_group: The current changes for the current place
        :type weight_group: int
        :param population_weights: If population weights where used
        :type: bool
        :return: List of all the non duplicated changes
        """
        cleaned_of_duplication = []
        for value in self._weights[weight_group].values():
            if population_weights:
                non_duplication = [[k, v["Area"], v["Population"]] for k, v in zip(value.keys(), value.values())]
            else:
                non_duplication = [[k, v["Area"]] for k, v in zip(value.keys(), value.values())]

            if non_duplication not in cleaned_of_duplication:
                cleaned_of_duplication.append(non_duplication)

        return cleaned_of_duplication

    def _load_weights(self, weights_name):
        """
        Load in the base weights from a given working directory and file name.
        """
        return load_json(f"{self._working_dir}/BaseWeights/{weights_name}")
