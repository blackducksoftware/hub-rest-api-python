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
parser.add_argument("-l", "--file_level_license", action="store_true", help="Include file level license data (aka deep license data from the Black Duck KB), if present")
parser.add_argument("-c", "--file_level_copyright", action="store_true", help="Include file level copyright data (aka copyright data from the Black Duck KB), if present")
parser.add_argument("-s", "--string_search", action="store_true", help="Include any licenses found via string search (i.e. --detect.blackduck.signature.scanner.license.search==true")
parser.add_argument("-a", "--all", action="store_true", help="Shortcut for including everything (i.e. all of it)")
parser.add_argument("output_file")

args = parser.parse_args()

if args.all:
    args.un_matched_files = args.file_level_license = args.file_level_copyright = args.string_search = True

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
        'file path', 
        'file name',
        'archive context',
        'usage(s)', 
        'license(s)',
        'source',
        'origin(s)',
        'origin_id(s)',
        'copyright',
        'match type(s)',
        'codelocation'
    ]
    writer = csv.DictWriter(csv_file, fieldnames=columns)
    writer.writeheader()

    for component, component_info in origin_info.items():
        if component in ['un_matched_files', 'license_search_results']:
            # ignore, skip un_matched_files and license search results
            # since they are not components but other sections of the JSON doc
            #
            continue
        logging.debug(f"Writing info for {component}")
        for matched_file_info in component_info.get('matched_files', []):
            # import pdb; pdb.set_trace()
            row = {
                'component': component,
                'file path': matched_file_info['filePath']['path'],
                'file name': matched_file_info['filePath']['fileName'],
                'archive context': matched_file_info['filePath']['archiveContext'],
                'usage(s)': ",".join(matched_file_info['usages']),
                'license(s)': ",".join([l['licenseDisplay'] for l in component_info['bom_component_info']['licenses']]),
                'source': 'customers source',
                'origin(s)': ",".join([o['externalNamespace'] for o in component_info['bom_component_info']['origins']]),
                'origin_id(s)': ",".join([o.get('externalId', "") for o in component_info['bom_component_info']['origins']]),
                'copyright': None,
                'match type(s)': ",".join(component_info['bom_component_info'].get('matchTypes', [])),
                'codelocation': matched_file_info['scan']['name'],
            }
            writer.writerow(row)

        if args.file_level_license or args.file_level_copyright:
            for origin in component_info.get('all_origin_details', []):
                if args.file_level_license:
                    for license in origin.get('file_licenses_fuzzy', []):
                        # import pdb; pdb.set_trace()
                        row = {
                            'component': component,
                            'file path': license['path'],
                            'file name': os.path.basename(license['path']),
                            'archive context': None,
                            'usage(s)': None,
                            'license(s)': license['licenseGroupName'],
                            'source': 'KB',
                            'origin(s)': origin.get('originName'),
                            'origin_id(s)': origin.get('originId'),
                            'copyright': None,
                            'match type(s)': 'From KB',
                            'codelocation': None,
                        }
                        writer.writerow(row)

                if args.file_level_copyright:
                    for copyright in origin.get('file_copyrights', []):
                        # import pdb; pdb.set_trace()
                        row = {
                            'component': component,
                            'file path': copyright['path'],
                            'file name': os.path.basename(copyright['path']),
                            'archive context': None,
                            'usage(s)': None,
                            'license(s)': None,
                            'source': 'KB',
                            'origin(s)': origin.get('originName'),
                            'origin_id(s)': origin.get('originId'),
                            'copyright': copyright['matchData'].replace('\n', ''),
                            'match type(s)': 'From KB',
                            'codelocation': None
                        }
                        writer.writerow(row)

    if args.un_matched_files:
        for un_matched_file in origin_info.get('un_matched_files', []):
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
                'file path': file_path,
                'file name': file_name,
                'archive context': archive_context,
                'usage(s)': None,
                'license(s)': None,
                'source': 'customers source',
                'origin(s)': None,
                'origin_id(s)': None,
                'copyright': None,
                'match type(s)': 'Not matched (un-identified)',
                'codelocation': None
            }
            writer.writerow(row)

    if args.string_search:
        for codelocation, codelocation_info in origin_info.get("license_search_results", {}).items():
            for scan in codelocation_info.get("scans", []):
                for file_bom_entry in scan.get("file_bom_entries", []):
                    row = {
                        'component': None,
                        'file path': file_bom_entry.get('uri'),
                        'file name': file_bom_entry.get('name'),
                        'archive context': file_bom_entry.get('compositePath', {}).get('archiveContext'),
                        'usage(s)': None,
                        'license(s)': None,
                        'source': 'customers source',
                        'origin(s)': None,
                        'origin_id(s)': None,
                        'copyright': None,
                        'match type(s)': 'License Search',
                        'codelocation': codelocation
                    }
                    writer.writerow(row)














