'''
Created on October 18, 2018

@author: bboule

Processes Version in a Hub Project
Looks for Snippets that belong to a File that has already been declared in the BOM
Ignores found Snippets that are already part of a BOM Match

'''
from bds.HubRestApi import HubInstance
from sys import argv
import json
import copy
import argparse

hub = HubInstance()

parser = argparse.ArgumentParser(description="Ignore Snippets that already have BOM File entries to a Component")
parser.add_argument('projectname', type=str, help='Project Name to edit')
args = parser.parse_args()

projects = hub.get_projects(limit=100)
target_project_name = args.projectname
print("Got Project Name as:", target_project_name)
print ("total projects found: %s" % projects['totalCount'])

# Find the Project ID of a project given it's name
def get_project_id(name): 
    projectlist = list()
    for project in projects['items']:
        uid = project['_meta']['href'].replace(hub.get_urlbase() + "/api/projects/", "")
        name = project['name']
        if name == target_project_name:
            return project
    return None

# Get the Versions of a project
# Takes the json representation of the project
# Returns a list of tuples
# Each tuple has 4 items:
#    project name, project id, version name, version id
def get_versions(project):
    versions = hub.get_project_versions(project)
    project_name = project['name']
    project_uid = project['_meta']['href'].replace(hub.get_urlbase() + "/api/projects/", "")
    version_list = versions['items']
    version_data = []
    for cur_version in version_list:
        version_name=cur_version['versionName']
        version_uid = cur_version['_meta']['href'].replace(hub.get_urlbase() + "/api/projects/" + project_uid + "/versions/", "")
        version_data.append((project_name, project_uid, version_name, version_uid))
    return version_data

# Get the Bom Components for a Project ID + Version ID Pair
# Returns the JSON representation from the HUB in object form
def get_bom_components(project_id, version_id): 
    version = hub.get_version_by_id(project_id, version_id)
    return hub.get_version_components(version)

# Takes the snippet entries from a Hub snippet-bom-entries request and organizes 
# them into a dictionary keyed by the path of the file the snippet was found in
def get_snippet_path_map(snippet_entries):
    snippet_map = {}
    for cur_snippet in snippet_entries['items']:
        path = cur_snippet['compositePath']['path']
        if path in snippet_map:
            print("Possible overwrite of snippet in map - more than on snippet for: ", path)
        snippet_map[path] = cur_snippet
    return snippet_map

# Takes a Bom Component representation + It's file data representation + the map of path -> Snippets
# Returns a dict that has keys as paths
# Each value in the map is the Bom Component that declares the path + the snippets that are for that Parth
def get_component_file_map_by_path(bom_component_json, component_files, snippets):
    component_path_map = {}
    for cur_file in component_files['items']:
        cur_path = cur_file['filePath']['path']
        if cur_path in snippets:
            component_path_map[cur_path] = (bom_component_json, snippets[cur_path])
    return component_path_map

# Prints a user visible report of a map from path -> component + snippets
# The argument for this is the output of get_component_file_map_by_path
# This report details what snippets the script is going to ignore
def print_snippet_component_report(component_snippet_by_path_map):
    print("******************* Snippet -> Component potential matches ********************************")
    if not component_snippet_by_path_map:
        print("No Snippets or Components")
    for cur_path in component_snippet_by_path_map:
        cur_component_candidate = component_snippet_by_path_map[cur_path][0]
        cur_snippet = component_snippet_by_path_map[cur_path][1]
        print(cur_path, ": ")
        print("--------------------Component: ")
        #print(json.dumps(cur_component_candidate, indent=2))
        print("Component Name: ", cur_component_candidate['componentName'])
        print("Component Version: ", cur_component_candidate['componentVersionName'])
        print("Unconfirmed/Ignored Snippets: Present")
        #print(json.dumps(cur_snippet, indent=2))
        print("***************************************************************************************")
    print()

# Gets the file paths that a snippet-bom-entries response represents
# This returns a flattened set of paths represented by the snippets
def getSnippetNames(snippet_bom_entries):
    files = set()
    for cur_item in snippet_bom_entries['items']:
        files.add(str(cur_item['name'] + " - " + cur_item['compositePath']['path']))
    return files

