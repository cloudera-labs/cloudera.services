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

from types import SimpleNamespace

import pytest

from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
)

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesClient,
    ServicesError,
    build_from_params,
    from_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
    RangerRoleClient,
    RangerRoleMember,
    extract_role_params,
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


# ---------------------------------------------------------------------------
# RangerRoleClient - create / update / delete
# ---------------------------------------------------------------------------


def test_create_role(mocker):
    """Test creating a role serialises to a camelCase payload."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = ROLE_RESPONSE

    client = RangerRoleClient(api_client=api_client)

    response = client.create_role(
        RangerRole(
            name="test_role",
            description="Test role",
            users=[{"name": "admin", "is_admin": True}],
        ),
    )

    assert response == _role_from_response(ROLE_RESPONSE)

    api_client.post.assert_called_once_with(
        "/service/roles/roles",
        params={"createNonExistUserGroup": False},
        data={
            "name": "test_role",
            "description": "Test role",
            "users": [{"name": "admin", "isAdmin": True}],
        },
    )


def test_create_role_minimal(mocker):
    """Test creating a role with only a name omits all NULLABLE fields."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = ROLE_RESPONSE

    client = RangerRoleClient(api_client=api_client)

    response = client.create_role(RangerRole(name="test_role"))

    assert isinstance(response, RangerRole)
    api_client.post.assert_called_once_with(
        "/service/roles/roles",
        params={"createNonExistUserGroup": False},
        data={"name": "test_role"},
    )


def test_create_role_with_create_non_exist_user_group(mocker):
    """Test the createNonExistUserGroup query parameter is forwarded."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = ROLE_RESPONSE

    client = RangerRoleClient(api_client=api_client)

    client.create_role(RangerRole(name="test_role"), create_non_exist_user_group=True)

    call = api_client.post.call_args
    assert call[1]["params"] == {"createNonExistUserGroup": True}


def test_update_role(mocker):
    """Test updating a role by its id."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = ROLE_RESPONSE

    client = RangerRoleClient(api_client=api_client)

    response = client.update_role(
        RangerRole(id=7, name="test_role", description="Updated"),
    )

    assert response == _role_from_response(ROLE_RESPONSE)

    api_client.put.assert_called_once_with(
        "/service/roles/roles/7",
        params={"createNonExistUserGroup": False},
        data={"id": 7, "name": "test_role", "description": "Updated"},
    )


def test_update_role_without_id(mocker):
    """Test updating a role without an id raises ValueError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = RangerRoleClient(api_client=api_client)

    with pytest.raises(ValueError, match="Cannot update a role without an id"):
        client.update_role(RangerRole(name="test_role"))

    api_client.put.assert_not_called()


def test_delete_role_by_id(mocker):
    """Test deleting a role by id."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = None

    client = RangerRoleClient(api_client=api_client)

    response = client.delete_role_by_id(role_id=7)

    assert response is None

    api_client.delete.assert_called_once_with(
        "/service/roles/roles/7",
        squelch={404: None},
        passthru=[400],
    )


def test_delete_role_by_id_not_found(mocker):
    """Test deleting a non-existent role (Ranger 400 DATA_NOT_FOUND) is a no-op."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = RANGER_NOT_FOUND_400

    client = RangerRoleClient(api_client=api_client)

    response = client.delete_role_by_id(role_id=999)

    assert response is None


def test_delete_role_by_id_error(mocker):
    """Test that a non "not found" Ranger 400 raises a ServicesError on delete."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = RANGER_ERROR_400

    client = RangerRoleClient(api_client=api_client)

    with pytest.raises(ServicesError):
        client.delete_role_by_id(role_id=7)


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------


def test_role_from_response_snakecase():
    """Test deserialisation maps camelCase to snake_case dataclass fields."""
    role = _role_from_response(ROLE_RESPONSE)

    assert isinstance(role, RangerRole)
    assert role.id == 7
    assert role.guid == "role-guid-7"
    assert role.name == "test_role"
    assert role.created_by == "Admin"
    assert role.updated_by == "Admin"
    assert role.created_by_user == "admin"

    # Nested member lists are parsed into RangerRoleMember dataclasses.
    assert isinstance(role.users[0], RangerRoleMember)
    assert role.users[0].name == "admin"
    assert role.users[0].is_admin is True
    assert role.users[1].name == "alice"
    assert role.users[1].is_admin is False

    assert isinstance(role.groups[0], RangerRoleMember)
    assert role.groups[0].name == "data_engineers"

    assert role.roles == []


# ---------------------------------------------------------------------------
# extract_role_params / build_from_params
# ---------------------------------------------------------------------------


def test_extract_role_params():
    """Test extracting role params from a module-like instance."""
    module = SimpleNamespace(
        name="r",
        description="d",
        users=[{"name": "alice"}],
    )

    params = extract_role_params(module)

    assert params["name"] == "r"
    assert params["description"] == "d"
    assert params["users"] == [{"name": "alice"}]
    # Unset attributes default to None.
    assert params["groups"] is None
    assert params["roles"] is None
    assert params["options"] is None


def test_build_from_params_create():
    """Test building a role for creation keeps unset fields NULLABLE."""
    role = build_from_params(
        RangerRole,
        {"name": "r", "description": "d"},
    )

    assert role.name == "r"
    assert role.description == "d"
    # Unset fields stay NULLABLE so they are omitted from the payload.
    assert role.users is NULLABLE
    assert role.options is NULLABLE
    assert "description" in to_dict(role)
    assert "users" not in to_dict(role)


def test_build_from_params_update_falls_back_to_existing():
    """Test building a replacement role falls back to the existing values."""
    existing = RangerRole(
        id=10,
        guid="guid-10",
        version=3,
        name="r",
        description="old",
        is_enabled=True,
        users=[RangerRoleMember(name="alice", is_admin=True)],
    )

    role = build_from_params(
        RangerRole,
        {"name": "r", "description": "new"},
        existing=existing,
    )

    # Provided value wins.
    assert role.description == "new"
    # Unset field falls back to existing.
    assert role.is_enabled is True
    assert role.users == [RangerRoleMember(name="alice", is_admin=True)]
    # Read-only fields are preserved from existing.
    assert role.id == 10
    assert role.guid == "guid-10"
    assert role.version == 3
