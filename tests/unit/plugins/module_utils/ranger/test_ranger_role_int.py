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

from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
    RangerRoleMember,
)

REQUIRED_ENV_VARS = [
    "RANGER_API_URL",
    "RANGER_API_USERNAME",
    "RANGER_API_PASSWORD",
]


def test_create_role(
    request,
    ranger_role_client,
    ranger_purge_role,
):
    """Test creating a role."""
    role_name = f"ansible-test-create-{request.node.name.lower()}"

    response = ranger_role_client.create_role(RangerRole(name=role_name))

    # Register the role for cleanup
    ranger_purge_role(response)

    assert isinstance(response, RangerRole)
    assert response.name == role_name
    assert response.id is not None
    assert response.guid is not None


def test_create_role_with_description_and_members(
    request,
    ranger_role_client,
    ranger_purge_role,
):
    """Test creating a role with a description and a user member."""
    role_name = f"ansible-test-members-{request.node.name.lower()}"
    username = os.environ["RANGER_API_USERNAME"]

    response = ranger_role_client.create_role(
        RangerRole(
            name=role_name,
            description="Created by an integration test",
            users=[RangerRoleMember(name=username, is_admin=True)],
        ),
    )

    # Register the role for cleanup
    ranger_purge_role(response)

    assert isinstance(response, RangerRole)
    assert response.name == role_name
    assert response.description == "Created by an integration test"
    assert [(m.name, m.is_admin) for m in response.users] == [(username, True)]


def test_update_role(ranger_role_client, ranger_deletable_role):
    """Test updating an existing role."""

    # Update the role description
    ranger_deletable_role.description = "Updated description via integration test"
    response = ranger_role_client.update_role(ranger_deletable_role)

    assert isinstance(response, RangerRole)
    assert response.id == ranger_deletable_role.id
    assert response.description == "Updated description via integration test"

    # Verify by fetching the role again
    fetched = ranger_role_client.get_role_by_id(response.id)
    assert fetched.description == "Updated description via integration test"


def test_delete_role_by_id(ranger_role_client, ranger_deletable_role):
    """Test deleting a role by id."""
    role_id = ranger_deletable_role.id

    # Delete the role
    response = ranger_role_client.delete_role_by_id(role_id)
    assert response is None

    # Verify the role no longer exists
    fetched = ranger_role_client.get_role_by_id(role_id)
    assert fetched is None


def test_delete_role_by_id_not_found(ranger_role_client):
    """Test deleting a non-existent role by id (idempotent)."""

    # This should not raise an error
    response = ranger_role_client.delete_role_by_id(role_id=999999)
    assert response is None
