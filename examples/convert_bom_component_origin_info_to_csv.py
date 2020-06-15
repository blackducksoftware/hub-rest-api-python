import argparse
import csv
import logging
import json
import os.path
import sys
import urllib.parse

parser = argparse.ArgumentParser("Process the JSON output from get_bom_component_origin_info.py to create CSV output format")
parser.add_argument("-f", "--origin_info", help="By default, program reads JSON doc from stdin, but you can alternatively give a file name")
parser.add_argument("-u", "--un_matched_files", action="store_true", help="Include un-matched files in the output")
parser.add_argument("output_file")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

if args.origin_info:
    origin_info = json.load(open(args.origin_info, 'r'))
else:
    origin_info = json.load(sys.stdin)

with open(args.output_file, 'w') as csv_file:
    columns = [
        'component',
        'component modified',
        'file path', 
        'file name',
        'archive context',
        'usage(s)', 
        'license(s)',
        'match type(s)',
        'scan (code location)'
    ]
    writer = csv.DictWriter(csv_file, fieldnames=columns)
    writer.writeheader()

    for component, component_info in origin_info.items():
        if component == 'un_matched_files':
            # ignore, skip un_matched_files
            continue
        logging.debug(f"Writing info for {component}")
        for matched_file_info in component_info.get('matched_files', []):
            row = {
                'component': component,
                'component modified': component_info['bom_component_info'].get('componentModified', None),
                'file path': matched_file_info['filePath']['path'],
                'file name': matched_file_info['filePath']['fileName'],
                'archive context': matched_file_info['filePath']['archiveContext'],
                'usage(s)': ",".join(matched_file_info['usages']),
                'license(s)': ",".join([l['licenseDisplay'] for l in component_info['bom_component_info']['licenses']]),
                'match type(s)': ",".join(component_info['bom_component_info']['matchTypes']),
                'scan (code location)': matched_file_info.get('scan', {}).get('name', 'unknown')
            }
            writer.writerow(row)

    if args.un_matched_files:
        for un_matched_file in origin_info.get('un_matched_files'):
            uri = urllib.parse.unquote(un_matched_file['uri'])
            parsed = urllib.parse.urlparse(uri)
            if parsed.scheme == 'zip':
                file_path = parsed.fragment
                file_name = os.path.basename(parsed.fragment)
                archive_context = parsed.path
            elif parsed.scheme == 'file':
                file_path = parsed.path
                file_name = os.path.basename(parsed.path)
                archive_context = None
            else:
                file_path = "unrecognized"
                file_name = "unrecognized"
                archive_context = "unrecognized scheme"

            row = {
                'component': None,
                'component modified': None,
                'file path': file_path,
                'file name': file_name,
                'archive context': archive_context,
                'usage(s)': None,
                'license(s)': None,
                'match type(s)': "Un-matched/Un-identified",
                'scan (code location)': un_matched_file.get('scan', {}).get('name', 'unknown')
            }
            writer.writerow(row)