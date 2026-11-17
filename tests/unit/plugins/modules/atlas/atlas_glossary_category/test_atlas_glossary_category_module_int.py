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
    atlas_glossary_category,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasRelatedCategoryHeader,
)
from ansible_collections.cloudera.services.plugins.module_utils.common import NULLABLE
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


def _run(atlas_module_args, **args):
    atlas_module_args(args)
    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category.main()
    return e.value


def _fail(atlas_module_args, **args):
    atlas_module_args(args)
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category.main()
    return e.value


def test_atlas_glossary_category_module_creates_a_top_level_category(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test a category is created in a glossary, top level, with its description."""
    result = _run(
        atlas_module_args,
        glossary_guid=atlas_deletable_glossary.guid,
        name="Customer",
        short_description="short",
    )

    assert result["changed"] is True
    stored = atlas_glossary_client.get_category(result["category"]["guid"])
    assert stored.name == "Customer"
    assert stored.short_description == "short"
    assert stored.anchor.glossary_guid == atlas_deletable_glossary.guid
    assert stored.parent_category is NULLABLE


def test_atlas_glossary_category_module_creates_below_a_parent(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test a category named with a parent is created below it."""
    glossary, parent, _ = atlas_glossary_category_tree

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Grandchild",
        parent_category="Parent",
    )

    stored = atlas_glossary_client.get_category(result["category"]["guid"])
    assert stored.parent_category.category_guid == parent.guid


def test_atlas_glossary_category_module_is_idempotent(
    atlas_module_args,
    atlas_glossary_category_tree,
):
    """Test a category that already matches the task is not changed."""
    glossary, _, _ = atlas_glossary_category_tree

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Child",
        parent_category="Parent",
    )

    assert result["changed"] is False


