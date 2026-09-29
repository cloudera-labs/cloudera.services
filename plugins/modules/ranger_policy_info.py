#!/usr/bin/python
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

DOCUMENTATION = r"""
module: ranger_policy_info
short_description: Retrieve policy details from Apache Ranger
description:
  - Retrieve details of a specific policy by ID or name.
  - If no identifier is provided, retrieves all services.
  - The module supports C(check_mode).
author:
  - "Ronald Suplina (@rsuplina)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the Ranger policy.
      - This parameter is mutually exclusive with O(policy_id).
    type: str
    required: false
    aliases:
      - policy_name
  policy_id:
    description:
      - ID of the Ranger policy to retrieve.
      - This parameter is mutually exclusive with O(name).
    type: int
    required: false
  service:
    description:
      - Name of the Ranger service associated with the policy.
      - When provided with O(name), retrieves a specific policy.
      - When provided alone, retrieves all policies for the service.
    type: str
    required: false
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields

- name: Retrieve policy by ID
  cloudera.services.ranger_policy_info:
    policy_id: 67

- name: Retrieve policy by name and service
  cloudera.services.ranger_policy_info:
    name: "all - global"
    service: "hive"

- name: Retrieve all policies in a specific service
  cloudera.services.ranger_policy_info:
    service: "hive"

- name: Retrieve all policies
  cloudera.services.ranger_policy_info:
"""

