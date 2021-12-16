from weightGIS.Errors import BaseNameNotFound, NoSubUnitWeightIndex

from miscSupports import flatten, multi_to_poly, directory_iterator, validate_path, write_json
from shapely.geometry import LineString, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import split as shp_split
from typing import List, Union, Optional, Tuple, Dict
from shapeObject import ShapeObject
from pathlib import Path
import re

import sys


class ConstructWeights:
    def __init__(self, working_directory: Union[str, Path], base_name: str, gid: int, name_indexes: List[int],
                 subunits: Optional[Union[str, Path]] = None, shapefile_folder="Shapefiles", cut_off=100,
                 weight_index: Optional[int] = None):
        """
        This class takes a set of shapefiles and creates a weighted json based on either the overlapping area or
        underlying population.

        """
        self._working_dir = Path(validate_path(working_directory))
        setup_files = self._validate_setup(shapefile_folder, base_name, subunits, weight_index)
        self.base, self.shapefiles, self.sub_units, self._weight_index = setup_files
        self._gid = gid
        self._name_indexes = name_indexes
        self._cut_off = cut_off

    def _validate_setup(self, shapefile_folder: str, base_name: str, subunits: Optional[Union[str, Path]],
                        weight_index: int) -> Tuple[ShapeObject, List[ShapeObject], Optional[ShapeObject],
                                                    Optional[int]]:
        """Validate the setup for constructing the base"""
        # Set shapefile name path, valid it exists
        file_path = validate_path(Path(self._working_dir, shapefile_folder))

        # Check the base name exists within the shapefile folder, and there is at least one other file
        shapefiles = sorted([file for file in directory_iterator(file_path) if Path(file_path, file).suffix == ".shp"])
        if base_name not in shapefiles:
            raise BaseNameNotFound(base_name, file_path)
        if len(shapefiles) <= 1:
            raise IndexError(f"Found {len(shapefiles)} files, but at least two files are required to weight")

        # Load the shapefiles and, if required, the subunits. Then return
        shape_files = [ShapeObject(f"{file_path}/{file}") for file in shapefiles]
        subunit_shapefile, weight_index = self._load_sub_units(subunits, weight_index)
        return ShapeObject(f"{file_path}/{base_name}"), shape_files, subunit_shapefile, weight_index

    def _load_sub_units(self, subunit_path: Optional[Union[str, Path]], weight_index: Optional[int]):
        """Load the Sub unit file, if it was requested, and validate a weight_index was set if loaded"""
        if not subunit_path:
            return None, None

        if Path(subunit_path).exists():
            subunits = ShapeObject(subunit_path)
        elif Path(f"{self._working_dir}/{subunit_path}").exists():
            subunits = ShapeObject(f"{self._working_dir}/{subunit_path}")
        else:
            raise FileNotFoundError(f"Sub unit weighting specified but no file called {subunit_path} found in "
                                    f"{self._working_dir}")

        # If we load the sub-unit shapefile but didn't specify a weight, inform the user
        if not weight_index:
            raise NoSubUnitWeightIndex()
        return subunits, weight_index

    def construct_base_weights(self, write_name: str = 'BaseWeights') -> None:
        """
        Construct the base weights for a set of shapefiles.

        This iterates through the shapes in the base shapefile to index to, and finds overlapping shapes in another
        shapefile to calculate anm area weight. If sub unit searching is enabled, it is also possible to use under-
        lapping geometery to calculate a sub unit weight. This is done for every shape in the base shapefile and then
        returned
        """
        base_weights = {f"{rec[self._gid]}__{self._construct_name(rec)}": [] for rec in self.base.records}
        for c, (shape, record) in enumerate(zip(self.base.polygons, self.base.records)):
            print(f"{c + 1} / {len(self.base.polygons)}")

            match_weights = {file: [] for file in [re.sub(r'\D', "", file.file_name) for file in self.shapefiles]}
            for index, match_shape_file in enumerate(self.shapefiles):

                # Set the weight from overlapping area
                weights = self._polygon_area_weights(shape, match_shape_file)

                # If set, set the weight from underling sub unit population
                if self.sub_units:
                    weights = {gid: self._sub_weight(shape, overlap_values) for gid, overlap_values in weights.items()}

                match_weights[re.sub(r'\D', "", match_shape_file.file_name)] = weights
            base_weights[f"{record[self._gid]}__{self._construct_name(record)}"] = match_weights

            print(match_weights)
        # write_json(base_weights, self._working_dir, write_name)

    def _polygon_area_weights(self, current_shape: Union[Polygon, MultiPolygon], match_shape_file: ShapeObject) -> dict:
        """
        Calculates the weights relative to the base years current_shape in terms of area for each shape in the
        match_shape_file which has an overlap
        """
        area_weights = {record[self._gid]: self._calculate_area_weight(current_shape, match_shape, record)
                        for match_shape, record in zip(match_shape_file.polygons, match_shape_file.records)}
        return {gid: weights for gid, weights in area_weights.items() if weights}

    def _calculate_area_weight(self, current_shape: Union[Polygon, MultiPolygon],
                               match_shape: Union[Polygon, MultiPolygon], record: List[str]):
        """
        If the overlap is greater than the cut off, return a dict with Name, Area Weight, Population Stub, and
        Match Shape
        """
        overlap_area = current_shape.intersection(match_shape).area
        if overlap_area > self._cut_off:
            return {'Name': self._construct_name(record), 'Area': (overlap_area / match_shape.area) * 100,
                    'Population': None, 'Match': match_shape}

    def _construct_name(self, record: List[str]) -> str:
        """
        Constructs the place name from the record from a list of indexes
        """
        return "_".join([record[i] for i in self._name_indexes])

    def _sub_weight(self, base_shape: Union[Polygon, MultiPolygon], overlap_values: dict):
        """
        Calculates and returns the sub unit weight for each overlapping shape

        If the overlap percentage isn't 100 then the population weight can be calculated from the under-lapping shapes.
        First all the parts of the under-lapping shapes of the overlapping distinct are isolated to calculate the total
        value of the sub weight value. Then, the parts of this shape that overlap the base_shape we are indexing too
        are isolated. The percentage weight is then just the value of (weight_of_match / weight_of_base) * 100.

        """
        if overlap_values['Area'] != 100:
            weight_of_match, weighted_set = self._sub_unit_weight(self.sub_units, overlap_values['Match'],
                                                                  self._weight_index)
            weight_of_base, weighted_set = self._sub_unit_weight(flatten(weighted_set), base_shape, None)

            overlap_values['Population'] = (weight_of_base / weight_of_match) * 100
        else:
            overlap_values['Population'] = 100
        overlap_values.pop('Match', None)
        return overlap_values

    def _sub_unit_weight(self, sub_unit_file, within_search_polygon, weight_index):
        """
        This configures the input file and then searches for under-lying polygons within the current
        within_search_polygon. Returns the weight associated with this polygon and the weight set of polygons

        :param sub_unit_file: The External ShapeObject to read in and check or the polygons found within this external
            ShapeObject in the form of a list
        :type sub_unit_file: ShapeObject | list

        :param within_search_polygon: The Current polygon to search within
        :type within_search_polygon: Polygon | MultiPolygon

        :param weight_index: For external data, the index position of the weights in the attribute table. Not required
            for the internal.
        :type weight_index: int | None

        :return: The weight associated with this polygon and the weight set of polygons
        :rtype: tuple[float, list[list[float, Polygon]]]
        """
        sub_units, record_list, sub_shape_polygons, current_shape = self._configure_sub_shapes(
            sub_unit_file, within_search_polygon, weight_index)

        weighted_set = [self._select_under(poly, sub_shape_polygons, record_list, sub_units) for poly in current_shape]
        weight = sum([population_weight for population_weight, _ in flatten(weighted_set)])
        return weight, weighted_set

    def _configure_sub_shapes(self, sub_unit_file, within_search_polygon, weight_index):
        """
        Returns the under-lapping sub units, weight records, reformed under-lapping sub units to be just Polygons and
        the reformed current shape

        This method is going to be called twice per overlapping polygon of the base shapefiles current polygon. Once to
        find the under-lapping units of the overlapping polygon, and once to see of these under-lapping units how much
        of them are in the base shapefiles current polygon.

        As such, this method checks the instance of the sub_unit file and formats under-lapping sub units and records
        accordingly as in the first instance this will be data that was held externally but the second instance will be
        an internal read from memory.

        Some shapely methods don't work well on multipolygons, so the found list of under-lapping polygons and the
        current shape are then set to be a list of shapely Polygons to fix this.

        :param sub_unit_file: The External ShapeObject to read in and check or the polygons found within this external
            ShapeObject in the form of a list
        :type sub_unit_file: ShapeObject | list

        :param within_search_polygon: The Current polygon to search within
        :type within_search_polygon: Polygon | MultiPolygon

        :param weight_index: For external data, the index position of the weights in the attribute table. Not required
            for the internal.
        :type weight_index: int | None

        :return: The under-lapping sub units, weight records, reformed under-lapping sub units and the reformed current
            shape
        :rtype: tuple[list[Polygon | MultiPolygon], list[float | int], list[list[Polygon]], list[Polygon]]
        """
        if isinstance(sub_unit_file, ShapeObject):
            sub_units, record_list = self._extract_sub_units_data(within_search_polygon, sub_unit_file, weight_index)
        else:
            sub_units, record_list = self._extract_overlap_units_data(within_search_polygon, sub_unit_file)

        sublist_shape_polygons = [multi_to_poly(polygon_type) for polygon_type in sub_units]
        current_shape = multi_to_poly(within_search_polygon)
        return sub_units, record_list, sublist_shape_polygons, current_shape

    def _extract_overlap_units_data(self, within_search_polygon, sub_shapes):
        """
        Extract the under-lapping polygons geometry from a list format

        :param within_search_polygon: The Current polygon to search within
        :type within_search_polygon: Polygon | MultiPolygon

        :param sub_shapes: A list, where each element in the list is a float weight and the Polygons
        :type sub_shapes: list[float, Polygons]

        :return: A list of all the under-lapping polygons and a list of records that correspond to those polygons.
        :rtype: tuple[list[float], list[Polygons]]
        """
        subunit_list = []
        record_list = []
        for record, poly in sub_shapes:
            if within_search_polygon.intersection(poly).area > self._cut_off:
                subunit_list.append(poly)
                record_list.append(record)
        return subunit_list, record_list

    def _extract_sub_units_data(self, within_search_polygon, sub_shapes, weight_index):
        """
        Extract the under-lapping polygons geometry

        :param within_search_polygon: The Current polygon to search within
        :type within_search_polygon: Polygon | MultiPolygon

        :param sub_shapes: A ShapeObject file, which contains under-lapping geometry
        :type sub_shapes: ShapeObject

        :param weight_index: The index to parse information out of the attribute table from the ShapeObject
        :type weight_index: int

        :return: A list of all the under-lapping polygons and a list of records that correspond to those polygons.
        :rtype: tuple[list[float], list[Polygons]]
        """
        subunit_list = []
        record_list = []
        for poly, record in zip(sub_shapes.polygons, sub_shapes.records):
            if within_search_polygon.intersection(poly).area > self._cut_off:
                subunit_list.append(poly)
                record_list.append(record[weight_index])
        return subunit_list, record_list

    def _select_under(self, polygon, sublist_shape_polygons, record_list, sub_units):
        """
        Select under-lapping polygons, select the interior parts of them, punch out any holes that existed in the the
        current polygon, and then return a list of lists of the weights and polygons.

        This splits the shapes that where found to be under-lapping and then isolates the interior polygons. If the
        current polygon has a hole, or hole(s) within it, then this hole is then used as to punch out the under-lapping
        polygons. Finally the weight is calculated and the combined with the polygon and returned in the form of a list
        of lists.

        :param polygon: A polygon from the current within_search_polygon
        :type polygon: Polygon

        :param sublist_shape_polygons: reformed under-lapping sub units to be just Polygons
        :type sublist_shape_polygons: list[list[Polygon]]

        :param record_list: list of weight records
        :type record_list: list[float | int]

        :param sub_units: A list of Polygonal geometry
        :type sub_units: list[Polygon | MultiPolygon]

        :return: A list of lists, where sub lists are made up of a float relating to the weight and a Polygon.
        :rtype: list[list[float, Polygon]]
        """
        split_shapes = self._split_sub_unit_shapes(sublist_shape_polygons, polygon)

        interior_polygons = [[rec_index, poly] for rec_index, shape in split_shapes for poly in shape
                             if polygon.intersection(poly).area > self._cut_off]

        if len(polygon.interiors) > 0:
            interior_polygons = [self._hole_punch_sub_unit(polygon, poly) for poly in interior_polygons]

        polygons_to_weight = self._reform_interior_polygons_for_weighting(interior_polygons)

        weighted_polygons = []
        for i, (rec_index, poly) in enumerate(polygons_to_weight):
            # The population is weighted based on the % area of the zone within the zone
            weight = float(record_list[rec_index]) * (poly.area / sub_units[rec_index].area)
            weighted_polygons.append([weight, poly])
        return weighted_polygons

    def _split_sub_unit_shapes(self, sublist_shape_polygons, polygon):
        """
        Returns a list of Geometery collects with the reference index to the original

        :param sublist_shape_polygons: reformed under-lapping sub units to be just Polygons
        :type sublist_shape_polygons: list[list[Polygon]]

        :param polygon: A polygon from the current within_search_polygon
        :type polygon: Polygon

        :return: A list of lists, where the sub lists include a reference index to the original shape found and a
            GeometryCollection found from the splitting
        :rtype: list[list[int, GeometryCollection]]
        """
        split_shapes = []
        for index, shape in enumerate(sublist_shape_polygons):
            for sub in shape:
                if polygon.intersection(sub).area > self._cut_off:
                    split_shapes.append([index, shp_split(sub, LineString(polygon.exterior))])
        return split_shapes

    @staticmethod
    def _reform_interior_polygons_for_weighting(interior_polygons):
        """
        Interior polygons may end up in multiple formats due to interior holes, this standardises them.

        :param interior_polygons: List of lists, where sub lists are a reference index and Polygon
        :type interior_polygons: list[list[int, Polygon] | list[int, list[Polygon]]]

        :return: list[list[int, Polygon]
        """
        polygons_to_weight = []
        for poly_list in interior_polygons:
            if isinstance(poly_list[0], list):
                for p_list in poly_list:
                    polygons_to_weight.append(p_list)
            else:
                polygons_to_weight.append(poly_list)
        return polygons_to_weight

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
