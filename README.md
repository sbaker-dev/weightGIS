# weightGIS

At its core weightGIS is designed to help standardise shapefile data to a base year, but weightGIS also contains some 
other supporting pipelines/methods relating to GIS to help you undertake research in this context. 

## Getting started
weightGIS is available via Pypi so you can just pip install it, if your a windows user the following command can
be used from the terminal. 

```shell script
python -m pip install weightGIS
```

### Weight Geographical Regions to a base year
weightGIS is designed first and foremost to allow you to simply create a cross relationship weight in both area and sub 
unit population (where available). There may be instances where you have a panel of shapefiles, but need to standardise 
them over time. Border changes that are not reflective of underling changes can cause empirical problems but data will 
exist for these places based on those changes. By standardising to a base year, this can be resolved, and data that is 
held can then be weighted accordingly. 

A fully worked example via a jupyter notebook called weightGIS Example, which is also available as an example script, 
and some example data is available within the Example folder of this repository that you can download to have a play 
around with. If you choose to convert it into a SQL database their is another worked example as SQLExample to show you
how you can use the class within weightGIS to aid accessing your data.

### Determine Relations Within and Between Shapefiles 
It can also be used for other relationships, so as getting adjacent polygons or construction a relational file of how
differing levels of geographic sedation relate to each other. Examples of these can be found within RelationExamples
jupyter Notebooks

#### Adjacent Polygons
You may wish to relate polygons by nearest neighbours, or N neighbours of nearest neighbours, and this will help you
construct these relationships.

#### Geographical Relations
We are often have shapefiles at multiple levels of separation, but want to know the links between them. By using 
GeoLookup, you can relate a list of shapefiles to a base shapefile, where the base is the lowest level of separation.


