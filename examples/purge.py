'''
Created on Dec 26 2018 from duplicate.py

@author: kumykov as duplicates.py
modified by JJerpseth to remove duplicate scans regardless of being duplicates.

Enumerates projects and project releases in the database and runs BOM comparisons
If two releases are found, delete the older one(s)

'''

from blackduck.HubRestApi import HubInstance


hub = HubInstance()

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
        print ("index is ".format(index))
        va = versionlist[index]
        components = hub.get_version_components(va)
        codelocations = hub.get_version_codelocations(va)
        # hub.execute_delete(va['_meta']['href'])
        print ("version {} has {} codelocations".format(va['versionName'], codelocations['totalCount']))
        if codelocations > 0:
            for codelocation in codelocations['items']:
                print (codelocation['_meta']['href'])
                locationid = codelocation['_meta']['href'].split("/")[5]
                print (locationid)
                print (hub.delete_codelocation(locationid))
        print(hub.execute_delete(va['_meta']['href']))
