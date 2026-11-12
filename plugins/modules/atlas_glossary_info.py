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
module: atlas_glossary_info
short_description: Retrieve glossaries from Apache Atlas
description:
  - Retrieve one or more glossaries from Apache Atlas, each with the headers of the terms and categories it contains.
  - Identify a glossary by its GUID, its name, or its qualified name. Without any of these, all glossaries are returned.
  - Returns no glossaries, and does not fail, when nothing matches.
author:
  - "Webster Mudge (@wmudge)"
version_added: "1.2.0"
options:
  guid:
    description:
      - GUID of the glossary.
      - Mutually exclusive with O(name) and O(qualified_name).
    type: str
  name:
    description:
      - Name of the glossary.
      - Only the qualified name is unique, so several glossaries can match; all of them are returned.
    type: str
  qualified_name:
    description:
      - Qualified name of the glossary, which Atlas sets to the name unless told otherwise at creation.
      - Can be combined with O(name); both must then match.
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
- name: Retrieve a glossary by name
  cloudera.services.atlas_glossary_info:
    name: Banking
  register: banking

- name: Retrieve a glossary by its GUID
  cloudera.services.atlas_glossary_info:
    guid: 4b4117f6-dd77-419d-9b8d-b120891ff2b4
  register: glossary

- name: Retrieve a glossary by its qualified name
  cloudera.services.atlas_glossary_info:
    qualified_name: banking_emea
  register: emea

- name: List all glossaries
  cloudera.services.atlas_glossary_info:
  register: all_glossaries

- name: Fail unless the glossary exists
  ansible.builtin.assert:
    that:
      - banking.glossaries | length == 1 # banking variable from above

- name: List the terms of a glossary
  ansible.builtin.debug:
    msg: "{{ banking.glossaries[0].terms | map(attribute='display_text') | list }}"
  when: banking.glossaries | length > 0
"""

RETURN = r"""
glossaries:
  description:
    - The glossaries that match, as a list. Empty when nothing matches.
    - Top-level keys are snake_case; the names inside RV(glossaries[].additional_attributes) are exactly the names Atlas uses.
  type: list
  elements: dict
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
      contains:
        term_guid:
          description: GUID of the term.
          type: str
        relation_guid:
          description: GUID of the relationship that anchors the term to the glossary.
          type: str
        display_text:
          description: Name of the term.
          type: str
    categories:
      description: Headers of the categories in the glossary.
      type: list
      elements: dict
      contains:
        category_guid:
          description: GUID of the category.
          type: str
        parent_category_guid:
          description: GUID of the parent category, absent for a top-level category.
          type: str
        relation_guid:
          description: GUID of the relationship that anchors the category to the glossary.
          type: str
        display_text:
          description: Name of the category.
          type: str
"""

from typing import Any, Dict, List, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryClient,
)


class AtlasGlossaryInfoModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                guid=dict(type="str", required=False),
                name=dict(type="str", required=False),
                qualified_name=dict(type="str", required=False),
            ),
            mutually_exclusive=[
                ["guid", "name"],
                ["guid", "qualified_name"],
            ],
            supports_check_mode=True,
        )

        self.guid: Optional[str] = self.get_param("guid")
        self.name: Optional[str] = self.get_param("name")
        self.qualified_name: Optional[str] = self.get_param("qualified_name")

        self.glossaries: List[Dict[str, Any]] = []

    def process(self) -> None:
        client = AtlasGlossaryClient(self.api_client)

        found: List[AtlasGlossary]
        if self.guid:
            glossary = client.get_glossary(self.guid)
            found = [glossary] if glossary is not None else []
        else:
            found = client.find_glossaries(
                name=self.name,
                qualified_name=self.qualified_name,
            )

        self.glossaries = [to_dict(glossary) for glossary in found]


def main():
    result = AtlasGlossaryInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        glossaries=result.glossaries,
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
