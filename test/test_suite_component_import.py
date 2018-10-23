#!/usr/bin/env python
 
import pytest
from suite_component_import import SuiteComponentImport
from unittest import mock


def test_import_component_returns_false_if_one_or_more_keys_missing():
	sci = SuiteComponentImport("my-component-list", hub_instance = mock.Mock())
	sci._import_component_approval_status = mock.Mock()

	component_info = {
		SuiteComponentImport.COMPONENT_ID_COL_NAME : "fake-component-id",
		SuiteComponentImport.RELEASE_ID_COL_NAME : 'fake-release-id',
	}

	assert sci._import_component(component_info) == False
	assert sci._import_component_approval_status.called == False

def test_import_component_with_all_values_present():
	sci = SuiteComponentImport("my-component-list", hub_instance = mock.Mock())
	sci._import_component_approval_status = mock.MagicMock()
	sci._import_component_approval_status.return_value = True

	component_info = {
		SuiteComponentImport.COMPONENT_ID_COL_NAME : "fake-component-id",
		SuiteComponentImport.RELEASE_ID_COL_NAME : 'fake-release-id',
		SuiteComponentImport.APPROVAL_COL_NAME : 'APPROVED'
	}

	assert sci._import_component(component_info) == True
	sci._import_component_approval_status.assert_called_once_with('fake-component-id', 'APPROVED', 'fake-release-id')


