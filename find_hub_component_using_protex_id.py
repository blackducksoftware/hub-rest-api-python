#!/usr/bin/env python

'''
Created on Oct 14, 2018

@author: gsnyder

Finds and prints a Hub component given the Protex (or CC) component id and release (version) id
Note: If no release id is provided, the search will result in a (parent) Hub component (no specific version)

'''
from bds.HubRestApi import HubInstance
from pprint import pprint
from sys import argv

hub = HubInstance()

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser()
	parser.add_argument("protex_component_id", help="The protex component id")
	parser.add_argument("--release", default=None, help="The protex component release (aka version)")
	args = parser.parse_args()

	hub_component_info = hub.find_component_info_for_protex_component(args.protex_component_id, args.release)

	pprint(hub_component_info)
