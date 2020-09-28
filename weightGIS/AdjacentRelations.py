from shapeObject import ShapeObject
from shapely.geometry import MultiPolygon, Polygon, mapping


class AdjacentRelations:
    def __init__(self, shapefile_path, record_identifier):
        self.shapefile = ShapeObject(shapefile_path)
        self.rec_id = record_identifier

    def border_overlap(self):
        for index, (shape, record) in enumerate(zip(self.shapefile.polygon_geometry, self.shapefile.polygon_records)):

            matches = self._determine_overlap(index, self._extract_points(shape))
            print(matches)
            break

    def _determine_overlap(self, index, current_points):
        """
        Iterate through the contents of the shapefile looking for polygons with matching points to the current point set
        """
        border_shapes = []
        for i, (shape, record) in enumerate(zip(self.shapefile.polygon_geometry, self.shapefile.polygon_records)):
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





AdjacentRelations(r"I:\Work\Shapefiles\Districts\EW1951_lgdistricts\EW1951_lgdistricts.shp", 0).border_overlap()