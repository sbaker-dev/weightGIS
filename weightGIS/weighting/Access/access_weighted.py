from miscSupports import flatten, terminal_time


def access_weighted(data_extraction_set, data_requested, name_index=0):
    """
    This will use a set of keys provided by the user within data_requested to access and write out the data in a
    weighted manner

    """
    row_data = []
    for place, attributes in zip(data_extraction_set.keys(), data_extraction_set.values()):

        # Whilst the first element is likely an ID, we may want to extract another index instead
        place = place.split("__")[name_index]

        # Not all places will have the same dates, so we need to get a common sorted list of them
        common_dates = sorted(list(set(flatten([attributes[data]["Dates"] for data in data_requested
                                                if data in attributes.keys()]))))

        # Then for each date we setup our first two columns of place-date
        for date in common_dates:
            date_values = [place, date]

            # And for each attribute requested, we extract the value if the date is valid, else NA
            for data in data_requested:
                if (data in attributes.keys()) and (date in attributes[data]["Dates"]):
                    date_values.append(attributes[data]["Values"][attributes[data]["Dates"].index(date)])
                else:
                    date_values.append("NA")
            row_data.append(date_values)

    print(f"Retrieved Weighted Data {terminal_time()}")
    return row_data
