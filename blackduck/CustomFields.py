import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def _get_cf_url(self):
    return self.get_apibase() + "/custom-fields/objects"

def supported_cf_object_types(self):
    '''Get the types and cache them since they are static (on a per-release basis)'''
    if not hasattr(self, "_cf_object_types"):
        logger.debug("retrieving object types")
        self._cf_object_types = [cfo['name'] for cfo in self.get_cf_objects().get('items', [])]
    return self._cf_object_types

def get_cf_objects(self):
    '''Get CF objects and cache them since these are static (on a per-release basis)'''
    url = self._get_cf_url()
    if not hasattr(self, "_cf_objects"):
        logger.debug("retrieving objects")
        response = self.execute_get(url)
        self._cf_objects = response.json()
    return self._cf_objects

def _get_cf_object_url(self, object_name):
    for cf_object in self.get_cf_objects().get('items', []):
        if cf_object['name'].lower() == object_name.lower():
            return cf_object['_meta']['href']

def get_cf_object(self, object_name):
    assert object_name in self.supported_cf_object_types(), "Object name {} not one of the supported types ({})".format(object_name, self.supported_cf_object_types())

    object_url = self._get_cf_object_url(object_name)
    response = self.execute_get(object_url)
    return response.json()

def _get_cf_obj_rel_path(self, object_name):
    return object_name.lower().replace(" ", "-")

def create_cf(self, object_name, field_type, description, label, position, active=True, initial_options=[]):
    '''
        Create a custom field for the given object type (e.g. "Project", "Project Version") using the field_type and other parameters.

        Initial options are needed for field types like multi-select where the multiple values to choose from must also be provided.

        initial_options = [{"label":"val1", "position":0}, {"label":"val2", "position":1}]
    '''
    assert isinstance(position, int) and position >= 0, "position must be an integer that is greater than or equal to 0"
    assert field_type in ["BOOLEAN", "DATE", "DROPDOWN", "MULTISELECT", "RADIO", "TEXT", "TEXTAREA"]

    types_using_initial_options = ["DROPDOWN", "MULTISELECT", "RADIO"]

    post_url = self._get_cf_object_url(object_name) + "/fields"
    cf_object = self._get_cf_obj_rel_path(object_name)
    cf_request = {
        "active": active,
        "description": description,
        "label": label,
        "position": position,
        "type": field_type,
    }
    if field_type in types_using_initial_options and initial_options:
        cf_request.update({"initialOptions": initial_options})
    response = self.execute_post(post_url, data=cf_request)
    return response

def delete_cf(self, object_name, field_id):
    '''Delete a custom field from a given object type, e.g. Project, Project Version, Component, etc

    WARNING: Deleting a custom field is irreversiable. Any data in the custom fields could be lost so use with caution.
    '''
    assert object_name in self.supported_cf_object_types(), "You must supply a supported object name that is in {}".format(self.supported_cf_object_types())

    delete_url = self._get_cf_object_url(object_name) + "/fields/{}".format(field_id)
    return self.execute_delete(delete_url)

def get_custom_fields(self, object_name):
    '''Get the custom field (definition) for a given object type, e.g. Project, Project Version, Component, etc
    '''
    assert object_name in self.supported_cf_object_types(), "You must supply a supported object name that is in {}".format(self.supported_cf_object_types())

    url = self._get_cf_object_url(object_name) + "/fields"

    response = self.execute_get(url)        
    return response.json()

def get_cf_values(self, obj):
    '''Get all of the custom fields from an object such as a Project, Project Version, Component, etc

    The obj is expected to be the JSON document for a project, project-version, component, etc
    '''
    url = self.get_link(obj, "custom-fields")
    response = self.execute_get(url)
    return response.json()

def get_cf_value(self, obj, field_id):
    '''Get a custom field value from an object such as a Project, Project Version, Component, etc

    The obj is expected to be the JSON document for a project, project-version, component, etc
    '''
    url = self.get_link(obj, "custom-fields") + "/{}".format(field_id)
    response = self.execute_get(url)
    return response.json()

def put_cf_value(self, cf_url, new_cf_obj):
    '''new_cf_obj is expected to be a modified custom field value object with the values updated accordingly, e.g.
    call get_cf_value, modify the object, and then call put_cf_value
    '''
    return self.execute_put(cf_url, new_cf_obj)
