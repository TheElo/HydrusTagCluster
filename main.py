"""

Controls
- use "v" to enable and disable the hover window
- use "e" to lock and not update the hover window

"""

import hydrus_api, hydrus_api.utils
import matplotlib
import fnmatch
import matplotlib.pyplot as plt
import squarify
import mplcursors
import numpy as np
from io import BytesIO
from PIL import Image
import functools
import time


def get_service_key_by_name(client, service_name):
    # Retrieve the services dictionary using the client
    services_dict = client.get_services()

    # Initialize a variable to store the service key
    service_key = None

    # Iterate through the services dictionary
    for key, service_info in services_dict['services'].items():
        if service_info['name'] == service_name:
            service_key = key
            break

    return service_key


def CreateDictFromID6(SearchFileIDs, tag_service=None, tag_service_key=None, add_hashes=True, blacklist=None):
    """

    :param tag_service: string -> "local", "my tags", "all known tags", ... 
    :param blacklist: List of patterns (strings) to exclude from the results.
    :return:
    """
    MyDict = []
    SkippedFiles = 0
    if not tag_service_key:
        if tag_service:
            tag_service_key = get_service_key_by_name(client, tag_service)  
        else:
            tag_service = "all known tags"
            tag_service_key = get_service_key_by_name(client, tag_service)  

    for file_ids in hydrus_api.utils.yield_chunks(SearchFileIDs, 512):  
        a = client.get_file_metadata(file_ids=file_ids)

        for y in range(0, len(a)):
            try:
                tags = a[y]["tags"][f"{tag_service_key}"]["storage_tags"]["0"]
            except:
                tags = []
            if tags:
                # Apply blacklist to tags
                if blacklist:
                    tags = [tag for tag in tags if not any(fnmatch.fnmatch(tag, pattern) for pattern in blacklist)]
                if add_hashes == True:
                    MyDict.append({'file_id': a[y]["file_id"], 'hash': a[y]["hash"],
                                    'tags': tags})
                else:
                    MyDict.append({'file_id': a[y]["file_id"], 'tags': tags})

    return MyDict


def cluster_files(file_data):
    # Create a dictionary to hold clusters. Key is a tuple of sorted tags, value is a list of file_ids.
    clusters = {}
    for file_info in file_data:
        # Sort the tags to use them as a key in the dictionary.
        sorted_tags = tuple(sorted(file_info['tags']))
        if sorted_tags in clusters:
            clusters[sorted_tags].append(file_info['file_id'])
        else:
            clusters[sorted_tags] = [file_info['file_id']]

    # Convert the dictionary to a list of dictionaries for easier handling.
    cluster_data = []
    for i, (tags, file_ids) in enumerate(clusters.items()):
        cluster_data.append({
            'cluster_id': i,
            'file_count': len(file_ids),
            'file_ids': file_ids,
            'tags': list(tags)
        })

    return cluster_data


def DisplayFileIDs(tabname, fileIDs, focus=True):
    tabs = client.get_page_list()
    page_keys = [d['page_key'] for d in tabs if d['name'] == tabname]
    TabKey = next(iter(page_keys), None)
    if not TabKey:
        print(f"No Tabkey found, you have to create the tab called {tabname}")
    else:
        # send files to page
        client.add_files_to_page(page_key=TabKey, file_ids=fileIDs)
        # focus on page
        if focus == True:
            client.focus_page(TabKey)


