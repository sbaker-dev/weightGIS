from weightGIS import ConstructWeights, AssignWeights

if __name__ == '__main__':

    # Construct Weights ################################################################################################
    # To start with we need to see when changes occur, to do this we need to compare a set of shapefiles and see if a
    # polygon stays the same in the next iteration of that place in time. You need to provide a working directory with
    # a folder called "Shapefiles" with all the shapefiles you want to compare in. You also need to put a population
    # shapefile in the project directory, not the shapefile directory, if you want to do population sub weighting and
    # set a weight index for the base zero column index that holds the population information. Check other keyword
    # arguments to see if the defaults are valid, and then run!

    project_directory = r"C:\Users\Samuel\PycharmProjects\weightGIS\Example\ExampleData"
    base_shape = "1951.shp"
    population_shape = "1921.shp"

    ConstructWeights(project_directory, base_shape, population_shape, weight_index=2).construct_base_weights()

    # Create Change Log ################################################################################################
    # Now we have our place's over time, we need to write out a file so the user can look up all the changes they need
    # in terms of dates for these places. In this case you just need to provide the path to file you just created. We
    # can just save the information to our working directory. Given in this case our unit's didn't have a class, then we
    # need to set name_class to be False.

    AssignWeights("BaseWeights_0.txt", project_directory, "ChangeLog").write_out_changes()

    # Weights by Dates #################################################################################################
    # Then we want to take these weights and construct a database that has the weights relative to the dates that places
    # change over time in. First we need to load the weights be generated in the ConstructWeights. Then load in the file
    # you have create with dates about these places, in this case mine is in dates_directory. It may be the case that
    # you only observe the dates of a census in a general year format, but the changes you have are more specific in
    # terms of year-month-day. If this is the case, you need to adjust the year format by assigning a month and day to
    # the assign_weights call method so we can look at changes occurring between them. Finally provide a write directory
    # and name, and then your finished!

    AssignWeights("BaseWeights_0.txt", project_directory, "1951_weights_by_dates").assign_weights_dates("0401")
