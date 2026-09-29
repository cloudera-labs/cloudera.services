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
module: ranger_policy
short_description: Manage policies in Apache Ranger
description:
  - Create, update, or delete policies in Apache Ranger.
author:
  - "Ronald Suplina (@rsuplina)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the policy.
    type: str
    required: false
  service:
    description:
      - Name of the Ranger service associated with the policy.
    type: str
    required: false
  service_type:
    description:
      - Type of the service (e.g., hive, hdfs) this policy applies to.
    type: str
    required: false
  description:
    description:
      - Description of the policy.
    type: str
    required: false
  policy_type:
    description:
      - Type of the policy.
    type: int
    required: false
  policy_priority:
    description:
      - Priority of the policy.
    type: int
    required: false
  is_enabled:
    description:
      - Whether the policy is enabled.
    type: bool
    required: false
    aliases:
      - enabled
  is_audit_enabled:
    description:
      - Whether auditing is enabled for the policy.
    type: bool
    required: false
    aliases:
      - audit_enabled
  is_deny_all_else:
    description:
      - Whether to deny all other accesses not explicitly allowed by the policy.
    type: bool
    required: false
    aliases:
      - deny_all_else
  zone_name:
    description:
      - Name of the security zone the policy belongs to.
    type: str
    required: false
  resources:
    description:
      - Dictionary of resource definitions for the policy.
    type: dict
    required: false
  additional_resources:
    description:
      - Additional resource definitions.
    type: list
    elements: dict
    required: false
  conditions:
    description:
      - List of custom conditions for the policy.
    type: list
    elements: dict
    required: false
    suboptions:
      type:
        description:
          - The type of the condition.
        type: str
        required: true
      values:
        description:
          - The values associated with the condition.
        type: list
        elements: str
        required: false
  policy_items:
    description:
      - List of allow policy items.
    type: list
    elements: dict
    required: false
    aliases:
      - access_policies
    suboptions:
      accesses:
        description:
          - List of access types and whether each is allowed.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The access type (e.g. V(read), V(write), V(select)).
            type: str
            required: true
          is_allowed:
            description:
              - Whether this access type is allowed.
            type: bool
            required: false
      users:
        description:
          - List of users the policy item applies to.
        type: list
        elements: str
        required: false
      groups:
        description:
          - List of groups the policy item applies to.
        type: list
        elements: str
        required: false
      roles:
        description:
          - List of roles the policy item applies to.
        type: list
        elements: str
        required: false
      conditions:
        description:
          - List of custom conditions for the policy item.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The type of the condition.
            type: str
            required: true
          values:
            description:
              - The values associated with the condition.
            type: list
            elements: str
            required: false
      delegate_admin:
        description:
          - Whether users/groups of this policy item are allowed to update the policy.
        type: bool
        required: false
  deny_policy_items:
    description:
      - List of deny policy items.
    type: list
    elements: dict
    required: false
    aliases:
      - deny_policies
    suboptions:
      accesses:
        description:
          - List of access types and whether each is allowed.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The access type (e.g. V(read), V(write), V(select)).
            type: str
            required: true
          is_allowed:
            description:
              - Whether this access type is allowed.
            type: bool
            required: false
      users:
        description:
          - List of users the policy item applies to.
        type: list
        elements: str
        required: false
      groups:
        description:
          - List of groups the policy item applies to.
        type: list
        elements: str
        required: false
      roles:
        description:
          - List of roles the policy item applies to.
        type: list
        elements: str
        required: false
      conditions:
        description:
          - List of custom conditions for the policy item.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The type of the condition.
            type: str
            required: true
          values:
            description:
              - The values associated with the condition.
            type: list
            elements: str
            required: false
      delegate_admin:
        description:
          - Whether users/groups of this policy item are allowed to update the policy.
        type: bool
        required: false
  allow_exceptions:
    description:
      - List of allow exception policy items.
    type: list
    elements: dict
    required: false
    suboptions:
      accesses:
        description:
          - List of access types and whether each is allowed.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The access type (e.g. V(read), V(write), V(select)).
            type: str
            required: true
          is_allowed:
            description:
              - Whether this access type is allowed.
            type: bool
            required: false
      users:
        description:
          - List of users the policy item applies to.
        type: list
        elements: str
        required: false
      groups:
        description:
          - List of groups the policy item applies to.
        type: list
        elements: str
        required: false
      roles:
        description:
          - List of roles the policy item applies to.
        type: list
        elements: str
        required: false
      conditions:
        description:
          - List of custom conditions for the policy item.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The type of the condition.
            type: str
            required: true
          values:
            description:
              - The values associated with the condition.
            type: list
            elements: str
            required: false
      delegate_admin:
        description:
          - Whether users/groups of this policy item are allowed to update the policy.
        type: bool
        required: false
  deny_exceptions:
    description:
      - List of deny exception policy items.
    type: list
    elements: dict
    required: false
    suboptions:
      accesses:
        description:
          - List of access types and whether each is allowed.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The access type (e.g. V(read), V(write), V(select)).
            type: str
            required: true
          is_allowed:
            description:
              - Whether this access type is allowed.
            type: bool
            required: false
      users:
        description:
          - List of users the policy item applies to.
        type: list
        elements: str
        required: false
      groups:
        description:
          - List of groups the policy item applies to.
        type: list
        elements: str
        required: false
      roles:
        description:
          - List of roles the policy item applies to.
        type: list
        elements: str
        required: false
      conditions:
        description:
          - List of custom conditions for the policy item.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The type of the condition.
            type: str
            required: true
          values:
            description:
              - The values associated with the condition.
            type: list
            elements: str
            required: false
      delegate_admin:
        description:
          - Whether users/groups of this policy item are allowed to update the policy.
        type: bool
        required: false
  data_mask_policy_items:
    description:
      - List of data masking policy items.
    type: list
    elements: dict
    required: false
    aliases:
      - data_mask_policies
    suboptions:
      data_mask_info:
        description:
          - The data masking configuration to apply.
        type: dict
        required: false
        suboptions:
          data_mask_type:
            description:
              - The type of data masking to apply.
            type: str
            required: false
          condition_expr:
            description:
              - The condition expression controlling when the mask applies.
            type: str
            required: false
          value_expr:
            description:
              - The expression used to compute the masked value.
            type: str
            required: false
      accesses:
        description:
          - List of access types and whether each is allowed.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The access type (e.g. V(read), V(write), V(select)).
            type: str
            required: true
          is_allowed:
            description:
              - Whether this access type is allowed.
            type: bool
            required: false
      users:
        description:
          - List of users the policy item applies to.
        type: list
        elements: str
        required: false
      groups:
        description:
          - List of groups the policy item applies to.
        type: list
        elements: str
        required: false
      roles:
        description:
          - List of roles the policy item applies to.
        type: list
        elements: str
        required: false
      conditions:
        description:
          - List of custom conditions for the policy item.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The type of the condition.
            type: str
            required: true
          values:
            description:
              - The values associated with the condition.
            type: list
            elements: str
            required: false
      delegate_admin:
        description:
          - Whether users/groups of this policy item are allowed to update the policy.
        type: bool
        required: false
  row_filter_policy_items:
    description:
      - List of row filtering policy items.
    type: list
    elements: dict
    required: false
    aliases:
      - row_filter_policies
    suboptions:
      row_filter_info:
        description:
          - The row filter configuration to apply.
        type: dict
        required: false
        suboptions:
          filter_expr:
            description:
              - The filter expression applied to rows.
            type: str
            required: false
      accesses:
        description:
          - List of access types and whether each is allowed.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The access type (e.g. V(read), V(write), V(select)).
            type: str
            required: true
          is_allowed:
            description:
              - Whether this access type is allowed.
            type: bool
            required: false
      users:
        description:
          - List of users the policy item applies to.
        type: list
        elements: str
        required: false
      groups:
        description:
          - List of groups the policy item applies to.
        type: list
        elements: str
        required: false
      roles:
        description:
          - List of roles the policy item applies to.
        type: list
        elements: str
        required: false
      conditions:
        description:
          - List of custom conditions for the policy item.
        type: list
        elements: dict
        required: false
        suboptions:
          type:
            description:
              - The type of the condition.
            type: str
            required: true
          values:
            description:
              - The values associated with the condition.
            type: list
            elements: str
            required: false
      delegate_admin:
        description:
          - Whether users/groups of this policy item are allowed to update the policy.
        type: bool
        required: false
  validity_schedules:
    description:
      - Time-based policy schedules.
    type: list
    elements: dict
    required: false
    suboptions:
      start_time:
        description:
          - The start time of the validity schedule.
        type: str
        required: false
      end_time:
        description:
          - The end time of the validity schedule.
        type: str
        required: false
      time_zone:
        description:
          - The time zone the schedule times are expressed in.
        type: str
        required: false
      recurrences:
        description:
          - List of recurrence definitions for the schedule.
        type: list
        elements: dict
        required: false
        suboptions:
          schedule:
            description:
              - The recurrence schedule definition.
            type: dict
            required: false
          interval:
            description:
              - The recurrence interval definition.
            type: dict
            required: false
  policy_labels:
    description:
      - List of labels associated with the policy.
    type: list
    elements: str
    required: false
  options:
    description:
      - Dictionary of additional options for the policy.
    type: dict
    required: false
  merged:
    description:
      - Whether to merge the provided policy items with the existing policy or replace it entirely.
      - When V(true), the module adds new users, groups, and accesses to existing policy items by concatenating lists.
      - When V(false), the module performs a full replacement (the default behavior).
    type: bool
    default: false
  state:
    description:
      - Whether the policy should be present or absent.
    type: str
    required: false
    default: present
    choices: ["present", "absent"]
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    description:
      - This module supports check mode.
    support: full
  diff_mode:
    description:
      - This module supports diff mode.
    support: full
    platforms:
      - all
