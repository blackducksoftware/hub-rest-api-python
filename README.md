# Overview

The hub-rest-api-python provides Python bindings for Hub REST API.

# Paging and Black Duck v2022.2

In v2022.2 of Black Duck the REST API introduced a max page size to protect system resource usage. See the Black Duck [release notes on Synopsys Community](https://community.synopsys.com/s/article/Black-Duck-Release-Notes) for the details of which API endpoints are affected. Users of the the python bindings here should leverage the Client interface which provides automatic paging support to make best use of these endpoints.

**The old HubInstance interface and many of the examples using it do not perform paging and will break as a result of the changes in v2022.2**.

Any issues related to the HubInstance Interface will be closed as *Won't Fix*

Any PRs with new or modified example scripts/utilities **must** use the client interface.

# New in 1.0.0

Introducing the new Client class.

In order to provide a more robust long-term connection, faster performance, and an overall better experience a new
Client class has been designed.

It is backed by a [Requests session](https://docs.python-requests.org/en/master/user/advanced/#session-objects) object. The user specifies a base URL, timeout, retries, proxies, and TLS verification upon initialization and these attributes are persisted across all requests.

At the REST API level, the Client class provides a consistent way to discover and traverse public resources, uses a
[generator](https://wiki.python.org/moin/Generators) to fetch all items using pagination, and automatically renews the bearer token.

See [Client versus HubInstance Comparison](https://github.com/blackducksoftware/hub-rest-api-python/wiki/Client-versus-HubInstance-Comparison) and also read the [Client User Guide](https://github.com/blackducksoftware/hub-rest-api-python/wiki/Client-User-Guide) on the [Hub REST API Python Wiki](https://github.com/blackducksoftware/hub-rest-api-python/wiki).

### Important Notes
The old HubInstance (in HubRestApi.py) keeps its existing functionality for backwards compatibility and therefore does **not** currently leverage any of the new features in the Client class.

We believe that the new features are compelling enough to strongly encourage users to consider moving from HubInstance to Client.
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

**Examples which use the old HubInstance interface -which is not maintained- are not guaranteed to work. Use at your own risk.**

# Version History

Including a version history on a go-forward basis. 

## v1.1.0

Retries will be attempted for all HTTP verbs, not just GET.

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

