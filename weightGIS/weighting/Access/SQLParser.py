from miscSupports import flatten, find_duplicates, parse_as_numeric
from collections import Counter
from operator import itemgetter
from pathlib import Path
import sqlite3


class SQLParser:
    def __init__(self, data_path):
        self._data_path = data_path

        assert Path(self._data_path).exists(), f"Failed to find database at {self._data_path}"
        self._database, self.cursor = self._set_connection()

    def __repr__(self):
        return f"DataParser Object for {Path(self._data_path).name}"

    def nested(self, nested_commands, remove_missing=False):
        """
        The user can set nested commands by submitting a dict of each command with its requested args with the exception
        of remove missing
        """

        # Execute the nested commands
        found_values = [getattr(self, command)(args).fetchall() for command, args in
                        self._validate_nested(nested_commands).items()]

        # Extract the common elements of the nested commands
        values = self._extract_common_nested(found_values)

        # Remove missing values if required
        return self._return_request(values, remove_missing)

    @property
    def table_names(self):
        """Return the tables names"""
        return flatten(self.cursor.execute("""SELECT name FROM sqlite_master WHERE type = 'table';""").fetchall())

    def table_attributes(self, table_name):
        """Extract a table attributes"""
        extract_all = self.cursor.execute(f"""SELECT * FROM {table_name}""")
        return [description[0] for description in extract_all.description]

    def table_places(self, table_name):
        """Extract the places of this location, returns as a sorted list of the unique place names found"""
        return sorted(list(set([p[0] for p in self.cursor.execute(f"SELECT Place FROM {table_name}").fetchall()])))

    def table_dates(self, table_name, as_counter=False):
        """Extract the dates for this location using Counter, Returns as Counter if requested else unique sorted list"""
        dates = self.cursor.execute(f"SELECT Date FROM {table_name}").fetchall()
        dates_occurrences = Counter([d[0] for d in dates])
        if as_counter:
            return dates_occurrences
        else:
            return sorted(list(dates_occurrences.keys()))

    def extract_attribute(self, table_name, attribute, remove_missing=False):
        """Extract a single attribute and return all its values unless remove missing is set, where NA is removed"""
        self._validate_args(table_name, attribute)

        values = self.cursor.execute(f"""SELECT Place, Date, {attribute} FROM {table_name}""")
        return self._return_request(values, remove_missing)

    def extract_with_dates(self, table_name, attribute, greater=None, less=None, remove_missing=False):
        """
        Isolate an attribute less than or equal to a date, greater than or equal to a date, or a combination of the two.
        If remove missing is set, then it will remove all missing from the list
        """
        values = self._dates_extract([table_name, attribute, greater, less])
        return self._return_request(values, remove_missing)

    def extract_with_place(self, table_name, attribute, places, remove_missing=False):
        """
        Extract data from a specific place
        """
        values = self._place_extract([table_name, attribute, places])
        return self._return_request(values, remove_missing)

    def extract_with_place_iteration(self, table_name, attribute, place, start_date, iterations, as_rate_of=None,
                                     rate_per=1000, remove_missing=False):
        """
        This will extract a given number of dates after the start date for a given place. If requested, it will return
        the value as a rate rather than as a list of values
        """
        # Extract the values for this place
        values = self._place_extract([table_name, attribute, place])

        # Extract the values greater than the start date for 'iterations' number
        values = [([place, date, attr]) for place, date, attr in values.fetchall() if date > start_date][:iterations]

        # If asked to calculate as a rate then calculate it as such, otherwise return the request
        if as_rate_of:
            return self._return_as_rates(values, place, start_date, as_rate_of, rate_per)
        else:
            return self._return_request(values, remove_missing)

    def _dates_extract(self, args):
        """
        Isolate an attribute less than or equal to a date, greater than or equal to a date, or a combination of the two
        """
        table_name, attribute, greater, less = args

        self._validate_args(table_name, attribute)
        assert less or greater, "Both less_or_equal and greater_or_equal are none. One must be set"

        # Less than or equal to date assigned to less
        if less and not greater:
            return self.cursor.execute(f"SELECT Place, Date, {attribute} FROM {table_name} WHERE Date <= {less}")

        # Greater than or equal to date assign to greater
        elif greater and not less:
            return self.cursor.execute(f"SELECT Place, Date, {attribute} FROM {table_name} WHERE Date >= {greater}")

        # Greater than or equal to greater and less than or equal to less
        else:
            return self.cursor.execute(f"SELECT Place, Date, {attribute} FROM {table_name} WHERE date <= {less} AND "
                                       f"date >= {greater}")

    def _place_extract(self, args):
        """Extract data from a specific place"""
        table_name, attribute, places = args
        self._validate_args(table_name, attribute)

        # Multiple Requests
        if isinstance(places, (list, tuple)) and len(places) > 1:
            return self.cursor.execute(f"SELECT Place, Date, {attribute} FROM {table_name}"
                                       f" WHERE Place in {tuple(places)}")

        # Single request made as list or tuple
        elif isinstance(places, (list, tuple)) and len(places) == 1:
            return self.cursor.execute(f"SELECT Place, Date, {attribute} FROM {table_name}"
                                       f" WHERE Place = '{places[0]}'")

        # Single request made as string
        elif isinstance(places, str):
            return self.cursor.execute(f"SELECT Place, Date, {attribute} FROM {table_name}"
                                       f" WHERE Place = '{places}'")
        else:
            raise TypeError(f"Expect list, tuple or string yet was passed {type(places)}")

    def _set_connection(self):
        """
        Assert the path is correct and load the database and set the cursor if it is, else assertion error
        """
        assert Path(self._data_path).exists(), f"Failed to find database at {self._data_path}"

        data_base = sqlite3.connect(self._data_path)
        return data_base, data_base.cursor()

    def _validate_args(self, table_name, attribute):
        """Validate the args submitted are correct"""
        # Check the table name is correct, extract the attributes of that table
        assert table_name in self.table_names, f"Table {table_name} invalid, ANNUAL and WEEKLY are only accepted values"
        table_attributes = self.table_attributes(table_name)

        # Check the attribute is within the attributes list
        assert attribute in table_attributes, f"Attribute {attribute} not found within {table_name}"

    @property
    def _nested_dict(self):
        """Allow nested commands with their respective private call command"""
        return {"extract_with_place": "_place_extract",
                "extract_with_dates": "_dates_extract"}

    @property
    def allowed_nested_commands(self):
        """So the user knows which commands they are allowed to nest"""
        return self._nested_dict.keys()

    def _validate_nested(self, nested_commands):
        """
        Not all commands can be nested, so when a nested command is called we validate that the command is valid and
        then set to the call command to the internal call so we can nest the command calls rather than the public
        command calls for a single operation for this object's curser
        """
        call_command = {}
        for command, parameters in nested_commands.items():
            try:
                call_command[self._nested_dict[command]] = parameters
            except KeyError:
                raise KeyError(f"{command} command was passed to nested parameters but is not an allow nested call")

        return call_command

    @staticmethod
    def _extract_common_nested(found_values):
        """
        Commands from sql are run separately of each other so to get the common values we look for duplicates across
        lists and then only isolate instances where we have these duplicates in both all the command lists that where
        run
        """

        # Reduce the complication of the search by looking for duplicates
        common_values = set(find_duplicates(flatten(found_values)))

        # Check each values found as common, check they are common to both lists rather than duplicated within a list
        return_values = []
        for v in common_values:
            common = True
            for command_values in found_values:
                if v not in command_values:
                    common = False
            if common:
                return_values.append(v)

        return sorted(return_values, key=itemgetter(1))

    @staticmethod
    def _return_request(values, missing_return):
        """Return the values to the end user"""

        if isinstance(values, sqlite3.Cursor):
            values = values.fetchall()

        if missing_return:
            return [tuple([place, date, value]) for place, date, value in values if value != "NA"]
        else:
            return values

    def _return_as_rates(self, values, place, start_date, as_rate_of, rate_per):
        """Calculate the rate for a given selection """
        # Extract possible population values as annual values so they can be used for weekly and annual data
        self._validate_args(as_rate_of["Table"], as_rate_of["Attribute"])
        population = self._place_extract([as_rate_of["Table"], as_rate_of["Attribute"], place])
        population = {str(date)[:4]: pop for place, date, pop in population.fetchall() if date >= start_date}

        # Extract an annual values that occur for each value found then sum and divided the list by the length
        population = (sum([population[str(date)[:4]] for _, date, _ in values]) / len(values))

        # Isolate the values, warn the user if NA was found within them
        values = [attr for _, _, attr in values]
        if "NA" in values:
            print("WARNING - NA found within values - setting NA to zero")
            values = [parse_as_numeric(v for v in values)]

        # Return the rate
        return sum(values) / (population / rate_per)
