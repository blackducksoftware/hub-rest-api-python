## Overview ##
The hub-rest-api-python provides Python bindings for Hub REST API.

## To use

```
pip install blackduck
```

```python
from blackduck.HubRestApi import HubInstance

username = "sysadmin"
password = "your-password"
urlbase = "https://ec2-34-201-23-208.compute-1.amazonaws.com"

hub = HubInstance(urlbase, username, password, insecure=True)

projects = hub.get_projects()
```

## Build ##
You should be using [virtualenv](https://pypi.org/project/virtualenv/), [virtrualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to make things easy on yourself.

Ref: [Packaging Python Projects Tutorial](https://packaging.python.org/tutorials/packaging-projects/)

### Build the blackduck packages
To build both the source distribution package and the wheel package,

```
pip install -r requirements.txt
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
pip install -r requirements.txt
pip install .
```

## Test ##
Using (pytest)[https://pytest.readthedocs.io/en/latest/contents.html]

```bash
git clone https://github.com/blackducksoftware/hub-rest-api-python.git
cd hub-rest-api-python
# optional but advisable: create/use virtualenv
# you should have 3.x+, e.g. Python 3.7.0

pip install -r requirements.txt
pip install .
cd test
pytest
```

## Where can I get the latest release? ##
This package is available on PyPi,

pip install blackduck

## Documentation ##
Documentation for hub-rest-api-python can be found on the base project:  [Hub REST API Python Wiki](https://github.com/blackducksoftware/hub-rest-api-python/wiki)


