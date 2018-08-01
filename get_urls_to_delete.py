'''
Created on Aug 1, 2018

@author: kumykov
'''
import os
import errno
from sys import argv,exit
from bds.HubRestApi import HubInstance

def print_usage():
    print("\n\n\t python3 {} projectlist [output dir]".format(argv[0]))


def get_urls_to_delete(project_id, project_name):
    hub = HubInstance()
    project = hub.get_project_by_id(project_id, limit=100)
    
    filename = outdir + "/" + project_name
    filename.replace(' ','_')

    print (project['name'])
    versions = hub.get_project_versions(project, limit=200)
    print ("\t versions found %s" % versions['totalCount'])
    versionlist = versions['items']
    for index in range(len(versionlist) - 1):
        va = versionlist[index]
        print ("Processing {}".format(va['versionName']))
        components = hub.get_version_components(va)
        if components['totalCount'] == 0:
            with open(filename, "a") as f:
                f.write(va['_meta']['href'])
                f.write('\n')
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
            with open(filename, "a") as f:
                f.write(va['_meta']['href'])
                f.write('\n')
            print (va['_meta']['href'])
            for codelocation in codelocations['items']:
                with open(filename, "a") as f:
                    f.write(codelocation['_meta']['href'])
                    f.write('\n')
                print (codelocation['_meta']['href'])


#
# main
# 

if (len(argv) < 2):
    print_usage()
    exit()


outdir = "results"
if (len(argv) > 2):
    outdir = argv[2]
    
if not os.path.exists(outdir):
    try:
        os.makedirs(outdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
  
with open(argv[1], "r") as f:
    projectlist = f.readlines() 

for line in projectlist:
    project_id = line.split()[0]
    project_name = line.split()[2]
    print ("Processing {} ".format(project_name))
    get_urls_to_delete(project_id, project_name)
