'''
Created on Jul 18, 2018

@author: kumykov

Removes versions from a project that have no bom components
'''

from bds.HubRestApi import HubInstance

# HUB URL and credentials
urlbase="https://ec2-18-208-209-223.compute-1.amazonaws.com"
username="sysadmin"
password="genesys"

# Set to True to cleanup otherwise a dry run
cleanup = False

hub = HubInstance(urlbase, username, password, insecure=True)

project = hub.get_project_by_id('6d93bd1c-eb01-4c94-b1c3-5a9c5865f10c', limit=100)

print (project['name'])
versions = hub.get_project_versions(project, limit=200)
print ("\t versions found %s" % versions['totalCount'])
versionlist = versions['items']
for index in range(len(versionlist) - 1):
    va = versionlist[index]
    components = hub.get_version_components(va, limit=1)
    totalCount = components['totalCount']
    print ("Vesion {} has {} components".format(va['versionName'], totalCount))
    if cleanup and totalCount == 0:
        print ("removing {}".format(va['_meta']['href']))
        hub.execute_delete(va['_meta']['href'])
        