def plot_treemap(cluster_data):
    # Extract data for visualization
    sizes = [cluster['file_count'] for cluster in cluster_data]

    # Create a treemap
    fig, ax = plt.subplots(figsize=(10, 8))
    squarify.plot(sizes=sizes, alpha=.7, text_kwargs={'fontsize': 0}, edgecolor='black', linewidth=2)

    # Add hover tooltips and click event handling using mplcursors
    cursor = mplcursors.cursor(hover=True)

    @cursor.connect("add")
    def on_add(sel):
        cluster_index = int(sel.index)
        tags_str = ', '.join(cluster_data[cluster_index]['tags'])
        file_count = cluster_data[cluster_index]['file_count']
        sel.annotation.set(text=f"Tags: {tags_str}\nFiles: {file_count}")

    def on_click(event):
        if event.inaxes == ax:
            x, y = event.xdata, event.ydata
            for i, rect in enumerate(ax.patches):
                # Debugging: print the rectangle's coordinates and dimensions
                # print(f"Rectangle {i}: xy={rect.get_xy()}, width={rect.get_width()}, height={rect.get_height()}")

                # Check if the click is within the rectangle
                if (x >= rect.get_x() and x <= rect.get_x() + rect.get_width()) and \
                   (y >= rect.get_y() and y <= rect.get_y() + rect.get_height()):
                    # print(f"Clicked Cluster {i}\nFile IDs: {cluster_data[i]['file_ids']}")
                    print(f"\nFile IDs: {cluster_data[i]['file_ids']}")
                    DisplayFileIDs("CLUSTER", cluster_data[i]['file_ids'], focus=True)
                    break

    fig.canvas.mpl_connect('button_press_event', on_click)

    plt.title(f'{query}')
    plt.axis('off')  # Turn off the axis to make it look cleaner
    plt.show()



def plot_treemap_thumbs(cluster_data):
    # Extract data for visualization
    sizes = [cluster['file_count'] for cluster in cluster_data]
    thumbnails = []

    # Fetch thumbnails for each cluster
    for cluster in cluster_data:
        file_id = cluster['file_ids'][0]  # Use the first file_id from the cluster
        image = client.get_thumbnail(file_id=file_id)
        img = Image.open(BytesIO(image.content))
        thumbnails.append(img)

    # Create a treemap with thumbnails
    fig, ax = plt.subplots(figsize=(19, 12))
    squarify.plot(sizes=sizes, alpha=.7, edgecolor='black', linewidth=0.5)
    # squarify.plot(sizes=sizes, alpha=.7, text_kwargs={'fontsize': 0}, edgecolor='black', linewidth=0.5)

    # Add thumbnails to the treemap
    for i, rect in enumerate(ax.patches):
        img = thumbnails[i]
        rect_width = rect.get_width()
        rect_height = rect.get_height()

        # Calculate the scaling factor while maintaining aspect ratio
        img_width, img_height = img.size
        scale_factor = min(rect_width / img_width, rect_height / img_height)
        scaled_width = img_width * scale_factor
        scaled_height = img_height * scale_factor

        x, y = rect.get_xy()
        # Add padding to the image within the rectangle
        padding = 0.04  # Adjust the padding as needed
        padded_width = scaled_width * (1 - 2 * padding)
        padded_height = scaled_height * (1 - 2 * padding)
        x_offset = (rect_width - padded_width) / 2
        y_offset = (rect_height - padded_height) / 2

        ax.imshow(img, extent=(x + x_offset, x + x_offset + padded_width,
                               y + y_offset, y + y_offset + padded_height),
                  aspect='auto', zorder=1)

    # Add hover tooltips and click event handling using mplcursors

    cursor = mplcursors.cursor(hover=True)


    @cursor.connect("add")
    def on_add(sel):
        cluster_index = sel.index
        tags_str = ', '.join(cluster_data[cluster_index]['tags'])
        file_count = cluster_data[cluster_index]['file_count']
        sel.annotation.set(text=f"Tags: {tags_str}\nFiles: {file_count}" )


    def on_click(event):
        if event.inaxes == ax:
            x, y = event.xdata, event.ydata
            for i, rect in enumerate(ax.patches):
                # Check if the click is within the rectangle
                if (x >= rect.get_x() and x <= rect.get_x() + rect.get_width()) and \
                   (y >= rect.get_y() and y <= rect.get_y() + rect.get_height()):
                    # print(f"Clicked Cluster {i}\nFile IDs: {cluster_data[i]['file_ids']}")
                    print(f"\nFile IDs: {cluster_data[i]['file_ids']}")
                    DisplayFileIDs("CLUSTER", cluster_data[i]['file_ids'], focus=True)
                    break

    fig.canvas.mpl_connect('button_press_event', on_click)

    plt.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=0.99, wspace=0.2)
    plt.title(str(query))
    plt.axis('off')  # Turn off the axis to make it look cleaner
    plt.show()



