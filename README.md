# HydrusTagCluster
A tool for Hydrus Network to visualize files that share tags.


# Setup
- install the libraries from the import section in main.py
- Provide API Key and API Url to the main.py
- In hydrus create a tab called "CLUSTER"
- use the plot function and provide a query and other settings to get the result you want

# Features
- helps the user to find files of groups with same tags / low diversity
- clicking on a cluster opens the files in a tab called "CLUSTER" for inspection and processing

# Patchlog

## V0.1
Known Limitations:
- Images do not scale correctly
- Aspect ratio has to be set manually
- Mouse Hovering over images causeses issues
- performance gets very low with lots of clusters
- currently used hard saved tags instead of displayed


# Future Ideas
- cluster limit, example: show only top 20 clusters
- sub clusters
- sorting scheme key use for hierarchical clustering
