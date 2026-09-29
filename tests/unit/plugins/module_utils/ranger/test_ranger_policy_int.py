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
    RangerPolicy,
    merge_ranger_policies,
)
from ansible_collections.cloudera.services.plugins.module_utils.common import (
    build_from_params,
)

REQUIRED_ENV_VARS = [
    "RANGER_API_URL",
    "RANGER_API_USERNAME",
    "RANGER_API_PASSWORD",
]


def _tag_resource(suffix):
    """Build a unique ``tag`` resource so each policy has a distinct signature."""
    base = os.environ.get("RANGER_TEST_POLICY_TAG", "ansible-test-tag")
    return {"tag": {"values": [f"{base}-{suffix}"]}}


def test_create_policy(
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_purge_policy,
):
    """Test creating a policy."""
    policy_name = f"ansible-test-create-policy-{os.getpid()}"

    response = ranger_policy_client.create_policy(
        RangerPolicy(
            name=policy_name,
            service=ranger_policy_test_service.name,
            resources=_tag_resource(f"create-{os.getpid()}"),
        ),
    )

    ranger_purge_policy(response)

    assert isinstance(response, RangerPolicy)
    assert response.name == policy_name
    assert response.service == ranger_policy_test_service.name
    assert response.id is not None
    assert response.guid is not None


def test_create_policy_with_items(
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_purge_policy,
):
    """Test creating a policy with an access policy item."""
    policy_name = f"ansible-test-create-items-{os.getpid()}"

    response = ranger_policy_client.create_policy(
        RangerPolicy(
            name=policy_name,
            service=ranger_policy_test_service.name,
            description="Created by an integration test",
            resources=_tag_resource(f"items-{os.getpid()}"),
            policy_items=[
                {
                    "accesses": [{"type": "hive:select", "is_allowed": True}],
                    "users": ["admin"],
                },
            ],
        ),
    )

    ranger_purge_policy(response)

    assert isinstance(response, RangerPolicy)
    assert response.description == "Created by an integration test"
    assert response.policy_items
    assert response.policy_items[0].users == ["admin"]


def test_update_policy(ranger_policy_client, ranger_deletable_policy):
    """Test updating an existing policy in place."""
    ranger_deletable_policy.description = "Updated description via integration test"
    response = ranger_policy_client.update_policy(ranger_deletable_policy)

    assert isinstance(response, RangerPolicy)
    assert response.id == ranger_deletable_policy.id
    assert response.description == "Updated description via integration test"

    fetched = ranger_policy_client.get_policy_by_id(response.id)
    assert fetched.description == "Updated description via integration test"


def test_delete_policy_by_id(ranger_policy_client, ranger_deletable_policy):
    """Test deleting a policy by id."""
    policy_id = ranger_deletable_policy.id

    response = ranger_policy_client.delete_policy_by_id(policy_id)
    assert response is None

    assert ranger_policy_client.get_policy_by_id(policy_id) is None


def test_delete_policy_by_id_not_found(ranger_policy_client):
    """Test deleting a non-existent policy by id (idempotent)."""
    response = ranger_policy_client.delete_policy_by_id(policy_id=9999999)
    assert response is None


def test_merge_policy_adds_user(
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_purge_policy,
):
    """Test the merge workflow adds a user to an existing policy item end-to-end."""
    policy_name = f"ansible-test-merge-{os.getpid()}"

    # Create the initial policy with a single user.
    created = ranger_policy_client.create_policy(
        RangerPolicy(
            name=policy_name,
            service=ranger_policy_test_service.name,
            resources=_tag_resource(f"merge-{os.getpid()}"),
            policy_items=[
                {
                    "accesses": [{"type": "hive:select", "is_allowed": True}],
                    "users": ["admin"],
                },
            ],
        ),
    )
    ranger_purge_policy(created)

    # Build a partial policy that adds a second user via merge mode.
    partial = build_from_params(
        RangerPolicy,
        {
            "name": policy_name,
            "service": ranger_policy_test_service.name,
            "policy_items": [
                {
                    "accesses": [{"type": "hive:select", "is_allowed": True}],
                    "users": ["hive"],
                },
            ],
        },
    )

    merged = merge_ranger_policies(created, partial)
    merged.id = created.id
    merged.guid = created.guid
    merged.version = created.version
    merged.resource_signature = created.resource_signature

    updated = ranger_policy_client.update_policy(merged)

    # Both users are present on a single consolidated item.
    assert len(updated.policy_items) == 1
    assert set(updated.policy_items[0].users) == {"admin", "hive"}
