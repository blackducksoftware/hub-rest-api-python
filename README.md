# Overview

The hub-rest-api-python provides Python bindings for Hub REST API.

:warning:Recently [CVE-2020-27589](https://nvd.nist.gov/vuln/detail/CVE-2020-27589), a medium severity security defect,
was discovered in the [blackduck PyPi](https://pypi.org/project/blackduck) library which affects versions 0.0.25 – 0.0.52
that could suppress certificate validation if the calling code used either the upload_scan or download_project_scans
methods. These methods did not enforce certificate validation. Other methods in the library are not affected.
The defect was fixed in version 0.0.53.

Customers using the [blackduck library](https://pypi.org/project/blackduck) should upgrade to version 0.0.53, or later, to implement the fix.

# New in 1.0.0

Introducing the new Client class.

In order to provide a more robust long-term connection, faster performance, and an overall better experience a new
Client class has been designed.

It is backed by a [Requests session](https://docs.python-requests.org/en/master/user/advanced/#session-objects)
object. The user specifies a base URL, timeout, retries, proxies, and TLS verification upon initialization and these
attributes are persisted across all requests.

At the REST API level, the Client class provides a consistent way to discover and traverse public resources, uses a
[generator](https://wiki.python.org/moin/Generators) to fetch all items using pagination, and automatically renews
the bearer token.

See [Client versus HubInstance Comparison](https://github.com/blackducksoftware/hub-rest-api-python/wiki/Client-versus-HubInstance-Comparison)
and also read the [Client User Guide](https://github.com/blackducksoftware/hub-rest-api-python/wiki/Client-User-Guide)
on the [Hub REST API Python Wiki](https://github.com/blackducksoftware/hub-rest-api-python/wiki).

### Important Note
The old HubInstance (in HubRestApi.py) keeps its existing functionality for backwards compatibility and therefore does
**not** currently leverage any of the new features in the Client class.

We believe that the new features are compelling enough to strongly encourage users to consider moving from HubInstance
to Client.
See [Client versus HubInstance Comparison](https://github.com/blackducksoftware/hub-rest-api-python/wiki/Client-versus-HubInstance-Comparison).


Please give it a try and let us know what you think!

# To use

```
pip3 install blackduck
```

```python
from blackduck import Client
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

bd = Client(
    token=os.environ.get('blackduck_token'),
    base_url="https://your.blackduck.url",
    # verify=False  # TLS certificate verification
)

for project in bd.get_resource(name='projects'):
    print(project.get('name'))
```

### Examples

Example code showing how to work with the new Client can be found in the *examples/client* folder.

# Test #
Using [pytest](https://pytest.readthedocs.io/en/latest/contents.html)

```bash
git clone https://github.com/blackducksoftware/hub-rest-api-python.git
cd hub-rest-api-python
# optional but advisable: create/use virtualenv
# you should have 3.x+, e.g. Python 3.8.0+

pip3 install -r requirements.txt
pip3 install .
cd test
pytest
```

## Install package locally

Do this when testing a new version.

```
git clone https://github.com/blackducksoftware/hub-rest-api-python.git
cd hub-rest-api-python
pip3 install -r requirements.txt
pip3 install .
```

To uninstall:

```
pip3 uninstall blackduck
```

## Where can I get the latest release? ##
This package is available on PyPi:

`pip3 install blackduck`

## Documentation ##
Documentation for hub-rest-api-python can be found on the base project:
[Hub REST API Python Wiki](https://github.com/blackducksoftware/hub-rest-api-python/wiki)
