'''
Created on Jul 6, 2018

@author: kumykov

Enumerates projects and project releases in the database and runs BOM comparisons
If two releases are identical, there is an option to delete older one

'''

from bds.HubRestApi import HubInstance

username="sysadmin"
password="genesys"

# To clean up duplicates set cleanup = True
cleanup = False

urlbase="https://ec2-18-208-209-223.compute-1.amazonaws.com"


hub = HubInstance(urlbase, username, password, insecure=True)

projects = hub.get_projects(limit=100)

print ("total projects found: %s" % projects['totalCount'])

for project in projects['items']:
    print (project['name'])
    versions = hub.get_project_versions(project)
    print ("\t versions found %s" % versions['totalCount'])
    versionlist = versions['items']
    if len(versionlist) == 1:
        continue
    for index in range(len(versionlist) - 1):
        va = versionlist[index]
        components = hub.get_version_components(va)
        if cleanup and components['totalCount'] == 0:
            hub.execute_delete(va['_meta']['href'])
            continue
        vb = versionlist[index + 1]
        result = hub.compare_project_versions(va, vb)
        codelocations = hub.get_codelocations(va)
        print ("comparing version {} to version {} total changes {}".format(
            vb['versionName'], 
            va['versionName'],
            result['totalCount']))
        print ("version {} has {} codelocations".format(va['versionName'], codelocations['totalCount']))
        if cleanup and result['totalCount'] == 0:
            print(hub.execute_delete(va['_meta']['href']))
            for codelocation in codelocations['items']:
                print (codelocation['_meta']['href'])
                locationid = codelocation['_meta']['href'].split("/")[6]
                print (locationid)
                print (hub.delete_codelocation(locationid))

