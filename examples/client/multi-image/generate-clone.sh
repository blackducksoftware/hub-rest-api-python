# Generate baseline project
#
# Project - container mapping

SUBPROJECTS="\
dashboard-ui:testcontainer:2.4,\
docs-ui:testcontainer:2.4,\
le:testcontainer:2.4,\
login-app-ui:testcontainer:2.4,\
nlv:testcontainer:2.4"

SPECFILE=~/Documents/Ciena/excelparameters/BP_SampleProduct.xlsx

ls -l $SPECFILE

COMMAND="python3 examples/client/multi-image/manage_project_structure.py"

# $COMMAND -u $BD_URL -t token -nv -pg "Test Group" -p P3 -pv 2.4 -sp $SUBPROJECTS --clone-from 2.3 $@
$COMMAND -u $BD_URL -t token -nv -pg "Test Group" -p P3 -pv 2.4 -ssf $SPECFILE --clone-from 2.3 $@
