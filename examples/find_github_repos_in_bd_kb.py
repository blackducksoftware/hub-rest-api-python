#!/usr/bin/env python

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from urllib.parse import urlparse

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Given the URL to a Github repository, find it in the Black Duck KB and return any info available")
parser.add_argument("github_url")
parser.add_argument("-l", "--limit", type=int, default=100, help="The number of components to return with each call to the REST API (default: 100)")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def match_urls(input_url, url_from_kb):
    '''Try matching variations of the input URL against the url from the Black Duck KB, 
        e.g. add a '/' or add '.git' or check http versus https
    '''
    if input_url.startswith("https:"):
        check_urls = [input_url, input_url.replace("https:", "http:")]
    elif input_url.startswith("http:"):
        check_urls = [input_url, input_url.replace("http:", "https:")]
    else:
        raise Exception("Unsupported scheme {}".format(urlparse(input_url).scheme))

    all_checks = []
    for check_url in check_urls:
        with_slash_added = check_url + "/" == url_from_kb
        with_dot_git_added = check_url + ".git" == url_from_kb
        exact = check_url == url_from_kb
        all_checks.extend([with_slash_added, with_dot_git_added, exact])

    return any(all_checks)

def has_github_link(links):
    http = any(["http://github.com" in l for l in links])
    https = any(["https://github.com" in l for l in links])
    return (http or https)

hub = HubInstance()

# 
# Get the repo name which, for now, is defined as the last "part" in the pathname to the repo
# The repo name will be used to search the Black Duck KB, e.g.
#       https://github.com/django/django --> django becomes the search keyword
#
repo_name = Path(urlparse(args.github_url).path).parts[-1]

possible_matches = []
exact_match = None

first = True
num_results_found = math.inf
offset = 0
total_hits = 0

#
# Loop on the search results (aka hits) accumulating any possible matches
# and stop if/when you find an exact match. 
#
# An exact match is a component from the initial search that has the exact URL provided
#
while offset < num_results_found:
    logging.debug(f"Searching for {repo_name}, offset {offset}, limit {args.limit}")
    parameters = {'limit': args.limit, 'offset': offset}

    search_results = hub.search_components(
        search_str_or_query=f"q={repo_name}", 
        parameters=parameters)

    if first:
        first = False
        num_results_found = search_results['items'][0]['searchResultStatistics']['numResultsFound']
        logging.debug(f"numResultsFound: {num_results_found}")
    
    for hit in search_results['items'][0].get('hits', []):
        number_versions = int(hit['fields']['release_count'][0])
        component_name = hit['fields']['name'][0]
        component_url = hit['component']
        component_description = hit['fields']['description'][0]
        links = hit['fields'].get('links', [])

        total_hits += 1

        if component_name.lower() == repo_name.lower() and has_github_link(links):
            component_info = {
                    'component_name': component_name,
                    'component_url': component_url,
                    'component_description': component_description,
                    'links': links,
                    'number_versions': number_versions
                }
            logging.info(f"Found one possible match in {component_name}")
            possible_matches.append(component_info)
            matched_urls = [l for l in links if match_urls(args.github_url, l)]

            if matched_urls:
                logging.debug(f"Found the following matched URLS: {matched_urls}")
                exact_match = component_info
                logging.debug("Found an exact match, breaking loop")
                break # breaks from for-loop

    if exact_match:
        break # breaks from while-loop

    offset += args.limit

logging.debug(f"Found {len(possible_matches)} components that could be matches after looking at {total_hits} components found in the search results")

if exact_match:
    logging.info("Found an exact match")
else:
    logging.warning("Did not find any exact match")

summary = {
    'possible_matches': possible_matches,
    'exact_match': exact_match
}
print(json.dumps(summary))

