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
module: atlas_glossary
short_description: Manage glossaries in Apache Atlas
description:
  - Create, update, and delete a glossary in Apache Atlas.
  - The module owns the glossary itself (name and descriptive fields). Categories and terms have their own modules.
  - Only the fields named in the task are managed; the others are left as they are.
  - Deleting a glossary also deletes every term and category in it, so the module refuses to do so unless O(cascade=true).
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.2.0"
options:
  guid:
    description:
      - GUID of the glossary.
      - Identifies an existing glossary, which lets O(name) change. Mutually exclusive with O(qualified_name).
      - The module fails under O(state=present) when no glossary has this GUID, rather than creating one.
    type: str
  name:
    description:
      - Name of the glossary.
      - With neither O(guid) nor O(qualified_name), the name identifies the glossary. Several glossaries can share a name, and the module then fails and asks for O(qualified_name) or O(guid).
      - With O(guid) or O(qualified_name), the name is the value to set, so this is how a glossary is renamed.
      - Required to create a glossary. A name may not contain C(@), C(.), C(<) or C(>).
    type: str
  qualified_name:
    description:
      - Unique qualified name of the glossary.
      - Identifies an existing glossary, and is the qualified name given to a new one. Atlas sets it to O(name) when omitted, and it cannot change afterwards.
      - Mutually exclusive with O(guid).
    type: str
  short_description:
    description:
      - Short description of the glossary.
      - An empty string clears it.
    type: str
  long_description:
    description:
      - Long description of the glossary.
      - An empty string clears it.
    type: str
  language:
    description:
      - Language of the glossary.
      - An empty string clears it.
    type: str
  usage:
    description:
      - Usage notes of the glossary.
      - An empty string clears it.
    type: str
  state:
    description:
      - The desired state of the glossary.
      - O(state=absent) cannot be combined with the descriptive options.
    type: str
    default: present
    choices:
      - present
      - absent
  cascade:
    description:
      - Allow O(state=absent) to delete a glossary that still holds terms or categories, together with them.
      - Atlas refuses the delete, and so does the module, while any term in the glossary is assigned to an entity.
      - Only valid with O(state=absent).
    type: bool
    default: false
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    description:
      - The module reports what it would do without writing, including the refusal to delete a glossary with content.
    support: full
  diff_mode:
    description:
      - The diff shows the fields the task manages; for a delete, the terms and categories that go with the glossary.
    support: full
seealso:
  - module: cloudera.services.atlas_glossary_info
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Create a glossary
  cloudera.services.atlas_glossary:
    name: Banking
    short_description: Terms used by the banking business

- name: Create a glossary with its own qualified name
  cloudera.services.atlas_glossary:
    name: Banking
    qualified_name: banking_emea
    language: English

- name: Change the descriptions of a glossary
  cloudera.services.atlas_glossary:
    name: Banking
    long_description: The terms the banking business uses to talk about its customers and accounts

- name: Clear the usage notes
  cloudera.services.atlas_glossary:
    name: Banking
    usage: ""

- name: Rename a glossary, identified by its qualified name
  cloudera.services.atlas_glossary:
    qualified_name: banking_emea
    name: Retail banking

- name: Delete an empty glossary
  cloudera.services.atlas_glossary:
    name: Banking
    state: absent

- name: Delete a glossary together with its terms and categories
  cloudera.services.atlas_glossary:
    name: Banking
    state: absent
    cascade: true
"""

RETURN = r"""
glossary:
  description:
    - The glossary as Atlas stores it after the task.
    - Empty after O(state=absent).
    - In check mode, the glossary as it would be, without a GUID for a new one.
  type: dict
  returned: always
  contains:
    guid:
      description: Atlas-assigned identifier.
      type: str
    name:
      description: Name of the glossary.
      type: str
    qualified_name:
      description: Unique qualified name of the glossary.
      type: str
    short_description:
      description: Short description of the glossary.
      type: str
    long_description:
      description: Long description of the glossary.
      type: str
    language:
      description: Language of the glossary.
      type: str
    usage:
      description: Usage notes of the glossary.
      type: str
    additional_attributes:
      description: User-defined attributes, keyed by the names Atlas uses.
      type: dict
    terms:
      description: Headers of the terms in the glossary.
      type: list
      elements: dict
    categories:
      description: Headers of the categories in the glossary.
      type: list
      elements: dict
