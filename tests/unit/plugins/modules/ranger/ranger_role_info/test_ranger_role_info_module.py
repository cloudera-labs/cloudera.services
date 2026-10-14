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
)

from ansible_collections.cloudera.services.plugins.modules import (
    ranger_role_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
    RangerRoleMember,
)

BASE_URL = "https://ranger.example"

ROLE_ONE = RangerRole(
    id=1,
    guid="role-guid-1",
    name="data_admin",
    description="Data administrator role",
    is_enabled=True,
    users=[RangerRoleMember(name="admin", is_admin=True)],
)

ROLE_TWO = RangerRole(
    id=2,
    guid="role-guid-2",
    name="data_engineers",
    description="Data engineer role",
    is_enabled=True,
    groups=[RangerRoleMember(name="data_engineers", is_admin=False)],
)


def test_ranger_role_info_module_list_all(module_args, mocker):
    """Test RangerRoleInfoModule listing all roles."""
    mock_list_roles = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.list_roles",
        return_value=[ROLE_ONE, ROLE_TWO],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 2
    assert result["roles"][0]["id"] == 1
    assert result["roles"][0]["name"] == "data_admin"
    assert result["roles"][1]["id"] == 2
    assert result["roles"][1]["name"] == "data_engineers"

    mock_list_roles.assert_called_once_with()


def test_ranger_role_info_module_by_id(module_args, mocker):
    """Test RangerRoleInfoModule retrieval by id."""
    mock_get_by_id = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.get_role_by_id",
        return_value=ROLE_ONE,
    )
    mock_list_roles = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.list_roles",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "id": 1,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 1
    assert result["roles"][0]["id"] == 1
    assert result["roles"][0]["name"] == "data_admin"

    mock_get_by_id.assert_called_once_with(role_id=1)
    mock_list_roles.assert_not_called()


def test_ranger_role_info_module_by_id_not_found(module_args, mocker):
    """Test RangerRoleInfoModule retrieval by id when the role doesn't exist."""
    mock_get_by_id = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.get_role_by_id",
        return_value=None,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "id": 999,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 0

    mock_get_by_id.assert_called_once_with(role_id=999)


def test_ranger_role_info_module_by_name(module_args, mocker):
    """Test RangerRoleInfoModule retrieval by name."""
    mock_get_by_name = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.get_role_by_name",
        return_value=ROLE_TWO,
    )
    mock_list_roles = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.list_roles",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "data_engineers",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 1
    assert result["roles"][0]["id"] == 2
    assert result["roles"][0]["name"] == "data_engineers"

    mock_get_by_name.assert_called_once_with(role_name="data_engineers")
    mock_list_roles.assert_not_called()


def test_ranger_role_info_module_by_name_not_found(module_args, mocker):
    """Test RangerRoleInfoModule retrieval by name when the role doesn't exist."""
    mock_get_by_name = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.get_role_by_name",
        return_value=None,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "nonexistent_role",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 0

    mock_get_by_name.assert_called_once_with(role_name="nonexistent_role")


def test_ranger_role_info_module_empty_list(module_args, mocker):
    """Test RangerRoleInfoModule with no roles present."""
    mock_list_roles = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.list_roles",
        return_value=[],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["roles"] == []

    mock_list_roles.assert_called_once_with()


def test_ranger_role_info_module_check_mode(module_args, mocker):
    """Test RangerRoleInfoModule in check mode still returns data (read-only)."""
    mock_list_roles = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ranger_role_info.RangerRoleClient.list_roles",
        return_value=[ROLE_ONE],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 1

    mock_list_roles.assert_called_once_with()
