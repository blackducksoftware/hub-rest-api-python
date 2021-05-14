from blackduck import Client
from blackduck.Utils import to_datetime

from datetime import datetime, timedelta
import argparse
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser("Delete empty projects and versions, older than <d> days (default: 30)")
parser.add_argument("--base-url", required=True, help="blackduck hub server url e.g. https://your.app.blackduck.com")
parser.add_argument("--token-file", dest='token_file', required=True, help="path to file containing blackduck hub token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("--days", dest='days', default=30, type=int, help="projects/versions older than <days>")
parser.add_argument("--delete", dest='delete', action='store_true', help="without this flag script will log/print only")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

max_age = datetime.now() - timedelta(days=args.days)

for project in bd.get_resource('projects'):
    # skip projects younger than max age
    if to_datetime(project.get('createdAt')) > max_age: continue

    for version in bd.get_resource('versions', project):
        # skip versions with > 0 code locations
        if int(bd.get_metadata('codelocations', version).get('totalCount')): continue
        # skip versions younger than max age
        if to_datetime(version.get('createdAt')) > max_age: continue
        # delete all others
        logger.info(f"delete {project.get('name')} version {version.get('versionName')}")
        if args.delete: bd.session.delete(version.get('href')).raise_for_status()
    
    # skip projects with any remaining versions
    if int(bd.get_metadata('versions', project).get('totalCount')): continue
    # delete all others
    logger.info(f"deleting {project.get('name')}")
    if args.delete: bd.session.delete(project.get('href')).raise_for_status()
 