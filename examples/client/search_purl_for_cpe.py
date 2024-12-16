'''
Created on December 12, 2024

@author: mkoishi

Generate reports which consolidates information on BOM components, versions with license information, BOM files with
license and copyright information from KB and license search (discoveries - file licenses or file copyrights), 
and BlackDuck unmatched files in the target source code.

Copyright (C) 2024 Black Duck, Inc.
http://www.synopsys.com/

Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements. See the NOTICE file
distributed with this work for additional information
regarding copyright ownership. The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the License for the
specific language governing permissions and limitations
under the License.
'''

import os
import sys
import traceback
import logging
import argparse
from blackduck import Client

program_description = \
'''This script receives NVD's CPE identifier as an input parameter and seaches the Black Duck component - version - origin to get the pURL.
'''

# Hub REST API
CPEID_BY_PARTIAL_CPE = "api/cpes"
COMPONENT_ORIGIN_BY_CPEID = "api/cpes/CPEID/origins"
HEADER_COMPONENTS_DETAIL5 = "application/vnd.blackducksoftware.component-detail-5+json"

def log_config(debug):
    if debug:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def parse_parameter():
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-c",
                        "--cpe",
                        metavar="cpe",
                        type=str,
                        help="Provide the CPE identifier")
    parser.add_argument("-t",
                        "--timeout",
                        metavar="",
                        type=int,
                        default=15,
                        help="Timeout for REST-API. Some API may take longer than the default 15 seconds")
    parser.add_argument("-r",
                        "--retries",
                        metavar="",
                        type=int,
                        default=3,
                        help="Retries for REST-API. Some API may need more retries than the default 3 times")
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="debugging option"
                        )
    return parser.parse_args()

def search_purl(hub_client=None, base_url=None, cpe=None):
    '''
    Search pURL with the provided CPE
    '''
    # Search Black Duck's internal CPE IDs
    url = base_url + CPEID_BY_PARTIAL_CPE
    headers = {'accept': HEADER_COMPONENTS_DETAIL5}
    params = {'q': cpe}

    cpe_origin_links = []
    for item in hub_client.get_items(url, headers=headers, params=params):
        if '_meta' in item and 'links' in item['_meta']:
            links = item['_meta']['links']
            cpe_origins = list(filter(lambda links: links['rel'] == "cpe-origins", links))
            if len(cpe_origins) != 0:
                cpe_origin_links.append(cpe_origins[0]['href'])
                logging.debug(f"Found link for the BD's CPE ID is {cpe_origins[0]['href']}")

    if len(cpe_origin_links) == 0:
        logging.warning(f"Searched BD's CPE ID for {cpe} is not found!")
        return None
    
    # Get origin data with the cpe_ids
    purls = []
    for cpe_origin in cpe_origin_links:
        for item in hub_client.get_items(cpe_origin, headers=headers):
            if 'packageUrl' in item:
                logging.debug(f"packageUrl is returned for the origin: {cpe_origin}, item: {item}")
                purls.append(item['packageUrl'])
            else:
                logging.debug(f"packageUrl is not returned for the origin: {cpe_origin}, item: {item}!")
    
    return purls

def main():
    try:
        blackduck_url = os.getenv("BLACKDUCK_URL")
        if blackduck_url is None:
            raise ValueError("Envrionment variable BLACKDUCK_URL is not provided!")
        blackduck_token = os.getenv("BLACKDUCK_TOKEN")
        if blackduck_token is None:
            raise ValueError("Envrionment variable BLACKDUCK_TOKEN is not provided!")
        if os.getenv("BLACKDUCK_VERIFY") == "false":
            blackduck_verify = False
        else:
            blackduck_verify = True
        
        args = parse_parameter()
        if args.cpe is None:
            raise ValueError("Provide CPE ID to search!")
        debug = 1 if args.debug else 0
        log_config(debug)
        
        client = Client(token=blackduck_token,
                            base_url=blackduck_url,
                            verify=blackduck_verify,
                            timeout=args.timeout,
                            retries=args.retries)

        if blackduck_url[-1:] != "/":
            blackduck_url = blackduck_url + "/"

        purls = search_purl(hub_client=client, base_url=blackduck_url, cpe=args.cpe)
        if len(purls) != 0:
            for purl in purls:
                logging.info(f"Found pUrl is {purl}")
        else:
            logging.info(f"pURL is not found for cpe {args.cpe}")

        # TODO: falback method for cpe that the associated pURL is not found for.

    except (Exception) as err:
        logging.error(f"Exception by {str(err)}. See the stack trace")
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(main())