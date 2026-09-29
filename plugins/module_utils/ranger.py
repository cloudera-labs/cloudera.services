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

"""
REST clients for the Apache Ranger Admin API.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import json

from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
    snake_dict_to_camel_dict,
)

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    NULLABLE,
    ServicesClient,
    ServicesError,
)


@dataclass
class RangerService:
    """Representation of an Apache Ranger service."""

    # Mutable - required when creating a service
    name: str

    # Mutable - optional
    type: Union[str, None, NULLABLE] = NULLABLE
    display_name: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    tag_service: Union[str, None, NULLABLE] = NULLABLE
    is_enabled: Union[bool, None, NULLABLE] = NULLABLE
    configs: Union[Dict[str, Any], None, NULLABLE] = NULLABLE

    # Read-only (set by Ranger)
    id: Union[int, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE
    policy_version: Union[int, None, NULLABLE] = NULLABLE
    policy_update_time: Union[int, None, NULLABLE] = NULLABLE
    tag_version: Union[int, None, NULLABLE] = NULLABLE
    tag_update_time: Union[int, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable RangerService parameters."""
        return dict(
            name=dict(type="str", required=False),
            type=dict(type="str", required=False),
            display_name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            tag_service=dict(type="str", required=False),
            is_enabled=dict(
                type="bool",
                required=False,
                default=True,
                aliases=["enabled"],
            ),
            configs=dict(type="dict", required=False),
        )


def _service_to_payload(service: RangerService) -> Dict[str, Any]:
    """Serialise a RangerService into a camelCase Ranger request payload."""
    data = to_dict(service)
    configs = data.pop("configs", None)
    payload = snake_dict_to_camel_dict(data)
    if configs is not None:
        payload["configs"] = configs
    return payload


def _service_from_response(raw: Dict[str, Any]) -> RangerService:
    """Deserialise a Ranger service response into a RangerService."""
    data = dict(raw)
    configs = data.pop("configs", None)
    service = from_dict(
        RangerService,
        camel_dict_to_snake_dict(data, reversible=True),
    )
    if configs is not None:
        service.configs = configs
    return service


def _is_ranger_not_found(result: Any) -> bool:
    """Check whether a passthru response is Ranger's DATA_NOT_FOUND 400 (its substitute for 404)."""
    if not isinstance(result, dict) or "status" not in result:
        return False

    if result["status"] != 400:
        return False

    body = result.get("body")
    if not body:
        return False

    try:
        error_data = json.loads(body) if isinstance(body, bytes) else body
        if error_data.get("statusCode") == 1:
            message_list = error_data.get("messageList", [])
            return any(msg.get("name") == "DATA_NOT_FOUND" for msg in message_list)
    except (json.JSONDecodeError, AttributeError, KeyError):
        pass

    return False


class RangerServiceClient:
    """Apache Ranger Service API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def list_services(self) -> List[RangerService]:
        """List all services."""
        result = self.api_client.get(
            "/service/plugins/services",
            squelch={404: {"services": []}},
        )
        services_raw = result.get("services", []) if result else []
        return [_service_from_response(s) for s in services_raw]

    def get_service_by_id(self, service_id: int) -> Optional[RangerService]:
        """Retrieve a single service by id, or None if not found."""
        result = self.api_client.get(
            f"/service/plugins/services/{service_id}",
            squelch={404: None},
            passthru=[400],
        )

        if result is None or _is_ranger_not_found(result):
            return None

        if isinstance(result, dict) and result.get("status") == 400:
            raise ServicesError(
                f"HTTP 400 Error retrieving service {service_id}",
                status=400,
            )

        return _service_from_response(result)

    def get_service_by_name(self, service_name: str) -> Optional[RangerService]:
        """Retrieve a single service by name, or None if not found."""
        result = self.api_client.get(
            f"/service/plugins/services/name/{service_name}",
            squelch={404: None},
            passthru=[400],
        )

        if result is None or _is_ranger_not_found(result):
            return None

        if isinstance(result, dict) and result.get("status") == 400:
            raise ServicesError(
                f"HTTP 400 Error retrieving service '{service_name}'",
                status=400,
            )

        return _service_from_response(result)

    def create_service(self, service: RangerService) -> RangerService:
        """Create a new service."""
        result = self.api_client.post(
            "/service/plugins/services",
            data=_service_to_payload(service),
        )
        return _service_from_response(result)

    def update_service(self, service: RangerService) -> RangerService:
        """Update an existing service by its id."""
        if service.id is NULLABLE or service.id is None:
            raise ValueError("Cannot update a service without an id.")
        result = self.api_client.put(
            f"/service/plugins/services/{service.id}",
            data=_service_to_payload(service),
        )
        return _service_from_response(result)

    def delete_service_by_id(self, service_id: int) -> None:
        """Delete a service by id (idempotent)."""
        result = self.api_client.delete(
            f"/service/plugins/services/{service_id}",
            squelch={404: None},
            passthru=[400],
        )

        if _is_ranger_not_found(result):
            return None

        if isinstance(result, dict) and result.get("status") == 400:
            raise ServicesError(
                f"HTTP 400 Error deleting service {service_id}",
                status=400,
            )


def extract_service_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable service parameters from a module instance into a dict."""
    return {
        "name": getattr(module_instance, "name", None),
        "type": getattr(module_instance, "type", None),
        "display_name": getattr(module_instance, "display_name", None),
        "description": getattr(module_instance, "description", None),
        "tag_service": getattr(module_instance, "tag_service", None),
        "is_enabled": getattr(module_instance, "is_enabled", None),
        "configs": getattr(module_instance, "configs", None),
    }


