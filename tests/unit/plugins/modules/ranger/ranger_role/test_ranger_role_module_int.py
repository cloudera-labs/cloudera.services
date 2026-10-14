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

from ansible_collections.cloudera.services.plugins.modules import ranger_role

REQUIRED_ENV_VARS = [
    "RANGER_API_URL",
    "RANGER_API_USERNAME",
    "RANGER_API_PASSWORD",
]


@pytest.fixture
def ranger_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args for Ranger role tests."""

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


def test_ranger_role_module_create(
    request,
    ranger_module_args,
    ranger_role_client,
    ranger_purge_role,
):
    """Test RangerRoleModule creates a new role."""
    role_name = f"ansible-test-module-create-{request.node.name.lower()}"

    ranger_module_args(
        {
            "name": role_name,
            "description": "Created by module integration test",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["name"] == role_name
    assert result["role"]["id"] is not None

    # Register for cleanup
    created = ranger_role_client.get_role_by_name(role_name)
    ranger_purge_role(created)

    assert created is not None
    assert created.description == "Created by module integration test"


def test_ranger_role_module_create_with_members(
    request,
    ranger_module_args,
    ranger_role_client,
    ranger_purge_role,
):
    """Test RangerRoleModule creates a role with a user member end-to-end."""
    role_name = f"ansible-test-module-members-{request.node.name.lower()}"
    username = os.environ["RANGER_API_USERNAME"]

    ranger_module_args(
        {
            "name": role_name,
            "users": [{"name": username, "is_admin": True}],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["users"][0]["name"] == username
    assert result["role"]["users"][0]["is_admin"] is True

    # Register for cleanup
    created = ranger_role_client.get_role_by_name(role_name)
    ranger_purge_role(created)

    # The member survives the camelCase round trip through Ranger.
    assert created is not None
    assert [(m.name, m.is_admin) for m in created.users] == [(username, True)]


def test_ranger_role_module_create_check_mode(
    request,
    ranger_module_args,
    ranger_role_client,
):
    """Test RangerRoleModule create in check mode does not create a role."""
    role_name = f"ansible-test-module-checkmode-{request.node.name.lower()}"

    ranger_module_args(
        {
            "name": role_name,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["name"] == role_name

    # The role must not actually exist remotely
    assert ranger_role_client.get_role_by_name(role_name) is None


def test_ranger_role_module_present_no_changes(
    ranger_module_args,
    ranger_existing_role,
):
    """Test RangerRoleModule present against an unchanged role is a no-op."""

    ranger_module_args(
        {
            "name": ranger_existing_role.name,
            "description": ranger_existing_role.description,
            "users": [
                {"name": member.name, "is_admin": member.is_admin}
                for member in ranger_existing_role.users
            ],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is False
    assert result["role"]["id"] == ranger_existing_role.id
    assert result["role"]["name"] == ranger_existing_role.name


def test_ranger_role_module_update_in_place(
    ranger_module_args,
    ranger_role_client,
    ranger_deletable_role,
):
    """Test RangerRoleModule updates an existing role in place."""

    ranger_module_args(
        {
            "name": ranger_deletable_role.name,
            "description": "Updated by module integration test",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"]["id"] == ranger_deletable_role.id
    assert result["role"]["description"] == "Updated by module integration test"

    # The role id must be unchanged (updated in place, not recreated)
    fetched = ranger_role_client.get_role_by_id(ranger_deletable_role.id)
    assert fetched.id == ranger_deletable_role.id
    assert fetched.description == "Updated by module integration test"

    # Members that were not specified are preserved by the update.
    assert [m.name for m in fetched.users] == [
        m.name for m in ranger_deletable_role.users
    ]


def test_ranger_role_module_update_idempotent(
    ranger_module_args,
    ranger_deletable_role,
):
    """Test RangerRoleModule reports no change when re-applying an update."""

    args = {
        "name": ranger_deletable_role.name,
        "description": "Applied twice by module integration test",
    }

    ranger_module_args(args)
    with pytest.raises(AnsibleExitJson) as first:
        ranger_role.main()
    assert first.value["changed"] is True

    ranger_module_args(args)
    with pytest.raises(AnsibleExitJson) as second:
        ranger_role.main()
    assert second.value["changed"] is False


def test_ranger_role_module_update_check_mode(
    ranger_module_args,
    ranger_role_client,
    ranger_deletable_role,
):
    """Test RangerRoleModule update in check mode does not modify the role."""

    ranger_module_args(
        {
            "name": ranger_deletable_role.name,
            "description": "Should not be persisted",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True

    fetched = ranger_role_client.get_role_by_id(ranger_deletable_role.id)
    assert fetched.description != "Should not be persisted"


def test_ranger_role_module_delete_existing(
    ranger_module_args,
    ranger_role_client,
    ranger_deletable_role,
):
    """Test RangerRoleModule deletes an existing role."""

    ranger_module_args(
        {
            "name": ranger_deletable_role.name,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True
    assert result["role"] == {}

    assert ranger_role_client.get_role_by_id(ranger_deletable_role.id) is None


def test_ranger_role_module_delete_nonexistent(request, ranger_module_args):
    """Test RangerRoleModule delete of a nonexistent role is a no-op."""

    ranger_module_args(
        {
            "name": f"ansible-test-nonexistent-{request.node.name.lower()}",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is False
    assert result["role"] == {}


def test_ranger_role_module_delete_check_mode(
    ranger_module_args,
    ranger_role_client,
    ranger_deletable_role,
):
    """Test RangerRoleModule delete in check mode does not delete the role."""

    ranger_module_args(
        {
            "name": ranger_deletable_role.name,
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_role.main()

    result = e.value
    assert result["changed"] is True

    assert ranger_role_client.get_role_by_id(ranger_deletable_role.id) is not None
