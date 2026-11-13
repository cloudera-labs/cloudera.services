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

import os
from typing import Optional

import pytest

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_glossary_category_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
)
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]

UNKNOWN_GUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def atlas_module_args(module_args, env_context):
    """Fixture to set common module args for Atlas tests."""

    def _atlas_module_args(overrides: Optional[dict] = None) -> None:
        overrides = overrides or {}
        args = {
            "url": env_context["ATLAS_API_URL"],
            "url_username": env_context["ATLAS_API_USERNAME"],
            "url_password": env_context["ATLAS_API_PASSWORD"],
            "force_basic_auth": True,
            "validate_certs": os.environ.get("ATLAS_VALIDATE_CERTS", "false").lower()
            == "true",
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _atlas_module_args


def test_atlas_glossary_category_info_module_by_guid(
    atlas_module_args,
    atlas_glossary_category_tree,
):
    """Test a guid alone returns the category with its parent and glossary."""
    glossary, parent, child = atlas_glossary_category_tree
    atlas_module_args({"guid": child.guid})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert e.value["changed"] is False
    assert len(e.value["categories"]) == 1
    category = e.value["categories"][0]
    assert category["guid"] == child.guid
    assert category["name"] == "Child"
    assert category["anchor"]["glossary_guid"] == glossary.guid
    assert category["parent_category"]["category_guid"] == parent.guid


def test_atlas_glossary_category_info_module_by_glossary_and_name(
    atlas_module_args,
    atlas_glossary_category_tree,
):
    """Test a glossary name and a category name find the category and its children."""
    glossary, parent, child = atlas_glossary_category_tree
    atlas_module_args({"glossary": glossary.name, "name": "Parent"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert [c["guid"] for c in e.value["categories"]] == [parent.guid]
    assert [
        c["category_guid"] for c in e.value["categories"][0]["children_categories"]
    ] == [child.guid]


def test_atlas_glossary_category_info_module_by_glossary_qualified_name(
    atlas_module_args,
    atlas_glossary_category_tree,
):
    """Test a glossary qualified name and a category name find the category."""
    glossary, _, child = atlas_glossary_category_tree
    atlas_module_args(
        {"glossary_qualified_name": glossary.qualified_name, "name": "Child"},
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert [c["guid"] for c in e.value["categories"]] == [child.guid]


def test_atlas_glossary_category_info_module_by_glossary_guid(
    atlas_module_args,
    atlas_glossary_category_tree,
):
    """Test a glossary guid and a category name find the category."""
    glossary, _, child = atlas_glossary_category_tree
    atlas_module_args({"glossary_guid": glossary.guid, "name": "Child"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert [c["guid"] for c in e.value["categories"]] == [child.guid]


def test_atlas_glossary_category_info_module_lists_a_whole_glossary(
    atlas_module_args,
    atlas_glossary_category_tree,
):
    """Test a glossary without a category name returns all its categories."""
    glossary, parent, child = atlas_glossary_category_tree
    atlas_module_args({"glossary_guid": glossary.guid})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert {c["guid"] for c in e.value["categories"]} == {parent.guid, child.guid}


def test_atlas_glossary_category_info_module_same_name_under_two_parents(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test a category name shared under different parents returns both."""
    glossary, _, child = atlas_glossary_category_tree
    twin = atlas_glossary_client.create_category(
        AtlasGlossaryCategory(
            name="Child",
            anchor=AtlasGlossaryHeader(glossary_guid=glossary.guid),
        ),
    )
    atlas_module_args({"glossary_guid": glossary.guid, "name": "Child"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert {c["guid"] for c in e.value["categories"]} == {child.guid, twin.guid}


def test_atlas_glossary_category_info_module_empty_glossary_has_no_categories(
    atlas_module_args,
    atlas_deletable_glossary,
):
    """Test a glossary without categories returns none rather than failing."""
    atlas_module_args({"glossary_guid": atlas_deletable_glossary.guid})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert e.value["categories"] == []


def test_atlas_glossary_category_info_module_unknown_category_name_returns_none(
    atlas_module_args,
    atlas_glossary_category_tree,
):
    """Test a category name nothing carries returns no categories."""
    glossary, _, _ = atlas_glossary_category_tree
    atlas_module_args({"glossary_guid": glossary.guid, "name": "Nope"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert e.value["categories"] == []


def test_atlas_glossary_category_info_module_unknown_guid_returns_none(
    atlas_module_args,
):
    """Test an unknown category guid returns no categories rather than failing."""
    atlas_module_args({"guid": UNKNOWN_GUID})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert e.value["categories"] == []


def test_atlas_glossary_category_info_module_unknown_glossary_fails(
    atlas_module_args,
    atlas_glossary_name,
):
    """Test a glossary that does not exist fails."""
    atlas_module_args({"glossary": atlas_glossary_name})

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category_info.main()

    assert "No glossary" in e.value["msg"]


def test_atlas_glossary_category_info_module_unknown_glossary_guid_fails(
    atlas_module_args,
):
    """Test a glossary guid that does not exist fails."""
    atlas_module_args({"glossary_guid": UNKNOWN_GUID})

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category_info.main()

    assert UNKNOWN_GUID in e.value["msg"]
