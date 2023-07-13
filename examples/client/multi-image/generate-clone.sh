# Generate baseline project
#
# Project - container mapping

SUBPROJECTS="\
dashboard-ui:testcontainer:2.4,\
docs-ui:testcontainer:2.4,\
le:testcontainer:2.4,\
login-app-ui:testcontainer:2.4,\
nlv:testcontainer:2.4"

COMMAND="python3 examples/client/multi-image/manage_project_structure.py"

$COMMAND -u $BD_URL -t token -nv -p P3 -pv 2.4 -sp $SUBPROJECTS --clone-from 2.3 $@