RETURN = r"""
policies:
  description:
    - List of policies matching the given criteria, or all policies if no filter is applied.
  type: list
  elements: dict
  returned: always
  contains:
    id:
      description:
        - Unique numeric ID of the policy.
      type: int
      returned: always
    guid:
      description:
        - Globally unique identifier for the policy.
      type: str
      returned: always
    is_enabled:
      description:
        - Whether the policy is currently enabled.
      type: bool
      returned: always
    created_by:
      description:
        - Username of the policy creator.
      type: str
      returned: always
    updated_by:
      description:
        - Username of the last person who updated the policy.
      type: str
      returned: always
    create_time:
      description:
        - Epoch timestamp when the policy was created.
      type: int
      returned: always
    update_time:
      description:
        - Epoch timestamp when the policy was last updated.
      type: int
      returned: always
    version:
      description:
        - Version number of the policy.
      type: int
      returned: always
    service:
      description:
        - Name of the service this policy applies to.
      type: str
      returned: always
    name:
      description:
        - Name of the policy.
      type: str
      returned: always
    policy_type:
      description:
        - Numeric identifier for the type of policy.
      type: int
      returned: always
    policy_priority:
      description:
        - Priority value for the policy.
      type: int
      returned: always
    description:
      description:
        - Optional description of the policy.
      type: str
      returned: always
    resource_signature:
      description:
        - Signature hash of the resources in the policy.
      type: str
      returned: always
    is_audit_enabled:
      description:
        - Whether auditing is enabled for the policy.
      type: bool
      returned: always
    resources:
      description:
        - Dictionary of resources the policy applies to.
      type: dict
      returned: always
      contains:
        values:
          description:
            - List of resource values matched by this resource definition.
          type: list
          elements: str
          returned: always
        is_excludes:
          description:
            - Whether the specified values are excluded rather than included.
          type: bool
          returned: always
        is_recursive:
          description:
            - Whether the resource match is applied recursively.
          type: bool
          returned: always
    additional_resources:
      description:
        - List of additional resource definitions.
      type: list
      elements: dict
      returned: always
      contains:
        values:
          description:
            - List of resource values matched by this resource definition.
          type: list
          elements: str
          returned: always
        is_excludes:
          description:
            - Whether the specified values are excluded rather than included.
          type: bool
          returned: always
        is_recursive:
          description:
            - Whether the resource match is applied recursively.
          type: bool
          returned: always
    conditions:
      description:
        - List of policy conditions.
      type: list
      elements: dict
      returned: always
      contains:
        type:
          description:
            - The type of the condition.
          type: str
          returned: always
        values:
          description:
            - The values associated with the condition.
          type: list
          elements: str
          returned: always
    policy_items:
      description:
        - List of allow policy items.
      type: list
      elements: dict
      returned: always
      contains:
        accesses:
          description:
            - List of access types and whether each is allowed.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The access type (e.g. V(read), V(write), V(select)).
              type: str
              returned: always
            is_allowed:
              description:
                - Whether this access type is allowed.
              type: bool
              returned: always
        users:
          description:
            - List of users the policy item applies to.
          type: list
          elements: str
          returned: always
        groups:
          description:
            - List of groups the policy item applies to.
          type: list
          elements: str
          returned: always
        roles:
          description:
            - List of roles the policy item applies to.
          type: list
          elements: str
          returned: always
        conditions:
          description:
            - List of custom conditions for the policy item.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The type of the condition.
              type: str
              returned: always
            values:
              description:
                - The values associated with the condition.
              type: list
              elements: str
              returned: always
        delegate_admin:
          description:
            - Whether users/groups of this policy item are allowed to update the policy.
          type: bool
          returned: always
    deny_policy_items:
      description:
        - List of deny policy items.
      type: list
      elements: dict
      returned: always
      contains:
        accesses:
          description:
            - List of access types and whether each is allowed.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The access type (e.g. V(read), V(write), V(select)).
              type: str
              returned: always
            is_allowed:
              description:
                - Whether this access type is allowed.
              type: bool
              returned: always
        users:
          description:
            - List of users the policy item applies to.
          type: list
          elements: str
          returned: always
        groups:
          description:
            - List of groups the policy item applies to.
          type: list
          elements: str
          returned: always
        roles:
          description:
            - List of roles the policy item applies to.
          type: list
          elements: str
          returned: always
        conditions:
          description:
            - List of custom conditions for the policy item.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The type of the condition.
              type: str
              returned: always
            values:
              description:
                - The values associated with the condition.
              type: list
              elements: str
              returned: always
        delegate_admin:
          description:
            - Whether users/groups of this policy item are allowed to update the policy.
          type: bool
          returned: always
    allow_exceptions:
      description:
        - List of allow exception policy items.
      type: list
      elements: dict
      returned: always
      contains:
        accesses:
          description:
            - List of access types and whether each is allowed.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The access type (e.g. V(read), V(write), V(select)).
              type: str
              returned: always
            is_allowed:
              description:
                - Whether this access type is allowed.
              type: bool
              returned: always
        users:
          description:
            - List of users the policy item applies to.
          type: list
          elements: str
          returned: always
        groups:
          description:
            - List of groups the policy item applies to.
          type: list
          elements: str
          returned: always
        roles:
          description:
            - List of roles the policy item applies to.
          type: list
          elements: str
          returned: always
        conditions:
          description:
            - List of custom conditions for the policy item.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The type of the condition.
              type: str
              returned: always
            values:
              description:
                - The values associated with the condition.
              type: list
              elements: str
              returned: always
        delegate_admin:
          description:
            - Whether users/groups of this policy item are allowed to update the policy.
          type: bool
          returned: always
    deny_exceptions:
      description:
        - List of deny exception policy items.
      type: list
      elements: dict
      returned: always
      contains:
        accesses:
          description:
            - List of access types and whether each is allowed.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The access type (e.g. V(read), V(write), V(select)).
              type: str
              returned: always
            is_allowed:
              description:
                - Whether this access type is allowed.
              type: bool
              returned: always
        users:
          description:
            - List of users the policy item applies to.
          type: list
          elements: str
          returned: always
        groups:
          description:
            - List of groups the policy item applies to.
          type: list
          elements: str
          returned: always
        roles:
          description:
            - List of roles the policy item applies to.
          type: list
          elements: str
          returned: always
        conditions:
          description:
            - List of custom conditions for the policy item.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The type of the condition.
              type: str
              returned: always
            values:
              description:
                - The values associated with the condition.
              type: list
              elements: str
              returned: always
        delegate_admin:
          description:
            - Whether users/groups of this policy item are allowed to update the policy.
          type: bool
          returned: always
    data_mask_policy_items:
      description:
        - List of data mask policy items.
      type: list
      elements: dict
      returned: always
      contains:
        data_mask_info:
          description:
            - The data masking configuration applied by this policy item.
          type: dict
          returned: always
          contains:
            data_mask_type:
              description:
                - The type of data masking to apply.
              type: str
              returned: always
            condition_expr:
              description:
                - The condition expression controlling when the mask applies.
              type: str
              returned: always
            value_expr:
              description:
                - The expression used to compute the masked value.
              type: str
              returned: always
        accesses:
          description:
            - List of access types and whether each is allowed.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The access type (e.g. V(read), V(write), V(select)).
              type: str
              returned: always
            is_allowed:
              description:
                - Whether this access type is allowed.
              type: bool
              returned: always
        users:
          description:
            - List of users the policy item applies to.
          type: list
          elements: str
          returned: always
        groups:
          description:
            - List of groups the policy item applies to.
          type: list
          elements: str
          returned: always
        roles:
          description:
            - List of roles the policy item applies to.
          type: list
          elements: str
          returned: always
        conditions:
          description:
            - List of custom conditions for the policy item.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The type of the condition.
              type: str
              returned: always
            values:
              description:
                - The values associated with the condition.
              type: list
              elements: str
              returned: always
        delegate_admin:
          description:
            - Whether users/groups of this policy item are allowed to update the policy.
          type: bool
          returned: always
    row_filter_policy_items:
      description:
        - List of row filter policy items.
      type: list
      elements: dict
      returned: always
      contains:
        row_filter_info:
          description:
            - The row filter configuration applied by this policy item.
          type: dict
          returned: always
          contains:
            filter_expr:
              description:
                - The filter expression applied to rows.
              type: str
              returned: always
        accesses:
          description:
            - List of access types and whether each is allowed.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The access type (e.g. V(read), V(write), V(select)).
              type: str
              returned: always
            is_allowed:
              description:
                - Whether this access type is allowed.
              type: bool
              returned: always
        users:
          description:
            - List of users the policy item applies to.
          type: list
          elements: str
          returned: always
        groups:
          description:
            - List of groups the policy item applies to.
          type: list
          elements: str
          returned: always
        roles:
          description:
            - List of roles the policy item applies to.
          type: list
          elements: str
          returned: always
        conditions:
          description:
            - List of custom conditions for the policy item.
          type: list
          elements: dict
          returned: always
          contains:
            type:
              description:
                - The type of the condition.
              type: str
              returned: always
            values:
              description:
                - The values associated with the condition.
              type: list
              elements: str
              returned: always
        delegate_admin:
          description:
            - Whether users/groups of this policy item are allowed to update the policy.
          type: bool
          returned: always
    service_type:
      description:
        - Type of the service (e.g., hive, hdfs) this policy applies to.
      type: str
      returned: always
    options:
      description:
        - Dictionary of additional policy options.
      type: dict
      returned: always
    validity_schedules:
      description:
        - List of validity schedules attached to the policy.
      type: list
      elements: dict
      returned: always
      contains:
        start_time:
          description:
            - The start time of the validity schedule.
          type: str
          returned: always
        end_time:
          description:
            - The end time of the validity schedule.
          type: str
          returned: always
        time_zone:
          description:
            - The time zone the schedule times are expressed in.
          type: str
          returned: always
        recurrences:
          description:
            - List of recurrence definitions for the schedule.
          type: list
          elements: dict
          returned: always
          contains:
            schedule:
              description:
                - The recurrence schedule definition.
              type: dict
              returned: always
            interval:
              description:
                - The recurrence interval definition.
              type: dict
              returned: always
    policy_labels:
      description:
        - List of policy labels.
      type: list
      elements: str
      returned: always
    zone_name:
      description:
        - Name of the security zone this policy belongs to.
      type: str
      returned: always
    is_deny_all_else:
      description:
        - Whether the policy denies all accesses not explicitly allowed.
      type: bool
      returned: always
"""

from typing import Any, Dict, List

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
    RangerPolicyClient,
)


class RangerPolicyInfoModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                name=dict(type="str", required=False, aliases=["policy_name"]),
                policy_id=dict(type="int", required=False),
                service=dict(type="str", required=False),
            ),
            mutually_exclusive=[["name", "policy_id"]],
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.policy_id = self.get_param("policy_id")
        self.service = self.get_param("service")

        # Initialize result variables
        self.policy_list: List[RangerPolicy] = []

    def process(self) -> None:
        client = RangerPolicyClient(self.api_client)

        if self.policy_id:
            policy = client.get_policy_by_id(policy_id=self.policy_id)
            if policy:
                self.policy_list.append(policy)

        elif self.name:
            if self.service:
                policy = client.get_policy_by_name(
                    service_name=self.service,
                    policy_name=self.name,
                )
                if policy:
                    self.policy_list.append(policy)
            else:
                policies = client.list_policies()
                self.policy_list.extend([p for p in policies if p.name == self.name])

        elif self.service:
            self.policy_list.extend(client.list_policies(service_name=self.service))

        else:
            self.policy_list.extend(client.list_policies())


def main():
    result = RangerPolicyInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        policies=[to_dict(policy) for policy in result.policy_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
