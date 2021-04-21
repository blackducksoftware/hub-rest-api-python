import argparse


from blackduck.HubRestApi import HubInstance

global_roles = [
		"Component Manager",
		"Global Code Scanner",
		"License Manager",
		"Policy Manager",
		"Project Creator",
		"Super User",
		"System Administrator",
		"All"
	]

parser = argparse.ArgumentParser("Delete a global role from a user group")
parser.add_argument("group_name")
parser.add_argument("role", choices=global_roles, help="Delete a global role from the user group. If set to 'All' will delete all global roles from the user group")

args = parser.parse_args()

hub = HubInstance()

group = hub.get_user_group_by_name(args.group_name)
if group:
	if args.role == 'All':
		roles_to_delete = [r for r in global_roles if r != 'All']
	else:
		roles_to_delete = [args.role]
	for role_to_delete in roles_to_delete:
		print("Deleting role {} from user group {}".format(role_to_delete, args.group_name))
		response = hub.delete_role_from_user_or_group(role_to_delete, group)
		print("Deleted role {}".format(role_to_delete))