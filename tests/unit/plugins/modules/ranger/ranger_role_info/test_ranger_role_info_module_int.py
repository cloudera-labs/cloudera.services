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

import os

from typing import Callable

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
)

from ansible_collections.cloudera.services.plugins.modules import (
    ranger_role_info,
)

REQUIRED_ENV_VARS = [
    "RANGER_API_URL",
    "RANGER_API_USERNAME",
    "RANGER_API_PASSWORD",
]


@pytest.fixture
def ranger_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args for Ranger role info tests."""

    def _ranger_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["RANGER_API_URL"],
            "url_username": env_context["RANGER_API_USERNAME"],
            "url_password": env_context["RANGER_API_PASSWORD"],
            "force_basic_auth": True,
            "validate_certs": os.environ.get("RANGER_VALIDATE_CERTS", "false").lower()
            == "true",
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _ranger_module_args


def test_ranger_role_info_module_list_all(
    ranger_module_args,
    ranger_existing_role,
):
    """Test RangerRoleInfoModule listing all roles."""

    ranger_module_args({})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert "roles" in result
    assert isinstance(result["roles"], list)
    assert any(role["id"] == ranger_existing_role.id for role in result["roles"])


def test_ranger_role_info_module_by_name(
    ranger_module_args,
    ranger_existing_role,
):
    """Test RangerRoleInfoModule get role by name."""

    ranger_module_args({"name": ranger_existing_role.name})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 1
    assert result["roles"][0]["id"] == ranger_existing_role.id
    assert result["roles"][0]["name"] == ranger_existing_role.name


def test_ranger_role_info_module_by_id(ranger_module_args, ranger_existing_role):
    """Test RangerRoleInfoModule get role by id."""

    ranger_module_args({"id": ranger_existing_role.id})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 1
    assert result["roles"][0]["id"] == ranger_existing_role.id
    assert result["roles"][0]["name"] == ranger_existing_role.name


def test_ranger_role_info_module_nonexistent_name(request, ranger_module_args):
    """Test RangerRoleInfoModule with a nonexistent role name."""

    ranger_module_args(
        {"name": f"nonexistent-role-{request.node.name.lower()}"},
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["roles"] == []


def test_ranger_role_info_module_nonexistent_id(ranger_module_args):
    """Test RangerRoleInfoModule with a nonexistent role id."""

    ranger_module_args({"id": 999999})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["roles"] == []


def test_ranger_role_info_module_check_mode(
    ranger_module_args,
    ranger_existing_role,
):
    """Test RangerRoleInfoModule in check mode."""

    ranger_module_args({"id": ranger_existing_role.id, "_ansible_check_mode": True})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["roles"]) == 1
    assert result["roles"][0]["id"] == ranger_existing_role.id


def test_ranger_role_info_module_with_members(
    ranger_module_args,
    ranger_existing_role,
):
    """Test RangerRoleInfoModule returns role members in snake_case."""

    ranger_module_args({"name": ranger_existing_role.name})

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role_info.main()

    result = e.value
    assert len(result["roles"]) == 1

    users = result["roles"][0]["users"]
    assert [user["name"] for user in users] == [
        member.name for member in ranger_existing_role.users
    ]
    assert all("is_admin" in user for user in users)