# Ignore Snippets for a given Hub Release ID
# Takes 2 parameters:
# The first is the Hub Version ID (project ID not needed)
# The second is a dict from path -> component + snippets
# The component in this case is the component that already declares the snippets.
# Returns the # of entries that were sent to the Hub to ignore
def ignore_snippet_matches(hub_release_id, component_snippet_by_path_map):
    map_copy = copy.deepcopy(component_snippet_by_path_map)
    snippets_ignored = 0
    for cur_path in map_copy:
        print("Ignoring snippet for path: ", cur_path)
        cur_component_candidate = map_copy[cur_path][0]
        cur_snippet = map_copy[cur_path][1]
        cur_num_snippet_bom_entries = len(cur_snippet['fileSnippetBomComponents'])
        #print("Component in place:")
        print("# Snippet entries to ignore: ", cur_num_snippet_bom_entries)
        #print(cur_component_candidate)
        #print("Snippet to ignore: ")
        #print(cur_snippet)

        if cur_component_candidate is not None and cur_snippet is not None:
            cur_status = hub.ignore_snippet_bom_entry(hub_release_id, cur_snippet)
            if cur_status == 1:
                print("SUCCESS")
            else:
                print("FAILED: ", cur_status)
            snippets_ignored = snippets_ignored + cur_num_snippet_bom_entries

    return snippets_ignored

# Returns the set of paths in the files entry for a component
# This is a flattened set, the set will contain duplicates if the Hub has multiple usages in the BOM for 
# the same path
def get_paths_for_component_files_entry(component_files_entry):
    paths = set()
    for cur_item in component_files_entry['items']:
        paths.add(cur_item['filePath']['path'])
    return paths

# Process a single component ina a BOM and ignore snippets that match a file already declared in the BOM
# Args:
#   Hub Project ID
#   Hub Version ID
#   BOM Component to process
#   Dict of Paths -> Snippets
# Returns the total # of snippets that were requested to be ignored
def process_bom_component(project_id, version_id, bom_component, snippet_path_map):
    item_link = bom_component['_meta']['href']

    print("*******************************************************")
    component_id = item_link.split("/")[-3]
    component_version_id = item_link.split("/")[-1]
    
    print('Processing:')
    print(bom_component['componentName'], ": ", bom_component['componentVersionName'])
    
    component_files_json = hub.get_file_matches_for_component_with_version(project_id, version_id, \
        component_id, component_version_id)  
    
    print("File paths associated with this component: ")
    for path in get_paths_for_component_files_entry(component_files_json):
        print(path)
    
    component_by_file_map = get_component_file_map_by_path(bom_component, component_files_json, snippet_path_map)
    print_snippet_component_report(component_by_file_map)

    if len(component_by_file_map) > 0:
        return ignore_snippet_matches(version_id, component_by_file_map)
    
    return 0


# Main method
def main():
    target_project = get_project_id(target_project_name)

    print("Found target project: " + target_project['name'])

    version_data = get_versions(target_project)

    print("Got version data as: ", version_data)

    for cur_version in version_data:
        project_name = cur_version[0]
        project_id = cur_version[1]
        version_name = cur_version[2]
        version_id = cur_version[3]

        # Get Snippets and process them into a map based on path
        snippet_data = hub.get_snippet_bom_entries(project_id, version_id)
        snippet_path_map = get_snippet_path_map(snippet_data)
        
        print("***********Project Snippets ***************************")
        print("# Snippet Files: ", snippet_data['totalCount'])
        print("Snippet file list:")
        for file in getSnippetNames(snippet_data):
            print(file)

        version_components = get_bom_components(project_id, version_id)
        total_snippets_ignored = 0
        
        for cur_item in version_components['items']:
            total_snippets_ignored = total_snippets_ignored + process_bom_component(project_id, version_id, cur_item, 
                snippet_path_map)

        print("Ignored: ", total_snippets_ignored, " for: ", project_name, " - ", version_name)
    
if __name__ == "__main__":
    main()

        



