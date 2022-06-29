from jinja2 import Environment, FileSystemLoader
from slugify import slugify
import os
import json
import argparse
import datetime

parser = argparse.ArgumentParser("A program to transform a JSON formatted representation of a Black Duck notices file into a standalone HTML document")
parser.add_argument("json_file", help="The input JSON file to be converted")
parser.add_argument("output_file_html", help="The file to output the results to")

args = parser.parse_args()
date = datetime.date.today()

templates_dir = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(templates_dir))
env.filters['slugify'] = slugify
template = env.get_template('notices-template.html')

with open(args.output_file_html, 'wb+') as fh:
    with open(args.json_file, 'r') as lj:
        data = json.load(lj)
        fileContent = data['reportContent'][0]['fileContent']

        fh.write(template.render(componentLicenses=fileContent['componentLicenses'],
                                 licenseTexts=fileContent['licenseTexts'],
                                 componentCopyrightTexts=fileContent['componentCopyrightTexts'],
                                 projectVersion=fileContent['projectVersion'],
                                 date=date
                                 ).encode("utf-8"))
