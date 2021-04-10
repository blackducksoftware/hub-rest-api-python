'''

Created on Dec 22, 2020
@author: ar-calder

'''

from datetime import datetime, timedelta
import dateutil.parser
import json
import logging
import re

logger = logging.getLogger(__name__)


def iso8601_to_date(iso_string, with_zone=False):
    """Utility function to convert iso_8601 formatted string to datetime object, optionally accounting for timezone

    Args:
        iso_string (string): the iso_8601 string to convert to datetime object
        with_zone (bool, optional): whether to account for timezone offset. Defaults to False.

    Returns:
        datetime.datetime: equivalent time, with or without timezone offsets
    """
    date_timezone = iso_string.split('Z')
    date = dateutil.parser.parse(date_timezone[0])
    if with_zone and len(date_timezone > 1):
        hours_minutes = date_timezone[1].split(':')
        minutes = (60*int(hours_minutes[0]) + int(hours_minutes[1] if len(hours_minutes) > 1 else 0))
        date = date + datetime.timedelta(minutes=minutes)
    return date

def iso8601_timespan(days_ago, from_date=datetime.utcnow(), delta=timedelta(weeks=1)):
    curr_date = from_date - timedelta(days=days_ago)
    while curr_date < from_date:
        yield curr_date.isoformat('T', 'seconds')
        curr_date += delta

def min_iso8601():
    """Utility wrapper for iso8601_to_date which provides minimum date (for comparison purposes).

    Returns:
        datetime.datetime: 0 / 1970-01-01T00:00:00.000
    """
    return iso8601_to_date("1970-01-01T00:00:00.000")

def find_field(data_to_filter, field_name, field_value):
    """Utility function to filter blackduck objects for specific fields

    Args:
        data_to_filter (dict): typically the blackduck object or subselection of this
        field_name (string): name of field to use in comparisons
        field_value (string): value of field we seek

    Returns:
        object: object if found or None.
    """
    return next(filter(lambda d: d.get(field_name) == field_value, data_to_filter), None)

def safe_get(obj, *keys):
    """Utility function to safely perform multiple get's on a dict.
       Particularly useful on complex/deep objects.

    Args:
        obj (dict): object to perform get on.
        *keys (string): consecutive keys as args.

    Returns:
        object: object if found or None.
    """
    for key in keys:
        try:
            obj = obj[key]
        except KeyError:
            return None
    return obj

def get_url(obj):
    """Utility wrapper for safe_get providing URL lookup for a given object

    Args:
        obj (dict): object to perform URL lookup on.

    Returns:
        string: url if found or None.
    """
    return safe_get(obj, '_meta', 'href')

def get_resource_name(obj):
    """Utility function to determine resource name from a given resource object

    Args:
        obj (dict): object to perform name lookup on.

    Returns:
        string: name if found or None.
    """
    parts = get_url(obj).split('/')
    print("parts =", get_url(obj))
    for part in reversed(parts[:-1]):
        # regex for id 8-4-4-12
        if re.search("^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$", part):
            continue    
        return part
    

def pfmt(value):
    """Utility function to 'pretty format' a dict or json 

    Args:
        value (json/dict): the json object or dict to pretty format

    Returns:
        string: json formatted string representing passed object
    """
    return json.dumps(value, indent=4)

def pprint(value):
    """Utility wrapper for pfmt that prints 'pretty formatted' json data.

    Args:
        value (json/dict): the json object or dict to pretty print

    Returns:
        None
    """
    print(pfmt(value))

def object_id(object):
    assert '_meta' in object, "REST API object must have _meta key"
    assert 'href' in object['_meta'], "REST API object must have href key in it's _meta"
    return object['_meta']['href'].split("/")[-1]

def expect_type(given, expected):
    """Utility wrapper for assert isinstance.

    Args:
        given (object): object to compare
        expected (type): expected object type

    Throws:
        AssertionError: on expected type != given type
    """
    assert isinstance(given, expected), f"Expected {expected} given {type(given)}"

