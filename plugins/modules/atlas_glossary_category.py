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
module: atlas_glossary_category
short_description: Manage glossary categories in Apache Atlas
description:
  - Create, update, move, and delete a category in an Apache Atlas glossary.
  - The module owns the category itself (name, descriptions, and parent). The terms in a category are managed on the term.
  - Only the fields named in the task are managed; the others, including the category's terms and children, are left as they are.
  - Deleting a category moves its child categories up to the deleted category's parent, or to the top level when it has none. With O(cascade=true) the child categories, and everything below them, are deleted instead.
  - Deleting a category never deletes its terms; they only lose the category.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.2.0"
options:
  guid:
    description:
      - GUID of the category.
      - Identifies an existing category, which lets O(name) change. Mutually exclusive with O(glossary), O(glossary_qualified_name), and O(glossary_guid).
      - The module fails under O(state=present) when no category has this GUID, rather than creating one.
    type: str
  name:
    description:
      - Name of the category.
      - Without O(guid), the name identifies the category within the glossary. The same name can exist under several parents, and the module then fails and asks for O(guid).
      - With O(guid), the name is the value to set, so this is how a category is renamed.
      - Required to create a category. A name may not contain C(@), C(.), C(<) or C(>).
    type: str
  glossary:
    description:
      - Name of the glossary that holds the category.
      - Fails if more than one glossary has this name; use O(glossary_guid) or O(glossary_qualified_name) instead.
      - Mutually exclusive with O(glossary_qualified_name) and O(glossary_guid).
      - The module fails under O(state=present) when the glossary does not exist. Under O(state=absent) there is nothing to delete.
    type: str
  glossary_qualified_name:
    description:
      - Qualified name of the glossary that holds the category.
      - Mutually exclusive with O(glossary) and O(glossary_guid).
    type: str
  glossary_guid:
    description:
      - GUID of the glossary that holds the category.
      - Mutually exclusive with O(glossary) and O(glossary_qualified_name).
    type: str
  short_description:
    description:
      - Short description of the category.
      - An empty string clears it.
    type: str
  long_description:
    description:
      - Long description of the category.
      - An empty string clears it.
    type: str
  parent_category:
    description:
      - Name of the category that should be the parent, looked up in the same glossary.
      - An empty string makes the category a top-level one. Omit it to leave the parent as it is.
      - Fails if the name matches several categories; use O(parent_category_guid) instead.
      - The parent must be in the same glossary and cannot be the category or one of its descendants.
      - Mutually exclusive with O(parent_category_guid).
      - Moving a category removes the old parent relationship and then adds the new one, which is not atomic.
    type: str
  parent_category_guid:
    description:
      - GUID of the category that should be the parent.
      - An empty string makes the category a top-level one.
      - Mutually exclusive with O(parent_category).
    type: str
  state:
    description:
      - The desired state of the category.
      - O(state=absent) cannot be combined with the descriptive or parent options.
    type: str
    default: present
    choices:
      - present
      - absent
  cascade:
    description:
      - Delete the category together with all categories below it, instead of moving them up.
      - Descendants are deleted one at a time, deepest first, so a failure part-way leaves the rest in place.
      - Only valid with O(state=absent).
    type: bool
    default: false
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    description:
      - The module reports what it would do without writing.
    support: full
  diff_mode:
    description:
      - The diff shows the fields the task manages; for a delete, the child categories that move up, or with O(cascade) the categories that go with it.
    support: full
seealso:
  - module: cloudera.services.atlas_glossary
  - module: cloudera.services.atlas_glossary_category_info
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Create a top-level category
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Loans
    short_description: Lending products

- name: Create a category below another one
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Customer
    parent_category: Loans

- name: Change the descriptions of a category
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Customer
    long_description: The people and organizations that borrow from the bank

- name: Clear the short description
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Customer
    short_description: ""

- name: Rename a category, identified by its GUID
  cloudera.services.atlas_glossary_category:
    guid: 5b292b6f-0983-4e43-8508-7115b9d9361d
    name: Client

- name: Move a category to another parent
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Client
    parent_category: Accounts

- name: Move a category to the top level
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Client
    parent_category: ""

- name: Delete a category (its children move to its parent, or the top level)
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Client
    state: absent

- name: Delete a category together with every category below it
  cloudera.services.atlas_glossary_category:
    glossary: Banking
    name: Loans
    state: absent
    cascade: true
