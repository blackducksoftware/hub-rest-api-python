import argparse
from datetime import datetime, timedelta
import json
import logging
import os
import sys

from blackduck.HubRestApi import HubInstance

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


hub = HubInstance()


deleted_projects = hub.delete_empty_projects()
if deleted_projects:
    logging.info("Removed the following empty projects (i.e. projects with no scans mapped to any of its versions)")
    logging.info(deleted_projects)
else:
    logging.debug("Didn't find any projects that were entirely empty")

deleted_versions = hub.delete_all_empty_versions()

if deleted_versions:
    logging.info("Removed the following empty versions")
    logging.info(deleted_versions)
else:
    logging.debug("Didn't find any empty versions")



