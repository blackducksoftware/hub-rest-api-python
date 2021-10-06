# get_upstream_copyrights.py

## Introduction

This program will attempt to produce missing Copyright statements 
for BOM entries that do not have orgin associated copyright statements.

The scriot will enumerate BOM entried that appear on NOTICES report 
without copyright and for each of then will try to retrieve 
upstream copyright notices from source origin (github, long_tail)

if that fails, the script will process earlier versions of componets
anf try to fetch copyright statements from there.

Note:  There is still a possibility that there will be no copyright 
       statements present on any version of a component

Once completed a text file will be writtent with the following format:
Optional JSON file can be written

## Program output

'''
#####
ComponentName ComponentversionName
#####
-----
Statement-1
-----
Statement-1
-----
.....
'''

## Invokig 

Usage: Enumerate BOM componets without copyrigth statements. retrieve 
       copyright statements form upstream channel and/or version

python3 get_upstream_copyrights.py [OPTIONS]

OPTIONS:
    [-h]                            Help
    -u BASE_URL                     URL of a Blackduck system
    -t TOKEN_FILE                   Authentication token file
    -p PROJECT_NAME                 Project to process
    -v VERSION_NAME                 Project Version to process
    [-o OUTPUT_FILE]                Output file (default: copyright_data.txt)
    [-jo JSON_OUTPUT_FILE]          Write an optional JSON file with output data
    [-ukc USE_UPDATED_COPYRIGHT]    Use kbCopyright instead of updatedCopyright (default: false)
    [-nv]                           Trust TLS certificate

