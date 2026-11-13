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
module: atlas_entity
short_description: Manage an entity in Apache Atlas
description:
  - Create, update or delete an entity, an instance of an entity type, in Apache Atlas.
  - Identify the entity by its type name and its unique attributes, usually its C(qualifiedName). To delete an entity, its GUID can be used instead.
  - Only the attributes and custom attributes given are managed. Other attributes of an existing entity are left as they are.
  - The classifications, labels and business metadata of the entity are not managed here; use M(cloudera.services.atlas_entity_classification), M(cloudera.services.atlas_entity_label) and M(cloudera.services.atlas_entity_business_metadata).
  - An entity of a type that a service hook owns, such as V(hive_table), is refused unless O(allow_service_types=true).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.2.0"
options:
  guid:
    description:
      - GUID of the entity.
      - Only allowed with O(state=absent).
      - Mutually exclusive with O(type_name), O(qualified_name), and O(unique_attributes).
    type: str
  type_name:
    description:
      - Name of the entity type, e.g. V(hive_table). The entity type must already be defined, for example with M(cloudera.services.atlas_entity_def).
      - Requires O(qualified_name) or O(unique_attributes).
    type: str
  qualified_name:
    description:
      - Value of the V(qualifiedName) unique attribute of the entity.
      - Shorthand for O(unique_attributes=qualifiedName).
      - Requires O(type_name); mutually exclusive with O(unique_attributes).
    type: str
  unique_attributes:
    description:
      - Unique attribute names and values that identify the entity within O(type_name).
      - Attribute names are Atlas names and are used as given, e.g. V(qualifiedName).
      - The values are also set on a new entity.
      - Requires O(type_name); mutually exclusive with O(qualified_name).
    type: dict
  attributes:
    description:
      - Attribute names and values to set on the entity, besides the unique attributes.
      - Not allowed with O(state=absent).
      - Every name must be an attribute of the entity type or of one of its super types. Atlas silently ignores unknown names, so the module fails on them instead.
      - Values are converted to the type the typedef declares, e.g. V("5") to V(5) for an C(int) attribute, so a repeated run reports no change.
      - Only the attributes listed here are managed. Other attributes of an existing entity are left as they are.
      - An attribute cannot be set to null.
      - Attributes that refer to other entities are sent as given and are not compared reliably.
    type: dict
  custom_attributes:
    description:
      - Custom attribute names and values to set on the entity. Both are strings.
      - Not allowed with O(state=absent).
      - Only the custom attributes listed here are managed; the others are kept.
    type: dict
  allow_service_types:
    description:
      - Whether an entity of a type that a service hook owns, such as V(hive_table), may be created, updated or deleted.
      - Deleting such an entity can also delete the entities it owns, for example the columns of a table, and the hook may register it again.
    type: bool
    default: false
  state:
    description:
      - V(present) makes sure the entity exists with the given attributes. A missing entity is created, and an existing one is updated.
      - V(absent) deletes the entity. An entity that does not exist, or is already deleted, is not an error.
    type: str
    choices:
      - present
      - absent
    default: present
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
notes:
  - Atlas deletes softly. A deleted entity stays in Atlas with the status V(DELETED) until an administrator purges it, but it is no longer found by its unique attributes. Creating an entity with the unique attributes of a deleted one makes a new entity with a new GUID.
  - A type that still has deleted entities cannot be deleted until they are purged.
seealso:
  - module: cloudera.services.atlas_entity_def
  - module: cloudera.services.atlas_entity_info
  - module: cloudera.services.atlas_entity_classification
  - module: cloudera.services.atlas_entity_label
  - module: cloudera.services.atlas_entity_business_metadata
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Create an entity of a custom type
  cloudera.services.atlas_entity:
    type_name: acme_dataset
    qualified_name: sales_2026@cluster1
    attributes:
      name: Sales 2026
      rowCount: 1200

