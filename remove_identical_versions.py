'''
Created on Jul 18, 2018

@author: kumykov

Compares adjacent versions in a project and removes older one if there are no changes detected

'''
from bds.HubRestApi import HubInstance
import json
import time


def clean_up(versionlist):
    attempt = 1
    i = 1
    index = 0
    while index < len(versionlist) - 1:
        try:
            va = versionlist[index]
            print("Processing {}".format(va['versionName']))
            components = hub.get_version_components(va) # could fail
            try:
                if cleanup and components['totalCount'] == 0:
                    print("removing {}".format(va['_meta']['href']))
                    hub.execute_delete(va['_meta']['href'])                # could fail
                    continue
            except KeyError as key_error:
                print(key_error)
                if i < 3:
                    print("Trying again, please wait...")
                    time.sleep(10)
                    index -= 1
                    i += 1
                else:
                    print("too many attempts here, moving on")
                    i = 1
                    continue
            finally:
                index += 1
            vb = versionlist[index + 1]
            result = hub.compare_project_versions(va, vb)              # could fail
            codelocations = hub.get_version_codelocations(va)          # could fail
            print("comparing version {} to version {} total changes {}".format(
                vb['versionName'],
                va['versionName'],
                result['totalCount']))
            print("version {} has {} codelocations".format(va['versionName'], codelocations['totalCount']))
            if cleanup and result['totalCount'] == 0:
                print(hub.execute_delete(va['_meta']['href']))          # could fail
                for codelocation in codelocations['items']:
                    print(codelocation['_meta']['href'])
                    locationid = codelocation['_meta']['href'].split("/")[6]
                    print(locationid)
                    print(hub.delete_codelocation(locationid))          # could fail

        except json.decoder.JSONDecodeError as json_decode_error:
            print(json_decode_error)
            print("... please wait ...")
            time.sleep(10)
            if attempt < 3:
                print("Trying again... this is attempt ", attempt+1)
                index -= 1
                attempt += 1
            else:
                print("Too many attempts failed... moving on")
                attempt = 1
                print("---------------------------------------")
                continue
        finally:
            index += 1

cleanup = True

hub = HubInstance()

try:
    project = hub.get_project_by_id('6d93bd1c-eb01-4c94-b1c3-5a9c5865f10c', limit=100)
except json.decoder.JSONDecodeError as error:
    print("request failed, trying again...")
    time.sleep(10)
    project = hub.get_project_by_id('6d93bd1c-eb01-4c94-b1c3-5a9c5865f10c', limit=100)
print(project['name'])
versions = hub.get_project_versions(project, limit=200)
print("\t versions found %s" % versions['totalCount'])
versionlist = versions['items']
clean_up(versionlist)
