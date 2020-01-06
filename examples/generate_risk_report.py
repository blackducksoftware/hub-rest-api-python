import argparse
from blackduck.HubRestApi import HubInstance
import json
import pandas as pd
import time

parser = argparse.ArgumentParser("A program to create consolidated Source report for sub projects")
parser.add_argument("project_name")
parser.add_argument("version_name")

args = parser.parse_args()
hub = HubInstance()


project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version_name)
bom_components = hub.get_version_components(version)
timestamp = time.strftime('%m_%d_%Y_%H_%M')
projname = args.project_name
projversion = args.version_name
file_out = (args.project_name + '-' + args.version_name + '-risk-report-' + timestamp + '.csv')

compnamelist = []
compversionlist = []
licensenameslist = []
critsecrisklist = []
highsecrisklist = []
medsecrisklist = []
lowsecrisklist = []
opriskvaluelist = []



if project:
    if version:
        for bom_components in bom_components['items']:
            all_risk_profile_info = list()
            licenses = bom_components['licenses']
            securityRiskProfile = bom_components['securityRiskProfile']
            operationalRiskProfile = bom_components['operationalRiskProfile']
            compname = bom_components['componentName']
            compnamelist.append(compname)
            compversion = bom_components['componentVersionName']
            compversionlist.append(compversion)
            opriskvalue= '' 
            for l in licenses:
                if l['licenseDisplay'] == 'licenseDisplay':
                    pass
                licensename = l.get('licenseDisplay')
                licensenameslist.append(licensename)

            lowsecrisk = securityRiskProfile['counts'][1]['count']
            lowsecrisklist.append(lowsecrisk)
            medsecrisk = securityRiskProfile['counts'][2]['count']
            medsecrisklist.append(medsecrisk)
            highsecrisk = securityRiskProfile['counts'][3]['count']
            highsecrisklist.append(highsecrisk)
            critsecrisk = securityRiskProfile['counts'][4]['count']
            critsecrisklist.append(critsecrisk)

            nooprisk = operationalRiskProfile['counts'][1]['count']
            lowoprisk = operationalRiskProfile['counts'][2]['count']
            medoprisk = operationalRiskProfile['counts'][3]['count']
            highoprisk = operationalRiskProfile['counts'][4]['count']
            critoprisk = operationalRiskProfile['counts'][5]['count']
            if critoprisk == 1:
                opriskvalue = 'critical'
            elif highoprisk == 1:
                opriskvalue = 'high'
            elif medoprisk == 1:
                opriskvalue = 'medium'
            elif lowoprisk == 1:
                opriskvalue = 'low'
            else:
                opriskvalue = 'none'
            opriskvaluelist.append(opriskvalue)

        print(opriskvaluelist)
        df = pd.DataFrame({'Component': compnamelist,
                           'Version': compversionlist,
                           'License(s)': licensenameslist,
                           'Critical Security Risk': critsecrisklist,
                           'High Security Risk': highsecrisklist,
                           'Medium Security Risk': medsecrisklist,
                           'Low Security Risk': lowsecrisklist,
                           'Operational Risk': opriskvaluelist})
        print(df)
        df.to_csv(file_out, encoding='utf-8', index=False)