- name: Change one attribute, leaving the others as they are
  cloudera.services.atlas_entity:
    type_name: acme_dataset
    qualified_name: sales_2026@cluster1
    attributes:
      rowCount: 1500

- name: Set custom attributes
  cloudera.services.atlas_entity:
    type_name: acme_dataset
    qualified_name: sales_2026@cluster1
    custom_attributes:
      steward: jane

- name: Identify the entity by several unique attributes
  cloudera.services.atlas_entity:
    type_name: acme_partition
    unique_attributes:
      qualifiedName: sales_2026.q1@cluster1
      partitionKey: q1
    attributes:
      name: Q1

- name: Delete an entity
  cloudera.services.atlas_entity:
    type_name: acme_dataset
    qualified_name: sales_2026@cluster1
    state: absent

- name: Delete an entity by its GUID
  cloudera.services.atlas_entity:
    guid: fc0fd256-be16-4775-99ad-9e0b7e304ae5
    state: absent
"""

RETURN = r"""
entity:
  description:
    - The entity after the module ran, as Atlas reports it.
    - With O(ignore:check_mode=true) this is the entity as it would be, without a GUID for a new one.
    - After a delete it is the deleted entity, with the status V(DELETED).
    - Empty when O(state=absent) and there was no entity.
  type: dict
  returned: always
  contains:
    guid:
      description: GUID of the entity.
      type: str
    type_name:
      description: Name of the entity type.
      type: str
    status:
      description: Status of the entity, V(ACTIVE) or V(DELETED).
      type: str
    attributes:
      description: Attribute values of the entity, with the attribute names as Atlas defines them.
      type: dict
      sample:
        qualifiedName: sales_2026@cluster1
    custom_attributes:
      description: Custom attribute values of the entity.
      type: dict
    labels:
      description: Labels of the entity, when it has any.
      type: list
      elements: str
    classifications:
      description: Classifications of the entity, when it has any.
      type: list
      elements: dict
deleted_guids:
  description:
    - GUIDs of the entities the module deleted.
    - Holds more than the GUID of the entity when Atlas deleted the entities it owns as well.
  type: list
  elements: str
  returned: always
