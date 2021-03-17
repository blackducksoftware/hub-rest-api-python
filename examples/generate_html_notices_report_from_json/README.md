## Overview ##
This mini project is designed to give customers the option of producing a standalone single html format notices file similar to the one found in the Black Duck Web UI.  The one in the UI is not easily downloadable, and it comes with various javascript, css, and other files which would make it cumbersome to distribute.


## To use ##

```
pip3 install blackduck
pip3 install -r requirements.txt
```

```
cd ../../
python3 examples/generate_notices_report_for_project_version.py project-name version-name -f examples/generate_html_notices_report_from_json/bd-notices -r JSON -c
cd examples/generate_html_notices_report_from_json
python3 generate_html_notices_from_json.py bd-notices.json my-report.html
```
