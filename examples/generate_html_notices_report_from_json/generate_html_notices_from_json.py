from jinja2 import Environment, FileSystemLoader
from slugify import slugify
import os
import json
import argparse
import datetime
import re

parser = argparse.ArgumentParser("A program to transform a JSON formatted representation of a Black Duck notices file into a standalone HTML document")
parser.add_argument("json_file", help="The input JSON file to be converted")
parser.add_argument("output_file_html", help="The file to output the results to")

args = parser.parse_args()
date = datetime.date.today()

templates_dir = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(templates_dir))
env.filters['slugify'] = slugify
template = env.get_template('notices-template.html')
copyrightFilters = [
    re.compile(r".*[0-9]{4,}.*"), # at least four numbers for years. years with 2 digits tend to follow 4 (e.g., 1991, 92, 93)
    # an email address https://stackoverflow.com/a/201378
    re.compile(r'''.*(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\]).*'''), 
    re.compile(r"copyright", re.IGNORECASE), # an explicit copyright statement
]

def processCopyrightText(copyrightTexts: dict, filters:list=[]) -> dict:
    """Sort, filter, and remove duplicates from copyright texts from componentCopyrightTexts.

    The algorithm for Copyright Texts in Black Duck are very conservative and result in a lot of potentially false positives. This function will attempt to remove false positives and order the list.

    Args:
        copyrightTexts (dict): Dictionary with list of copyrights in key copyrightTexts
        filters (list, optional): List of regex pattern filters. Matching any filters will keep the item. Defaults to [].

    Returns:
        dict: A processed version of copyrightTexts.
    """
    from collections import OrderedDict
    if copyrightTexts:
        for component in copyrightTexts:
            copyrightlist = component.get("copyrightTexts")
            if filters:
                filteredlist = []
                for filterRegex in filters:
                    filteredlist += list(filter(lambda x: filterRegex.match(x), copyrightlist))
                    filteredlist                  
                copyrightlist = map(lambda x: x.strip(),filteredlist)
            if copyrightlist:
                component["copyrightTexts"] = list(OrderedDict.fromkeys(copyrightlist))
                component["copyrightTexts"].sort()
    return copyrightTexts

with open(args.output_file_html, 'wb+') as fh:
    with open(args.json_file, 'r') as lj:
        data = json.load(lj)
        fileContent = data['reportContent'][0]['fileContent']

        fh.write(template.render(componentLicenses=fileContent['componentLicenses'],
                                 licenseTexts=fileContent['licenseTexts'],
                                 componentCopyrightTexts=processCopyrightText(fileContent['componentCopyrightTexts'], copyrightFilters),
                                 projectVersion=fileContent['projectVersion'],
                                 date=date
                                 ).encode("utf-8"))
