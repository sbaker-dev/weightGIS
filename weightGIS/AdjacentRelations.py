from shapely.geometry import MultiPolygon, Polygon, mapping
from shapeObject import ShapeObject
from miscSupports import write_json


class AdjacentRelations:
    def __init__(self, shapefile_path, record_identifier, write_directory, write_name):
        self.shapefile = ShapeObject(shapefile_path)
        self.rec_id = record_identifier
        self._write_dir = write_directory
        self._write_name = write_name

    def border_overlap(self):
        """
        For each shape in the shapefile, this method will iterate through all the points in all the other shapefiles
        looking for matches. If found, then it will return the identifier record and attach that to the identifier
        record of the current shape. It will then write the data out to the directory as a json database
        """

        matches = {}
        for index, (shape, record) in enumerate(zip(self.shapefile.polygons, self.shapefile.records)):
            if index % 100 == 0:
                print(f"{index} / {len(self.shapefile.records)}")

            matches[record[self.rec_id]] = self._determine_overlap(index, self._extract_points(shape))

        write_json(matches, self._write_dir, self._write_name)
        print("Constructed Overlap")

    def _determine_overlap(self, index, current_points):
        """
        Iterate through the contents of the shapefile looking for polygons with matching points to the current point set
        """
        border_shapes = []
        for i, (shape, record) in enumerate(zip(self.shapefile.polygons, self.shapefile.records)):
            if self._match(current_points, self._extract_points(shape)) and i != index:
                border_shapes.append(record[self.rec_id])
        return border_shapes

    @staticmethod
    def _extract_points(polygon):
        """
        Polygonal geometry in shapefile can be Polygon or Multipolygon. The later is a list of Polygons, so we need to
        add an additional loop to extract points than when we have polygons.
        """
        if isinstance(polygon, Polygon):
            return {point for polygon in mapping(polygon)["coordinates"] for point in polygon}

        elif isinstance(polygon, MultiPolygon):
            return {point for shape in mapping(polygon)["coordinates"] for polygon in shape for point in polygon}

        else:
            print(f"Unexpected Type {type(polygon)}")

    @staticmethod
    def _match(polygon_lines, border_lines):
        """
        If there are any points in both sets that are common return True, else False
        """
        if len(set(polygon_lines) & set(border_lines)) > 0:
            return True
        else:
            return False
