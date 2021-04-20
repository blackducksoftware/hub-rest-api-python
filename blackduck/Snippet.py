import logging
import requests
import json
from operator import itemgetter
import urllib.parse
from .Exceptions import UnsupportedBDVersion

logger = logging.getLogger(__name__)

def _check_version_compatibility(self):
    if int(self.bd_major_version) < 2018:
        raise UnsupportedBDVersion("The BD major version {} is less than the minimum required major version {}".format(self.bd_major_version, 2018))        

def get_file_matches_for_bom_component(self, bom_component, limit=1000):
    self._check_version_compatibility()
    url = self.get_link(bom_component, "matched-files")
    paramstring = self.get_limit_paramstring(limit)
    logger.debug("GET {}".format(url))
    response = self.execute_get(url)
    jsondata = response.json()
    return jsondata

