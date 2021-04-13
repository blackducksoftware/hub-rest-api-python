import os
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s'
)

# Brief demo
from datetime import datetime, timedelta
import blackduck

def vulns_in_all_project_versions_components(bd):
    for project in bd.get_resource('projects'):
        for version in bd.get_resource('versions', project):
            for component in bd.get_resource('components', version):
                for vulnerability in bd.get_resource('vulnerabilities', component):
                    print(f"{project.get('name')}-{version.get('versionName')} [{component.get('componentName')}] has {vulnerability.get('severity')} severity vulnerability '{vulnerability.get('name')}'")
    
def list_project_subresources(bd):
    for project in bd.get_resource('projects'):
        subresources = bd.list_resources(project)
        print(f"projects has the following subresources: {', '.join(subresources)}")
        return

def list_project_versions(bd):
    i = 1
    project_count = bd.get_metadata('projects').get('totalCount')
    for project in bd.get_resource('projects'):
        print(f"Project ({i}/{project_count}): {project.get('name')}")
        for version in bd.get_resource('versions', project):
            print(f"  {version.get('versionName')}")
        i += 1

def projects_added_at_4_week_intervals(bd):
    last_count = 0
    count = 0
    print("Projects added, in 4 week intervals:")
    for timestamp in blackduck.Utils.iso8601_timespan(days_ago=365, delta=timedelta(weeks=4)):
        last_count=count
        count=0
        for project in bd.get_resource('projects'):
            created_at = blackduck.Utils.iso8601_to_date(project.get('createdAt'))
            count += (created_at <= blackduck.Utils.iso8601_to_date(timestamp))

        print(f"{count-last_count} projects added as of {timestamp}")

bd = blackduck.Client(
    token=os.environ.get('blackduck_token', 'MISSING_ENV_VAR'),
    base_url=os.environ.get('blackduck_url', 'MISSING_ENV_VAR'),
    verify=False  # TLS certificate verification
)

# Various examples:
# vulns_in_all_project_versions_components(bd)
projects_added_at_4_week_intervals(bd)
list_project_subresources(bd)
list_project_versions(bd)
