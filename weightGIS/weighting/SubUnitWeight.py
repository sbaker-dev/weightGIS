import sys

from shapely.geometry import Polygon, MultiPolygon, LineString
from miscSupports import flatten, multi_to_poly, directory_iterator, validate_path, write_json
from shapely.ops import split as shp_split

from dataclasses import dataclass
from shapeObject import write_shape_file

from shapeObject import ShapeObject

from typing import Union


class SubUnit2:
    def __init__(self, valid_shapes, weight_index, gid, overlap, cut_off):

        print(valid_shapes)
        self.records = [rec for rec, shp in valid_shapes]
        self.shps = flatten([multi_to_poly(shp) for rec, shp in valid_shapes])
        self.cut_off = cut_off
        self.interiors = self._set_interior(overlap)

        print(self.records)

        print(self.shps)


        sys.exit()

    def _set_interior(self, overlap):


        isolates = []
        for sub_poly in self.shps:
            if overlap.intersection(sub_poly).area > self.cut_off:
                for poly in shp_split(sub_poly, LineString(overlap.exterior)):
                    if overlap.intersection(poly).area > self.cut_off:
                        isolates.append(poly)

        print(isolates)


class SubUnit:
    def __init__(self, full_weight: float, overlap_poly: Polygon, sub_unit_poly: Union[Polygon, MultiPolygon], cut_off, base_shp):
        self.full_weight = full_weight
        self.area = sub_unit_poly.area
        self.cut_off = cut_off
        self.base_shp = base_shp

        self.interiors = flatten([self._set_interior_polygons(overlap_poly, sub_poly) for sub_poly in multi_to_poly(sub_unit_poly)])


        # print(self.interiors)
        #
        # sys.exit()

        # self.interiors = self._construct_interior_polygons(sub_unit_poly, overlap_poly)


    def _set_interior_polygons(self, overlap_poly, sub_poly):
        return [poly for poly in shp_split(sub_poly, LineString(overlap_poly.exterior))
                if overlap_poly.intersection(poly).area > self.cut_off]

    def _construct_interior_polygons(self, sub_unit_poly, shape):

        return flatten(flatten([self._isolate_interior_polygons(bp, p) for bp in multi_to_poly(shape)
                                for p in multi_to_poly(sub_unit_poly)]))

    def _isolate_interior_polygons(self, bp, p):
        a = self._set_interior_polygons(bp, p)
        if (len(self.base_shp.interiors) > 0) and (len(a) > 0):
            return [self._hole_punch_sub_unit(c) for c in a]
        return [a]





@dataclass
class InteriorPoly:
    poly: Polygon
    weight: float



class SubUnitWeight:
    def __init__(self, sub_units: list, overlap: Union[Polygon, MultiPolygon], cut_off: Union[int, float],
                 base_shape: Union[Polygon, MultiPolygon]):

        self.sub_units = sub_units
        self.overlap = overlap
        self._cut_off = cut_off
        self.base_shp = base_shape

    def _reconstruct_high_order_unit(self, polygon: Polygon):
        """This recreates a shape by the sub-unit shapefile"""

        a = {}

        for rec, poly in zip(self.sub_units.records, self.sub_units.polygons):
            for p in multi_to_poly(poly):
                print(p)

        valid_p = [[rec, poly] for rec, poly in zip(self.sub_units.records, self.sub_units.polygons)
                   if polygon.intersection(poly).area > self._cut_off]

        SubUnit2(valid_p, self.weight_index, self.gid, polygon, self._cut_off)

        print(valid_p)

        sys.exit()

        for rec, poly in zip(self.sub_units.records, self.sub_units.polygons):
            if polygon.intersection(poly).area > self._cut_off:
                a[rec[self.gid]] = SubUnit(float(rec[self.weight_index]), polygon, poly, self._cut_off, self.base_shp)

        return a

    def a(self):
        return [poly for poly in shp_split(sub_poly, LineString(overlap_poly.exterior))
                if overlap_poly.intersection(poly).area > self.cut_off]

    def sub_unit_weight(self):

        c = []
        d = []
        for i, poly in enumerate(multi_to_poly(self.overlap)):

            interior_polys = []
            for sub_poly in self.sub_units:
                if poly.intersection(sub_poly.poly).area > self._cut_off:
                    for p in shp_split(sub_poly.poly, LineString(poly.exterior)):
                        if poly.intersection(p).area > self._cut_off:
                            for pp in self._hole_punch_sub_unit(poly, p):

                                interior_polys.append(InteriorPoly(pp, sub_poly.weight * (pp.area / sub_poly.poly.area)))

                            # # todo Add in the split on holes
                            # interior_polys.append(InteriorPoly(p, sub_poly.weight * (p.area / sub_poly.poly.area)))


            c.append(sum([i.weight for i in interior_polys]))


            base_polys = []
            for interior in interior_polys:
                if self.base_shp.intersection(interior.poly).area > self._cut_off:

                    for p in shp_split(interior.poly, LineString(self.base_shp.exterior)):
                        if self.base_shp.intersection(p).area > self._cut_off:
                            for pp in self._hole_punch_sub_unit(self.base_shp, p):

                                base_polys.append(InteriorPoly(pp, interior.weight * (pp.area / interior.poly.area)))

                            # base_polys.append(InteriorPoly(p, interior.weight * (p.area / interior.poly.area)))

            d.append(sum([i.weight for i in base_polys]))

        print(f"NEW WEIGHT: {(sum(d) / sum(c) * 100)}")

    def _hole_punch_sub_unit(self, current_polygon, split_poly):
        """
        A polygon may have holes within it, so we need to punch the holes out so as to not get an inaccurate area.

        :param current_polygon: The current polygon from the current shape we are processing
        :type current_polygon: Polygon

        :param split_poly: The polygon we have split which we need to punch a hole out of
        :type split_poly: list[Polygon]

        :return: If there are any changes from holes, return a new list otherwise just return a list holding the split
            polygon that was found where the list is the reference int and Polygon.
        :rtype: list[Polygon]
        """
        changes_from_holes = False
        poly_list = []
        for hole in current_polygon.interiors:
            if Polygon(hole).intersection(split_poly).area > self._cut_off:
                changes_from_holes = True
                split_poly_hole_punched = shp_split(split_poly, LineString(hole))

                # Now we only isolate the parts that are within the overlap from the cut
                for hole_cut_poly in split_poly_hole_punched:
                    if current_polygon.intersection(hole_cut_poly).area > self._cut_off:
                        poly_list.append(hole_cut_poly)

                if len(poly_list) == 0:
                    changes_from_holes = False

        if changes_from_holes:
            return poly_list
        else:
            return [split_poly]