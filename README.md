## Overview ##

The hub-rest-api-python provides Python bindings for Hub REST API.

:warning:Recently CVE-2020- 27589, a medium severity security defect, was discovered in the [blackduck PyPi](https://pypi.org/project/blackduck/) library which affects versions 0.0.25 – 0.0.52 that could suppress certificate validation if the calling code used either the upload_scan or download_project_scans methods. These methods did not enforce certificate validation. Other methods in the library are not affected. The defect was fixed in version 0.0.53.

Customers using the [blackduck library](https://pypi.org/project/blackduck/) should upgrade to version 0.0.53, or later, to implement the fix.

## To use ##

```
pip install blackduck
```

```python
from blackduck import Client
import json
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s'
)

bd = Client(
    token=os.environ.get('blackduck_token', "YOUR TOKEN HERE"),
    base_url="https://your.blackduck.url",
    # verify=False  # TLS certificate verification
)

for project in bd.get_projects():
    print(project.get('name'))
```

### Examples

Example code showing how to do various things can be found in the *examples* folder. 

## Build ##

You should be using [virtualenv](https://pypi.org/project/virtualenv/), [virtrualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to make things easy on yourself.

Ref: [Packaging Python Projects Tutorial](https://packaging.python.org/tutorials/packaging-projects/)

### Build the blackduck packages
To build both the source distribution package and the wheel package,

```
pip3 install -r requirements.txt
python3 setup.py sdist bdist_wheel
```

### Distribute the package

Requires you have an account on either/both [PyPi](https://pypi.org) and [Test PyPi](https://test.pypi.org) *AND* you must be a package maintainer.

Send a request to gsnyder@synopsys.com or gsnyder2007@gmail.com if you want to be listed as a package maintainer.

#### To PyPi

Upload to PyPi,

```
twine upload dist/*
```

Then try installing it from PyPy

```
pip install blackduck
```

#### To Test PyPi

Upload to Test PyPi,

```
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Then try installing it from Test PyPy

```
pip install --index-url https://test.pypi.org/simple/ blackduck
```

### Install package locally

Do this when testing a new version.

```
git clone https://github.com/blackducksoftware/hub-rest-api-python.git
cd hub-rest-api-python
pip3 install -r requirements.txt
pip3 install .
```

## Test ##
Using (pytest)[https://pytest.readthedocs.io/en/latest/contents.html]

```bash
git clone https://github.com/blackducksoftware/hub-rest-api-python.git
cd hub-rest-api-python
# optional but advisable: create/use virtualenv
# you should have 3.x+, e.g. Python 3.7.0

pip3 install -r requirements.txt
pip3 install .
cd test
pytest
```

## Where can I get the latest release? ##
This package is available on PyPi,

`pip3 install blackduck`

## Documentation ##
Documentation for hub-rest-api-python can be found on the base project:  [Hub REST API Python Wiki](https://github.com/blackducksoftware/hub-rest-api-python/wiki)


