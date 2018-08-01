'''
Created on Jul 18, 2018

@author: kumykov

Produces a report that includes project id, number of versuons and name
Projects with largest number of versions first

'''
from bds.HubRestApi import HubInstance
from sys import argv

# To clean up duplicates set cleanup = True
cleanup = False

hub = HubInstance()

projects = hub.get_projects(limit=100)

print ("total projects found: %s" % projects['totalCount'])

projectlist = list()
for project in projects['items']:
    versions = hub.get_project_versions(project)
    uid = project['_meta']['href'].replace(hub.get_urlbase() + "/api/projects/", "")
    count = versions['totalCount']
    name = project['name']
    projectlist.append((uid, count, name))
    print ("\b.", end='')
   
print () 
for s in sorted(projectlist, key=lambda x: x[1], reverse=False):
    print ("{0:36} {1:6} {2}".format(s[0],s[1], s[2]))
    
if len(argv) > 1:
    with open(argv[1],"w") as f:
        for s in sorted(projectlist, key=lambda x: x[1], reverse=False):
            f.write ("{0:36} {1:6} {2}\n".format(s[0],s[1], s[2])) 