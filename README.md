## Overview ##
The hub-rest-api-python provides Python bindings for Hub REST API.

This is the Synamedia fork of this Open Source repository. The default branch is synamedia. The master branch is the original repo default branch.

```
git clone https://github.com/synamedia/hub-rest-api-python.git
cd hub-rest-api-python
pip3 install -r requirements.txt
pip3 install .
```
### Configure your connection
Create a token in BlackDuck for your user or generic account

`cp restconfig.json.api_token.example restconfig.json`

Update restconfig.json with your credentials

## Generate reports
### Common usage example
`python3 generate_reports.py --project_name <your project> --summary short --detailed --licence --output <path>`

### Usage
```
$ ./generate_reports.py --help
usage: generate_reports.py [-h]
                           (--project_name PROJECT_NAME | --project_file PROJECT_FILE)
                           [--version VERSION] [--summary {short,full}]
                           [--detailed] [--licence] [--output OUTPUT]
                           [--format {CSV,JSON}] [--skip_cleanup]
                           [--prefix PREFIX] [--sleep_time SLEEP_TIME] [--log]

Generates and downloads reports for project(s) on blackduck.com

optional arguments:
  -h, --help            show this help message and exit
  --project_name PROJECT_NAME, -p PROJECT_NAME
                        Add a single project
  --project_file PROJECT_FILE, -f PROJECT_FILE
                        Add all projects listed in the file
  --version VERSION, -v VERSION
                        Version to use if not specified in the file. Default:
                        master
  --output OUTPUT, -o OUTPUT
                        Output folder to download the reports into. Default: .
  --format {CSV,JSON}, -m {CSV,JSON}
                        Report format. 1 JSON file or multiple CSV files
  --skip_cleanup, -c    Do not remove reports generated on BlackDuck
  --prefix PREFIX, -x PREFIX
                        String to add to the start of all project names
  --sleep_time SLEEP_TIME, -t SLEEP_TIME
                        Time in seconds to sleep between download attempts
  --log                 Debug log output

reports:
  Select 1 or more to generate

  --summary {short,full}, -s {short,full}
                        Create a summary report json file of the project(s).
                        short option only lists the CRITICAL and HIGH issues.
  --detailed, -d        Generate and fetch the detailed reports.
  --licence, -l         Generate and fetch the licence report (aka Notices
                        file).

Note: When using the --project_file option the file format per line MUST be:

# Lines starting # are ignored, so are empty lines
project name[;version][;filename]

# The default version is master but can be overridden with --version
# The default filenema is the project-version name with .zip e.g. "my proj-master.zip" 
```
## Rename user groups
BlackDuck does sync with Azure but it does not bring the security group names in, only the GUIDs are displayed. To fix that we need to get a dump of [groups from Azure](https://portal.azure.com/#blade/Microsoft_AAD_IAM/GroupsManagementMenuBlade/AllGroups) but **Download groups** is greyed out for normal users. So we need to ask an Azure admin e.g. Natan Kahana. Once we have the file we can apply the correct group names to BlackDuck.
### Example
`./rename_user_groups.py --file c__temp_exportGroup_2020-8-12.csv`

## Documentation ##
Documentation for hub-rest-api-python can be found on the base project:  [Hub REST API Python Wiki](https://github.com/blackducksoftware/hub-rest-api-python/wiki)


