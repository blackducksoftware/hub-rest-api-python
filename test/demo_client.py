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

def list_project_versions(bd):
    projects = list(bd.get_projects(bd))
    num_projects = len(projects)
    i = 0
    for project in projects:
        i += 1
        print(f"Project ({i}/{num_projects}): {project.get('name')}")
        for version in bd.get_resource(project, 'versions'):
            print(f"  {version.get('versionName')}")

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
    base_url="https://your.blackduck.url",
    # verify=False  # TLS certificate verification
)

# Various examples:
#vulns_in_all_project_versions_components(bd)
#projects_added_at_4_week_intervals(bd)
list_project_subresources(bd)
list_project_versions(bd)