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

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ranger_role
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
    RangerRoleMember,
)

BASE_URL = "https://ranger.example"

# RangerRoleMember (not a raw dict) is used here to match what the real
# RangerRoleClient returns (via from_dict()) - a raw dict would never
# compare equal to the RangerRoleMember instances build_from_params()
# constructs from matching module args, breaking "no changes" detection.
EXISTING_ROLE = RangerRole(
    id=7,
    guid="role-guid-7",
    name="test_role",
    description="An existing role",
    is_enabled=True,
    users=[RangerRoleMember(name="admin", is_admin=True)],
    version=1,
)


def test_ranger_role_module_create_minimal(module_args, mocker):
    """Test RangerRoleModule creating a new role with only a name."""
    mock_get_by_name = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=None,
    )
    mock_create = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.create_role",
        return_value=RangerRole(
            id=1,
            guid="new-role-guid",
            name="test_role02",
            is_enabled=True,
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "test_role02",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["id"] == 1
    assert result["role"]["name"] == "test_role02"
    assert "diff" not in result

    mock_get_by_name.assert_called_once_with("test_role02")
    mock_create.assert_called_once()


def test_ranger_role_module_create_full(module_args, mocker):
    """Test RangerRoleModule creating a new role with all fields set."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=None,
    )
    mock_create = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.create_role",
        return_value=RangerRole(
            id=2,
            guid="role-guid-2",
            name="test_role",
            description="Created by unit test",
            is_enabled=True,
            users=[{"name": "admin", "is_admin": True}],
            groups=[{"name": "data_engineers", "is_admin": False}],
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "test_role",
            "description": "Created by unit test",
            "users": [{"name": "admin", "is_admin": True}],
            "groups": [{"name": "data_engineers"}],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["name"] == "test_role"
    assert result["role"]["users"][0]["name"] == "admin"
    assert result["role"]["groups"][0]["name"] == "data_engineers"

    created_role = mock_create.call_args[0][0]
    assert created_role.name == "test_role"
    assert created_role.description == "Created by unit test"


def test_ranger_role_module_create_check_mode(module_args, mocker):
    """Test RangerRoleModule create in check mode does not call the API."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=None,
    )
    mock_create = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.create_role",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "test_role02",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["name"] == "test_role02"

    mock_create.assert_not_called()


def test_ranger_role_module_create_diff_mode(module_args, mocker):
    """Test RangerRoleModule create in diff mode reports before/after."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=None,
    )
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.create_role",
        return_value=RangerRole(id=1, name="test_role02", is_enabled=True),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "test_role02",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"] == {}
    assert result["diff"]["after"]["name"] == "test_role02"


def test_ranger_role_module_present_no_changes(module_args, mocker):
    """Test RangerRoleModule present with no drift is a no-op."""
    mock_get_by_name = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=EXISTING_ROLE,
    )
    mock_update = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.update_role",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_ROLE.name,
            "description": EXISTING_ROLE.description,
            "users": [{"name": "admin", "is_admin": True}],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is False
    assert result["role"]["id"] == EXISTING_ROLE.id
    assert result["role"]["name"] == EXISTING_ROLE.name

    mock_get_by_name.assert_called_once_with(EXISTING_ROLE.name)
    mock_update.assert_not_called()


def test_ranger_role_module_update_in_place(module_args, mocker):
    """Test RangerRoleModule updates an existing role in place (no delete/recreate)."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=EXISTING_ROLE,
    )
    mock_delete = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.delete_role_by_id",
    )
    mock_update = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.update_role",
        return_value=RangerRole(
            id=EXISTING_ROLE.id,
            name=EXISTING_ROLE.name,
            description="Updated description",
            is_enabled=True,
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_ROLE.name,
            "description": "Updated description",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["description"] == "Updated description"

    mock_update.assert_called_once()
    updated_role = mock_update.call_args[0][0]
    assert updated_role.id == EXISTING_ROLE.id
    assert updated_role.description == "Updated description"

    # The module replaces the role in place; it must never delete it.
    mock_delete.assert_not_called()


def test_ranger_role_module_update_check_mode(module_args, mocker):
    """Test RangerRoleModule update in check mode does not call the API."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=EXISTING_ROLE,
    )
    mock_update = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.update_role",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_ROLE.name,
            "description": "Updated in check mode",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["description"] == "Updated in check mode"

    mock_update.assert_not_called()


def test_ranger_role_module_update_diff_mode(module_args, mocker):
    """Test RangerRoleModule update in diff mode reports before/after."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=EXISTING_ROLE,
    )
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.update_role",
        return_value=RangerRole(
            id=EXISTING_ROLE.id,
            name=EXISTING_ROLE.name,
            description="Updated description",
            is_enabled=True,
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_ROLE.name,
            "description": "Updated description",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"]["description"] == EXISTING_ROLE.description
    assert result["diff"]["after"]["description"] == "Updated description"


def test_ranger_role_module_delete_existing(module_args, mocker):
    """Test RangerRoleModule deletes an existing role."""
    mock_get_by_name = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=EXISTING_ROLE,
    )
    mock_delete = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.delete_role_by_id",
        return_value=None,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_ROLE.name,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"] == {}

    mock_get_by_name.assert_called_once_with(EXISTING_ROLE.name)
    mock_delete.assert_called_once_with(EXISTING_ROLE.id)


def test_ranger_role_module_delete_nonexistent(module_args, mocker):
    """Test RangerRoleModule delete of a nonexistent role is a no-op."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=None,
    )
    mock_delete = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.delete_role_by_id",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "nonexistent_role",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is False
    assert result["role"] == {}

    mock_delete.assert_not_called()


def test_ranger_role_module_delete_check_mode(module_args, mocker):
    """Test RangerRoleModule delete in check mode does not call the API."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=EXISTING_ROLE,
    )
    mock_delete = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.delete_role_by_id",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_ROLE.name,
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True

    mock_delete.assert_not_called()


def test_ranger_role_module_delete_diff_mode(module_args, mocker):
    """Test RangerRoleModule delete in diff mode reports before/after."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=EXISTING_ROLE,
    )
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.delete_role_by_id",
        return_value=None,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_ROLE.name,
            "state": "absent",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["diff"]["before"]["name"] == EXISTING_ROLE.name
    assert result["diff"]["after"] == {}


def test_ranger_role_module_create_non_exist_user_group(module_args, mocker):
    """Test the create_non_exist_user_group option is forwarded to the client."""
    mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.get_role_by_name",
        return_value=None,
    )
    mock_create = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role.RangerRoleClient.create_role",
        return_value=RangerRole(id=1, name="test_role02", is_enabled=True),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "test_role02",
            "create_non_exist_user_group": True,
        },
    )

    with pytest.raises(AnsibleExitJson):
        ranger_role.main()

    assert mock_create.call_args[1]["create_non_exist_user_group"] is True


def test_ranger_role_module_missing_name_fails(module_args, mocker):
    """Test RangerRoleModule fails fast when name is not provided."""
    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
        },
    )

    with pytest.raises(AnsibleFailJson):
        ranger_role.main()