"""

RETURN = r"""
category:
  description:
    - The category as Atlas stores it after the task.
    - Empty after O(state=absent).
    - In check mode, the category as it would be, without a GUID for a new one.
  type: dict
  returned: always
  contains:
    guid:
      description: Atlas-assigned identifier.
      type: str
    name:
      description: Name of the category.
      type: str
    qualified_name:
      description:
        - Qualified name of the category.
        - Atlas does not keep it current after a re-parent, so do not rely on it to find a category.
      type: str
    short_description:
      description: Short description of the category.
      type: str
    long_description:
      description: Long description of the category.
      type: str
    additional_attributes:
      description: User-defined attributes, keyed by the names Atlas uses.
      type: dict
    anchor:
      description: The glossary that holds the category.
      type: dict
      contains:
        glossary_guid:
          description: GUID of the glossary.
          type: str
        relation_guid:
          description: GUID of the relationship that anchors the category to the glossary.
          type: str
        display_text:
          description: Name of the glossary.
          type: str
    parent_category:
      description: The parent category, absent for a top-level category.
      type: dict
      contains:
        category_guid:
          description: GUID of the parent category.
          type: str
        relation_guid:
          description: GUID of the relationship between the parent and this category.
          type: str
        display_text:
          description: Name of the parent category.
          type: str
    children_categories:
      description: Headers of the categories directly below this one.
      type: list
      elements: dict
      contains:
        category_guid:
          description: GUID of the child category.
          type: str
        parent_category_guid:
          description: GUID of this category.
          type: str
        relation_guid:
          description: GUID of the relationship between this category and the child.
          type: str
        display_text:
          description: Name of the child category.
          type: str
    terms:
      description: Headers of the terms in the category.
      type: list
      elements: dict
      contains:
        term_guid:
          description: GUID of the term.
          type: str
        relation_guid:
          description: GUID of the relationship between the category and the term.
          type: str
        display_text:
          description: Name of the term.
          type: str
