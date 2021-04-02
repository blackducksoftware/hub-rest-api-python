'''
Created on Apr 1, 2021

add_component_list_to_project_version.py 

Processes an input file formated as forgename:forge_id 
And imports them as components into specified project.

program uses component search API as described in 
https://your-blackduck-host/api-doc/public.html#component-list

Usage:

python3 examples/add_component_list_to_project_version.py project_name version_name input_file

Note: 
   Response code 412 means that the component is already part of the project and will not be added again.
   There are two component version URLs that are returned by component search api.
    json['items'][0]['version']   - this is the upstream version of software
    json['items'][0]['variant']   - this is forge specific version of software
   This example adds both of them, however adding forge specific version can produce more precice vulnerability data
   and might be sufficient.

Note:
   Resulting number of components will not match the number of packages.
   Components to packages relationship is 1 to many

Note:
   prefixing forge name with '@' sign will allow fallback search into parent forge if results are not available

input file examples as following:

Ubuntu

@ubuntu:sysstat/11.6.1-1ubuntu0.1/amd64
@ubuntu:systemd/237-3ubuntu10.42/amd64
ubuntu:systemd-sysv/237-3ubuntu10.42/amd64
ubuntu:sysvinit-utils/2.88dsf-59.10ubuntu1/amd64
ubuntu:tar/1.29b-2ubuntu0.2/amd64

Redhat

redhat:yum-utils/4.0.17-5.el8/noarch
redhat:zip/3.0-23.el8/x86_64
@redhat:zlib/1.2.11-16.el8_2/i686
@redhat:zlib-devel/1.2.11-16.el8_2/i686
@redhat:zlib-devel/1.2.11-16.el8_2/x86_64
redhat:zstd/1.4.4-1.el8/x86_64

Alpine

alpine:curl/7.66.0-r3/x86_64
alpine:ncurses-terminfo-base/6.1_p20190518-r0/x86_64
alpine:alpine-baselayout/3.1.2-r0/x86_64
alpine:libpng/1.6.37-r1/x86_64
alpine:libjpeg-turbo/2.0.4-r0/x86_64
alpine:libwebp/1.0.2-r0/x86_64

data is formatted directly from respective package manager output.

@author: kumykov
'''


from blackduck.HubRestApi import HubInstance
import json
import sys, argparse
import urllib


parser = argparse.ArgumentParser("Add a Black Duck component to the selected project-version")
parser.add_argument("project_name")
parser.add_argument("version")
parser.add_argument("component_input_file", help="Supply a file with components listed as foundry:componentname/version/arch one per line")

args = parser.parse_args()

project_name = args.project_name
version = args.version
inputfile = args.component_input_file

with open(inputfile,"r") as f:
    inputdata = f.readlines()

hub = HubInstance()
headers = hub.get_headers()
headers['Accept'] = 'application/vnd.blackducksoftware.component-detail-4+json'

project_version = hub.get_or_create_project_version(args.project_name, args.version)
print (project_version)
project_components_url = hub.get_link(project_version, "components")
components_url = hub.get_apibase() + "/components"

for line in inputdata:
    query = { "q": line.rstrip().replace(':amd64','') }
    url = "{}?{}".format(components_url,urllib.parse.urlencode(query))
    print (url)
    json = hub.execute_get(url, custom_headers=headers).json()
    print (json)
    if (json['totalCount'] > 0):
        component_version_url = json['items'][0]['version']
        post_data = {"component": component_version_url}
        response = hub.execute_post(project_components_url, data=post_data)
        print(response.status_code)
        component_version_url = json['items'][0]['variant']
        post_data = {"component": component_version_url}
        response = hub.execute_post(project_components_url, data=post_data)
        print(response.status_code)
        
