'''
purge_daily_cronjob.py

Created on December 28, 2018

@author: kumykov as duplicates.py
modified by JJerpseth to purge non-duplicates and to run as cronjob

Enumerates projects and project releases in the database
If two releases are found, delete the older one.
There is no checking for differences just a pure purge since can use 
the SVN branch and trunk as a comparison.
This version is run as a cron job with the command
30 * * * * * cd /home/centos/hub-rest-api-python/examples && /usr/bin/python /home/centos/hub-rest-api-python/examples/purge_daily.py 

'''


from blackduck.HubRestApi import HubInstance

username = "sysadmin"
password = "<password>"
urlbase = "https://ec2-1-2-3-4.us-west-1.compute.amazonaws.com"

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
        print ("index is ".format(index))
        va = versionlist[index]
        components = hub.get_version_components(va)
        codelocations = hub.get_version_codelocations(va)
        print ("version {} has {} codelocations".format(va['versionName'], codelocations['totalCount']))
        if codelocations > 0:
            for codelocation in codelocations['items']:
                print (codelocation['_meta']['href'])
                locationid = codelocation['_meta']['href'].split("/")[5]
                print (locationid)
                print (hub.delete_codelocation(locationid))
        print(hub.execute_delete(va['_meta']['href']))
