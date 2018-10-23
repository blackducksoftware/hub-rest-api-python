#!/usr/bin/env python

import csv
import logging
from pprint import pprint

from bds.HubRestApi import HubInstance


class SuiteComponentImport(object):
	# Map from Protex approval status to Hub approval status
	# TODO: Finish mapping all the code center/protex components approval status values into Hub here
	APPROVAL_STATUS_MAP = {
		'NOT_REVIEWED': 'UNREVIEWED',
		'APPROVED': 'APPROVED',
		'PENDING': 'UNREVIEWED',
		'REJECTED': 'REJECTED',

	}
	COMPONENT_COL_NAME='name'
	COMPONENT_TYPE_COL_NAME='ComponentType'
	VERSION_COL_NAME='version'
	LICENSE_COL_NAME='kblicensename'
	LICENSE_ID_COL_NAME='kblicenseid'
	APPROVAL_COL_NAME='status'
	COMPONENT_ID_COL_NAME='kbcomponentid'
	RELEASE_ID_COL_NAME='kbreleaseid'

	SUPPORTED_COMPONENT_TYPES = ["STANDARD", "STANDARD_MODIFIED"]

	def __init__(self, suite_component_list_file, hub_instance):
		'''Expects a pipe-delimited ("|") file with a header row that includes the following fields (note the case and spaces in the names)
			- Component
			- Version
			- License
			- Approval Status
			- component id
			- release id
		'''
		self.suite_component_list_file = suite_component_list_file
		self.hub_instance = hub_instance

	def _import_component_approval_status(self, protex_component_id, protex_approval_status, protex_release_id=None):
		imported_component_successfully = False
		protex_release_id = None if protex_release_id == "null" else protex_release_id
		logging.debug("Searching for Protex component with ID {} and version ID {}".format(protex_component_id, protex_release_id))
		try:
			hub_component_info = self.hub_instance.find_component_info_for_protex_component(
					protex_component_id,
					protex_release_id
				)
			if hub_component_info:
				if 'version' in hub_component_info:
					details_url = hub_component_info['version']
				elif 'component' in hub_component_info:
					details_url = hub_component_info['component']
				else:
					logging.error("Hub component info ({}) did not contain either a component or version url".format(hub_component_info))
					return False

				component_or_version_details = self.hub_instance.get_component_by_url(details_url)

				if component_or_version_details and 'approvalStatus' in component_or_version_details:
					logging.debug("Hub component or component version before update: {}".format(component_or_version_details))
					component_or_version_details['approvalStatus'] = SuiteComponentImport.APPROVAL_STATUS_MAP[
						protex_approval_status]

					self.hub_instance.update_component_by_url(details_url, component_or_version_details)
					imported_component_successfully = True
					
					component_or_version_details = self.hub_instance.get_component_by_url(details_url)
					logging.debug("Hub component or component version after update: {}".format(component_or_version_details))
			else:
				logging.warning('Could not locate Hub component or component version for Protex component id {} and release id {}'.format(protex_component_id, protex_release_id))
		except:
			logging.error(
				"Ooops. Something went very wrong for Protex component {}, release {}".format(protex_component_id, protex_release_id),
				exc_info=True)
			imported_component_successfully = False
		finally:
			return imported_component_successfully

	def _dump_updated_to_file(self, failed):
		self._dump_to_file(failed, "-updated.csv")

	def _dump_failed_to_file(self, failed):
		self._dump_to_file(failed, "-failed.csv")

	def _dump_skipped_to_file(self, skipped):
		self._dump_to_file(skipped, "-skipped.csv")
		
	def _dump_to_file(self, component_list, extension):
		# import pdb; pdb.set_trace()
		dump_csv_file = self.suite_component_list_file.replace(".csv", extension)
		with open(dump_csv_file, 'w', newline='') as csvfile:
			fieldnames = [
				SuiteComponentImport.COMPONENT_COL_NAME,
				SuiteComponentImport.VERSION_COL_NAME,
				SuiteComponentImport.LICENSE_COL_NAME,
				SuiteComponentImport.LICENSE_ID_COL_NAME,
				SuiteComponentImport.APPROVAL_COL_NAME,
				SuiteComponentImport.COMPONENT_ID_COL_NAME,
				SuiteComponentImport.RELEASE_ID_COL_NAME
			]
			writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
			writer.writeheader()
			for component in component_list:
				writer.writerow(component)
		logging.info("Dumped {} components into {}".format(len(component_list), dump_csv_file))

	def _import_component(self, suite_component_info):
		try:
			component_id = suite_component_info[SuiteComponentImport.COMPONENT_ID_COL_NAME]
			version_id = suite_component_info[SuiteComponentImport.RELEASE_ID_COL_NAME]
			approval_status = suite_component_info[SuiteComponentImport.APPROVAL_COL_NAME]
		except KeyError:
			logging.error("Missing required key in component info ({}), skipping...".format(suite_component_info))
			return False
		return self._import_component_approval_status(component_id,	approval_status, version_id)

	def import_components(self):
		with open(args.suite_component_list, newline='') as component_list_file:
			reader = csv.DictReader(component_list_file, delimiter="|")
			updated = []
			failed = []
			skipped = []
			for suite_component_info in reader:
				# if component type not give, default to STANDARD (i.e. KB component)
				component_type = suite_component_info.get(SuiteComponentImport.COMPONENT_TYPE_COL_NAME, "STANDARD")
				if component_type in SuiteComponentImport.SUPPORTED_COMPONENT_TYPES:
					logging.debug("Importing suite component: {}".format(suite_component_info))
					if self._import_component(suite_component_info):
						logging.info("Updated the Hub with suite component: {}".format(suite_component_info))
						updated.append(suite_component_info)
					else:
						logging.warn("Failed to update suite component: {}".format(suite_component_info))
						failed.append(suite_component_info)
				else:
					logging.debug("Skipping suite component because the type ({}) is not in supported types ({})".format(
						component_type, SuiteComponentImport.SUPPORTED_COMPONENT_TYPES))
					skipped.append(suite_component_info)

			logging.info("Updated {} suite components or component versions".format(len(updated)))
			self._dump_updated_to_file(updated)

			if len(failed) > 0:
				logging.info("Failed to update {} suite components or component versions".format(len(failed)))
				self._dump_failed_to_file(failed)
			if len(skipped) > 0:
				logging.info(
					"Skipped {} suite components or component versions because their type was not in {} types".format(
						len(skipped), SuiteComponentImport.SUPPORTED_COMPONENT_TYPES)
					)
				self._dump_skipped_to_file(skipped)

if __name__ == "__main__":
	import argparse
	import sys

	parser = argparse.ArgumentParser()
	parser.add_argument("suite_component_list", help="Pipe-delimited file containing the component information from Protex")
	parser.add_argument("--loglevel", choices=["CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING"], default="DEBUG", help="Choose the desired logging level - CRITICAL, DEBUG, ERROR, INFO, or WARNING. (default: DEBUG)")
	args = parser.parse_args()

	logging_levels = {
		'CRITICAL': logging.CRITICAL,
		'DEBUG': logging.DEBUG,
		'ERROR': logging.ERROR,
		'INFO': logging.INFO,
		'WARNING': logging.WARNING,
	}
	logging.basicConfig(stream=sys.stdout, format='%(threadName)s: %(asctime)s: %(levelname)s: %(message)s', level=logging_levels[args.loglevel])

	hub = HubInstance()

	protex_importer = SuiteComponentImport(args.suite_component_list, hub)

	protex_importer.import_components()