"""

from dataclasses import replace
from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesError,
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryClient,
    validate_glossary_name,
)

_DESCRIPTIVE_FIELDS = ("short_description", "long_description", "language", "usage")


def _count(number: int, singular: str, plural: str) -> str:
    return f"{number} {singular if number == 1 else plural}"


def _plain(value: Any) -> Any:
    """The value of a glossary field, with an unset field as None."""
    return None if value is NULLABLE else value


class AtlasGlossaryModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                name=dict(type="str", required=False),
                qualified_name=dict(type="str", required=False),
                short_description=dict(type="str", required=False),
                long_description=dict(type="str", required=False),
                language=dict(type="str", required=False),
                usage=dict(type="str", required=False),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
                cascade=dict(type="bool", default=False),
            ),
            mutually_exclusive=[["guid", "qualified_name"]],
            required_one_of=[["guid", "name", "qualified_name"]],
            supports_check_mode=True,
        )

        self.guid: Optional[str] = self.get_param("guid")
        self.name: Optional[str] = self.get_param("name")
        self.qualified_name: Optional[str] = self.get_param("qualified_name")
        self.descriptive: Dict[str, str] = {
            field: self.get_param(field)
            for field in _DESCRIPTIVE_FIELDS
            if self.get_param(field) is not None
        }
        self.state: str = self.get_param("state")
        self.cascade: bool = self.get_param("cascade")

        self.changed = False
        self.diff: Dict[str, Any] = {}
        self.glossary: Dict[str, Any] = {}

    def process(self) -> None:
        if self.state == "absent" and self.descriptive:
            raise ServicesError(
                f"{', '.join(self.descriptive)} cannot be used with state 'absent'.",
            )
        if self.state == "present" and self.cascade:
            raise ServicesError("'cascade' can only be used with state 'absent'.")
        if self.state == "present" and self.name is not None:
            validate_glossary_name("glossary", self.name)

        client = AtlasGlossaryClient(self.api_client)
        existing = self._find(client)

        if self.state == "present":
            self._present(client, existing)
        else:
            self._absent(client, existing)

    def _find(self, client: AtlasGlossaryClient) -> Optional[AtlasGlossary]:
        if self.guid:
            return client.get_glossary(self.guid)

        if self.qualified_name:
            matches = client.find_glossaries(qualified_name=self.qualified_name)
        else:
            matches = client.find_glossaries(name=self.name)

        if len(matches) > 1:
            raise ServicesError(
                f"More than one glossary is named '{self.name}'; "
                "identify it with 'qualified_name' or 'guid'.",
            )

        return matches[0] if matches else None

    def _present(
        self,
        client: AtlasGlossaryClient,
        existing: Optional[AtlasGlossary],
    ) -> None:
        if existing is None:
            self._create(client)
        else:
            self._update(client, existing)

    def _create(self, client: AtlasGlossaryClient) -> None:
        if self.guid:
            raise ServicesError(f"No glossary with guid '{self.guid}' exists.")
        if not self.name:
            raise ServicesError("'name' is required to create a glossary.")

        fields: Dict[str, Any] = {"name": self.name, **self.descriptive}
        if self.qualified_name:
            fields["qualified_name"] = self.qualified_name
        new = AtlasGlossary(**fields)

        self.changed = True
        if self.module._diff:
            self.diff = {"before": {}, "after": {"glossary": fields}}

        if self.module.check_mode:
            self.glossary = to_dict(new)
            return

        created = client.create_glossary(new)
        self.glossary = to_dict(self._read_back(client, str(created.guid)))

    def _update(self, client: AtlasGlossaryClient, existing: AtlasGlossary) -> None:
        managed: Dict[str, Any] = dict(self.descriptive)
        if self.name is not None:
            managed["name"] = self.name

        delta = {
            field: value
            for field, value in managed.items()
            if (_plain(getattr(existing, field)) or "") != value
        }

        if not delta:
            self.glossary = to_dict(existing)
            return

        self.changed = True
        if self.module._diff:
            self.diff = {
                "before": {
                    "glossary": {
                        field: _plain(getattr(existing, field)) for field in delta
                    },
                },
                "after": {"glossary": dict(delta)},
            }

        if self.module.check_mode:
            self.glossary = to_dict(replace(existing, **delta))
            return

        client.partial_update_glossary(str(existing.guid), delta)
        self.glossary = to_dict(self._read_back(client, str(existing.guid)))

    def _absent(
        self,
        client: AtlasGlossaryClient,
        existing: Optional[AtlasGlossary],
    ) -> None:
        if existing is None:
            return

        terms = existing.terms if isinstance(existing.terms, list) else []
        categories = (
            existing.categories if isinstance(existing.categories, list) else []
        )

        if (terms or categories) and not self.cascade:
            raise ServicesError(
                f"Glossary '{existing.name}' still holds "
                f"{_count(len(terms), 'term', 'terms')} and "
                f"{_count(len(categories), 'category', 'categories')}; "
                "set 'cascade' to true to delete them with it.",
            )

        if terms:
            assigned = [
                term.name
                for term in client.list_terms(str(existing.guid))
                if any(
                    entity.relationship_status != "DELETED"
                    for entity in (
                        term.assigned_entities
                        if isinstance(term.assigned_entities, list)
                        else []
                    )
                )
            ]
            if assigned:
                raise ServicesError(
                    f"Glossary '{existing.name}' cannot be deleted while terms are "
                    f"assigned to entities: {', '.join(assigned)}. Unassign them first.",
                )

        self.changed = True
        if self.module._diff:
            before: Dict[str, Any] = {"name": existing.name}
            if terms:
                before["terms"] = [header.display_text for header in terms]
            if categories:
                before["categories"] = [header.display_text for header in categories]
            self.diff = {"before": {"glossary": before}, "after": {}}

        if self.module.check_mode:
            return

        client.delete_glossary(str(existing.guid))
        if client.get_glossary(str(existing.guid)) is not None:
            raise ServicesError(
                f"Glossary '{existing.name}' still exists after the delete.",
            )

    @staticmethod
    def _read_back(client: AtlasGlossaryClient, guid: str) -> AtlasGlossary:
        glossary = client.get_glossary(guid)
        if glossary is None:
            raise ServicesError(
                f"Glossary '{guid}' was written but could not be read back.",
            )
        return glossary


def main():
    result = AtlasGlossaryModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        glossary=result.glossary,
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
