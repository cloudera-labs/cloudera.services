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

from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerRole,
)

REQUIRED_ENV_VARS = [
    "RANGER_API_URL",
    "RANGER_API_USERNAME",
    "RANGER_API_PASSWORD",
]


def test_list_roles(ranger_role_client, ranger_existing_role):
    """Test listing all roles."""
    response = ranger_role_client.list_roles()

    assert isinstance(response, list)
    assert len(response) > 0
    assert isinstance(response[0], RangerRole)
    assert any(role.id == ranger_existing_role.id for role in response)


def test_get_role_by_id(ranger_role_client, ranger_existing_role):
    """Test getting a role by id."""
    response = ranger_role_client.get_role_by_id(
        role_id=ranger_existing_role.id,
    )

    assert isinstance(response, RangerRole)
    assert response.id == ranger_existing_role.id
    assert response.name == ranger_existing_role.name


def test_get_role_by_id_not_found(ranger_role_client):
    """Test getting a non-existent role by id returns None."""
    response = ranger_role_client.get_role_by_id(role_id=999999)

    assert response is None


def test_get_role_by_name(ranger_role_client, ranger_existing_role):
    """Test getting a role by name."""
    response = ranger_role_client.get_role_by_name(
        role_name=ranger_existing_role.name,
    )

    assert isinstance(response, RangerRole)
    assert response.name == ranger_existing_role.name
    assert response.id == ranger_existing_role.id


def test_get_role_by_name_not_found(ranger_role_client):
    """Test getting a non-existent role by name returns None."""
    response = ranger_role_client.get_role_by_name(
        role_name="non-existent-role-12345",
    )

    assert response is None
