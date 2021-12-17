import sys

from shapely.geometry import Polygon, MultiPolygon, LineString
from miscSupports import flatten, multi_to_poly, directory_iterator, validate_path, write_json
from shapely.ops import split as shp_split

from shapeObject import ShapeObject

from typing import Union


class SubUnit:
    def __init__(self, full_weight: float, shape: Union[Polygon, MultiPolygon],
                 sub_unit_poly: Union[Polygon, MultiPolygon], cut_off):
        self.full_weight = full_weight
        self.area = sub_unit_poly.area
        self.interiors = flatten([self._set_interior_polygons(shape, p, cut_off) for p in multi_to_poly(sub_unit_poly)])

    @staticmethod
    def _set_interior_polygons(polygon, p, cut_off):
        return [shp for shp in shp_split(p, LineString(polygon.exterior)) if polygon.intersection(shp).area > cut_off]


class SubUnitWeight:
    def __init__(self, sub_units: ShapeObject, overlap: Union[Polygon, MultiPolygon], weight_index: int,
                 cut_off: Union[int, float], gid: int, base_shape: Union[Polygon, MultiPolygon]):

        self.sub_units = sub_units
        self.overlap = overlap
        self.weight_index = weight_index
        self._cut_off = cut_off
        self.gid = gid
        self.base_shp = base_shape

    def _reconstruct_high_order_unit(self, polygon: Union[Polygon, MultiPolygon], weight_index: Union[int, float]):
        """This recreates a shape by the sub-unit shapefile"""

        a = {}

        for rec, poly in zip(self.sub_units.records, self.sub_units.polygons):
            if polygon.intersection(poly).area > self._cut_off:
                a[rec[self.gid]] = SubUnit(float(rec[weight_index]), polygon, poly, self._cut_off)

        return a



    def sub_unit_weight(self):
        print("NEW")

        for poly in multi_to_poly(self.overlap):

            a = self._reconstruct_high_order_unit(poly, self.weight_index)

            # # TODO: This is going to crash
            # if len(poly.interiors) > 0:
            #     print('INTERIOR FOUND')
            #     interior_polygons = [self._hole_punch_sub_unit(poly, p) for p in a]
            #     sys.exit()
            #

            c = []
            d = []
            for sub_unit in a.values():

                # TODO: Population weight sshould be calcualted WITHIN Sub units, we also need to allow for polygon interiors
                for interior in sub_unit.interiors:
                    population_weight = float(sub_unit.full_weight) * (interior.area / sub_unit.area)
                    c.append(population_weight)

                    if interior.intersection(self.base_shp).area > self._cut_off:
                        d.append(population_weight * (interior.intersection(self.base_shp).area / interior.area))



            print(sum(c))
            print(sum(d))
            print(f"NEW WEIGHT: {(sum(d) / sum(c) * 100)}")

        return

    def _hole_punch_sub_unit(self, current_polygon, split_poly):
        """
        A polygon may have holes within it, so we need to punch the holes out so as to not get an inaccurate area.

        :param current_polygon: The current polygon from the current shape we are processing
        :type current_polygon: Polygon

        :param split_poly: The polygon we have split which we need to punch a hole out of
        :type split_poly: list[Polygon]

        :return: If there are any changes from holes, return a new list otherwise just return a list holding the split
            polygon that was found where the list is the reference int and Polygon.
        :rtype: list[int, Polygon]
        """
        changes_from_holes = False

        record_index, split_poly = split_poly

        poly_list = []
        for hole in current_polygon.interiors:
            if Polygon(hole).intersection(split_poly).area > self._cut_off:
                changes_from_holes = True
                split_poly_hole_punched = shp_split(split_poly, LineString(hole))

                # Now we only isolate the parts that are within the overlap from the cut
                for hole_cut_poly in split_poly_hole_punched:
                    if current_polygon.intersection(hole_cut_poly).area > self._cut_off:
                        poly_list.append([record_index, hole_cut_poly])

                if len(poly_list) == 0:
                    changes_from_holes = False

        if changes_from_holes:
            return poly_list
        else:
            return [record_index, split_poly]


