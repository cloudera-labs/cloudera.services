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

from ansible_collections.cloudera.services.plugins.modules import ranger_policy
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
    RangerPolicyItem,
    RangerPolicyItemAccess,
)

BASE_URL = "https://ranger.internal"

GET_BY_NAME = (
    "ansible_collections.cloudera.services.plugins.modules.ranger_policy"
    ".RangerPolicyClient.get_policy_by_name"
)
CREATE = (
    "ansible_collections.cloudera.services.plugins.modules.ranger_policy"
    ".RangerPolicyClient.create_policy"
)
UPDATE = (
    "ansible_collections.cloudera.services.plugins.modules.ranger_policy"
    ".RangerPolicyClient.update_policy"
)
DELETE = (
    "ansible_collections.cloudera.services.plugins.modules.ranger_policy"
    ".RangerPolicyClient.delete_policy_by_id"
)

EXISTING_POLICY = RangerPolicy(
    id=67,
    guid="policy-guid-67",
    version=2,
    resource_signature="sig-67",
    name="test_policy",
    service="cm_hdfs",
    description="An existing policy",
    is_enabled=True,
    resources={"path": {"values": ["/tmp/test"]}},
    policy_items=[
        RangerPolicyItem(
            accesses=[RangerPolicyItemAccess(type="select", is_allowed=True)],
            users=["alice"],
            groups=["public"],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_ranger_policy_module_create_minimal(module_args, mocker):
    """Test RangerPolicyModule creating a new policy with name and service."""
    mock_get = mocker.patch(GET_BY_NAME, return_value=None)
    mock_create = mocker.patch(
        CREATE,
        return_value=RangerPolicy(id=1, guid="g1", name="p1", service="cm_hdfs"),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "p1",
            "service": "cm_hdfs",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"]["id"] == 1
    assert result["policy"]["name"] == "p1"
    assert "diff" not in result

    mock_get.assert_called_once_with(service_name="cm_hdfs", policy_name="p1")
    mock_create.assert_called_once()


def test_ranger_policy_module_create_full(module_args, mocker):
    """Test RangerPolicyModule creating a policy with items and resources."""
    mocker.patch(GET_BY_NAME, return_value=None)
    mock_create = mocker.patch(
        CREATE,
        return_value=RangerPolicy(id=2, guid="g2", name="p2", service="cm_hdfs"),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "p2",
            "service": "cm_hdfs",
            "description": "Created by unit test",
            "deny_all_else": True,
            "resources": {"path": {"values": ["/data"]}},
            "access_policies": [
                {
                    "accesses": [{"type": "read", "is_allowed": True}],
                    "users": ["admin"],
                },
            ],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True

    incoming = mock_create.call_args[0][0]
    assert incoming.name == "p2"
    assert incoming.service == "cm_hdfs"
    assert incoming.description == "Created by unit test"
    # The deny_all_else alias maps onto is_deny_all_else (regression guard).
    assert incoming.is_deny_all_else is True
    # The access_policies alias maps onto policy_items.
    assert incoming.policy_items[0].users == ["admin"]


def test_ranger_policy_module_create_check_mode(module_args, mocker):
    """Test RangerPolicyModule create in check mode does not call the API."""
    mocker.patch(GET_BY_NAME, return_value=None)
    mock_create = mocker.patch(CREATE)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "p1",
            "service": "cm_hdfs",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"]["name"] == "p1"

    mock_create.assert_not_called()


def test_ranger_policy_module_create_diff_mode(module_args, mocker):
    """Test RangerPolicyModule create in diff mode reports before/after."""
    mocker.patch(GET_BY_NAME, return_value=None)
    mocker.patch(
        CREATE,
        return_value=RangerPolicy(id=1, name="p1", service="cm_hdfs"),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "p1",
            "service": "cm_hdfs",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["diff"]["before"] == {}
    assert result["diff"]["after"]["name"] == "p1"
    assert result["diff"]["after"]["service"] == "cm_hdfs"


# ---------------------------------------------------------------------------
# Present - full replacement (merged=false, the default)
# ---------------------------------------------------------------------------


def test_ranger_policy_module_present_no_changes(module_args, mocker):
    """Test RangerPolicyModule present with no drift is a no-op."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_update = mocker.patch(UPDATE)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is False
    assert result["policy"]["id"] == EXISTING_POLICY.id

    mock_update.assert_not_called()


def test_ranger_policy_module_update_in_place(module_args, mocker):
    """Test RangerPolicyModule replaces an existing policy in place."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_delete = mocker.patch(DELETE)
    mock_update = mocker.patch(
        UPDATE,
        return_value=RangerPolicy(
            id=EXISTING_POLICY.id,
            name=EXISTING_POLICY.name,
            service=EXISTING_POLICY.service,
            description="Updated description",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "description": "Updated description",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"]["description"] == "Updated description"

    mock_update.assert_called_once()
    updated = mock_update.call_args[0][0]
    assert updated.id == EXISTING_POLICY.id
    assert updated.description == "Updated description"

    # The module replaces the policy in place; it must never delete it.
    mock_delete.assert_not_called()


def test_ranger_policy_module_update_diff_mode(module_args, mocker):
    """Test RangerPolicyModule update in diff mode reports before/after."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mocker.patch(
        UPDATE,
        return_value=RangerPolicy(
            id=EXISTING_POLICY.id,
            name=EXISTING_POLICY.name,
            service=EXISTING_POLICY.service,
            description="Updated description",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "description": "Updated description",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["diff"]["before"]["description"] == EXISTING_POLICY.description
    assert result["diff"]["after"]["description"] == "Updated description"


def test_ranger_policy_module_update_check_mode(module_args, mocker):
    """Test RangerPolicyModule update in check mode does not call the API."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_update = mocker.patch(UPDATE)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "description": "Updated in check mode",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"]["description"] == "Updated in check mode"

    mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# Present - merge mode (merged=true)
# ---------------------------------------------------------------------------


def test_ranger_policy_module_merge_adds_user(module_args, mocker):
    """Test merge mode concatenates a new user onto a matching policy item."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_update = mocker.patch(
        UPDATE,
        return_value=RangerPolicy(id=EXISTING_POLICY.id, name="p", service="s"),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "merged": True,
            "access_policies": [
                {
                    "accesses": [{"type": "select", "is_allowed": True}],
                    "users": ["bob"],
                },
            ],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True

    mock_update.assert_called_once()
    merged = mock_update.call_args[0][0]

    # The item with the matching access pattern gains the new user.
    assert len(merged.policy_items) == 1
    assert merged.policy_items[0].users == ["alice", "bob"]
    # Fields not supplied by the incoming item are preserved.
    assert merged.policy_items[0].groups == ["public"]

    # Read-only fields are preserved from the existing policy.
    assert merged.id == EXISTING_POLICY.id
    assert merged.guid == EXISTING_POLICY.guid
    assert merged.version == EXISTING_POLICY.version
    assert merged.resource_signature == EXISTING_POLICY.resource_signature


def test_ranger_policy_module_merge_noop_when_subset(module_args, mocker):
    """Test merge mode is a no-op when the request is already a subset."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_update = mocker.patch(UPDATE)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "merged": True,
            "access_policies": [
                {
                    "accesses": [{"type": "select", "is_allowed": True}],
                    "users": ["alice"],
                },
            ],
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is False
    assert result["policy"]["id"] == EXISTING_POLICY.id

    mock_update.assert_not_called()


def test_ranger_policy_module_merge_check_mode(module_args, mocker):
    """Test merge mode in check mode reports the merged policy but calls no API."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_update = mocker.patch(UPDATE)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "merged": True,
            "access_policies": [
                {
                    "accesses": [{"type": "select", "is_allowed": True}],
                    "users": ["bob"],
                },
            ],
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    # The returned (unpersisted) policy reflects the merge.
    assert result["policy"]["policy_items"][0]["users"] == ["alice", "bob"]

    mock_update.assert_not_called()


def test_ranger_policy_module_merge_diff_mode(module_args, mocker):
    """Test merge mode in diff mode reports the before/after users."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mocker.patch(
        UPDATE,
        return_value=RangerPolicy(id=EXISTING_POLICY.id, name="p", service="s"),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "merged": True,
            "access_policies": [
                {
                    "accesses": [{"type": "select", "is_allowed": True}],
                    "users": ["bob"],
                },
            ],
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert "before" in result["diff"]
    assert "after" in result["diff"]


# ---------------------------------------------------------------------------
# Absent
# ---------------------------------------------------------------------------


def test_ranger_policy_module_delete_existing(module_args, mocker):
    """Test RangerPolicyModule deletes an existing policy."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_delete = mocker.patch(DELETE, return_value=None)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["policy"] == {}

    mock_delete.assert_called_once_with(EXISTING_POLICY.id)


def test_ranger_policy_module_delete_nonexistent(module_args, mocker):
    """Test RangerPolicyModule delete of a nonexistent policy is a no-op."""
    mocker.patch(GET_BY_NAME, return_value=None)
    mock_delete = mocker.patch(DELETE)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "nonexistent_policy",
            "service": "cm_hdfs",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is False
    assert result["policy"] == {}

    mock_delete.assert_not_called()


def test_ranger_policy_module_delete_check_mode(module_args, mocker):
    """Test RangerPolicyModule delete in check mode does not call the API."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mock_delete = mocker.patch(DELETE)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True

    mock_delete.assert_not_called()


def test_ranger_policy_module_delete_diff_mode(module_args, mocker):
    """Test RangerPolicyModule delete in diff mode reports before/after."""
    mocker.patch(GET_BY_NAME, return_value=EXISTING_POLICY)
    mocker.patch(DELETE, return_value=None)

    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": EXISTING_POLICY.name,
            "service": EXISTING_POLICY.service,
            "state": "absent",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ranger_policy.main()

    result = e.value
    assert result["changed"] is True
    assert result["diff"]["before"]["name"] == EXISTING_POLICY.name
    assert result["diff"]["after"] == {}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_ranger_policy_module_present_requires_name_and_service(module_args, mocker):
    """Test RangerPolicyModule fails when present is missing required params."""
    module_args(
        {
            "endpoint": BASE_URL,
            "url_username": "admin",
            "url_password": "changeme",
            "name": "p1",
        },
    )

    with pytest.raises(AnsibleFailJson):
        ranger_policy.main()
