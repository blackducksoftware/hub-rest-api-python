#!/bin/bash
# set -x
# invoke from root of repository, e.g.
# 	cd repo_dir
# 	./examples/poll_for_bom_computed_notifications.bash
#

while true
do
	echo "polling for bom computed notifications to create fix it messages for the project-versions"
	if [ -f ".last_run" ]
	then
		OPTIONS="-n $(cat .last_run) -d"
	else
		OPTIONS="-n $(date +"%Y-%m-%dT%H:%M:%SZ") -d"
	fi
	python examples/get_bom_computed_notifications.py ${OPTIONS} |
	python examples/project_version_urls_from_bom_computed_notifications.py | 
	while read url
	do
		echo "Processing BOM to produce a fix it message for url $url" >&2
		python examples/get_bom_component_policy_violations.py -u $url |
		python examples/create_fix_it_message.py -o $(basename $url).html
		echo "Wrote fix it message to $(basename $url).html"
	done
	sleep 5
done