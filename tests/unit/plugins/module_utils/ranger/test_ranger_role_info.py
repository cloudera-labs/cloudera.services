# -*- coding: utf-8 -*-

# Copyright 2026 Cloudera, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
)

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesClient,
    ServicesError,
    from_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
    RangerRoleClient,
)

ENDPOINT_URL = "https://ranger.example"

# Ranger returns role objects with camelCase keys.
ROLE_RESPONSE = {
    "id": 7,
    "guid": "role-guid-7",
    "isEnabled": True,
    "createdBy": "Admin",
    "updatedBy": "Admin",
    "createTime": 1700000000000,
    "updateTime": 1700000000000,
    "version": 1,
    "name": "test_role",
    "description": "Test role",
    "options": {},
    "users": [{"name": "admin", "isAdmin": True}, {"name": "alice", "isAdmin": False}],
    "groups": [{"name": "data_engineers", "isAdmin": False}],
    "roles": [],
    "createdByUser": "admin",
}

ROLES_LIST = {"roles": [ROLE_RESPONSE]}

# A Ranger 400 response with a DATA_NOT_FOUND body (Ranger's "not found" signal).
RANGER_NOT_FOUND_400 = {
    "status": 400,
    "body": {
        "statusCode": 1,
        "messageList": [{"name": "DATA_NOT_FOUND"}],
    },
}

# A Ranger 400 response for some other (non "not found") error.
RANGER_ERROR_400 = {
    "status": 400,
    "body": {
        "statusCode": 2,
        "messageList": [{"name": "VALIDATION_ERROR"}],
    },
}


def _role_from_response(raw):
    """Mirror the client's deserialisation of a Ranger role response."""
    return from_dict(RangerRole, camel_dict_to_snake_dict(raw, reversible=True))


def test_list_roles(mocker):
    """Test listing all roles."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = ROLES_LIST

    client = RangerRoleClient(api_client=api_client)

    response = client.list_roles()

    assert isinstance(response, list)
    assert len(response) == 1
    assert isinstance(response[0], RangerRole)
    assert response[0] == _role_from_response(ROLE_RESPONSE)

    api_client.get.assert_called_once_with(
        "/service/roles/roles",
        squelch={404: {"roles": []}},
    )


def test_list_roles_empty(mocker):
    """Test listing roles when none exist."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {"roles": []}

    client = RangerRoleClient(api_client=api_client)

    response = client.list_roles()

    assert response == []


def test_get_role_by_id(mocker):
    """Test getting a role by id."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = ROLE_RESPONSE

    client = RangerRoleClient(api_client=api_client)

    response = client.get_role_by_id(role_id=7)

    assert isinstance(response, RangerRole)
    assert response.id == 7
    assert response.name == "test_role"

    api_client.get.assert_called_once_with(
        "/service/roles/roles/7",
        squelch={404: None},
        passthru=[400],
    )


def test_get_role_by_id_not_found_squelched(mocker):
    """Test getting a non-existent role by id (squelched 404) returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = RangerRoleClient(api_client=api_client)

    response = client.get_role_by_id(role_id=999)

    assert response is None


def test_get_role_by_id_not_found_400(mocker):
    """Test getting a non-existent role by id (Ranger 400 DATA_NOT_FOUND) returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = RANGER_NOT_FOUND_400

    client = RangerRoleClient(api_client=api_client)

    response = client.get_role_by_id(role_id=999)

    assert response is None


def test_get_role_by_id_not_found_empty_response(mocker):
    """Test an unknown id (Ranger returns an empty 200 body) returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {}

    client = RangerRoleClient(api_client=api_client)

    assert client.get_role_by_id(role_id=999) is None


def test_get_role_by_id_error(mocker):
    """Test that a non "not found" Ranger 400 raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = RANGER_ERROR_400

    client = RangerRoleClient(api_client=api_client)

    with pytest.raises(ServicesError):
        client.get_role_by_id(role_id=7)


def test_get_role_by_name(mocker):
    """Test getting a role by name checks the names list, then fetches the role."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [["other", "test_role"], ROLE_RESPONSE]

    client = RangerRoleClient(api_client=api_client)

    response = client.get_role_by_name(role_name="test_role")

    assert isinstance(response, RangerRole)
    assert response.name == "test_role"
    assert response.id == 7

    assert api_client.get.call_args_list == [
        mocker.call("/service/roles/roles/names", squelch={404: []}),
        mocker.call(
            "/service/roles/roles/name/test_role",
            squelch={404: None},
            passthru=[400],
        ),
    ]


def test_get_role_by_name_not_in_names(mocker):
    """Test a name absent from the names list returns None without a second call."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = ["other"]

    client = RangerRoleClient(api_client=api_client)

    assert client.get_role_by_name(role_name="non-existent-role") is None

    api_client.get.assert_called_once_with(
        "/service/roles/roles/names",
        squelch={404: []},
    )


def test_get_role_by_name_no_roles(mocker):
    """Test an empty or squelched names response returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = RangerRoleClient(api_client=api_client)

    assert client.get_role_by_name(role_name="test_role") is None


def test_get_role_by_name_not_found_400(mocker):
    """Test a listed role that vanishes (DATA_NOT_FOUND 400) returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [["test_role"], RANGER_NOT_FOUND_400]

    client = RangerRoleClient(api_client=api_client)

    assert client.get_role_by_name(role_name="test_role") is None


def test_get_role_by_name_error(mocker):
    """Test that a non "not found" Ranger 400 raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.side_effect = [["test_role"], RANGER_ERROR_400]

    client = RangerRoleClient(api_client=api_client)

    with pytest.raises(ServicesError):
        client.get_role_by_name(role_name="test_role")
