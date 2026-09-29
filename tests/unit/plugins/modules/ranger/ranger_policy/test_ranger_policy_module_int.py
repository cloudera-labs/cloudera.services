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

from ansible_collections.cloudera.services.plugins.modules import ranger_policy
from ansible_collections.cloudera.services.plugins.module_utils.common import to_dict
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
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


@pytest.fixture
def ranger_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args for Ranger policy tests."""

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


def test_ranger_policy_module_create(
    request,
    ranger_module_args,
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_purge_policy,
):
    """Test RangerPolicyModule creates a new policy."""
    policy_name = f"ansible-test-module-create-{request.node.name.lower()}"

    ranger_module_args(
        {
            "name": policy_name,
            "service": ranger_policy_test_service.name,
            "description": "Created by module integration test",
            "resources": _tag_resource(f"module-create-{request.node.name.lower()}"),
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"]["name"] == policy_name
    assert result["policy"]["service"] == ranger_policy_test_service.name
    assert result["policy"]["id"] is not None

    # Register for cleanup.
    created = ranger_policy_client.get_policy_by_name(
        service_name=ranger_policy_test_service.name,
        policy_name=policy_name,
    )
    ranger_purge_policy(created)

    assert created is not None
    assert created.description == "Created by module integration test"


def test_ranger_policy_module_create_check_mode(
    request,
    ranger_module_args,
    ranger_policy_client,
    ranger_policy_test_service,
):
    """Test RangerPolicyModule create in check mode does not create a policy."""
    policy_name = f"ansible-test-module-checkmode-{request.node.name.lower()}"

    ranger_module_args(
        {
            "name": policy_name,
            "service": ranger_policy_test_service.name,
            "resources": _tag_resource(f"module-checkmode-{request.node.name.lower()}"),
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"]["name"] == policy_name

    # The policy must not actually exist remotely.
    assert (
        ranger_policy_client.get_policy_by_name(
            service_name=ranger_policy_test_service.name,
            policy_name=policy_name,
        )
        is None
    )


def test_ranger_policy_module_present_no_changes(
    ranger_module_args,
    ranger_existing_policy,
    ranger_policy_test_service,
):
    """Test RangerPolicyModule present against an unchanged policy is a no-op."""

    ranger_module_args(
        {
            "name": ranger_existing_policy.name,
            "service": ranger_policy_test_service.name,
            "description": ranger_existing_policy.description,
            "resources": to_dict(ranger_existing_policy)["resources"],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is False
    assert result["policy"]["id"] == ranger_existing_policy.id
    assert result["policy"]["name"] == ranger_existing_policy.name


def test_ranger_policy_module_update_in_place(
    ranger_module_args,
    ranger_policy_client,
    ranger_deletable_policy,
    ranger_policy_test_service,
):
    """Test RangerPolicyModule updates an existing policy in place."""

    ranger_module_args(
        {
            "name": ranger_deletable_policy.name,
            "service": ranger_policy_test_service.name,
            "description": "Updated by module integration test",
            "resources": to_dict(ranger_deletable_policy)["resources"],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"]["id"] == ranger_deletable_policy.id
    assert result["policy"]["description"] == "Updated by module integration test"

    # The policy id must be unchanged (updated in place, not recreated).
    fetched = ranger_policy_client.get_policy_by_id(ranger_deletable_policy.id)
    assert fetched.id == ranger_deletable_policy.id
    assert fetched.description == "Updated by module integration test"


def test_ranger_policy_module_update_check_mode(
    ranger_module_args,
    ranger_policy_client,
    ranger_deletable_policy,
    ranger_policy_test_service,
):
    """Test RangerPolicyModule update in check mode does not modify the policy."""

    ranger_module_args(
        {
            "name": ranger_deletable_policy.name,
            "service": ranger_policy_test_service.name,
            "description": "Should not be persisted",
            "resources": to_dict(ranger_deletable_policy)["resources"],
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True

    fetched = ranger_policy_client.get_policy_by_id(ranger_deletable_policy.id)
    assert fetched.description != "Should not be persisted"


def test_ranger_policy_module_merge_adds_user(
    request,
    ranger_module_args,
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_purge_policy,
):
    """Test RangerPolicyModule merge mode adds a user to a matching item end-to-end."""
    policy_name = f"ansible-test-module-merge-{request.node.name.lower()}"

    # Seed a policy with a single access item.
    created = ranger_policy_client.create_policy(
        RangerPolicy(
            name=policy_name,
            service=ranger_policy_test_service.name,
            resources=_tag_resource(f"module-merge-{request.node.name.lower()}"),
            policy_items=[
                {
                    "accesses": [{"type": "hive:select", "is_allowed": True}],
                    "users": ["admin"],
                },
            ],
        ),
    )
    ranger_purge_policy(created)

    # Merge a second user onto the same access pattern.
    ranger_module_args(
        {
            "name": policy_name,
            "service": ranger_policy_test_service.name,
            "merged": True,
            "access_policies": [
                {
                    "accesses": [{"type": "hive:select", "is_allowed": True}],
                    "users": ["hive"],
                },
            ],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True

    # Both users are present on a single consolidated item.
    fetched = ranger_policy_client.get_policy_by_id(created.id)
    assert len(fetched.policy_items) == 1
    assert set(fetched.policy_items[0].users) == {"admin", "hive"}


def test_ranger_policy_module_merge_noop_when_subset(
    request,
    ranger_module_args,
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_purge_policy,
):
    """Test RangerPolicyModule merge mode is a no-op when the request is a subset."""
    policy_name = f"ansible-test-module-merge-noop-{request.node.name.lower()}"

    created = ranger_policy_client.create_policy(
        RangerPolicy(
            name=policy_name,
            service=ranger_policy_test_service.name,
            resources=_tag_resource(f"module-merge-noop-{request.node.name.lower()}"),
            policy_items=[
                {
                    "accesses": [{"type": "hive:select", "is_allowed": True}],
                    "users": ["admin"],
                },
            ],
        ),
    )
    ranger_purge_policy(created)

    # The requested item is already satisfied by the existing policy.
    ranger_module_args(
        {
            "name": policy_name,
            "service": ranger_policy_test_service.name,
            "merged": True,
            "access_policies": [
                {
                    "accesses": [{"type": "hive:select", "is_allowed": True}],
                    "users": ["admin"],
                },
            ],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is False
    assert result["policy"]["id"] == created.id


def test_ranger_policy_module_delete_existing(
    ranger_module_args,
    ranger_policy_client,
    ranger_deletable_policy,
    ranger_policy_test_service,
):
    """Test RangerPolicyModule deletes an existing policy."""

    ranger_module_args(
        {
            "name": ranger_deletable_policy.name,
            "service": ranger_policy_test_service.name,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"] == {}

    assert ranger_policy_client.get_policy_by_id(ranger_deletable_policy.id) is None


def test_ranger_policy_module_delete_nonexistent(
    request,
    ranger_module_args,
    ranger_policy_test_service,
):
    """Test RangerPolicyModule delete of a nonexistent policy is a no-op."""

    ranger_module_args(
        {
            "name": f"ansible-test-nonexistent-{request.node.name.lower()}",
            "service": ranger_policy_test_service.name,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is False
    assert result["policy"] == {}


def test_ranger_policy_module_delete_check_mode(
    ranger_module_args,
    ranger_policy_client,
    ranger_deletable_policy,
    ranger_policy_test_service,
):
    """Test RangerPolicyModule delete in check mode does not delete the policy."""

    ranger_module_args(
        {
            "name": ranger_deletable_policy.name,
            "service": ranger_policy_test_service.name,
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True

    assert ranger_policy_client.get_policy_by_id(ranger_deletable_policy.id) is not None
