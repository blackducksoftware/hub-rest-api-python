'''
Created on January 31, 2019

@author: gsnyder

Update one or more settings on a project version
'''
import argparse
import logging
import sys

from blackduck.HubRestApi import HubInstance

class InvalidSetting(Exception):
	pass

def validate_setting(setting):
	setting_choices = HubInstance.PROJECT_VERSION_SETTINGS

	if setting not in setting_choices:
		raise InvalidSetting("Setting {} is not in the list of valid Settings ({})".format(
			setting, setting_choices))

map_to_internal_setting_name = {
	'notes': 'releaseComments'
}

def create_setting_d_from_setting_l(settings_l):
	setting_d = dict()
	for setting in settings_l:
		setting_key = setting[0]
		setting_value = setting[1]

		validate_setting(setting_key)
		if setting_key in map_to_internal_setting_name:
			setting_key = map_to_internal_setting_name[setting_key]
		setting_d.update({setting_key: setting_value})
	return setting_d

parser = argparse.ArgumentParser("Update one or more settings on a project version in Black Duck")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("-s", "--setting", action="append", nargs=2,metavar=('setting', 'value'), 
	help=f"Settings you can change are {HubInstance.PROJECT_VERSION_SETTINGS}. Possible phases are {HubInstance.VERSION_PHASES}. Possible distribution values are {HubInstance.VERSION_DISTRIBUTION}")

args = parser.parse_args()

setting_d = create_setting_d_from_setting_l(args.setting)

hub = HubInstance()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)

hub.update_project_version_settings(args.project_name, args.version_name, setting_d)