notes:
  - When O(merged=false) (default), the module performs full replacements of existing policies rather than merges.
  - If the desired state differs from the current policy, the existing policy is fully overwritten with the new definition.
  - This guarantees consistent, predictable updates and avoids the risk of duplicate or conflicting entries.
  - When O(merged=true), the module concatenates lists (users, groups, accesses) with the existing ones.
  - Merge mode is useful for adding users, groups, or accesses to existing policies without specifying all current values.
  - Values already present are not duplicated when merging.
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields


- name: Create a basic Ranger policy
  cloudera.services.ranger_policy:
    name: "Test Policy 2"
    service: "cm_hdfs"
    service_type: "hdfs"
    description: "Description1"
    resources:
      path:
        values:
          - "/hbase/archive2"

- name: Update an existing Ranger policy
  cloudera.services.ranger_policy:
    name: "Policy test create request"
    service: "cm_hdfs"
    resources:
      path:
        values:
          - "/tmp/test"

- name: Create a policy with users, groups, and multiple accesses
  cloudera.services.ranger_policy:
    name: "atlas-policy"
    service: "cm_atlas"
    resources:
      entity-type:
        values:
          - "hive_table"
    access_policies:
      - accesses:
          - type: "type-create"
            is_allowed: true
          - type: "type-read"
            is_allowed: true
        users:
          - "admin"
          - "impala"
          - "flink"
          - "zookeeper"
        groups:
          - "public"
        roles: []
        conditions: []