"""

from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesError,
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryClient,
    AtlasGlossaryHeader,
    AtlasRelatedCategoryHeader,
    validate_glossary_name,
)

_DESCRIPTIVE_FIELDS = ("short_description", "long_description")


def _plain(value: Any) -> Any:
    """The value of a category field, with an unset field as None."""
    return None if value is NULLABLE else value


class AtlasGlossaryCategoryModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                name=dict(type="str", required=False),
                glossary=dict(type="str", required=False),
                glossary_qualified_name=dict(type="str", required=False),
                glossary_guid=dict(type="str", required=False),
                short_description=dict(type="str", required=False),
                long_description=dict(type="str", required=False),
                parent_category=dict(type="str", required=False),
                parent_category_guid=dict(type="str", required=False),
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
                cascade=dict(type="bool", default=False),
            ),
            mutually_exclusive=[
                ["guid", "glossary"],
                ["guid", "glossary_qualified_name"],
                ["guid", "glossary_guid"],
                ["glossary", "glossary_qualified_name", "glossary_guid"],
                ["parent_category", "parent_category_guid"],
            ],
            required_one_of=[
                ["guid", "glossary", "glossary_qualified_name", "glossary_guid"],
            ],
            supports_check_mode=True,
        )

        self.guid: Optional[str] = self.get_param("guid")
        self.name: Optional[str] = self.get_param("name")
        self.glossary: Optional[str] = self.get_param("glossary")
        self.glossary_qualified_name: Optional[str] = self.get_param(
            "glossary_qualified_name",
        )
        self.glossary_guid: Optional[str] = self.get_param("glossary_guid")
        self.descriptive: Dict[str, str] = {
            field: self.get_param(field)
            for field in _DESCRIPTIVE_FIELDS
            if self.get_param(field) is not None
        }
        self.parent_category: Optional[str] = self.get_param("parent_category")
        self.parent_category_guid: Optional[str] = self.get_param(
            "parent_category_guid",
        )
        self.state: str = self.get_param("state")
        self.cascade: bool = self.get_param("cascade")

        self.changed = False
        self.diff: Dict[str, Any] = {}
        self.category: Dict[str, Any] = {}

    def process(self) -> None:
        if self.state == "absent":
            given = [
                *self.descriptive,
                *(
                    option
                    for option in ("parent_category", "parent_category_guid")
                    if self.get_param(option) is not None
                ),
            ]
            if given:
                raise ServicesError(
                    f"{', '.join(given)} cannot be used with state 'absent'.",
                )
        else:
            if self.cascade:
                raise ServicesError("'cascade' can only be used with state 'absent'.")
            if self.name is not None:
                validate_glossary_name("category", self.name)

        client = AtlasGlossaryClient(self.api_client)
        glossary = self._find_glossary(client)
        existing = self._find(client, glossary)

        if self.state == "absent":
            self._absent(client, existing)
        elif existing is None:
            self._create(client, glossary)
        else:
            self._update(client, existing)

    def _find_glossary(self, client: AtlasGlossaryClient) -> Optional[AtlasGlossary]:
        if self.guid:
            return None

        if self.glossary_guid:
            return client.get_glossary(self.glossary_guid)

        matches = client.find_glossaries(
            name=self.glossary,
            qualified_name=self.glossary_qualified_name,
        )
        if len(matches) > 1:
            raise ServicesError(
                f"More than one glossary is named '{self.glossary}'; "
                "identify it with 'glossary_qualified_name' or 'glossary_guid'.",
            )

        return matches[0] if matches else None

    def _find(
        self,
        client: AtlasGlossaryClient,
        glossary: Optional[AtlasGlossary],
    ) -> Optional[AtlasGlossaryCategory]:
        if self.guid:
            return client.get_category(self.guid)

        if glossary is None:
            if self.state == "present":
                raise ServicesError(f"No glossary '{self._glossary_label()}' exists.")
            return None

        if not self.name:
            raise ServicesError("'name' is required to identify a category.")

        matches = client.find_categories(str(glossary.guid), name=self.name)
        if len(matches) > 1:
            raise ServicesError(
                f"More than one category is named '{self.name}' in glossary "
                f"'{glossary.name}'; identify it with 'guid'.",
            )

        return matches[0] if matches else None

    def _glossary_label(self) -> str:
        return str(self.glossary or self.glossary_qualified_name or self.glossary_guid)

    def _resolve_parent(
        self,
        client: AtlasGlossaryClient,
        glossary_guid: str,
    ) -> Optional[AtlasGlossaryCategory]:
        """The category named as parent; None when none is named."""
        if self.parent_category_guid:
            parent = client.get_category(self.parent_category_guid)
            if parent is None:
                raise ServicesError(
                    f"No category with guid '{self.parent_category_guid}' exists.",
                )
            anchor = _plain(parent.anchor)
            if anchor is None or _plain(anchor.glossary_guid) != glossary_guid:
                raise ServicesError(
                    f"Parent category '{parent.name}' must be in the same glossary.",
                )
            return parent

        if self.parent_category:
            matches = client.find_categories(glossary_guid, name=self.parent_category)
            if not matches:
                raise ServicesError(
                    f"No parent category named '{self.parent_category}' exists "
                    "in the glossary.",
                )
            if len(matches) > 1:
                raise ServicesError(
                    f"More than one category is named '{self.parent_category}'; "
                    "identify the parent with 'parent_category_guid'.",
                )
            return matches[0]

        return None

    def _create(
        self,
        client: AtlasGlossaryClient,
        glossary: Optional[AtlasGlossary],
    ) -> None:
        if self.guid:
            raise ServicesError(f"No category with guid '{self.guid}' exists.")
        if not self.name:
            raise ServicesError("'name' is required to create a category.")
        if glossary is None:
            raise ServicesError(f"No glossary '{self._glossary_label()}' exists.")

        glossary_guid = str(glossary.guid)
        fields: Dict[str, Any] = {
            "name": self.name,
            "anchor": AtlasGlossaryHeader(glossary_guid=glossary_guid),
            **self.descriptive,
        }
        parent = self._resolve_parent(client, glossary_guid)
        if parent:
            fields["parent_category"] = AtlasRelatedCategoryHeader(
                category_guid=str(parent.guid),
            )
        new = AtlasGlossaryCategory(**fields)

        self.changed = True
        if self.module._diff:
            after: Dict[str, Any] = {"name": self.name, **self.descriptive}
            if parent:
                after["parent_category"] = parent.guid
            self.diff = {"before": {}, "after": {"category": after}}

        if self.module.check_mode:
            self.category = to_dict(new)
            return

        created = client.create_category(new)
        self.category = to_dict(self._read_back(client, str(created.guid)))

    def _update(
        self,
        client: AtlasGlossaryClient,
        existing: AtlasGlossaryCategory,
    ) -> None:
        anchor = _plain(existing.anchor)
        glossary_guid = _plain(anchor.glossary_guid) if anchor else None
        if not glossary_guid:
            raise ServicesError(
                f"Category '{existing.name}' does not report its glossary.",
            )

        managed: Dict[str, Any] = dict(self.descriptive)
        if self.name is not None:
            managed["name"] = self.name
        delta = {
            field: value
            for field, value in managed.items()
            if (_plain(getattr(existing, field)) or "") != value
        }

        current_parent = _plain(existing.parent_category)
        current_parent_guid = (
            _plain(current_parent.category_guid) if current_parent else None
        )
        parent_managed = (
            self.parent_category is not None or self.parent_category_guid is not None
        )
        desired_parent_guid: Optional[str] = None
        if parent_managed:
            parent = self._resolve_parent(client, glossary_guid)
            desired_parent_guid = str(parent.guid) if parent else None
        move = parent_managed and desired_parent_guid != current_parent_guid
        if move and desired_parent_guid:
            self._check_acyclic(client, glossary_guid, existing, desired_parent_guid)

        if not delta and not move:
            self.category = to_dict(existing)
            return

        self.changed = True
        if self.module._diff:
            before = {field: _plain(getattr(existing, field)) for field in delta}
            after = dict(delta)
            if move:
                before["parent_category"] = current_parent_guid
                after["parent_category"] = desired_parent_guid
            self.diff = {"before": {"category": before}, "after": {"category": after}}

        guid = str(existing.guid)
        if self.module.check_mode:
            changes: Dict[str, Any] = dict(delta)
            if move:
                changes["parent_category"] = (
                    AtlasRelatedCategoryHeader(category_guid=desired_parent_guid)
                    if desired_parent_guid
                    else NULLABLE
                )
            self.category = to_dict(replace(existing, **changes))
            return

        if delta:
            client.partial_update_category(guid, delta)
        if move:
            if current_parent:
                client.unlink_category_parent(str(current_parent.relation_guid))
            if desired_parent_guid:
                client.link_category_parent(desired_parent_guid, guid)
        self.category = to_dict(self._read_back(client, guid))

    def _absent(
        self,
        client: AtlasGlossaryClient,
        existing: Optional[AtlasGlossaryCategory],
    ) -> None:
        if existing is None:
            return

        children = _plain(existing.children_categories) or []
        parent = _plain(existing.parent_category)
        parent_guid = _plain(parent.category_guid) if parent else None
        descendants = self._descendants(client, existing) if self.cascade else []

        self.changed = True
        if self.module._diff:
            before: Dict[str, Any] = {"name": existing.name}
            if self.cascade and descendants:
                before["descendant_categories"] = [name for _, name in descendants]
            elif children and not self.cascade:
                before["children_categories"] = [
                    header.display_text for header in children
                ]
            self.diff = {"before": {"category": before}, "after": {}}

        if self.module.check_mode:
            return

        guid = str(existing.guid)
        for descendant_guid, _ in descendants:
            client.delete_category(descendant_guid)
        client.delete_category(guid)
        if not self.cascade and parent_guid:
            # Atlas makes the children top-level on delete; hang them on the grandparent.
            for child in children:
                client.link_category_parent(parent_guid, str(child.category_guid))
        if client.get_category(guid) is not None:
            raise ServicesError(
                f"Category '{existing.name}' still exists after the delete.",
            )

    @staticmethod
    def _descendants(
        client: AtlasGlossaryClient,
        category: AtlasGlossaryCategory,
    ) -> List[Tuple[str, str]]:
        """The (guid, name) of every category below this one, deepest first."""
        anchor = _plain(category.anchor)
        glossary_guid = _plain(anchor.glossary_guid) if anchor else None
        if not glossary_guid:
            raise ServicesError(
                f"Category '{category.name}' does not report its glossary.",
            )

        below: Dict[str, List[Tuple[str, str]]] = {}
        for header in client.list_category_headers(glossary_guid):
            below.setdefault(str(_plain(header.parent_category_guid)), []).append(
                (str(header.category_guid), str(header.display_text)),
            )

        ordered: List[Tuple[str, str]] = []
        seen = {str(category.guid)}

        def walk(guid: str) -> None:
            for child_guid, name in below.get(guid, []):
                if child_guid in seen:
                    continue
                seen.add(child_guid)
                walk(child_guid)
                ordered.append((child_guid, name))

        walk(str(category.guid))
        return ordered

    @staticmethod
    def _check_acyclic(
        client: AtlasGlossaryClient,
        glossary_guid: str,
        category: AtlasGlossaryCategory,
        parent_guid: str,
    ) -> None:
        """Fail for a parent that is the category or one of its descendants."""
        if parent_guid == category.guid:
            raise ServicesError(
                f"Category '{category.name}' cannot be its own parent.",
            )

        parents = {
            header.category_guid: _plain(header.parent_category_guid)
            for header in client.list_category_headers(glossary_guid)
        }
        node: Optional[str] = parent_guid
        seen = set()
        while node and node not in seen:
            if node == category.guid:
                raise ServicesError(
                    f"The new parent is a descendant of category '{category.name}'; "
                    "a category cannot sit below its own descendant.",
                )
            seen.add(node)
            node = parents.get(node)

    @staticmethod
    def _read_back(client: AtlasGlossaryClient, guid: str) -> AtlasGlossaryCategory:
        category = client.get_category(guid)
        if category is None:
            raise ServicesError(
                f"Category '{guid}' was written but could not be read back.",
            )
        return category


def main():
    result = AtlasGlossaryCategoryModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        category=result.category,
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
