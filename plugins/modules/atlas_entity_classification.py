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
module: atlas_entity_classification
short_description: Manage a classification on an Apache Atlas entity
description:
  - Attach a classification to, update it on, or remove it from an existing entity in Apache Atlas, such as a Hive table registered by a hook.
  - Identify the entity either by its GUID or by its type name and unique attributes, usually its C(qualifiedName).
  - The entity itself is not created or changed; it must already exist.
  - The classification must already be defined, for example with M(cloudera.services.atlas_classification_def).
  - Only a classification attached directly to the entity is managed. A classification that reaches the entity only by propagation from another entity is ignored.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.2.0"
options:
  guid:
    description:
      - GUID of the entity.
      - Mutually exclusive with O(type_name), O(qualified_name), and O(unique_attributes).
    type: str
  type_name:
    description:
      - Name of the entity type, e.g. V(hive_table).
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
      - Requires O(type_name); mutually exclusive with O(qualified_name).
    type: dict
  name:
    description:
      - Name of the classification, as defined by its typedef.
    type: str
    required: true
  attributes:
    description:
      - Attribute names and values to set on the classification.
      - Not allowed with O(state=absent).
      - Every name must be an attribute of the classification typedef or of one of its super types. Atlas silently ignores unknown names, so the module fails on them instead.
      - Values are converted to the type the typedef declares, e.g. V("5") to V(5) for an C(int) attribute, so a repeated run reports no change.
      - Only the attributes listed here are managed. Other attributes of the classification are left as they are.
      - An attribute cannot be set to null. To drop it, remove the classification with O(state=absent) and attach it again without that attribute.
    type: dict
  propagate:
    description:
      - Whether the classification propagates to the entities derived from this one through lineage and relationships.
      - Not allowed with O(state=absent).
      - When not set, a new classification gets Atlas's default, which is V(true), and an attached one is left as it is.
    type: bool
  remove_propagations_on_entity_delete:
    description:
      - Whether the propagated copies of the classification are removed when the entity is deleted.
      - Not allowed with O(state=absent).
      - When not set, a new classification gets Atlas's default, which is V(false), and an attached one is left as it is.
    type: bool
  state:
    description:
      - V(present) makes sure the classification is attached to the entity with the given values.
      - V(absent) removes the classification from the entity, with all of its attributes. An entity that does not exist, or is deleted, has nothing to remove and is not an error.
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
  - Validity periods of an attached classification are kept as they are but cannot be set by this module.
  - Atlas merges the attributes given into an attached classification, so a single attribute cannot be removed; V(absent) always removes the whole classification.
  - A classification propagated to the entity cannot be removed from that entity; remove it from the entity it comes from, or stop its propagation there.
  - With O(state=present) the entity must exist and be active; an entity registered asynchronously by a hook may need L(until,https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_loops.html) retries.
seealso:
  - module: cloudera.services.atlas_classification_def
  - module: cloudera.services.atlas_entity_info
  - module: cloudera.services.atlas_entity_label
  - module: cloudera.services.atlas_entity_business_metadata
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Attach a classification to a table
  cloudera.services.atlas_entity_classification:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: PII

- name: Attach a classification with an attribute, without propagation
  cloudera.services.atlas_entity_classification:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: sensitivity
    attributes:
      level: high
    propagate: false

- name: Attach a classification to an entity by its GUID
  cloudera.services.atlas_entity_classification:
    guid: fc0fd256-be16-4775-99ad-9e0b7e304ae5
    name: PII

- name: Change one attribute, leaving the others as they are
  cloudera.services.atlas_entity_classification:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: sensitivity
    attributes:
      level: low

- name: Remove a classification from a table
  cloudera.services.atlas_entity_classification:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: PII
    state: absent

- name: Classify a table as soon as a hook registers it
  cloudera.services.atlas_entity_classification:
    type_name: hive_table
    qualified_name: default.sales@cluster1
    name: PII
  register: classified
  until: classified is succeeded
  retries: 12
  delay: 10
"""

RETURN = r"""
classification:
  description:
    - The classification attached to the entity after the module ran, as Atlas reports it.
    - With O(ignore:check_mode=true) this is the classification the entity would have.
    - Empty when the entity does not exist or the classification was removed.
  type: dict
  returned: always
  contains:
    type_name:
      description: Name of the classification.
      type: str
      sample: sensitivity
    attributes:
      description: Attribute values of the classification, with the attribute names as Atlas defines them.
      type: dict
      sample:
        level: high
    propagate:
      description: Whether the classification propagates.
      type: bool
    remove_propagations_on_entity_delete:
      description: Whether the propagated copies are removed when the entity is deleted.
      type: bool
    validity_periods:
      description: Time ranges in which the classification applies.
      type: list
      elements: dict
    entity_guid:
      description: GUID of the entity the classification is attached to.
      type: str
    entity_status:
      description: Status of that entity.
      type: str
