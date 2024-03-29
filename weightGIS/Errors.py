class BaseNameNotFound(Exception):
    def __init__(self, base_name, shapefile_folder):
        super(BaseNameNotFound, self).__init__(
            f"\n\tFailed to find {base_name} within {shapefile_folder}"
        )


class NoSubUnitWeightIndex(Exception):
    def __init__(self):
        super(NoSubUnitWeightIndex, self).__init__(
            f"\n\tYou have specified you wish to use subunit weights, and have provided a valid file to do so, but not "
            f"provided the index of the weighting parameter within the attribute table of said shapefile"
        )


class AmbiguousIsolatesAlternatives(Exception):
    def __init__(self, potential_matches, root_name, alternate_names):
        super(AmbiguousIsolatesAlternatives, self).__init__(
            f"\n\tFound the following potential matches {potential_matches} for root '{root_name}' but could not "
            f"uniquely identify them with {alternate_names}"
        )


class AmbiguousIsolates(Exception):
    def __init__(self, potential_matches, root_name):
        super(AmbiguousIsolates, self).__init__(
            f"\n\tFound the following potential matches {potential_matches} for root '{root_name}' but "
            "could not uniquely identify them"
        )


class OrderError(Exception):
    def __init__(self, split_place, place, splitter, order):
        super(OrderError, self).__init__(
            f"Attempted to order {len(split_place)} place names within {place.split(splitter)} with {len(order)} "
            f"orderings of {order}")


class UnexpectedQCName(Exception):
    def __init__(self, name, date, qc_type):
        super(UnexpectedQCName, self).__init__(
            f"Failed to find {name} during {qc_type} QC operation for {date}")


class UnexpectedQCDate(Exception):
    def __init__(self, name, date, qc_type):
        super(UnexpectedQCDate, self).__init__(
            f"Failed to find {date} within {name} for {qc_type} QC Operation")
