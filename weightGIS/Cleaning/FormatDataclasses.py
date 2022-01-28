from miscSupports import simplify_string
from dataclasses import dataclass
from typing import List


@dataclass
class Match:
    gid: str
    standardised: str
    alternate: List[List[str]]

    @property
    def name(self) -> str:
        """The standardised name entry"""
        return f"{self.gid}__{self.standardised}__" + "__".join([alt[0] for alt in self.alternate])

    def validate_alternate(self, alternate_names: List[str]) -> bool:
        """If we need to validate alternative names, check if all the alternative names are present"""
        check = [1 for alt_group, alt_search in zip(self.alternate, alternate_names) if alt_search in alt_group]
        # If alternate names are valid, accept
        if sum(check) == len(self.alternate):
            return True
        else:
            return False


@dataclass
class Correction:
    correction: str
    alt_names: str
    year: str
    delete: str

    def validate_correction(self, root, alternated_names, current_year):
        if simplify_string(self.delete) == 'true':
            return None

        # If we have no alternated names, and the year is not important or the year is greater than or equal to the
        # current year, then we accept this correction as the valid correction
        if (self.year == '-' or int(current_year) >= int(self.year)) and self.alt_names == '-':
            return simplify_string(self.correction)

        # However, if we have alternated names, then we only accept the correction if alternated names match
        elif self.year == '-' or int(current_year) >= int(self.year):
            if self.alt_names.split('__') == alternated_names:
                return simplify_string(self.correction)
            else:
                return root

        # If the correction is not valid, just return the root
        else:
            return root