guid:
  description:
    - GUID of the entity.
    - V(null) when the entity does not exist and O(state=absent).
  type: str
  returned: always
"""

from dataclasses import replace
from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesError,
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasTypeDefClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_entity import (
    AtlasClassification,
    AtlasEntity,
    AtlasEntityClient,
    classification_attribute_defs,
    normalize_attributes,
)


class AtlasEntityClassificationModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                type_name=dict(type="str", required=False),
                qualified_name=dict(type="str", required=False),
                unique_attributes=dict(type="dict", required=False),
                name=dict(type="str", required=True),
                attributes=dict(type="dict", required=False),
                propagate=dict(type="bool", required=False),
                remove_propagations_on_entity_delete=dict(type="bool", required=False),
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
        self.name: str = self.get_param("name")
        self.attributes: Optional[Dict[str, Any]] = self.get_param("attributes")
        self.propagate: Optional[bool] = self.get_param("propagate")
        self.remove_propagations: Optional[bool] = self.get_param(
            "remove_propagations_on_entity_delete",
        )
        self.state: str = self.get_param("state")

        self.changed = False
        self.diff: Dict[str, Any] = {}
        self.result_guid: Optional[str] = None
        self.result_classification: Optional[AtlasClassification] = None

    def process(self) -> None:
        if self.state == "absent" and (
            self.attributes is not None
            or self.propagate is not None
            or self.remove_propagations is not None
        ):
            self.module.fail_json(
                msg="'attributes', 'propagate' and 'remove_propagations_on_entity_delete' cannot be used with state 'absent'; Atlas can only remove the whole classification.",
            )

        client = AtlasEntityClient(self.api_client)

        entity = self._find_entity(client)

        if entity is None or entity.status != "ACTIVE":
            if self.state == "present":
                self.module.fail_json(
                    msg="A classification can only be attached to an active entity, but the entity was not found or is deleted.",
                )
            # Entity is inactive or deleted and state is absent
            return

        guid = str(entity.guid)
        self.result_guid = guid
        current = self._attached(entity)

        if self.state == "absent":
            self._remove(client, guid, current)
        else:
            self._set(client, guid, current)

    def _remove(
        self,
        client: AtlasEntityClient,
        guid: str,
        current: Optional[AtlasClassification],
    ) -> None:
        if current is None:
            return

        self.changed = True

        if self.module._diff:
            self.diff = {
                "before": {"classification": {self.name: self._summary(current)}},
                "after": {"classification": {}},
            }

        if not self.module.check_mode:
            client.remove_entity_classification(guid, self.name)

    def _set(
        self,
        client: AtlasEntityClient,
        guid: str,
        current: Optional[AtlasClassification],
    ) -> None:
        attribute_defs = classification_attribute_defs(
            AtlasTypeDefClient(self.api_client),
            self.name,
        )
        if attribute_defs is None:
            self.module.fail_json(msg=f"Classification '{self.name}' does not exist.")

        desired = normalize_attributes(
            "Classification",
            self.name,
            attribute_defs,
            self.attributes or {},
        )

        if current is None:
            self._attach(client, guid, desired)
        else:
            self._update(client, guid, current, desired)

    def _attach(
        self,
        client: AtlasEntityClient,
        guid: str,
        desired: Dict[str, Any],
    ) -> None:
        requested: Dict[str, Any] = {}
        if desired:
            requested["attributes"] = desired
        if self.propagate is not None:
            requested["propagate"] = self.propagate
        if self.remove_propagations is not None:
            requested["remove_propagations_on_entity_delete"] = self.remove_propagations

        self.changed = True

        if self.module._diff:
            self.diff = {
                "before": {"classification": {}},
                "after": {"classification": {self.name: requested}},
            }

        if self.module.check_mode:
            self.result_classification = AtlasClassification(
                type_name=self.name,
                attributes=desired,
                propagate=True if self.propagate is None else self.propagate,
                remove_propagations_on_entity_delete=(
                    False
                    if self.remove_propagations is None
                    else self.remove_propagations
                ),
                entity_guid=guid,
                entity_status="ACTIVE",
            )
            return

        client.add_entity_classifications(
            guid,
            [AtlasClassification(type_name=self.name, **requested)],
        )
        self.result_classification = self._read_back(client, guid)

    def _update(
        self,
        client: AtlasEntityClient,
        guid: str,
        current: AtlasClassification,
        desired: Dict[str, Any],
    ) -> None:
        existing = self._set_attributes(current)
        changed_attributes = {
            attribute: value
            for attribute, value in desired.items()
            if attribute not in existing or existing[attribute] != value
        }

        propagate = self._flag(current.propagate)
        remove_propagations = self._flag(current.remove_propagations_on_entity_delete)

        before: Dict[str, Any] = {}
        after: Dict[str, Any] = {}
        if changed_attributes:
            before["attributes"] = {
                attribute: existing[attribute]
                for attribute in changed_attributes
                if attribute in existing
            }
            after["attributes"] = changed_attributes
        if self.propagate is not None and self.propagate != propagate:
            before["propagate"] = propagate
            after["propagate"] = self.propagate
            propagate = self.propagate
        if (
            self.remove_propagations is not None
            and self.remove_propagations != remove_propagations
        ):
            before["remove_propagations_on_entity_delete"] = remove_propagations
            after["remove_propagations_on_entity_delete"] = self.remove_propagations
            remove_propagations = self.remove_propagations

        if not after:
            self.result_classification = current
            return

        self.changed = True

        if self.module._diff:
            self.diff = {
                "before": {"classification": {self.name: before}},
                "after": {"classification": {self.name: after}},
            }

        merged = {**existing, **changed_attributes}

        if self.module.check_mode:
            self.result_classification = replace(
                current,
                attributes=merged,
                propagate=propagate,
                remove_propagations_on_entity_delete=remove_propagations,
            )
            return

        # Atlas merges attributes but not the other fields, so send the current values
        # of the ones that are not being changed.
        fields: Dict[str, Any] = {}
        if merged:
            fields["attributes"] = merged
        if propagate is not NULLABLE:
            fields["propagate"] = propagate
        if remove_propagations is not NULLABLE:
            fields["remove_propagations_on_entity_delete"] = remove_propagations
        if isinstance(current.validity_periods, list):
            fields["validity_periods"] = current.validity_periods

        client.update_entity_classifications(
            guid,
            [AtlasClassification(type_name=self.name, **fields)],
        )
        self.result_classification = self._read_back(client, guid)

    def _read_back(
        self,
        client: AtlasEntityClient,
        guid: str,
    ) -> AtlasClassification:
        entity = client.get_entity_by_guid(guid)
        written = self._attached(entity) if entity is not None else None
        if written is None:
            raise ServicesError(
                f"Atlas did not report classification '{self.name}' on the entity after the write",
            )
        return written

    def _attached(self, entity: AtlasEntity) -> Optional[AtlasClassification]:
        """The named classification attached directly to the entity, not one propagated to it."""
        classifications = (
            entity.classifications if isinstance(entity.classifications, list) else []
        )
        for classification in classifications:
            origin = classification.entity_guid
            propagated = (
                isinstance(origin, str) and origin != "" and origin != entity.guid
            )
            if classification.type_name == self.name and not propagated:
                return classification
        return None

    @staticmethod
    def _set_attributes(classification: AtlasClassification) -> Dict[str, Any]:
        """The attributes Atlas reports with a value; it also reports the unset ones as null."""
        attributes = classification.attributes
        if not isinstance(attributes, dict):
            return {}
        return {name: value for name, value in attributes.items() if value is not None}

    @staticmethod
    def _flag(value: Any) -> Any:
        return value if isinstance(value, bool) else NULLABLE

    def _summary(self, classification: AtlasClassification) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "attributes": self._set_attributes(classification),
        }
        for field in ("propagate", "remove_propagations_on_entity_delete"):
            value = getattr(classification, field)
            if isinstance(value, bool):
                summary[field] = value
        return summary

    def _find_entity(self, client: AtlasEntityClient) -> Optional[AtlasEntity]:
        if self.guid:
            return client.get_entity_by_guid(self.guid)

        unique_attributes = self.unique_attributes or (
            {"qualifiedName": self.qualified_name} if self.qualified_name else None
        )
        if not unique_attributes:
            self.module.fail_json(
                msg="Specify 'qualified_name' or 'unique_attributes' with 'type_name'.",
            )

        return client.get_entity_by_unique_attributes(
            str(self.type_name),
            unique_attributes,
        )


def main():
    result = AtlasEntityClassificationModule()

    classification: Dict[str, Any] = (
        to_dict(result.result_classification) if result.result_classification else {}
    )

    output: Dict[str, Any] = dict(
        changed=result.changed,
        guid=result.result_guid,
        classification=classification,
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
