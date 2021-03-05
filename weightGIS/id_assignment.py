from csvObject import CsvObject, write_csv
from shapeObject import ShapeObject
from shapely.geometry import Point
from pathlib import Path


def locate_individuals(ids_path, lowest_level_shapefile_path, geo_lookup, east_i, north_i,
                       shape_match_index, write_directory, write_name):
    """
    This will assist you locating individuals with a geo lookup files

    :param ids_path: The path to a csv file filled with id's with a eastings and northings
    :type ids_path: Path | str

    :param lowest_level_shapefile_path: path to the lowest level shapefile you used in your geo reference
    :type lowest_level_shapefile_path: Path | str

    :param geo_lookup: The path to the geo lookup
    :type geo_lookup: Path | str

    :param east_i: Index of the eastings in the id data
    :type east_i: int

    :param north_i: Index of the northings in the id data
    :type north_i: int

    :param shape_match_index: Index of the mating parameter, should be common in both geo reference and shapefile
    :type shape_match_index: int

    :param write_directory: Saved file will be writen here
    :type write_name: Path | str

    :param write_name: The name of the file to write
    :type write_name: str

    :return: Nothing, write the file then stop
    :rtype: None
    """

    id_file = CsvObject(ids_path)
    geo_file = CsvObject(geo_lookup)
    shape_obj = ShapeObject(lowest_level_shapefile_path)

    # Create a list of unique easting_westing coordinates to avoid unnecessary iteration
    unique_places = sorted(list(set([f"{respondent[east_i]}__{respondent[north_i]}"
                                     for respondent in id_file.row_data])))

    # Create an id: all other rows lookup so we can identify each location from the lowest
    geo_lookup = {row[shape_match_index]: row for row in geo_file.row_data}

    # Link all the geometry
    geo_link = create_geo_link(unique_places, geo_file, geo_lookup, shape_obj, shape_match_index)

    output_rows = []
    for respondent in id_file.row_data:
        # Isolate the rows that are not east/north
        non_location = [r for i, r in enumerate(respondent) if i not in (east_i, north_i)]

        # Prepend this along with the geo_link birth location
        birth_location = f"{respondent[east_i]}__{respondent[north_i]}"
        output_rows.append(non_location + geo_link[birth_location])

    headers = [h for i, h in enumerate(id_file.headers) if i not in (east_i, north_i)] + geo_file.headers
    write_csv(write_directory, write_name, headers, output_rows)


def create_geo_link(unique_places, geo_file, geo_lookup, shape_obj, shape_match_index):
    """
    This will iterate each unique place, and determine where the point is based on the geo lookup

    :param unique_places: A list of unique places eastings and northings that have been put in a string with a __
        delimiter
    :type unique_places: list[str]

    :param geo_file: The csv file for the geo lookup, used to determine row length of failed
    :type geo_file: CsvObject

    :param geo_lookup: The GID: Geographic lookup row dict
    :type geo_lookup: dict

    :param shape_obj: The loaded lowest level shapefile
    :type shape_obj: ShapeObject

    :param shape_match_index: The index to load the csv information from
    :type shape_match_index: int

    :return: A dict of easting__northing: geo row to be used to match to individuals
    :rtype: dict
    """
    geo_link = {}
    # Determine the location of each place
    for index, coordinate in enumerate(unique_places):
        if index % 100 == 0:
            print(f"{index + 1}/{len(unique_places)}")

        # Isolate the two coordinates
        east, north = coordinate.split("__")

        if len(east) == 0 or len(north) == 0:
            geo_link[coordinate] = ["No or invalid coordinates" for _ in range(geo_file.row_length)]
        else:
            point = Point(float(east), float(north))

            location_id = point_identification(shape_obj, point, shape_match_index)
            try:
                geo_link[coordinate] = geo_lookup[location_id]
            except KeyError:
                print(f"Failed to find {location_id}")
                geo_link[coordinate] = ["ID not found in geolookup" for _ in range(geo_file.row_length)]

    return geo_link


def point_identification(shapefile, point, shape_match_index):
    """
    Located the point within the shapefile

    :param shapefile: The ShapeObject of the lowest level shapefile
    :type shapefile: ShapeObject

    :param point: A shapely Point from the eastings and northings
    :type point: Point

    :param shape_match_index: The index to use as the match
    :type shape_match_index: int

    :return: A match record from the shapefile that was returned
    :rtype:
    """
    for shape, record in zip(shapefile.polygons, shapefile.records):
        if shape.contains(point):
            return str(record[shape_match_index])

    # If we fail to find the location within, create a list of all the distances
    lowest_list = [[point.distance(shape), record[shape_match_index]] for shape, record in zip(
        shapefile.polygons, shapefile.records)]

    # Return the smallest distance of the sorted list [0] record [1] if we find anything. Else Return the string of None
    try:
        return str(sorted(lowest_list)[0][1])
    except KeyError:
        return "None"

