from blackduck.HubRestApi import HubInstance

hub = HubInstance()

response = hub.get_health_checks()

print(response.json())