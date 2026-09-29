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
    RangerPolicy,
)

REQUIRED_ENV_VARS = [
    "RANGER_API_URL",
    "RANGER_API_USERNAME",
    "RANGER_API_PASSWORD",
]


def test_list_policies(ranger_policy_client, ranger_existing_policy):
    """Test listing all policies."""
    response = ranger_policy_client.list_policies()

    assert isinstance(response, list)
    assert len(response) > 0
    assert all(isinstance(p, RangerPolicy) for p in response)
    assert any(policy.id == ranger_existing_policy.id for policy in response)


def test_list_policies_by_service(
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_existing_policy,
):
    """Test listing policies filtered by service name."""
    response = ranger_policy_client.list_policies(
        service_name=ranger_policy_test_service.name,
    )

    assert isinstance(response, list)
    assert any(policy.id == ranger_existing_policy.id for policy in response)
    assert all(policy.service == ranger_policy_test_service.name for policy in response)


def test_get_policy_by_id(ranger_policy_client, ranger_existing_policy):
    """Test getting a policy by id."""
    response = ranger_policy_client.get_policy_by_id(
        policy_id=ranger_existing_policy.id,
    )

    assert isinstance(response, RangerPolicy)
    assert response.id == ranger_existing_policy.id
    assert response.name == ranger_existing_policy.name


def test_get_policy_by_id_not_found(ranger_policy_client):
    """Test getting a non-existent policy by id returns None."""
    assert ranger_policy_client.get_policy_by_id(policy_id=9999999) is None


def test_get_policy_by_name(
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_existing_policy,
):
    """Test getting a policy by service and name."""
    response = ranger_policy_client.get_policy_by_name(
        service_name=ranger_policy_test_service.name,
        policy_name=ranger_existing_policy.name,
    )

    assert isinstance(response, RangerPolicy)
    assert response.id == ranger_existing_policy.id
    assert response.name == ranger_existing_policy.name


def test_get_policy_by_name_not_found(ranger_policy_client, ranger_policy_test_service):
    """Test getting a non-existent policy by name returns None."""
    response = ranger_policy_client.get_policy_by_name(
        service_name=ranger_policy_test_service.name,
        policy_name="non-existent-policy-12345",
    )

    assert response is None
