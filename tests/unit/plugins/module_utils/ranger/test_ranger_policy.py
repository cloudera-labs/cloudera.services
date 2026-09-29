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

from types import SimpleNamespace

import pytest

from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
)

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesClient,
    ServicesError,
    build_from_params,
    diff_dict,
    from_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
    RangerPolicyClient,
    RangerPolicyItem,
    RangerPolicyItemAccess,
    _consolidate_policy_items,
    extract_policy_params,
    merge_ranger_policies,
)

ENDPOINT_URL = "https://ranger.internal"

# Ranger returns policy objects with camelCase keys.
POLICY_RESPONSE = {
    "id": 67,
    "guid": "policy-guid-67",
    "isEnabled": True,
    "createdBy": "Admin",
    "updatedBy": "Admin",
    "createTime": 1700000000000,
    "updateTime": 1700000000000,
    "version": 1,
    "service": "cm_hdfs",
    "name": "test_policy",
    "policyType": 0,
    "policyPriority": 0,
    "description": "Test policy",
    "isAuditEnabled": True,
    "resources": {
        "path": {"values": ["/tmp/test"], "isExcludes": False, "isRecursive": True},
    },
    "policyItems": [
        {
            "accesses": [{"type": "read", "isAllowed": True}],
            "users": ["admin"],
            "groups": ["public"],
            "roles": [],
            "conditions": [],
            "delegateAdmin": False,
        },
    ],
    "denyPolicyItems": [],
    "allowExceptions": [],
    "denyExceptions": [],
    "dataMaskPolicyItems": [],
    "rowFilterPolicyItems": [],
    "serviceType": "hdfs",
    "options": {},
    "validitySchedules": [],
    "policyLabels": [],
    "zoneName": "",
    "isDenyAllElse": False,
}

# A Ranger 400 response with a DATA_NOT_FOUND body (Ranger's "not found" signal).
RANGER_NOT_FOUND_400 = {
    "status": 400,
    "body": {
        "statusCode": 1,
        "messageList": [{"name": "DATA_NOT_FOUND"}],
    },
}

# A Ranger 400 response for some other (non "not found") error.
RANGER_ERROR_400 = {
    "status": 400,
    "body": {
        "statusCode": 2,
        "messageList": [{"name": "VALIDATION_ERROR"}],
    },
}


def _policy_from_response(raw):
    """Mirror the client's deserialisation of a Ranger policy response."""
    return from_dict(RangerPolicy, camel_dict_to_snake_dict(raw, reversible=True))


# ---------------------------------------------------------------------------
# RangerPolicyClient - create / update / delete
# ---------------------------------------------------------------------------


def test_create_policy(mocker):
    """Test creating a policy serialises to a camelCase payload."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = POLICY_RESPONSE

    client = RangerPolicyClient(api_client=api_client)

    response = client.create_policy(
        RangerPolicy(
            name="test_policy",
            service="cm_hdfs",
            policy_type=0,
            is_audit_enabled=True,
            resources={"path": {"values": ["/tmp/test"]}},
            policy_items=[
                {
                    "accesses": [{"type": "read", "is_allowed": True}],
                    "users": ["admin"],
                },
            ],
        ),
    )

    assert response == _policy_from_response(POLICY_RESPONSE)

    # Payload keys must be camelCase.
    api_client.post.assert_called_once()
    call = api_client.post.call_args
    assert call[0][0] == "/service/plugins/policies"
    payload = call[1]["data"]
    assert payload["name"] == "test_policy"
    assert payload["service"] == "cm_hdfs"
    assert payload["policyType"] == 0
    assert payload["isAuditEnabled"] is True
    assert payload["resources"] == {"path": {"values": ["/tmp/test"]}}
    assert payload["policyItems"][0]["users"] == ["admin"]
    # Snake_case forms must not survive the transformation.
    assert "policy_type" not in payload
    assert "is_audit_enabled" not in payload
    assert "policy_items" not in payload


def test_create_policy_minimal(mocker):
    """Test creating a policy with only name/service omits all NULLABLE fields."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = POLICY_RESPONSE

    client = RangerPolicyClient(api_client=api_client)

    response = client.create_policy(RangerPolicy(name="test_policy", service="cm_hdfs"))

    assert isinstance(response, RangerPolicy)
    api_client.post.assert_called_once_with(
        "/service/plugins/policies",
        data={"name": "test_policy", "service": "cm_hdfs"},
    )


def test_create_policy_deny_all_else(mocker):
    """Test the is_deny_all_else field serialises to isDenyAllElse."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = POLICY_RESPONSE

    client = RangerPolicyClient(api_client=api_client)

    client.create_policy(
        RangerPolicy(name="test_policy", service="cm_hdfs", is_deny_all_else=True),
    )

    payload = api_client.post.call_args[1]["data"]
    assert payload["isDenyAllElse"] is True


def test_update_policy(mocker):
    """Test updating a policy by its id calls PUT."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = POLICY_RESPONSE

    client = RangerPolicyClient(api_client=api_client)

    response = client.update_policy(
        RangerPolicy(id=67, name="test_policy", service="cm_hdfs", description="New"),
    )

    assert response == _policy_from_response(POLICY_RESPONSE)
    call = api_client.put.call_args
    assert call[0][0] == "/service/plugins/policies/67"
    payload = call[1]["data"]
    assert payload["id"] == 67
    assert payload["description"] == "New"


