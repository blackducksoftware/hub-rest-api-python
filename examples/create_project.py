
import argparse
import json

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("--version", default="1.0", type=str)
parser.add_argument("--description", default="", type=str)

args = parser.parse_args()

hub = HubInstance()

response = hub.create_project(args.project_name, args.version, parameters = {
		"description": args.description
	})
print(response.status_code)