# Process tutorial to follow along

Within this directory are a bunch of jupyter notebooks that are designed to help you use this package. Each one 
represents a separate process, so you should follow them in order but anything with an ***A*** in the title is optional 
as it will not be used within the tutorial but may be useful for using your own dataset

## 1 Constructing Weights
This tutorial will show you how to create weights for places over time when these places change via area weight or 
sub-unit population. As an extension, it will also show you how to fix problems that might occur from multiple changes
occurring to a region that you do not directly observe.  

## 2 Place Reference
If your dataset has multiple levels, you will probably wish to create a unique place reference over time. Even if your
data set does not, you will need to go through this step as the output file is required in the next one. However, given
our data set is only at a single level, the output that is used in the next steps will not be generate from this in 
this case. 
 
###### todo we need to move Formatting into weightGIS

## 3 Weighting external data

This will show you how to use formatted data to construct your weight dataset, how you can use it, parse it, and 
re-construct it into a SQL data base

## 4 SQL Parser
This will show you how to use SQL to parse your data out of your database based on the formatting we used in tutorial 3.

###### todo We then need to add creating the geo look (within relational examples) and then add ID assignment  