def test_update_policy_without_id(mocker):
    """Test updating a policy without an id raises ValueError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = RangerPolicyClient(api_client=api_client)

    with pytest.raises(ValueError, match="Cannot update a policy without an id"):
        client.update_policy(RangerPolicy(name="test_policy", service="cm_hdfs"))

    api_client.put.assert_not_called()


def test_delete_policy_by_id(mocker):
    """Test deleting a policy by id."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = None

    client = RangerPolicyClient(api_client=api_client)

    response = client.delete_policy_by_id(policy_id=67)

    assert response is None
    api_client.delete.assert_called_once_with(
        "/service/plugins/policies/67",
        squelch={404: None},
        passthru=[400],
    )


def test_delete_policy_by_id_not_found(mocker):
    """Test deleting a non-existent policy (Ranger 400 DATA_NOT_FOUND) is a no-op."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = RANGER_NOT_FOUND_400

    client = RangerPolicyClient(api_client=api_client)

    response = client.delete_policy_by_id(policy_id=999)

    assert response is None


def test_delete_policy_by_id_error(mocker):
    """Test that a non "not found" Ranger 400 raises a ServicesError on delete."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = RANGER_ERROR_400

    client = RangerPolicyClient(api_client=api_client)

    with pytest.raises(ServicesError):
        client.delete_policy_by_id(policy_id=67)


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------


def test_policy_from_response_snakecase():
    """Test deserialisation maps camelCase to snake_case dataclass fields."""
    policy = _policy_from_response(POLICY_RESPONSE)

    assert isinstance(policy, RangerPolicy)
    assert policy.id == 67
    assert policy.guid == "policy-guid-67"
    assert policy.name == "test_policy"
    assert policy.service == "cm_hdfs"
    assert policy.is_audit_enabled is True
    assert policy.is_deny_all_else is False
    assert policy.service_type == "hdfs"
    # Nested policy items are parsed into dataclasses.
    assert isinstance(policy.policy_items[0], RangerPolicyItem)
    assert policy.policy_items[0].users == ["admin"]
    assert isinstance(policy.policy_items[0].accesses[0], RangerPolicyItemAccess)
    assert policy.policy_items[0].accesses[0].type == "read"
    assert policy.policy_items[0].accesses[0].is_allowed is True


# ---------------------------------------------------------------------------
# extract_policy_params / build_from_params
# ---------------------------------------------------------------------------


def test_extract_policy_params():
    """Test extracting policy params from a module-like instance."""
    module = SimpleNamespace(
        name="p",
        service="s",
        description="d",
        policy_items=[{"users": ["alice"]}],
    )

    params = extract_policy_params(module)

    assert params["name"] == "p"
    assert params["service"] == "s"
    assert params["description"] == "d"
    assert params["policy_items"] == [{"users": ["alice"]}]
    # Unset attributes default to None.
    assert params["zone_name"] is None
    assert params["resources"] is None


def test_build_from_params_create():
    """Test building a policy for creation keeps unset fields NULLABLE."""
    policy = build_from_params(
        RangerPolicy,
        {"name": "p", "service": "s", "description": "d"},
    )

    assert policy.name == "p"
    assert policy.service == "s"
    assert policy.description == "d"
    # Unset fields stay NULLABLE so they are omitted from the payload.
    assert policy.zone_name is NULLABLE
    assert policy.is_enabled is NULLABLE
    assert "description" in to_dict(policy)
    assert "zone_name" not in to_dict(policy)


def test_build_from_params_replace_falls_back_to_existing():
    """Test building a replacement policy falls back to the existing values."""
    existing = RangerPolicy(
        id=10,
        guid="guid-10",
        version=3,
        resource_signature="sig",
        name="p",
        service="s",
        description="old",
        is_enabled=True,
    )

    policy = build_from_params(
        RangerPolicy,
        {"name": "p", "service": "s", "description": "new"},
        existing=existing,
    )

    # Provided value wins.
    assert policy.description == "new"
    # Unset field falls back to existing.
    assert policy.is_enabled is True
    # Read-only fields are preserved from existing.
    assert policy.id == 10
    assert policy.guid == "guid-10"
    assert policy.version == 3
    assert policy.resource_signature == "sig"


# ---------------------------------------------------------------------------
# merge_ranger_policies (the critical merge behaviour)
# ---------------------------------------------------------------------------


