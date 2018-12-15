'''
Created on Jul 18, 2018

@author: kumykov
'''
from blackduck.HubRestApi import HubInstance

hub = HubInstance("https://your-hub-host","the-user","the-password", insecure=True, debug=True)
