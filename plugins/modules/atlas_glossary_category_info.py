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
module: atlas_glossary_category_info
short_description: Retrieve glossary categories from Apache Atlas
description:
  - Retrieve one or more categories from an Apache Atlas glossary, each with its parent, its child categories, and the headers of the terms it contains.
  - Identify a category by its GUID, which is unique across Atlas, or by its name within a glossary. Without a name, all categories of the glossary are returned.
  - Fails when the glossary does not exist. Returns no categories, and does not fail, when no category matches.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.2.0"
options:
  guid:
    description:
      - GUID of the category.
      - Mutually exclusive with O(name), O(glossary), O(glossary_qualified_name), and O(glossary_guid).
    type: str
  name:
    description:
      - Name of the category.
      - Several categories can share a name under different parents; all of them are returned.
      - Requires one of O(glossary), O(glossary_qualified_name), or O(glossary_guid).
    type: str
  glossary:
    description:
      - Name of the glossary that holds the categories.
      - Fails if more than one glossary has this name; use O(glossary_guid) or O(glossary_qualified_name) instead.
      - Mutually exclusive with O(glossary_qualified_name) and O(glossary_guid).
    type: str
  glossary_qualified_name:
    description:
      - Qualified name of the glossary that holds the categories.
      - Mutually exclusive with O(glossary) and O(glossary_guid).
    type: str
  glossary_guid:
    description:
      - GUID of the glossary that holds the categories.
      - Mutually exclusive with O(glossary) and O(glossary_qualified_name).
    type: str
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    description:
      - This module supports check mode.
    support: full
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields
- name: Retrieve a category by name within a glossary
  cloudera.services.atlas_glossary_category_info:
    glossary: Banking
    name: Customer
  register: customer

- name: List all categories of a glossary by the glossary name
  cloudera.services.atlas_glossary_category_info:
    glossary: Banking
  register: banking_categories

- name: Retrieve a category by its GUID
  cloudera.services.atlas_glossary_category_info:
    guid: 5b292b6f-0983-4e43-8508-7115b9d9361d
  register: category

- name: List all categories of a glossary identified by its GUID
  cloudera.services.atlas_glossary_category_info:
    glossary_guid: 4b4117f6-dd77-419d-9b8d-b120891ff2b4
  register: categories

- name: Fail unless the category exists
  ansible.builtin.assert:
    that:
      - customer.categories | length == 1 # customer variable from above

- name: List the terms of a category
  ansible.builtin.debug:
    msg: "{{ customer.categories[0].terms | map(attribute='display_text') | list }}"
  when: customer.categories | length > 0
"""

RETURN = r"""
categories:
  description:
    - The categories that match, as a list. Empty when nothing matches.
    - Top-level keys are snake_case; the names inside RV(categories[].additional_attributes) are exactly the names Atlas uses.
  type: list
  elements: dict
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

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossaryCategory,
    AtlasGlossaryClient,
    resolve_glossary,
)


class AtlasGlossaryCategoryInfoModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                name=dict(type="str", required=False),
                glossary=dict(type="str", required=False),
                glossary_qualified_name=dict(type="str", required=False),
                glossary_guid=dict(type="str", required=False),
            ),
            mutually_exclusive=[
                ["guid", "name"],
                ["guid", "glossary"],
                ["guid", "glossary_qualified_name"],
                ["guid", "glossary_guid"],
                ["glossary", "glossary_qualified_name", "glossary_guid"],
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

        self.categories: List[Dict[str, Any]] = []

    def process(self) -> None:
        client = AtlasGlossaryClient(self.api_client)

        found: List[AtlasGlossaryCategory] = []
        if self.guid:
            category = client.get_category(self.guid)
            if category is not None:
                found.append(category)
        else:
            glossary = resolve_glossary(
                client,
                name=self.glossary,
                qualified_name=self.glossary_qualified_name,
                guid=self.glossary_guid,
            )
            found = client.find_categories(str(glossary.guid), name=self.name)

        self.categories = [to_dict(category) for category in found]


def main():
    result = AtlasGlossaryCategoryInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        categories=result.categories,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
