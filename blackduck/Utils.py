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


def to_datetime(date):
    """Utility function to convert common date formats to datetime object

    Args:
        iso_string (string/datetime/date)

    Returns:
        datetime.datetime
    """
    if isinstance(date, str):
        from dateutil.parser import parse
        return parse(date)
    if isinstance(date, datetime.datetime):
        return date
    if isinstance(date, datetime.date):
        return datetime.datetime(
            year=date.year,
            month=date.month,
            day=date.day
        )
        

def timespan(days_ago, from_date=datetime.now(), delta=timedelta(weeks=1)):
    curr_date = from_date - timedelta(days=days_ago)
    while curr_date < from_date:
        yield curr_date
        curr_date += delta

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

