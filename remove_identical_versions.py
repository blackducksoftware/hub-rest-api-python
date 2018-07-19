'''
Created on Jul 18, 2018

@author: kumykov

Compares adjacent versions in a project and removes older one if there are no changes detected

'''
from bds.HubRestApi import HubInstance

# To clean up duplicates set cleanup = True

cleanupEmpty = False
cleanup = False


hub = HubInstance()

project = hub.get_project_by_id('17155144-404e-43b4-b5e4-d43efb31cbfc', limit=100)


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
    if cleanup and result['totalCount'] == 0:
        print(hub.execute_delete(va['_meta']['href']))
        for codelocation in codelocations['items']:
            print (codelocation['_meta']['href'])
            locationid = codelocation['_meta']['href'].split("/")[6]
            print (locationid)
            print (hub.delete_codelocation(locationid))

