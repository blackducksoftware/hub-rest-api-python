'''
Created on Jan 12, 2021

@author: kumykov
'''

from blackduck.HubRestApi import HubInstance
import json
import os
import requests


hub=HubInstance()

batch_size=500

codelocations = hub.get_codelocations(limit=1, offset=1)
total_count = codelocations['totalCount']

print("{} codelocations in the database".format(total_count))

offset=0
output_location = 'scan_data/{:06d}'
while offset < total_count:
    hub = HubInstance()
    output_folder = output_location.format(offset)
    codelocations = hub.get_codelocations(limit=batch_size, offset=offset)
    for item in codelocations['items']:
        links = item['_meta']['links']
        matches = [x for x in links if x['rel'] == 'enclosure' or x['rel'] == 'scan-data']
        for m in matches:
            url = m['href']
            print (url)
            filename = url.split('/')[6]
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            pathname = os.path.join(output_folder, filename)
            response = requests.get(url, headers=hub.get_headers(), stream=True, verify=not hub.config['insecure'])
            with open(pathname, "wb") as f:
                for data in response.iter_content():
                    f.write(data)
            print (pathname)
    offset += batch_size