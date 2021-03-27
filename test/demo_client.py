import os
import requests
from requests.adapters import HTTPAdapter
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s'
)

# create http adapter with exponential backoff (for unstable and/or slow connections)
http_adapter = HTTPAdapter(
    max_retries=requests.packages.urllib3.util.retry.Retry(
        total=5,
        backoff_factor=10,
        status_forcelist=[429,500,502,503,504]
    )
)
custom_session = requests.session()
custom_session.mount('http://', http_adapter)
custom_session.mount('https://', http_adapter)

# use os env proxy settings, if any
custom_session.proxies.update({
    'http' : os.environ.get('http_proxy',''),
    'https' : os.environ.get('http_proxy', '')
})


# Brief demo
from datetime import datetime, timedelta
import blackduck

def vulns_in_all_project_versions_components(bd):
    for project in bd.get_projects():
        for version in bd.get_resource(project, 'versions'):
            for component in bd.get_resource(version, 'components'):
                for vulnerability in bd.get_resource(component, 'vulnerabilities'):
                    print(f"{project.get('name')}-{version.get('versionName')} [{component.get('componentName')}] has {vulnerability.get('severity')} severity vulnerability '{vulnerability.get('name')}'")
    
def list_project_subresources(bd):
    for project in bd.get_projects():
        subresources = bd.list_resources(project)
        print(f"projects has the following subresources: {', '.join(subresources)}")
        return
        

def projects_added_at_4_week_intervals(bd):
    last_count = 0
    count = 0
    print("Projects added, in 4 week intervals:")
    for timestamp in blackduck.Utils.iso8601_timespan(days_ago=365, delta=timedelta(weeks=4)):
        last_count=count
        count=0
        for project in bd.get_projects():
            created_at = blackduck.Utils.iso8601_to_date(project.get('createdAt'))
            count += (created_at <= blackduck.Utils.iso8601_to_date(timestamp))

        print(f"{count-last_count} projects as of {timestamp}")      

bd = blackduck.Client(
    token=os.environ.get('blackduck_token', 'YOUR TOKEN HERE'),
    base_url='https://your.blackduck.url', #!important! no trailing slash
    session=custom_session
    # verify=False # if required
)

# If disabling warnings, don't do so at the library level:
requests.packages.urllib3.disable_warnings()

# Various examples:
# vulns_in_all_project_versions_components(bd)
projects_added_at_4_week_intervals(bd)
# list_project_subresources(bd)