@dataclass
class RangerPolicyItemAccess:
    """A single access entry inside a RangerPolicyItem (type + isAllowed)."""

    type: str
    is_allowed: Union[bool, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            type=dict(type="str", required=True),
            is_allowed=dict(type="bool", required=False),
        )


@dataclass
class RangerPolicyItemCondition:
    """A custom condition entry inside a RangerPolicyItem or RangerPolicy."""

    type: str
    values: Union[List[str], None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            type=dict(type="str", required=True),
            values=dict(type="list", elements="str", required=False),
        )


@dataclass
class RangerPolicyItem:
    """A policy item (allow / deny / allow-exception / deny-exception)."""

    accesses: Union[List[RangerPolicyItemAccess], None, NULLABLE] = NULLABLE
    users: Union[List[str], None, NULLABLE] = NULLABLE
    groups: Union[List[str], None, NULLABLE] = NULLABLE
    roles: Union[List[str], None, NULLABLE] = NULLABLE
    conditions: Union[List[RangerPolicyItemCondition], None, NULLABLE] = NULLABLE
    delegate_admin: Union[bool, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            accesses=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItemAccess.argument_spec(),
            ),
            users=dict(type="list", elements="str", required=False),
            groups=dict(type="list", elements="str", required=False),
            roles=dict(type="list", elements="str", required=False),
            conditions=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItemCondition.argument_spec(),
            ),
            delegate_admin=dict(type="bool", required=False),
        )


@dataclass
class RangerPolicyItemDataMaskInfo:
    """Data-mask info for ``dataMaskPolicyItems``."""

    data_mask_type: Union[str, None, NULLABLE] = NULLABLE
    condition_expr: Union[str, None, NULLABLE] = NULLABLE
    value_expr: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            data_mask_type=dict(type="str", required=False),
            condition_expr=dict(type="str", required=False),
            value_expr=dict(type="str", required=False),
        )


@dataclass
class RangerDataMaskPolicyItem:
    """A data-mask policy item."""

    data_mask_info: Union[RangerPolicyItemDataMaskInfo, None, NULLABLE] = NULLABLE
    accesses: Union[List[RangerPolicyItemAccess], None, NULLABLE] = NULLABLE
    users: Union[List[str], None, NULLABLE] = NULLABLE
    groups: Union[List[str], None, NULLABLE] = NULLABLE
    roles: Union[List[str], None, NULLABLE] = NULLABLE
    conditions: Union[List[RangerPolicyItemCondition], None, NULLABLE] = NULLABLE
    delegate_admin: Union[bool, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            data_mask_info=dict(
                type="dict",
                required=False,
                options=RangerPolicyItemDataMaskInfo.argument_spec(),
            ),
            accesses=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItemAccess.argument_spec(),
            ),
            users=dict(type="list", elements="str", required=False),
            groups=dict(type="list", elements="str", required=False),
            roles=dict(type="list", elements="str", required=False),
            conditions=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItemCondition.argument_spec(),
            ),
            delegate_admin=dict(type="bool", required=False),
        )


@dataclass
class RangerPolicyItemRowFilterInfo:
    """Row-filter info for ``rowFilterPolicyItems``."""

    filter_expr: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            filter_expr=dict(type="str", required=False),
        )


