# Process tutorial to follow along

Within this directory are a bunch of jupyter notebooks that are designed to help you use this package. Each one 
represents a separate process, so you should follow them in order but anything with an ***A*** in the title is optional 
as it will not be used within the tutorial but may be useful for using your own dataset

## 1 Constructing Weights
This tutorial will show you how to create weights for places over time when these places change via area weight or 
sub-unit population. As an extension, it will also show you how to fix problems that might occur from multiple changes
occurring to a region that you do not directly observe.  

## 2A Place Reference
If your dataset has multiple levels, you will probably wish to create a unique place reference over time. In our data
set we only have data a single level that has been pre-formatted. However, weighted data requires that all names for a 
single district be standardised so you may need to learn how to do this for your own data-sets. This will walk you 
through a hypothetical on how to do it. 

###### todo we need to move Formatting into weightGIS

## 3 Weighting external data

This will show you how to use formatted data to construct your weight dataset, how you can use it, parse it, and 
re-construct it into a SQL data base

## 4 SQL Parser
This will show you how to use SQL to parse your data out of your database based on the formatting we used in tutorial 3.

 

