'''
Created on Jul 19, 2018

@author: kumykov

usage: remove_empty_codelocations.py [-h] [--before-date BEFORE_DATE]
                                     [--delete-complete-only DELETE_COMPLETE_ONLY]
                                     [--delete-mapped DELETE_MAPPED]

optional arguments:
  -h, --help            show this help message and exit
  --before-date BEFORE_DATE
                        Will affect scans created before YYYY-MM-
                        DD[THH:MM:SS[.mmm]]
  --delete-complete-only DELETE_COMPLETE_ONLY
                        Delete completed scans only
  --delete-mapped DELETE_MAPPED
                        Delete only unmapped scans


'''
from blackduck.HubRestApi import HubInstance
import sys
from datetime import datetime
from argparse import ArgumentParser

#
# main
# 

# TODO: Delete older scans? X oldest?

beforedatestr="2019-06-19T00:07:00.000"

beforedate = datetime.fromisoformat(beforedatestr)

def delete_codelocations(delete_mapped, delete_complete_only, before_date):
    hub = HubInstance()
    
    message = '''
    Processing scans with following parameters
         deleting mapped scans {}
         deleting complete scans only {}
         before date specified as {}
    '''
    
    if before_date:
        beforedate = datetime.fromisoformat(before_date)
        
    print(message.format(delete_mapped, delete_complete_only, before_date))
    
    code_locations = hub.get_codelocations(500, not delete_mapped).get('items', [])
    
    for c in code_locations:
        scan_summaries = hub.get_codelocation_scan_summaries(code_location_obj = c).get('items', [])
        name = c['name']
        created = datetime.fromisoformat(scan_summaries[0]['createdAt'].replace("Z", ""))
        status = scan_summaries[0]['status']
        print ("processing {}  created on {}  status {}".format(name, created, status))

        dateChecks = False
        if before_date:
            if created < beforedate:
                dateChecks = True
        else:
            dateChecks = True
        completeChecks = False
        if delete_complete_only:
            if status == 'COMPLETE':
                completeChecks = True
        else:
            completeChecks = True
        
        if dateChecks and completeChecks:
            print ("executing delete request")
            print (hub.execute_delete(c['_meta']['href']))
        else:
            print('will not delete ')
        #    response = hub.execute_delete(c['_meta']['href'])


def main(argv=None):
    
    if argv is None:
        argv = sys.argv
    else:
        argv.extend(sys.argv)
        
    parser = ArgumentParser()
    parser.add_argument('--before-date', default=None, help="Will affect scans created before YYYY-MM-DD[THH:MM:SS[.mmm]]")
    parser.add_argument('--delete-complete-only',default=True, help="Delete completed scans only")
    parser.add_argument('--delete-mapped', default=False, help="Delete only unmapped scans")
    args = parser.parse_args()
    
    delete_codelocations(args.delete_mapped, args.delete_complete_only, args.before_date)

if __name__ == "__main__":
    sys.exit(main())
    