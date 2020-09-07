#!/usr/bin/python3 

import argparse
import json

from blackduck.HubRestApi import HubInstance

# ------------------------------------------------------------------------------
# Parse command line

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Update project(s) on blackduck.com',
    epilog='''\
Note: When using the --project_file option the file format per line MUST be:

# Lines starting # are ignored, so are empty lines
project name[;group1[,group2,...,groupN]][;description][;version]
'''
)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--project_name', '-p', type=str, help='Add a single project')
group.add_argument('--project_file', '-f', type=argparse.FileType(), help='Add all projects listed in the file')

parser.add_argument('--group', '-g', type=str, help='Default group to use (normally SAML). Optionally overridden when using a file.' )

parser.add_argument('--prefix', default='', type=str, help='String to add to the start of the project name')
parser.add_argument('--version', '-v', default='master', type=str, help='Version to use if not specified in the file')
parser.add_argument('--description', '-d', default='', type=str, help='Default description for all projects')

args = parser.parse_args()


# ------------------------------------------------------------------------------
# Functions
   
def get_user_groups(names=[]):
    #print(f"Getting groups: {names}")
    groups = []
    for name in names:
        if name == args.group:
            group = default_group
        else:
            group = hub.get_user_group_by_name(name)
            if not group:
                print(f"Unable to find group: {name}")
                return None
        
        groups.append(group['name'])
    return groups


def create_project_with_groups(name=str, version=str, description=str, groups=[]):
    #print(f"create_project_with_groups({name}, {version}, {description}, {groups})")
    if not groups:
        groups = [args.group]
    else:
        groups = get_user_groups(groups)
        if groups is None:
            return False, "Failed to find group"

    if args.prefix:
        name = f"{args.prefix} {name}"
        
    #print(f"Creating project: {name}")        
    response = hub.create_project(name, version, parameters = {
		'description': description
	})
    
    if response and response.status_code == 201:
        # Attach the user group(s) to the new project
        for group in groups:
            response = hub.assign_user_group_to_project(name, group, [])
            if not response or response.status_code != 201:
                print(f"WARNING: Failed to assign group {group} to project {name}")
        
        return True, f"Created project: {name}"
        
    if response.status_code == 412:
        return False, f"Project already exists: {name}"
        
    return False, f"Failed to create project: {name} : {response}"
        
        
# ------------------------------------------------------------------------------  
# Main code

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
print(f"{project}")

#roles = hub.get_project_roles()
#print(f"{roles}")

default_group = hub.get_user_group_by_name(args.group)
print(f"{default_group}")    

if project:
    project_updated = project

    #project_updated['name'] = "mlester-test-cli"
    #project_updated['description'] = "Hello world"
    #project_updated['owner'] = "mlester"
    #hub.update_project_settings(project, project_updated)
    
raise SystemExit(f"Done")


default_group = hub.get_user_group_by_name(args.group)
if default_group is None:
    raise SystemExit(f"Unable to find default group: ${args.group}")
#print(f"default_group: {default_group}")    

if args.project_name is not None:
    print(f"Adding the single project: {args.project_name}")
    status, response = create_project_with_groups(args.project_name, args.version, args.description)
    if status == False:
        raise SystemExit(f"FATAL: {response}")
    else:
        print(response)
else:
    f = args.project_file
    print(f"Parsing the projects file: {f.name}")
    for line in f.readlines():
        line = line.strip()
        if not line or line[0] == "#":
            continue
        
        #print(f">> {line}")
        params = line.split(";")
        options = {'project_name':'', 'groups': [args.group], 'description': args.description, 'version':args.version}
        option_names = list(options)
        index=0
        for param in params:
            if index >= len(option_names):
                break
            
            if option_names[index] == "groups":
                param = param.split(",")
                if len(param) == 1 and not param[0]:
                    param = None
            
            if param:
                options[option_names[index]] = param
                
            index += 1

        #print(options)
        status, response = create_project_with_groups(options['project_name'], options['version'], options['description'], options['groups'])
        if status == False:
            print(f"ERROR: {response}")
        else:
            print(response)
