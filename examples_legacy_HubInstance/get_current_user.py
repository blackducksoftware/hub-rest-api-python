

import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()

current_user = hub.get_current_user()

print(json.dumps(current_user))