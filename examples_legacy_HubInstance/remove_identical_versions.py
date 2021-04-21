'''
Created on Jul 18, 2018

@author: kumykov

Compares adjacent versions in a project and removes older one if there are no changes detected

'''
from blackduck.HubRestApi import HubInstance

# To clean up duplicates set cleanup = True

cleanupEmpty = False
cleanup = True


hub = HubInstance()

project = hub.get_project_by_id('3108a69a-71c3-4663-81bd-647844f24318', limit=100)


print (project['name'])
versions = hub.get_project_versions(project, limit=200)
print ("\t versions found %s" % versions['totalCount'])
versionlist = versions['items']
for index in range(len(versionlist) - 1):
    va = versionlist[index]
    print ("Processing {}".format(va['versionName']))
    components = hub.get_version_components(va)
    if cleanup and components['totalCount'] == 0:
        print ("removing {}".format(va['_meta']['href']))
        hub.execute_delete(va['_meta']['href'])
        continue
    vb = versionlist[index + 1]
    result = hub.compare_project_versions(va, vb)
    codelocations = hub.get_version_codelocations(va)
    print ("comparing version {} to version {} total changes {}".format(
        vb['versionName'], 
        va['versionName'],
        result['totalCount']))
    print ("version {} has {} codelocations".format(va['versionName'], codelocations['totalCount']))
    if result['totalCount'] == 0:
        print (va['_meta']['href'])
        if cleanup:
            print(hub.execute_delete(va['_meta']['href']))
        for codelocation in codelocations['items']:
            print (codelocation['_meta']['href'])
            if cleanup:
                print (hub.execute_delete(codelocation['_meta']['href']))

