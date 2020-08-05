#!/usr/bin/python3 

import argparse
import json

from blackduck.HubRestApi import HubInstance

const_project_roles = [ "Project Code Scanner", "BOM Manager", "Project Viewer", "Project Manager", "Security Manager", "Policy Violation Reviewer"]

# ------------------------------------------------------------------------------
# Parse command line

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Creates project(s) on blackduck.com',
    epilog='''\
Note: When using the --project_file option the file format per line MUST be:

# Lines starting # are ignored, so are empty lines
project name[;group1[,group2,...,groupN]][;description][;version][;project_role1[,project_role2,...,project_roleN]]
'''
)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--project_name', '-p', type=str, help='Add a single project')
group.add_argument('--project_file', '-f', type=argparse.FileType(), help='Add all projects listed in the file')

parser.add_argument('--group', '-g', type=str, required=True, help='Default group to use (normally SAML). Optionally overridden when using a file.' )

parser.add_argument('--prefix', default='', type=str, help='String to add to the start of the project name')
parser.add_argument('--version', '-v', default='master', type=str, help='Version to use if not specified in the file')
parser.add_argument('--description', '-d', default='', type=str, help='Default description for all projects')
parser.add_argument('--project_roles', '-r', default='all', type=str, help=f"List of Project Roles to apply (default 'all'), or 'none' from {const_project_roles}")
parser.add_argument('--update', '-u', action="store_true", help="Existing project(s) are updated rather than skipped")

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

def parse_project_roles(project_roles_str=str):
    if project_roles_str == 'none':
        project_roles = []   
    elif project_roles_str == 'all':
        project_roles = const_project_roles
    else:
        role_names = project_roles_str.split(",")
        for role_name in role_names:
            if role_name not in const_project_roles:
                return False, f"Invalid Project Role '{role_name}'. Must be one of {const_project_roles}"
        project_roles = role_names
    
    return True, project_roles

def attach_groups_to_project(name, groups, projecct_roles):
    # Attach the user group(s) to the new project
    for group in groups:
        response = hub.assign_user_group_to_project(name, group, project_roles)
        if not response or response.status_code != 201:
            print(f"WARNING: Failed to assign group {group} to project {name}")
                    
def create_project_with_groups(name=str, version=str, description=str, groups=[], project_roles=[]):
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
    
    if response is not None:
        if response.status_code == 201:
            attach_groups_to_project(name, groups, projecct_roles)
            return True, f"Created project: {name}"
        elif response.status_code == 412:
            if args.update:
                project = hub.get_project_by_name(name)
                if project:
                    project_updated = project
                    project_updated['description'] = description
                    
                    # Delete all the current project's user groups
                    project_url = project['_meta']['href']
                    project_user_groups_url = f"{project_url}/usergroups"
                    response = hub.execute_get(project_user_groups_url)
                    if response:
                        project_user_groups = response.json()
                        for group in project_user_groups['items']:
                            hub.delete_user_group_from_project(name, group['name'])
                        
                        # Attach the new list of user groups
                        attach_groups_to_project(name, groups, project_roles)
                        hub.update_project_settings(project, project_updated)
                        return True, f"Updated project: {name}"
                    return False, f"Project does not exist: {name}"
                else:
                    return False, f"Project does not exist: {name}"
            else:
                return False, f"Project already exists: {name}"
        
        return False, f"Failed to create project: {name} : {response.status_code}"
        
    return False, f"No response from BlackDuck hub"
    
    
        
        
# ------------------------------------------------------------------------------  
# Main code

hub = HubInstance()
default_group = hub.get_user_group_by_name(args.group)
if default_group is None:
    raise SystemExit(f"Unable to find default group: ${args.group}")
#print(f"default_group: {default_group}")    

status, project_roles = parse_project_roles(args.project_roles)
if status == False:
    raise SystemExit(project_roles)

if args.project_name is not None:
    print(f"Adding the single project: {args.project_name}")
    status, response = create_project_with_groups(args.project_name, args.version, args.description, args.group.split(","), project_roles)
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
        
        print(f">> {line}")
        params = line.split(";")
        options = {
            'project_name':'',
            'groups': [args.group],
            'description': args.description,
            'version': args.version,
            'project_roles': project_roles,
            }
        option_names = list(options)
        index=0
        status = True
        for param in params:
            if index >= len(option_names):
                break

            print(f">>> param: {param}")
            if option_names[index] == "groups":
                param = param.split(",")
                if len(param) == 1 and not param[0]:
                    param = None
            
            if option_names[index] == "project_roles":
                status, param = parse_project_roles(param)
                if status == False:
                    print(f"ERROR: {param}. Not creating project {options['project_name']}")
                    break;
            
            if param:
                options[option_names[index]] = param
                
            index += 1

        if status:
            print(options)
            status, response = create_project_with_groups(options['project_name'], options['version'], options['description'], options['groups'], options['project_roles'])
            if status == False:
                print(f"ERROR: {response}")
            else:
                print(response)
