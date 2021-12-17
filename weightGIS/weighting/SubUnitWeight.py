import sys

from shapely.geometry import Polygon, MultiPolygon, LineString
from miscSupports import flatten, multi_to_poly, directory_iterator, validate_path, write_json
from shapely.ops import split as shp_split

from shapeObject import ShapeObject

from typing import Union


class SubUnitWeight:
    def __init__(self, sub_units: ShapeObject, overlap: Union[Polygon, MultiPolygon], weight_index: int,
                 cut_off: Union[int, float], gid: int):

        self.sub_units = sub_units
        self.overlap = overlap
        self.weight_index = weight_index
        self._cut_off = cut_off
        self.gid = gid

        print("NEW")
        self.sub_unit_weight()

    def _reconstruct_high_order_unit(self, polygon: Union[Polygon, MultiPolygon], weight_index: Union[int, float]):
        """This recreates a shape by the sub-unit shapefile"""

        a = {}

        for rec, poly in zip(self.sub_units.records, self.sub_units.polygons):
            if polygon.intersection(poly).area > self._cut_off:
                a[rec[self.gid]] = {'FullWeight': rec[weight_index], 'Polygons': multi_to_poly(poly), 'Interior': flatten([self._set_interior_polygons(polygon, p) for p in multi_to_poly(poly)]),
                                    'Area': poly.area, 'SubWeight': -1, 'BaseWeight': -1}

        return a

    def _set_interior_polygons(self, polygon, p):
        return [b for b in shp_split(p, LineString(polygon.exterior)) if polygon.intersection(b).area > self._cut_off]


    def sub_unit_weight(self):

        for poly in multi_to_poly(self.overlap):

            a = self._reconstruct_high_order_unit(poly, self.weight_index)

            # for i, sub_unit in enumerate(a.values()):
            #     for p in sub_unit['Polygons']:
            #         for b in shp_split(p, LineString(poly.exterior)):
            #             if poly.intersection(b).area > self._cut_off:
            #                 sub_unit['Interior'].append(b)

            print(a)

            # TODO: This is going to crash
            if len(poly.interiors) > 0:
                print('INTERIOR FOUND')
                interior_polygons = [self._hole_punch_sub_unit(poly, p) for p in a]
                sys.exit()

            for sub_unit in a.values():

                for interior in sub_unit['Interior']:
                    sub_unit['SubWeight'] = float(sub_unit['FullWeight']) * (interior.area / sub_unit['Area'])

                    print(sub_unit['SubWeight'])

            print(a.values())





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