@dataclass
class RangerRowFilterPolicyItem:
    """A row-filter policy item."""

    row_filter_info: Union[RangerPolicyItemRowFilterInfo, None, NULLABLE] = NULLABLE
    accesses: Union[List[RangerPolicyItemAccess], None, NULLABLE] = NULLABLE
    users: Union[List[str], None, NULLABLE] = NULLABLE
    groups: Union[List[str], None, NULLABLE] = NULLABLE
    roles: Union[List[str], None, NULLABLE] = NULLABLE
    conditions: Union[List[RangerPolicyItemCondition], None, NULLABLE] = NULLABLE
    delegate_admin: Union[bool, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            row_filter_info=dict(
                type="dict",
                required=False,
                options=RangerPolicyItemRowFilterInfo.argument_spec(),
            ),
            accesses=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItemAccess.argument_spec(),
            ),
            users=dict(type="list", elements="str", required=False),
            groups=dict(type="list", elements="str", required=False),
            roles=dict(type="list", elements="str", required=False),
            conditions=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItemCondition.argument_spec(),
            ),
            delegate_admin=dict(type="bool", required=False),
        )


@dataclass
class RangerPolicyResource:
    """A single resource definition used inside ``RangerPolicy.resources``."""

    values: Union[List[str], None, NULLABLE] = NULLABLE
    is_excludes: Union[bool, None, NULLABLE] = NULLABLE
    is_recursive: Union[bool, None, NULLABLE] = NULLABLE


@dataclass
class RangerValidityRecurrence:
    """One recurrence entry inside a RangerValiditySchedule."""

    schedule: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    interval: Union[Dict[str, Any], None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            schedule=dict(type="dict", required=False),
            interval=dict(type="dict", required=False),
        )


@dataclass
class RangerValiditySchedule:
    """A validity schedule for a policy."""

    start_time: Union[str, None, NULLABLE] = NULLABLE
    end_time: Union[str, None, NULLABLE] = NULLABLE
    time_zone: Union[str, None, NULLABLE] = NULLABLE
    recurrences: Union[List[RangerValidityRecurrence], None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            start_time=dict(type="str", required=False),
            end_time=dict(type="str", required=False),
            time_zone=dict(type="str", required=False),
            recurrences=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerValidityRecurrence.argument_spec(),
            ),
        )