- name: Add a user to an existing policy using merge mode
  cloudera.services.ranger_policy:
    name: "all - database, table"
    service: "cm_kudu"
    merged: true
    access_policies:
      - users:
          - "kafka"
        accesses:
          - type: "select"
            is_allowed: true

- name: Delete a Ranger policy
  cloudera.services.ranger_policy:
    name: "Test Policy 6"
    service: "cm_hdfs"
    state: "absent"
"""

RETURN = r"""
policy:
  description:
    - A dictionary containing details about the policy.
  type: dict
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

from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    build_from_params,
    diff_dict,
    from_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
    RangerPolicyClient,
    extract_policy_params,
    merge_ranger_policies,
)


class RangerPolicyModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                **RangerPolicy.argument_spec(),
                merged=dict(
                    type="bool",
                    default=False,
                ),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            required_if=[
                ("state", "present", ["name", "service"]),
            ],
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.service = self.get_param("service")
        self.state = self.get_param("state")
        self.merged = self.get_param("merged")
        self.service_type = self.get_param("service_type")
        self.description = self.get_param("description")
        self.policy_type = self.get_param("policy_type")
        self.policy_priority = self.get_param("policy_priority")
        self.is_enabled = self.get_param("is_enabled")
        self.is_audit_enabled = self.get_param("is_audit_enabled")
        self.is_deny_all_else = self.get_param("is_deny_all_else")
        self.zone_name = self.get_param("zone_name")
        self.resources = self.get_param("resources")
        self.additional_resources = self.get_param("additional_resources")
        self.conditions = self.get_param("conditions")
        self.policy_items = self.get_param("policy_items")
        self.deny_policy_items = self.get_param("deny_policy_items")
        self.allow_exceptions = self.get_param("allow_exceptions")
        self.deny_exceptions = self.get_param("deny_exceptions")
        self.data_mask_policy_items = self.get_param("data_mask_policy_items")
        self.row_filter_policy_items = self.get_param("row_filter_policy_items")
        self.validity_schedules = self.get_param("validity_schedules")
        self.policy_labels = self.get_param("policy_labels")
        self.options = self.get_param("options")

        # Initialize result variables
        self.changed = False
        self.diff = {}
        self.policy: Optional[RangerPolicy] = None

    def process(self) -> None:
        client = RangerPolicyClient(self.api_client)

        existing: Optional[RangerPolicy] = None

        if self.name and self.service:
            existing = client.get_policy_by_name(
                service_name=self.service,
                policy_name=self.name,
            )

        if self.state == "absent":
            if existing:
                self.changed = True

                if self.module._diff:
                    self.diff = {"before": to_dict(existing), "after": {}}

                if not self.module.check_mode:
                    client.delete_policy_by_id(existing.id)

        elif self.state == "present":
            if not existing:
                incoming = build_from_params(
                    RangerPolicy,
                    extract_policy_params(self),
                )

                self.changed = True

                if self.module._diff:
                    self.diff = {"before": {}, "after": to_dict(incoming)}

                if not self.module.check_mode:
                    self.policy = client.create_policy(incoming)
                else:
                    self.policy = incoming

            else:
                if self.merged:
                    partial_policy = build_from_params(
                        RangerPolicy,
                        extract_policy_params(self),
                    )

                    incoming = merge_ranger_policies(existing, partial_policy)
                    existing_normalized = from_dict(RangerPolicy, to_dict(existing))

                    prev_config, next_config = diff_dict(existing_normalized, incoming)

                    if prev_config or next_config:
                        self.changed = True

                        if self.module._diff:
                            self.diff = {
                                "before": prev_config,
                                "after": next_config,
                            }

                        if not self.module.check_mode:
                            self.policy = client.update_policy(incoming)
                        else:
                            self.policy = incoming
                    else:
                        self.policy = existing
                else:
                    incoming = build_from_params(
                        RangerPolicy,
                        extract_policy_params(self),
                        existing=existing,
                    )

                    prev_config, next_config = diff_dict(existing, incoming)

                    if prev_config or next_config:
                        self.changed = True

                        if self.module._diff:
                            self.diff = {
                                "before": prev_config,
                                "after": next_config,
                            }

                        if not self.module.check_mode:
                            self.policy = client.update_policy(incoming)
                        else:
                            self.policy = incoming
                    else:
                        self.policy = existing

        else:
            self.module.fail_json(msg=f"Invalid state '{self.state}'.")


def main():
    result = RangerPolicyModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        policy=to_dict(result.policy) if result.policy else {},
    )

    if result.module._diff:
        output.update(diff=result.diff)

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
