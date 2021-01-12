from shapely.geometry import LineString, Polygon, MultiPolygon, GeometryCollection
from miscSupports import flatten, multi_to_poly
from shapely.ops import split as shp_split
from shapeObject import ShapeObject
from pathlib import Path
import json
import re
import os


class ConstructWeights:
    def __init__(self, working_directory, base_name, subunits=None, shape_file_folder_name="Shapefiles", gid=0, name=1,
                 name_class=None, cut_off=100, weight_index=-1):
        """
        This class takes a set of shapefiles and creates a weighted json based on either the overlapping area or
        underlying population.

        :param working_directory: Project Directory
        :param base_name: Shapefile name that you wish to weight too
        :param subunits: If you want to use geographic sub units
        :param shape_file_folder_name: Default name of the folder holding shapefiles, can be renamed
        :param gid: the index of the index column of the attribute table
        :param name: the index of the name column of the attribute table
        :param name_class: If names have a second column of supporting information assigned to them in the attribute
            then place the index of that column here
        :param cut_off: Cut of to deal with floating point errors and minor human error
        :param weight_index: If using subunits, the column index of the attribute table containing your weight data
        """

        self._working_dir = Path(working_directory)
        self.base, self.base_index, self.shapefiles, self.sub_units = self._validate_setup(
            shape_file_folder_name, base_name, subunits, weight_index)

        self._gid = gid
        self._name = name
        self._name_class = name_class
        self._cut_off = cut_off
        self._weight_index = weight_index

    def construct_base_weights(self):
        """
        Construct the base weights for a set of shapefiles.

        Further information
        -----------------------
        This iterates through the shapes in the base shapefile to index to, and finds overlapping shapes in another
        shapefile to calculate anm area weight. If sub unit searching is enabled, it is also possible to use under-
        lapping geometery to calculate a sub unit weight. This is done for every shape in the base shapefile and then
        returned

        :return: The base weights calculated
        :rtype: list
        """
        base_weights = {f"{rec[self._gid]}__{self._construct_name(rec)}": [] for rec in self.base.records}
        for c, (shape, record) in enumerate(zip(self.base.polygons, self.base.records)):
            print(f"{c+1} / {len(self.base.polygons)}")

            match_weights = {file: [] for file in [re.sub(r'\D', "", file.file_name) for file in self.shapefiles]}
            for index, match_shape_file in enumerate(self.shapefiles):

                # Set the weight from overlapping area
                area_weight = self._polygon_area_weights(shape, match_shape_file)

                # If set, set the weight from underling sub unit population
                if self.sub_units:
                    weights = self._sub_weight(shape, area_weight)
                else:
                    weights = [area[:-1] for area in area_weight]
                match_weights[re.sub(r'\D', "", match_shape_file.file_name)] = weights

            base_weights[f"{record[self._gid]}__{self._construct_name(record)}"] = self._format_weights(match_weights)

        self._write_out_base_weights(base_weights)

    def _polygon_area_weights(self, current_shape, match_shape_file):
        """
        Calculates the weights relative to the base year in terms of area

        :param current_shape: The Current polygonal shape from our base shapefile
        :type current_shape: Polygon | MultiPolygon

        :param match_shape_file: The current shapefile that is being based
        :type match_shape_file: ShapeObject

        :return: A list of lists, where each sub list is a list of the found overlap ID, Name, Area Weight, Polygon.
        :rtype: list[list[int, str, float, Polygon | MultiPolygon]]
        """
        area_weights = []
        for match_shape, record in zip(match_shape_file.polygons, match_shape_file.records):
            overlap_area = current_shape.intersection(match_shape).area
            if overlap_area > self._cut_off:
                overlap_percentage = (overlap_area / match_shape.area) * 100
                area_weights.append([record[self._gid], self._construct_name(record), overlap_percentage, match_shape])

        return area_weights

    def _construct_name(self, record):
        """
        Constructs the place name

        Further Information
        ---------------------
        Names may be broken into types, for example in the UK Districts can often have an urban and rural districts
        which means the actual name of the district is split into two columns. This function stitches the names back
        together if this is the case, and just returns the name otherwise

        :param record: A list of records, where each record represents an entry in a given column in the attribute table
        :type record: list

        :return: The name of the current place
        :rtype: str
        """

        if self._name_class:
            return record[self._name] + record[self._name_class]
        else:
            return record[self._name]

    def _sub_weight(self, base_shape, area_weight):
        """
        Calculates and returns the sub unit weight for each overlapping shape

        Further Information
        --------------------
        If the overlap percentage isn't 100 then the population weight can be calculated from the under-lapping shapes.
        First all the parts of the under-lapping shapes of the overlapping distinct are isolated to calculate the total
        value of the sub weight value. Then, the parts of this shape that overlap the base_shape we are indexing too
        are isolated. The percentage weight is then just the value of (weight_of_match / weight_of_base) * 100.

        :param base_shape: The current shape in the base shapefile we are indexing too
        :type base_shape: Polygon | MultiPolygon

        :param area_weight: The currently calculated values from the are weights
        :type area_weight: list[list[int, str, float, Polygon | MultiPolygon]]

        :return: A list of lists, where each sub list is composed of the overlap id, name, area weight, and sub unit
            weight
        :rtype: list[list[int, str, float, float]]
        """
        reformatted_weights = []
        for place_key, place_name, overlap_percentage, overlap in area_weight:
            if int(overlap_percentage) != 100:
                weight_of_match, weighted_set = self._sub_unit_weight(self.sub_units, overlap, self._weight_index)
                weight_of_base, weighted_set = self._sub_unit_weight(flatten(weighted_set), base_shape, None)

                sub_unit_weight = (weight_of_base / weight_of_match) * 100
                reformatted_weights.append([place_key, place_name, overlap_percentage, sub_unit_weight])

            else:
                reformatted_weights.append([place_key, place_name, overlap_percentage, 100.0])

        return reformatted_weights

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
        weight = sum([area for area, _ in flatten(weighted_set)])
        return weight, weighted_set

    def _configure_sub_shapes(self, sub_unit_file, within_search_polygon, weight_index):
        """
        Returns the under-lapping sub units, weight records, reformed under-lapping sub units to be just Polygons and
        the reformed current shape

        Further information
        ---------------------
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

        Further information
        --------------------
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
            weight = float(record_list[rec_index]) * (poly.area / sub_units[rec_index].area)
            weighted_polygons.append([weight, poly])
        return weighted_polygons

    def _split_sub_unit_shapes(self, sublist_shape_polygons, polygon):
        """
        returns a list of Geometery collects with the reference index to the original

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

    def _write_out_base_weights(self, base_weights):
        """
        Write out the base weights

        :param base_weights: A list of all the base weights
        :type base_weights: dict

        :return: Nothing, write out file then stop
        :rtype: None
        """
        try:
            length = len([file for file in os.listdir(f"{self._working_dir}/BaseWeights")])
            with open(f"{self._working_dir}/BaseWeights/BaseWeights_{length}.txt", "w", encoding="utf-8") as json_saver:
                json.dump(base_weights, json_saver, ensure_ascii=False, indent=4, sort_keys=True)

        except FileNotFoundError:
            Path(f"{self._working_dir}/BaseWeights").mkdir()

            length = len([file for file in os.listdir(f"{self._working_dir}/BaseWeights")])
            with open(f"{self._working_dir}/BaseWeights/BaseWeights_{length}.txt", "w", encoding="utf-8") as json_saver:
                json.dump(base_weights, json_saver, ensure_ascii=False, indent=4, sort_keys=True)

        except OSError as ex:
            print(ex)

    def _validate_setup(self, shape_file_folder_name, base_name, subunits, weight_index):
        """
        Valid setup for constructing the base
        """
        file_path = f"{self._working_dir}/{shape_file_folder_name}"

        # Check a directory of shapefiles exist
        assert os.path.isdir(file_path), f"Directory '{shape_file_folder_name}' was not found in {self._working_dir}"

        # Check enough files where submitted
        shape_file_files = sorted([file for file in os.listdir(file_path) if file.split(".")[-1] == "shp"])
        assert base_name in shape_file_files, f"{base_name} was not found in the list of files: {shape_file_files}"
        assert len(shape_file_files) > 1, f"Found {len(shape_file_files)} files, but at least two files are required" \
                                          f" to weight"

        # If subunits, check file can be loaded and return, else just return.
        if subunits:
            if Path(subunits).exists():
                subunits = ShapeObject(subunits)
            elif Path(f"{self._working_dir}/{subunits}").exists():
                subunits = ShapeObject(f"{self._working_dir}/{subunits}")
            else:
                raise FileNotFoundError(f"Sub unit weighting specified but no file called {subunits} found in "
                                        f"{self._working_dir}")

            assert weight_index >= 0, "Please specify the record base zero index for the column with the population " \
                                      "weight within it"

        base_index = [index for index, file in enumerate(shape_file_files) if file == base_name][0]
        shape_files = [ShapeObject(f"{file_path}/{file}") for file in shape_file_files]

        return ShapeObject(f"{file_path}/{shape_file_files[base_index]}"), base_index, shape_files, subunits

    def _set_format(self, weights):
        """
        If we only have area weights, then we won't have the same number of data points and will lead to an unexpected
        unpacking error. So we use the existance of sub units to determine the data that is written out
        """

        if self.sub_units:
            return {f"{gid}__{place}": {"Area": area, "Population": population}
                    for gid, place, area, population in weights}
        else:
            return {f"{gid}__{place}": {"Area": area} for gid, place, area in weights}

    def _format_weights(self, weights):
        """
        Now we have lists of data, but we want to structure these lists into dictionarys so we can parse the information
        quickly and also have the data have a greater level of human readability
        """
        return {key: self._set_format(place_weights) for key, place_weights in zip(weights.keys(), weights.values())}
