import logging
import requests
import json
from operator import itemgetter
import urllib.parse

from .Utils import object_id

logger = logging.getLogger(__name__)

valid_categories = ['VERSION','CODE_LOCATIONS','COMPONENTS','SECURITY','FILES', 'ATTACHMENTS', 'CRYPTO_ALGORITHMS', 'PROJECT_VERSION_CUSTOM_FIELDS', 'BOM_COMPONENT_CUSTOM_FIELDS', 'LICENSE_TERM_FULFILLMENT', 'UPGRADE_GUIDANCE', 'VULNERABILITY_MATCH']
valid_report_formats = ["CSV", "JSON"]
def create_version_reports(self, version, report_list, format="CSV"):
    assert all(list(map(lambda k: k in valid_categories, report_list))), "One or more selected report categories in {} are not valid ({})".format(
        report_list, valid_categories)
    assert format in valid_report_formats, "Format must be one of {}".format(valid_report_formats)

    post_data = {
        'categories': report_list,
        'versionId': version['_meta']['href'].split("/")[-1],
        'reportType': 'VERSION',
        'reportFormat': format
    }
    version_reports_url = self.get_link(version, 'versionReport')
    return self.execute_post(version_reports_url, post_data)

valid_notices_formats = ["TEXT", "JSON"]
def create_version_notices_report(self, version, format="TEXT", include_copyright_info=True):
    assert format in valid_notices_formats, "Format must be one of {}".format(valid_notices_formats)

    post_data = {
        'versionId': object_id(version),
        'reportType': 'VERSION_LICENSE',
        'reportFormat': format
    }
    if include_copyright_info:
        post_data.update({'categories': ["COPYRIGHT_TEXT"] })

    notices_report_url = self.get_link(version, 'licenseReports')
    return self.execute_post(notices_report_url, post_data)

def download_report(self, report_id):
    # TODO: Fix me, looks like the reports should be downloaded from different paths than the one here, and depending on the type and format desired the path can change
    url = self.get_urlbase() + "/api/reports/{}".format(report_id)
    return self.execute_get(url, {'Content-Type': 'application/zip', 'Accept':'application/zip'})

def download_notification_report(self, report_location_url):
    '''Download the notices report using the report URL. Inspect the report object to determine
    the format and use the appropriate media header'''
    custom_headers = {'Accept': 'application/vnd.blackducksoftware.report-4+json'}
    response = self.execute_get(report_location_url, custom_headers=custom_headers)
    report_obj = response.json()

    if report_obj['reportFormat'] == 'TEXT':
        download_url = self.get_link(report_obj, "download") + ".json"
        logger.debug("downloading report from {}".format(download_url))
        response = self.execute_get(download_url, {'Accept': 'application/zip'})
    else:
        # JSON
        contents_url = self.get_link(report_obj, "content")
        logger.debug("retrieving report contents from {}".format(contents_url))
        response = self.execute_get(contents_url, {'Accept': 'application/json'})
    return response, report_obj['reportFormat']

##
#
# (Global) Vulnerability reports
#
##
valid_vuln_status_report_formats = ["CSV", "JSON"]
def create_vuln_status_report(self, format="CSV"):
    assert format in valid_vuln_status_report_formats, "Format must be one of {}".format(valid_vuln_status_report_formats)

    post_data = {
        "reportFormat": format,
        "locale": "en_US"
    }
    url = self.get_apibase() + "/vulnerability-status-reports"
    custom_headers = {
        'Content-Type': 'application/vnd.blackducksoftware.report-4+json',
        'Accept': 'application/vnd.blackducksoftware.report-4+json'
    }
    return self.execute_post(url, custom_headers=custom_headers, data=post_data)