def test_merge_ranger_policies_adds_user_to_existing_item():
    """Test merging concatenates users on items sharing the same access pattern."""
    existing = RangerPolicy(
        id=10,
        guid="guid-10",
        version=2,
        resource_signature="sig",
        name="p",
        service="s",
        policy_items=[
            RangerPolicyItem(
                accesses=[RangerPolicyItemAccess(type="select", is_allowed=True)],
                users=["alice"],
                groups=["public"],
            ),
        ],
    )
    incoming = RangerPolicy(
        name="p",
        service="s",
        policy_items=[
            {
                "accesses": [{"type": "select", "is_allowed": True}],
                "users": ["bob"],
            },
        ],
    )

    merged = merge_ranger_policies(existing, incoming)

    # Items with the same access pattern are consolidated into one.
    assert len(merged.policy_items) == 1
    item = merged.policy_items[0]
    assert item.users == ["alice", "bob"]
    # Fields not supplied by the incoming item are preserved.
    assert item.groups == ["public"]


def test_merge_ranger_policies_appends_distinct_access_pattern():
    """Test merging keeps two items when their access patterns differ."""
    existing = RangerPolicy(
        name="p",
        service="s",
        policy_items=[
            RangerPolicyItem(
                accesses=[RangerPolicyItemAccess(type="select", is_allowed=True)],
                users=["alice"],
            ),
        ],
    )
    incoming = RangerPolicy(
        name="p",
        service="s",
        policy_items=[
            {
                "accesses": [{"type": "update", "is_allowed": True}],
                "users": ["bob"],
            },
        ],
    )

    merged = merge_ranger_policies(existing, incoming)

    assert len(merged.policy_items) == 2
    access_types = sorted(item.accesses[0].type for item in merged.policy_items)
    assert access_types == ["select", "update"]


def test_merge_ranger_policies_scalar_field_incoming_wins():
    """Test merging lets an incoming scalar override the existing one."""
    existing = RangerPolicy(name="p", service="s", description="old", is_enabled=True)
    incoming = RangerPolicy(name="p", service="s", description="new")

    merged = merge_ranger_policies(existing, incoming)

    assert merged.description == "new"
    # A field only present on existing is retained.
    assert merged.is_enabled is True


def test_merge_ranger_policies_preserves_existing_when_incoming_empty():
    """Test merging with no incoming list items retains the existing items."""
    existing = RangerPolicy(
        name="p",
        service="s",
        policy_items=[
            RangerPolicyItem(
                accesses=[RangerPolicyItemAccess(type="read", is_allowed=True)],
                users=["alice"],
            ),
        ],
    )
    incoming = RangerPolicy(name="p", service="s", description="new")

    merged = merge_ranger_policies(existing, incoming)

    assert len(merged.policy_items) == 1
    assert merged.policy_items[0].users == ["alice"]
    assert merged.description == "new"


def test_merge_ranger_policies_is_idempotent_when_already_present():
    """Test merging a value that's already present produces no diff."""
    existing = RangerPolicy(
        name="p",
        service="s",
        policy_items=[
            RangerPolicyItem(
                accesses=[RangerPolicyItemAccess(type="select", is_allowed=True)],
                users=["alice"],
                groups=["public"],
            ),
        ],
    )
    incoming = RangerPolicy(
        name="p",
        service="s",
        policy_items=[
            {
                "accesses": [{"type": "select", "is_allowed": True}],
                "users": ["alice"],
            },
        ],
    )

    merged = merge_ranger_policies(existing, incoming)
    before, after = diff_dict(existing, merged)

    assert before == {}
    assert after == {}


# ---------------------------------------------------------------------------
# _consolidate_policy_items
# ---------------------------------------------------------------------------


def test_consolidate_policy_items_merges_same_access():
    """Test items sharing an access pattern have their members combined."""
    items = [
        {"accesses": [{"type": "read", "is_allowed": True}], "users": ["a"]},
        {
            "accesses": [{"type": "read", "is_allowed": True}],
            "users": ["b"],
            "groups": ["g"],
        },
    ]

    result = _consolidate_policy_items(items)

    assert len(result) == 1
    assert result[0]["users"] == ["a", "b"]
    assert result[0]["groups"] == ["g"]


def test_consolidate_policy_items_keeps_distinct_access():
    """Test items with distinct access patterns are not merged."""
    items = [
        {"accesses": [{"type": "read", "is_allowed": True}], "users": ["a"]},
        {"accesses": [{"type": "write", "is_allowed": True}], "users": ["b"]},
    ]

    result = _consolidate_policy_items(items)

    assert len(result) == 2


def test_consolidate_policy_items_deduplicates_partial_overlap():
    """Test consolidating items with a partially-overlapping member list does not duplicate entries."""
    items = [
        {"accesses": [{"type": "read", "is_allowed": True}], "users": ["alice", "bob"]},
        {
            "accesses": [{"type": "read", "is_allowed": True}],
            "users": ["bob", "charlie"],
        },
    ]

    result = _consolidate_policy_items(items)

    assert len(result) == 1
    assert result[0]["users"] == ["alice", "bob", "charlie"]