"""

from dataclasses import replace
from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesError,
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasTypeDefClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasEntity,
    AtlasEntityClient,
    entity_attribute_defs,
    normalize_attributes,
)


class AtlasEntityModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                type_name=dict(type="str", required=False),
                qualified_name=dict(type="str", required=False),
                unique_attributes=dict(type="dict", required=False),
                attributes=dict(type="dict", required=False),
                custom_attributes=dict(type="dict", required=False),
                allow_service_types=dict(type="bool", default=False),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            mutually_exclusive=[
                ["guid", "type_name"],
                ["guid", "qualified_name"],
                ["guid", "unique_attributes"],
                ["qualified_name", "unique_attributes"],
            ],
            required_one_of=[["guid", "type_name"]],
            required_by={
                "qualified_name": ["type_name"],
                "unique_attributes": ["type_name"],
            },
            supports_check_mode=True,
        )

        self.guid: Optional[str] = self.get_param("guid")
        self.type_name: Optional[str] = self.get_param("type_name")
        self.qualified_name: Optional[str] = self.get_param("qualified_name")
        self.unique_attributes: Optional[Dict[str, Any]] = self.get_param(
            "unique_attributes",
        )
        self.attributes: Optional[Dict[str, Any]] = self.get_param("attributes")
        self.custom_attributes: Optional[Dict[str, Any]] = self.get_param(
            "custom_attributes",
        )
        self.allow_service_types: bool = self.get_param("allow_service_types")
        self.state: str = self.get_param("state")

        self.changed = False
        self.diff: Dict[str, Any] = {}
        self.result_entity: Optional[AtlasEntity] = None
        self.result_deleted_guids: List[str] = []

    def process(self) -> None:
        if self.state == "present" and self.guid:
            self.module.fail_json(
                msg="'guid' can only be used with state 'absent'; to create or update an entity, specify 'type_name' with 'qualified_name' or 'unique_attributes'.",
            )

        if self.state == "absent" and (
            self.attributes is not None or self.custom_attributes is not None
        ):
            self.module.fail_json(
                msg="'attributes' and 'custom_attributes' cannot be used with state 'absent'.",
            )

        identity = self._identity()

        client = AtlasEntityClient(self.api_client)

        if self.state == "present":
            self._present(client, str(self.type_name), identity)
        else:
            self._absent(client, identity)

    def _identity(self) -> Dict[str, Any]:
        if self.guid:
            return {}

        identity = self.unique_attributes or (
            {"qualifiedName": self.qualified_name} if self.qualified_name else None
        )
        if not identity:
            self.module.fail_json(
                msg="Specify 'qualified_name' or 'unique_attributes' with 'type_name'.",
            )

        return identity

    def _refuse_service_type(
        self,
        typedef_client: AtlasTypeDefClient,
        type_name: str,
    ) -> None:
        entity_def = typedef_client.get_entity_def_by_name(type_name)
        if entity_def is None:
            return

        service_type = entity_def.service_type
        if (
            isinstance(service_type, str)
            and service_type
            and not self.allow_service_types
        ):
            self.module.fail_json(
                msg=f"Entity type '{type_name}' is owned by the service '{service_type}', whose hooks maintain its entities. Set 'allow_service_types' to manage them directly.",
            )

    def _present(
        self,
        client: AtlasEntityClient,
        type_name: str,
        identity: Dict[str, Any],
    ) -> None:
        typedef_client = AtlasTypeDefClient(self.api_client)

        if typedef_client.get_entity_def_by_name(type_name) is None:
            self.module.fail_json(msg=f"Entity type '{type_name}' does not exist.")
        self._refuse_service_type(typedef_client, type_name)

        attribute_defs = entity_attribute_defs(typedef_client, type_name)

        requested = dict(self.attributes or {})
        for name, value in identity.items():
            if name in requested and requested[name] != value:
                self.module.fail_json(
                    msg=f"Attribute '{name}' differs from the unique attribute '{name}' that identifies the entity.",
                )

        desired = normalize_attributes(
            "Entity type",
            type_name,
            attribute_defs,
            {**requested, **identity},
            null_hint="; Atlas cannot clear an attribute, so leave it out",
        )

        custom = dict(self.custom_attributes or {})
        for name, value in custom.items():
            if not isinstance(value, str):
                self.module.fail_json(
                    msg=f"Custom attribute '{name}' must be a string, not {value!r}.",
                )

        entity = client.get_entity_by_unique_attributes(type_name, identity)

        if entity is None or entity.status != "ACTIVE":
            self._create(client, type_name, desired, custom)
        else:
            self._update(client, type_name, identity, entity, desired, custom)

    def _create(
        self,
        client: AtlasEntityClient,
        type_name: str,
        desired: Dict[str, Any],
        custom: Dict[str, str],
    ) -> None:
        new = AtlasEntity(type_name=type_name, attributes=desired)
        if custom:
            new.custom_attributes = custom

        self.changed = True

        if self.module._diff:
            after: Dict[str, Any] = {"attributes": desired}
            if custom:
                after["custom_attributes"] = custom
            self.diff = {"before": {"entity": {}}, "after": {"entity": after}}

        if self.module.check_mode:
            self.result_entity = replace(new, status="ACTIVE")
            return

        created = client.create_entity(new)
        self._require_status(created, "ACTIVE", "creation")
        self.result_entity = created

    def _update(
        self,
        client: AtlasEntityClient,
        type_name: str,
        identity: Dict[str, Any],
        current: AtlasEntity,
        desired: Dict[str, Any],
        custom: Dict[str, str],
    ) -> None:
        existing: Dict[str, Any] = (
            current.attributes if isinstance(current.attributes, dict) else {}
        )
        existing_custom: Dict[str, str] = (
            current.custom_attributes
            if isinstance(current.custom_attributes, dict)
            else {}
        )

        delta = {
            name: value
            for name, value in desired.items()
            if name not in identity
            and (name not in existing or existing[name] != value)
        }
        custom_delta = {
            name: value
            for name, value in custom.items()
            if name not in existing_custom or existing_custom[name] != value
        }

        if not delta and not custom_delta:
            self.result_entity = current
            return

        self.changed = True

        if self.module._diff:
            before: Dict[str, Any] = {}
            after: Dict[str, Any] = {}
            if delta:
                before["attributes"] = {
                    name: existing[name] for name in delta if name in existing
                }
                after["attributes"] = delta
            if custom_delta:
                before["custom_attributes"] = {
                    name: existing_custom[name]
                    for name in custom_delta
                    if name in existing_custom
                }
                after["custom_attributes"] = custom_delta
            self.diff = {"before": {"entity": before}, "after": {"entity": after}}

        # Atlas may replace the whole custom attribute map, so send the kept ones too.
        merged_custom = {**existing_custom, **custom_delta}

        if self.module.check_mode:
            self.result_entity = replace(
                current,
                attributes={**existing, **delta},
                custom_attributes=(
                    merged_custom if custom_delta else current.custom_attributes
                ),
            )
            return

        update = AtlasEntity(type_name=type_name)
        if delta:
            update.attributes = delta
        if custom_delta:
            update.custom_attributes = merged_custom

        client.update_entity_by_unique_attributes(type_name, identity, update)

        updated = client.get_entity_by_guid(str(current.guid))
        if updated is None:
            raise ServicesError(
                f"Atlas does not report entity '{current.guid}' as ACTIVE after the update",
            )
        self._require_status(updated, "ACTIVE", "update")
        self.result_entity = updated

    def _absent(self, client: AtlasEntityClient, identity: Dict[str, Any]) -> None:
        if self.guid:
            entity = client.get_entity_by_guid(self.guid)
        else:
            entity = client.get_entity_by_unique_attributes(
                str(self.type_name),
                identity,
            )

        if entity is None or entity.status != "ACTIVE":
            # No entity, or one that is already deleted
            return

        self._refuse_service_type(
            AtlasTypeDefClient(self.api_client),
            entity.type_name,
        )

        guid = str(entity.guid)

        self.changed = True

        if self.module._diff:
            self.diff = {
                "before": {
                    "entity": {
                        "guid": guid,
                        "type_name": entity.type_name,
                        "attributes": (
                            entity.attributes
                            if isinstance(entity.attributes, dict)
                            else {}
                        ),
                    },
                },
                "after": {"entity": {}},
            }

        if self.module.check_mode:
            self.result_entity = replace(entity, status="DELETED")
            self.result_deleted_guids = [guid]
            return

        deleted = client.delete_entity_by_guid(guid)

        # A hard-delete configuration removes the entity entirely, so a missing one is deleted too.
        remaining = client.get_entity_by_guid(guid)
        if remaining is not None:
            self._require_status(remaining, "DELETED", "delete")

        self.result_entity = remaining or replace(entity, status="DELETED")
        self.result_deleted_guids = deleted or [guid]

    @staticmethod
    def _require_status(entity: AtlasEntity, status: str, action: str) -> None:
        if entity.status != status:
            raise ServicesError(
                f"Atlas reports entity '{entity.guid}' as {entity.status}, not {status}, after the {action}",
            )


def main():
    result = AtlasEntityModule()

    entity: Dict[str, Any] = (
        to_dict(result.result_entity) if result.result_entity else {}
    )

    output: Dict[str, Any] = dict(
        changed=result.changed,
        entity=entity,
        deleted_guids=result.result_deleted_guids,
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