def test_atlas_glossary_category_module_updates_a_description(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test a changed description is written and the hierarchy is kept."""
    glossary, parent, child = atlas_glossary_category_tree

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Parent",
        long_description="long",
    )

    assert result["changed"] is True
    stored = atlas_glossary_client.get_category(str(parent.guid))
    assert stored.long_description == "long"
    assert [c.category_guid for c in stored.children_categories] == [child.guid]


def test_atlas_glossary_category_module_renames_by_guid(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test a guid identifies the category, so the name changes."""
    _, parent, _ = atlas_glossary_category_tree

    result = _run(atlas_module_args, guid=parent.guid, name="Renamed")

    assert result["changed"] is True
    assert atlas_glossary_client.get_category(str(parent.guid)).name == "Renamed"


def test_atlas_glossary_category_module_moves_to_the_top_level(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test an empty parent makes a nested category top-level."""
    glossary, _, child = atlas_glossary_category_tree

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Child",
        parent_category="",
    )

    assert result["changed"] is True
    assert (
        atlas_glossary_client.get_category(str(child.guid)).parent_category is NULLABLE
    )


def test_atlas_glossary_category_module_moves_to_another_parent(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test a category is re-parented to another category."""
    glossary, parent, child = atlas_glossary_category_tree
    other = atlas_glossary_client.create_category(
        AtlasGlossaryCategory(
            name="Other",
            anchor=AtlasGlossaryHeader(glossary_guid=glossary.guid),
        ),
    )

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Child",
        parent_category_guid=other.guid,
    )

    assert result["changed"] is True
    stored = atlas_glossary_client.get_category(str(child.guid))
    assert stored.parent_category.category_guid == other.guid
    assert atlas_glossary_client.get_category(str(parent.guid)).children_categories in (
        NULLABLE,
        None,
        [],
    )


def test_atlas_glossary_category_module_descendant_as_parent_fails(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test a descendant as parent fails, and nothing changes."""
    glossary, parent, child = atlas_glossary_category_tree

    result = _fail(
        atlas_module_args,
        glossary=glossary.name,
        name="Parent",
        parent_category_guid=child.guid,
    )

    assert "descendant" in result["msg"]
    assert (
        atlas_glossary_client.get_category(str(parent.guid)).parent_category is NULLABLE
    )


def test_atlas_glossary_category_module_parent_in_another_glossary_fails(
    atlas_module_args,
    atlas_glossary_client,
    atlas_cleanup_glossary,
    atlas_glossary_name,
    atlas_glossary_category_tree,
):
    """Test a parent from another glossary is refused, though Atlas would accept it."""
    glossary, _, _ = atlas_glossary_category_tree
    other_glossary = atlas_glossary_client.create_glossary(
        AtlasGlossary(name=atlas_glossary_name),
    )
    atlas_cleanup_glossary(str(other_glossary.guid))
    foreign = atlas_glossary_client.create_category(
        AtlasGlossaryCategory(
            name="Foreign",
            anchor=AtlasGlossaryHeader(glossary_guid=other_glossary.guid),
        ),
    )

    result = _fail(
        atlas_module_args,
        glossary=glossary.name,
        name="Fresh",
        parent_category_guid=foreign.guid,
    )

    assert "same glossary" in result["msg"]
    assert atlas_glossary_client.find_categories(str(glossary.guid), name="Fresh") == []


def test_atlas_glossary_category_module_delete_promotes_children_to_the_top_level(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test deleting a top-level category leaves its child top-level."""
    glossary, parent, child = atlas_glossary_category_tree

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Parent",
        state="absent",
    )

    assert result["changed"] is True
    assert atlas_glossary_client.get_category(str(parent.guid)) is None
    assert (
        atlas_glossary_client.get_category(str(child.guid)).parent_category is NULLABLE
    )


def test_atlas_glossary_category_module_delete_moves_children_to_the_parent(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test deleting a middle category hangs its child on the grandparent."""
    glossary, parent, child = atlas_glossary_category_tree
    grandchild = atlas_glossary_client.create_category(
        AtlasGlossaryCategory(
            name="Grandchild",
            anchor=AtlasGlossaryHeader(glossary_guid=glossary.guid),
            parent_category=AtlasRelatedCategoryHeader(category_guid=child.guid),
        ),
    )

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Child",
        state="absent",
    )

    assert result["changed"] is True
    assert atlas_glossary_client.get_category(str(child.guid)) is None
    moved = atlas_glossary_client.get_category(str(grandchild.guid))
    assert moved.parent_category.category_guid == parent.guid


def test_atlas_glossary_category_module_cascade_deletes_the_descendants(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_category_tree,
):
    """Test a cascade deletes the category and every category below it."""
    glossary, parent, child = atlas_glossary_category_tree

    result = _run(
        atlas_module_args,
        glossary=glossary.name,
        name="Parent",
        state="absent",
        cascade=True,
    )

    assert result["changed"] is True
    assert atlas_glossary_client.get_category(str(parent.guid)) is None
    assert atlas_glossary_client.get_category(str(child.guid)) is None


def test_atlas_glossary_category_module_delete_of_a_missing_category_is_a_no_op(
    atlas_module_args,
    atlas_deletable_glossary,
):
    """Test deleting a category that does not exist changes nothing."""
    result = _run(
        atlas_module_args,
        glossary=atlas_deletable_glossary.name,
        name="Nothing",
        state="absent",
    )

    assert result["changed"] is False


def test_atlas_glossary_category_module_check_mode_writes_nothing(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test check mode reports a create but leaves Atlas as it was."""
    result = _run(
        atlas_module_args,
        glossary=atlas_deletable_glossary.name,
        name="Customer",
        _ansible_check_mode=True,
    )

    assert result["changed"] is True
    assert (
        atlas_glossary_client.find_categories(
            str(atlas_deletable_glossary.guid),
            name="Customer",
        )
        == []
    )


def test_atlas_glossary_category_module_unknown_glossary_fails(
    atlas_module_args,
    atlas_glossary_name,
):
    """Test a glossary that does not exist fails the task."""
    result = _fail(atlas_module_args, glossary=atlas_glossary_name, name="Customer")

    assert atlas_glossary_name in result["msg"]


def test_atlas_glossary_category_module_unknown_guid_fails(atlas_module_args):
    """Test a guid nothing carries fails instead of creating a category."""
    result = _fail(atlas_module_args, guid=UNKNOWN_GUID, name="Customer")

    assert UNKNOWN_GUID in result["msg"]
