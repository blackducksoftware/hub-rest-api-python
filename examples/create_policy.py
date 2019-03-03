from blackduck.HubRestApi import HubInstance

hub = HubInstance()


policy_data = {"name":"new-rule",
	"description":"description",
	"severity":"BLOCKER",
	"enabled":True,
	"overridable":True,
	"policyType":"BOM_COMPONENT_DISALLOW",
	"expression":{
		"operator":"AND",
		"expressions":[{
			"name":"HIGH_SEVERITY_VULN_COUNT",
			"operation":"EQ",
			"parameters":{"values":["0"]}}]},"wait":True}

result = hub.create_policy(policy_data)

print(result)