def plot(query, minimum_cluster_size=8, tag_service_file_ids="my tags", tag_service_tags="my tags", use_thumbs=True, blacklist=None, whitelist=None):
    def CreateDictFromID6(SearchFileIDs, tag_service=None, tag_service_key=None, add_hashes=True, blacklist=None, whitelist=None):
        # to drop tags that are not beneficial to clustering, like metadata, page, favourites.. # # Blacklist - blacklist tags will be ignored for the cluster formation, use that for page or filenames, tags the are irrelevant for your clustering
        MyDict = []
        SkippedFiles = 0
        if not tag_service_key:
            if tag_service:
                tag_service_key = get_service_key_by_name(client, tag_service)
            else:
                tag_service = "all known tags"
                tag_service_key = get_service_key_by_name(client, tag_service)

        for file_ids in hydrus_api.utils.yield_chunks(SearchFileIDs, 512):
            a = client.get_file_metadata(file_ids=file_ids)
            for y in range(len(a)):
                try:
                    tags = a[y]["tags"][f"{tag_service_key}"]["storage_tags"]["0"]
                except:
                    tags = []

                if not tags:
                    continue

                # Apply whitelist or blacklist to the tags
                if whitelist:
                    # Only include tags present in the whitelist
                    filtered_tags = [tag for tag in tags if any(fnmatch.fnmatch(tag, pattern) for pattern in whitelist)]
                elif blacklist:
                    # Exclude tags that match any patterns in the blacklist
                    filtered_tags = [tag for tag in tags if not any(fnmatch.fnmatch(tag, pattern) for pattern in blacklist)]
                else:
                    # If neither is provided, use all tags as they are
                    filtered_tags = tags

                if not add_hashes:
                    MyDict.append({'file_id': a[y]["file_id"], 'tags': filtered_tags})

                else:
                    MyDict.append({'file_id': a[y]["file_id"], 'hash': a[y]["hash"], 'tags': filtered_tags})


        return MyDict

    tag_service_key_all = get_service_key_by_name(client, "all known tags")

    # get file ids from query
    file_ids = client.search_files(tags=query, file_sort_type=13, tag_service_name=tag_service_file_ids) 

    # collect tags
    # dict = CreateDictFromID6(file_ids, tag_service=tag_service_tags, add_hashes=False, blacklist=blacklist)
    if whitelist:
        dict = CreateDictFromID6(file_ids, tag_service=tag_service_tags, add_hashes=False, whitelist=whitelist)
    else:
        dict = CreateDictFromID6(file_ids, tag_service=tag_service_tags, add_hashes=False, blacklist=blacklist)
    # create filter and sort data
    cluster_data = cluster_files(dict)
    cluster_data = [cluster for cluster in cluster_data if cluster['file_count'] >= minimum_cluster_size]
    cluster_data.sort(key=lambda x: x['file_count'], reverse=True)

    if use_thumbs:
        plot_treemap_thumbs(cluster_data)
    else:
        plot_treemap(cluster_data)




# API CONFIGURATION
API_KEY = "YOUR API KEY HERE"
API_URL = "http://127.0.0.1:45869/"


# initialize
# Connect to Hydrus
client = hydrus_api.Client(access_key=API_KEY, api_url=API_URL)


# examples

# blacklist example, this will avoid having the page, filename and title tags have an impact on clusterisation
# plot(query=["system:archive", "system:number of tags < 5"], blacklist=["page:*", "filename:*", "title:*"])

# this sets the minimal cluster size to 6, clusters smaller than that won't be displayed
# plot(query=["playlist:1906 favs"], minimum_cluster_size=6)

# whitelist use this will only cluster by the thread tags, all other tags will be ignored for clustering, try also series, character, person, ... namespaces
# plot(["thread:*", "system:inbox"], whitelist=["thread:*"], tag_service_tags="metadata", tag_service_file_ids="metadata", minimum_cluster_size=3, use_thumbs=True)

# performance mode without images
# plot(["beach", "system:inbox"], use_thumbs=False)

# specify tag service, here we search for file ides in my tags using the query and then we use ptr to cluster the files by their tags from there.
# plot(["system:archive", "system:number of tags < 4"], tag_service_file_ids="my tags", tag_service_tags="public tag repository")

plot(["character:samus aran"])