@dataclass
class RangerPolicy:
    """Full representation of an Apache Ranger policy."""

    # Mutable - required when creating a policy
    name: str
    service: str

    # Mutable - optional
    service_type: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    policy_type: Union[int, None, NULLABLE] = NULLABLE
    policy_priority: Union[int, None, NULLABLE] = NULLABLE
    is_enabled: Union[bool, None, NULLABLE] = NULLABLE
    is_audit_enabled: Union[bool, None, NULLABLE] = NULLABLE
    is_deny_all_else: Union[bool, None, NULLABLE] = NULLABLE
    zone_name: Union[str, None, NULLABLE] = NULLABLE
    resources: Union[Dict[str, RangerPolicyResource], None, NULLABLE] = NULLABLE
    additional_resources: Union[
        List[Dict[str, RangerPolicyResource]],
        None,
        NULLABLE,
    ] = NULLABLE
    conditions: Union[List[RangerPolicyItemCondition], None, NULLABLE] = NULLABLE
    policy_items: Union[List[RangerPolicyItem], None, NULLABLE] = NULLABLE
    deny_policy_items: Union[List[RangerPolicyItem], None, NULLABLE] = NULLABLE
    allow_exceptions: Union[List[RangerPolicyItem], None, NULLABLE] = NULLABLE
    deny_exceptions: Union[List[RangerPolicyItem], None, NULLABLE] = NULLABLE
    data_mask_policy_items: Union[List[RangerDataMaskPolicyItem], None, NULLABLE] = (
        NULLABLE
    )
    row_filter_policy_items: Union[List[RangerRowFilterPolicyItem], None, NULLABLE] = (
        NULLABLE
    )
    validity_schedules: Union[List[RangerValiditySchedule], None, NULLABLE] = NULLABLE
    policy_labels: Union[List[str], None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE

    # Read-only (set by Ranger)
    id: Union[int, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    resource_signature: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable RangerPolicy parameters."""
        return dict(
            name=dict(type="str", required=False),
            service=dict(type="str", required=False),
            service_type=dict(type="str", required=False),
            description=dict(type="str", required=False),
            policy_type=dict(type="int", required=False),
            policy_priority=dict(type="int", required=False),
            is_enabled=dict(type="bool", required=False, aliases=["enabled"]),
            is_audit_enabled=dict(
                type="bool",
                required=False,
                aliases=["audit_enabled"],
            ),
            is_deny_all_else=dict(
                type="bool",
                required=False,
                aliases=["deny_all_else"],
            ),
            zone_name=dict(type="str", required=False),
            resources=dict(type="dict", required=False),
            additional_resources=dict(
                type="list",
                elements="dict",
                required=False,
            ),
            conditions=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItemCondition.argument_spec(),
            ),
            policy_items=dict(
                type="list",
                elements="dict",
                required=False,
                aliases=["access_policies"],
                options=RangerPolicyItem.argument_spec(),
            ),
            deny_policy_items=dict(
                type="list",
                elements="dict",
                required=False,
                aliases=["deny_policies"],
                options=RangerPolicyItem.argument_spec(),
            ),
            allow_exceptions=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItem.argument_spec(),
            ),
            deny_exceptions=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerPolicyItem.argument_spec(),
            ),
            data_mask_policy_items=dict(
                type="list",
                elements="dict",
                required=False,
                aliases=["data_mask_policies"],
                options=RangerDataMaskPolicyItem.argument_spec(),
            ),
            row_filter_policy_items=dict(
                type="list",
                elements="dict",
                required=False,
                aliases=["row_filter_policies"],
                options=RangerRowFilterPolicyItem.argument_spec(),
            ),
            validity_schedules=dict(
                type="list",
                elements="dict",
                required=False,
                options=RangerValiditySchedule.argument_spec(),
            ),
            policy_labels=dict(type="list", elements="str", required=False),
            options=dict(type="dict", required=False),
        )


class RangerPolicyClient:
    """Apache Ranger Policy API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def list_policies(
        self,
        service_name: Optional[str] = None,
    ) -> List[RangerPolicy]:
        """List all policies, optionally filtered by service_name."""
        params: Dict[str, Any] = {}
        if service_name:
            params["serviceName"] = service_name

        result = self.api_client.get(
            "/service/plugins/policies",
            params=params if params else None,
            squelch={404: {"policies": []}},
        )
        policies_raw = result.get("policies", []) if result else []
        return [
            from_dict(RangerPolicy, camel_dict_to_snake_dict(p, reversible=True))
            for p in policies_raw
        ]

    def get_policy_by_id(self, policy_id: int) -> Optional[RangerPolicy]:
        """Retrieve a single policy by id, or None if not found."""
        result = self.api_client.get(
            f"/service/plugins/policies/{policy_id}",
            squelch={404: None},
            passthru=[400],
        )

        if result is None or _is_ranger_not_found(result):
            return None

        if isinstance(result, dict) and result.get("status") == 400:
            raise ServicesError(
                f"HTTP 400 Error retrieving policy {policy_id}",
                status=400,
            )

        return from_dict(
            RangerPolicy,
            camel_dict_to_snake_dict(result, reversible=True),
        )

    def get_policy_by_name(
        self,
        service_name: str,
        policy_name: str,
    ) -> Optional[RangerPolicy]:
        """Retrieve a policy by service_name and policy_name, or None if not found."""
        policies = self.list_policies(service_name=service_name)
        for policy in policies:
            if policy.name == policy_name:
                return policy
        return None

    def create_policy(self, policy: RangerPolicy) -> RangerPolicy:
        """Create a new policy."""
        result = self.api_client.post(
            "/service/plugins/policies",
            data=snake_dict_to_camel_dict(to_dict(policy)),
        )
        return from_dict(
            RangerPolicy,
            camel_dict_to_snake_dict(result, reversible=True),
        )

    def update_policy(self, policy: RangerPolicy) -> RangerPolicy:
        """Update an existing policy by its id."""
        if policy.id is NULLABLE or policy.id is None:
            raise ValueError("Cannot update a policy without an id.")
        result = self.api_client.put(
            f"/service/plugins/policies/{policy.id}",
            data=snake_dict_to_camel_dict(to_dict(policy)),
        )
        return from_dict(
            RangerPolicy,
            camel_dict_to_snake_dict(result, reversible=True),
        )

    def delete_policy_by_id(self, policy_id: int) -> None:
        """Delete a policy by id (idempotent)."""
        result = self.api_client.delete(
            f"/service/plugins/policies/{policy_id}",
            squelch={404: None},
            passthru=[400],
        )

        if _is_ranger_not_found(result):
            return None

        if isinstance(result, dict) and result.get("status") == 400:
            raise ServicesError(
                f"HTTP 400 Error deleting policy {policy_id}",
                status=400,
            )


def extract_policy_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable policy parameters from a module instance into a dict."""
    return {
        "name": getattr(module_instance, "name", None),
        "service": getattr(module_instance, "service", None),
        "service_type": getattr(module_instance, "service_type", None),
        "description": getattr(module_instance, "description", None),
        "policy_type": getattr(module_instance, "policy_type", None),
        "policy_priority": getattr(module_instance, "policy_priority", None),
        "is_enabled": getattr(module_instance, "is_enabled", None),
        "is_audit_enabled": getattr(module_instance, "is_audit_enabled", None),
        "is_deny_all_else": getattr(module_instance, "is_deny_all_else", None),
        "zone_name": getattr(module_instance, "zone_name", None),
        "resources": getattr(module_instance, "resources", None),
        "additional_resources": getattr(module_instance, "additional_resources", None),
        "conditions": getattr(module_instance, "conditions", None),
        "policy_items": getattr(module_instance, "policy_items", None),
        "deny_policy_items": getattr(module_instance, "deny_policy_items", None),
        "allow_exceptions": getattr(module_instance, "allow_exceptions", None),
        "deny_exceptions": getattr(module_instance, "deny_exceptions", None),
        "data_mask_policy_items": getattr(
            module_instance,
            "data_mask_policy_items",
            None,
        ),
        "row_filter_policy_items": getattr(
            module_instance,
            "row_filter_policy_items",
            None,
        ),
        "validity_schedules": getattr(module_instance, "validity_schedules", None),
        "policy_labels": getattr(module_instance, "policy_labels", None),
        "options": getattr(module_instance, "options", None),
    }


def merge_ranger_policies(
    existing: RangerPolicy,
    incoming: RangerPolicy,
) -> RangerPolicy:
    """Combine an incoming (partial) policy with the policy already in Ranger.

    Used for ``merged=true``, where policy items should be added to the
    existing policy rather than replacing it wholesale (which is what
    ``overlay()`` would do, and is correct for ``merged=false``). Scalars and
    non-item fields set on `incoming` replace those on `existing`; the
    policy-item list fields are concatenated and then consolidated via
    `_consolidate_policy_items` so items sharing the same access pattern are
    combined instead of duplicated.
    """
    existing_dict = to_dict(existing)
    incoming_dict = to_dict(incoming)

    # Policy item fields need special (append + consolidate) handling.
    policy_list_fields = [
        "policy_items",
        "deny_policy_items",
        "allow_exceptions",
        "deny_exceptions",
        "data_mask_policy_items",
        "row_filter_policy_items",
    ]

    # Separate list fields from the rest to avoid dict-sorting issues in the merge.
    existing_lists = {}
    incoming_lists = {}

    for field in policy_list_fields:
        if field in existing_dict:
            existing_lists[field] = existing_dict.pop(field)
        if field in incoming_dict:
            incoming_lists[field] = incoming_dict.pop(field)

    merged_dict = {**existing_dict, **incoming_dict}

    # Concatenate and consolidate the policy item lists.
    for field in policy_list_fields:
        combined = existing_lists.get(field, []) + incoming_lists.get(field, [])
        if combined:
            merged_dict[field] = _consolidate_policy_items(combined)

    return from_dict(RangerPolicy, merged_dict)


def _consolidate_policy_items(items: List[Dict]) -> List[Dict]:
    """Merge users/groups/roles/conditions for items that share the same access pattern.

    Helper for `merge_ranger_policies`: after concatenating the existing and
    incoming policy-item lists, this collapses items with the same set of
    accesses (e.g. both granting ``select``) into a single item, instead of
    leaving two duplicate-looking entries, unioning their users/groups/roles
    rather than duplicating values already present.
    """
    if not items:
        return items

    consolidated = {}

    for item in items:
        # Build a signature from the accesses (sorted for consistency).
        accesses = item.get("accesses", [])
        key = str(
            sorted([(a.get("type"), a.get("is_allowed", True)) for a in accesses]),
        )

        if key not in consolidated:
            # First time seeing this access pattern - store it.
            consolidated[key] = item.copy()
        else:
            # Merge users/groups/roles/conditions into the existing entry,
            # skipping values already present to avoid duplicates.
            for field in ["users", "groups", "roles", "conditions"]:
                if field in item and item[field]:
                    existing_values = consolidated[key].get(field) or []
                    new_values = [v for v in item[field] if v not in existing_values]
                    if existing_values or new_values:
                        consolidated[key][field] = existing_values + new_values

    return list(consolidated.values())
