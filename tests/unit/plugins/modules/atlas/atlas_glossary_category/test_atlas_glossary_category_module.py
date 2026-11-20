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

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.module_utils.common import NULLABLE
from ansible_collections.cloudera.services.plugins.modules import (
    atlas_glossary_category,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasRelatedCategoryHeader,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_glossary_category.AtlasGlossaryClient"
GLOSSARY_GUID = "4b4117f6-dd77-419d-9b8d-b120891ff2b4"
CATEGORY_GUID = "5b292b6f-0983-4e43-8508-7115b9d9361d"
PARENT_GUID = "ac37096b-6021-402d-8a65-7f3538615d27"

GLOSSARY = AtlasGlossary(name="Bank", guid=GLOSSARY_GUID, qualified_name="Bank")


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def _run(module_args, **extra):
    module_args(_args(**extra))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category.main()
    return e.value


def _fail(module_args, **extra):
    module_args(_args(**extra))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category.main()
    return e.value


@pytest.fixture
def client(mocker):
    """Patch every AtlasGlossaryClient method the module uses."""
    mocks = {
        name: mocker.patch(f"{CLIENT}.{name}")
        for name in (
            "get_glossary",
            "find_glossaries",
            "get_category",
            "find_categories",
            "list_category_headers",
            "create_category",
            "partial_update_category",
            "link_category_parent",
            "unlink_category_parent",
            "delete_category",
        )
    }
    mocks["find_glossaries"].return_value = [GLOSSARY]
    mocks["get_glossary"].return_value = GLOSSARY
    mocks["list_category_headers"].return_value = []
    return mocks


# ---------------------------------------------------------------- present: create


def test_atlas_glossary_category_module_creates_a_top_level_category(
    module_args,
    client,
):
    """Test a missing category is created in its glossary with only the fields given."""
    created = AtlasGlossaryCategory(
        name="Customer",
        guid=CATEGORY_GUID,
        anchor=AtlasGlossaryHeader(glossary_guid=GLOSSARY_GUID),
    )
    client["find_categories"].return_value = []
    client["create_category"].return_value = created
    client["get_category"].return_value = created

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="short",
    )

    assert result["changed"] is True
    assert result["category"]["guid"] == CATEGORY_GUID
    client["find_glossaries"].assert_called_once_with(
        name="Bank",
        qualified_name=None,
    )
    client["find_categories"].assert_called_once_with(GLOSSARY_GUID, name="Customer")
    client["create_category"].assert_called_once_with(
        AtlasGlossaryCategory(
            name="Customer",
            short_description="short",
            anchor=AtlasGlossaryHeader(glossary_guid=GLOSSARY_GUID),
        ),
    )
    client["partial_update_category"].assert_not_called()


def test_atlas_glossary_category_module_creates_under_a_parent_by_name(
    module_args,
    client,
):
    """Test a parent named in the task is looked up in the glossary and set on create."""
    parent = AtlasGlossaryCategory(
        name="Loans",
        guid=PARENT_GUID,
        anchor=AtlasGlossaryHeader(glossary_guid=GLOSSARY_GUID),
    )
    created = AtlasGlossaryCategory(name="Customer", guid=CATEGORY_GUID)
    client["find_categories"].side_effect = [[], [parent]]
    client["create_category"].return_value = created
    client["get_category"].return_value = created

    result = _run(
        module_args,
        glossary_guid=GLOSSARY_GUID,
        name="Customer",
        parent_category="Loans",
    )

    assert result["changed"] is True
    client["create_category"].assert_called_once_with(
        AtlasGlossaryCategory(
            name="Customer",
            anchor=AtlasGlossaryHeader(glossary_guid=GLOSSARY_GUID),
            parent_category=AtlasRelatedCategoryHeader(category_guid=PARENT_GUID),
        ),
    )


def test_atlas_glossary_category_module_creates_under_a_parent_by_guid(
    module_args,
    client,
):
    """Test a parent guid is checked to be in the same glossary, then set on create."""
    parent = AtlasGlossaryCategory(
        name="Loans",
        guid=PARENT_GUID,
        anchor=AtlasGlossaryHeader(glossary_guid=GLOSSARY_GUID),
    )
    created = AtlasGlossaryCategory(name="Customer", guid=CATEGORY_GUID)
    client["find_categories"].return_value = []
    client["get_category"].side_effect = [parent, created]
    client["create_category"].return_value = created

    _run(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category_guid=PARENT_GUID,
    )

    assert client["create_category"].call_args.args[0].parent_category == (
        AtlasRelatedCategoryHeader(category_guid=PARENT_GUID)
    )


@pytest.mark.parametrize("parent", ["", None], ids=["empty-name", "unset"])
def test_atlas_glossary_category_module_creates_top_level_without_a_parent(
    module_args,
    client,
    parent,
):
    """Test an empty or missing parent makes a top-level category."""
    created = AtlasGlossaryCategory(name="Customer", guid=CATEGORY_GUID)
    client["find_categories"].return_value = []
    client["create_category"].return_value = created
    client["get_category"].return_value = created

    extra = {} if parent is None else {"parent_category": parent}
    _run(module_args, glossary="Bank", name="Customer", **extra)

    assert client["create_category"].call_args.args[0].parent_category is NULLABLE


def test_atlas_glossary_category_module_unknown_parent_fails(module_args, client):
    """Test a parent that does not exist fails before anything is created."""
    client["find_categories"].side_effect = [[], []]

    result = _fail(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category="Loans",
    )

    assert "Loans" in result["msg"]
    client["create_category"].assert_not_called()


def test_atlas_glossary_category_module_parent_in_another_glossary_fails(
    module_args,
    client,
):
    """Test Atlas accepts a parent from another glossary, so the module refuses it."""
    other = AtlasGlossaryCategory(
        name="Loans",
        guid=PARENT_GUID,
        anchor=AtlasGlossaryHeader(glossary_guid="other-glossary"),
    )
    client["find_categories"].return_value = []
    client["get_category"].return_value = other

    result = _fail(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category_guid=PARENT_GUID,
    )

    assert "same glossary" in result["msg"]
    client["create_category"].assert_not_called()


def test_atlas_glossary_category_module_ambiguous_parent_fails(module_args, client):
    """Test a parent name that matches several categories asks for the guid."""
    loans = AtlasGlossaryCategory(name="Loans", guid="p1")
    client["find_categories"].side_effect = [[], [loans, loans]]

    result = _fail(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category="Loans",
    )

    assert "parent_category_guid" in result["msg"]
    client["create_category"].assert_not_called()


def test_atlas_glossary_category_module_unknown_glossary_fails(module_args, client):
    """Test a glossary that does not exist fails under state present."""
    client["find_glossaries"].return_value = []

    result = _fail(module_args, glossary="Bank", name="Customer")

    assert "Bank" in result["msg"]
    client["create_category"].assert_not_called()


def test_atlas_glossary_category_module_ambiguous_glossary_fails(module_args, client):
    """Test a glossary name shared by several glossaries asks for a qualified name."""
    client["find_glossaries"].return_value = [GLOSSARY, GLOSSARY]

    result = _fail(module_args, glossary="Bank", name="Customer")

    assert "glossary_qualified_name" in result["msg"]


def test_atlas_glossary_category_module_unknown_guid_fails(module_args, client):
    """Test a guid nothing carries fails instead of creating a category."""
    client["get_category"].return_value = None

    result = _fail(module_args, guid=CATEGORY_GUID, name="Customer")

    assert CATEGORY_GUID in result["msg"]
    client["create_category"].assert_not_called()


def test_atlas_glossary_category_module_ambiguous_category_fails(module_args, client):
    """Test a name shared by categories under different parents asks for the guid."""
    client["find_categories"].return_value = [
        AtlasGlossaryCategory(name="Customer", guid="c1"),
        AtlasGlossaryCategory(name="Customer", guid="c2"),
    ]

    result = _fail(module_args, glossary="Bank", name="Customer")

    assert "guid" in result["msg"]
    client["create_category"].assert_not_called()


def test_atlas_glossary_category_module_create_needs_a_name(module_args, client):
    """Test a glossary alone cannot identify a category to create."""
    result = _fail(module_args, glossary="Bank")

    assert "'name' is required" in result["msg"]


def test_atlas_glossary_category_module_create_fails_when_atlas_does_not_return_it(
    module_args,
    client,
):
    """Test a created category that cannot be read back is reported."""
    client["find_categories"].return_value = []
    client["create_category"].return_value = AtlasGlossaryCategory(
        name="Customer",
        guid=CATEGORY_GUID,
    )
    client["get_category"].return_value = None

    result = _fail(module_args, glossary="Bank", name="Customer")

    assert "could not be read back" in result["msg"]


@pytest.mark.parametrize("character", ["@", ".", "<", ">"])
def test_atlas_glossary_category_module_invalid_name_fails_before_any_request(
    module_args,
    client,
    character,
):
    """Test a name Atlas would reject fails without a request."""
    result = _fail(module_args, glossary="Bank", name=f"a{character}b")

    assert "may not contain" in result["msg"]
    for mock in client.values():
        mock.assert_not_called()


# ---------------------------------------------------------------- present: update

OTHER_PARENT_GUID = "0d9a6b3e-6a43-4e62-b4a8-5c0a6f8d1e11"
RELATION_GUID = "9c2b1d7e-3f1a-4e55-8a52-0d6a1f0e4c77"
ANCHOR = AtlasGlossaryHeader(glossary_guid=GLOSSARY_GUID)

EXISTING = AtlasGlossaryCategory(
    name="Customer",
    guid=CATEGORY_GUID,
    qualified_name="Customer@Bank",
    short_description="short",
    anchor=ANCHOR,
)
NESTED = AtlasGlossaryCategory(
    name="Customer",
    guid=CATEGORY_GUID,
    qualified_name="Loans.Customer@Bank",
    short_description="short",
    anchor=ANCHOR,
    parent_category=AtlasRelatedCategoryHeader(
        category_guid=PARENT_GUID,
        relation_guid=RELATION_GUID,
    ),
)
NEW_PARENT = AtlasGlossaryCategory(
    name="Accounts",
    guid=OTHER_PARENT_GUID,
    anchor=ANCHOR,
)


def test_atlas_glossary_category_module_is_idempotent(module_args, client):
    """Test a category that already matches the task is left alone."""
    client["find_categories"].return_value = [EXISTING]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="short",
    )

    assert result["changed"] is False
    assert result["category"]["guid"] == CATEGORY_GUID
    client["create_category"].assert_not_called()
    client["partial_update_category"].assert_not_called()
    client["link_category_parent"].assert_not_called()
    client["unlink_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_sends_only_the_changed_fields(
    module_args,
    client,
):
    """Test the partial update carries the fields that differ and nothing else."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = EXISTING

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="changed",
        long_description="",
    )

    assert result["changed"] is True
    client["partial_update_category"].assert_called_once_with(
        CATEGORY_GUID,
        {"short_description": "changed"},
    )


def test_atlas_glossary_category_module_clears_a_field_with_an_empty_string(
    module_args,
    client,
):
    """Test an empty string clears a set field."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = EXISTING

    _run(module_args, glossary="Bank", name="Customer", short_description="")

    client["partial_update_category"].assert_called_once_with(
        CATEGORY_GUID,
        {"short_description": ""},
    )


def test_atlas_glossary_category_module_renames_by_guid(module_args, client):
    """Test a guid identifies the category and the name is the value to set."""
    client["get_category"].return_value = EXISTING

    result = _run(module_args, guid=CATEGORY_GUID, name="Client")

    assert result["changed"] is True
    client["partial_update_category"].assert_called_once_with(
        CATEGORY_GUID,
        {"name": "Client"},
    )
    client["find_categories"].assert_not_called()


def test_atlas_glossary_category_module_leaves_the_parent_unmanaged(
    module_args,
    client,
):
    """Test a task that names no parent keeps the one the category has."""
    client["find_categories"].return_value = [NESTED]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="short",
    )

    assert result["changed"] is False
    client["unlink_category_parent"].assert_not_called()
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_same_parent_is_idempotent(module_args, client):
    """Test naming the current parent changes nothing."""
    client["find_categories"].side_effect = [
        [NESTED],
        [AtlasGlossaryCategory(name="Loans", guid=PARENT_GUID, anchor=ANCHOR)],
    ]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category="Loans",
    )

    assert result["changed"] is False
    client["unlink_category_parent"].assert_not_called()
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_sets_a_parent_on_a_top_level_category(
    module_args,
    client,
):
    """Test a top-level category is linked to its new parent without an unlink."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].side_effect = [NEW_PARENT, EXISTING]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category_guid=OTHER_PARENT_GUID,
    )

    assert result["changed"] is True
    client["unlink_category_parent"].assert_not_called()
    client["link_category_parent"].assert_called_once_with(
        OTHER_PARENT_GUID,
        CATEGORY_GUID,
    )
    client["partial_update_category"].assert_not_called()


def test_atlas_glossary_category_module_moves_to_another_parent(module_args, client):
    """Test a re-parent removes the old relationship, then adds the new one."""
    client["find_categories"].return_value = [NESTED]
    client["get_category"].side_effect = [NEW_PARENT, NESTED]
    calls = []
    client["unlink_category_parent"].side_effect = lambda *a: calls.append("unlink")
    client["link_category_parent"].side_effect = lambda *a: calls.append("link")

    _run(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category_guid=OTHER_PARENT_GUID,
    )

    assert calls == ["unlink", "link"]
    client["unlink_category_parent"].assert_called_once_with(RELATION_GUID)
    client["link_category_parent"].assert_called_once_with(
        OTHER_PARENT_GUID,
        CATEGORY_GUID,
    )


def test_atlas_glossary_category_module_moves_to_the_top_level(module_args, client):
    """Test an empty parent removes the hierarchy relationship."""
    client["find_categories"].return_value = [NESTED]
    client["get_category"].return_value = EXISTING

    result = _run(module_args, glossary="Bank", name="Customer", parent_category="")

    assert result["changed"] is True
    client["unlink_category_parent"].assert_called_once_with(RELATION_GUID)
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_empty_parent_on_top_level_is_idempotent(
    module_args,
    client,
):
    """Test asking for the top level of a top-level category changes nothing."""
    client["find_categories"].return_value = [EXISTING]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category_guid="",
    )

    assert result["changed"] is False
    client["unlink_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_own_parent_fails(module_args, client):
    """Test a category cannot be its own parent."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = EXISTING

    result = _fail(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category_guid=CATEGORY_GUID,
    )

    assert "its own parent" in result["msg"]
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_descendant_as_parent_fails(module_args, client):
    """Test a descendant as parent fails, since Atlas answers a cycle with HTTP 500."""
    grandchild = AtlasGlossaryCategory(name="Gold", guid="gc", anchor=ANCHOR)
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = grandchild
    client["list_category_headers"].return_value = [
        AtlasRelatedCategoryHeader(
            category_guid=CATEGORY_GUID,
            display_text="Customer",
        ),
        AtlasRelatedCategoryHeader(
            category_guid="child",
            parent_category_guid=CATEGORY_GUID,
            display_text="Retail",
        ),
        AtlasRelatedCategoryHeader(
            category_guid="gc",
            parent_category_guid="child",
            display_text="Gold",
        ),
    ]

    result = _fail(
        module_args,
        glossary="Bank",
        name="Customer",
        parent_category_guid="gc",
    )

    assert "descendant" in result["msg"]
    client["unlink_category_parent"].assert_not_called()
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_update_fails_when_atlas_does_not_return_it(
    module_args,
    client,
):
    """Test an updated category that cannot be read back is reported."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = None

    result = _fail(module_args, glossary="Bank", name="Customer", short_description="x")

    assert "could not be read back" in result["msg"]


# ---------------------------------------------------------------- absent


def test_atlas_glossary_category_module_deletes_a_category(module_args, client):
    """Test an existing category is deleted and its absence verified."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = None

    result = _run(module_args, glossary="Bank", name="Customer", state="absent")

    assert result["changed"] is True
    assert result["category"] == {}
    client["delete_category"].assert_called_once_with(CATEGORY_GUID)


def test_atlas_glossary_category_module_deletes_by_guid(module_args, client):
    """Test a guid alone identifies the category to delete."""
    client["get_category"].side_effect = [EXISTING, None]

    result = _run(module_args, guid=CATEGORY_GUID, state="absent")

    assert result["changed"] is True
    client["delete_category"].assert_called_once_with(CATEGORY_GUID)


def test_atlas_glossary_category_module_delete_of_a_missing_category_is_a_no_op(
    module_args,
    client,
):
    """Test a category that does not exist needs no delete."""
    client["find_categories"].return_value = []

    result = _run(module_args, glossary="Bank", name="Customer", state="absent")

    assert result["changed"] is False
    client["delete_category"].assert_not_called()


def test_atlas_glossary_category_module_delete_of_an_unknown_guid_is_a_no_op(
    module_args,
    client,
):
    """Test a guid nothing carries needs no delete."""
    client["get_category"].return_value = None

    result = _run(module_args, guid=CATEGORY_GUID, state="absent")

    assert result["changed"] is False
    client["delete_category"].assert_not_called()


def test_atlas_glossary_category_module_delete_in_a_missing_glossary_is_a_no_op(
    module_args,
    client,
):
    """Test a glossary that does not exist leaves nothing to delete."""
    client["find_glossaries"].return_value = []

    result = _run(module_args, glossary="Bank", name="Customer", state="absent")

    assert result["changed"] is False
    client["delete_category"].assert_not_called()


def test_atlas_glossary_category_module_delete_fails_when_the_category_remains(
    module_args,
    client,
):
    """Test a category that is still there after the delete is reported."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = EXISTING

    result = _fail(module_args, glossary="Bank", name="Customer", state="absent")

    assert "still exists" in result["msg"]


@pytest.mark.parametrize(
    "option",
    [
        {"short_description": "s"},
        {"long_description": "l"},
        {"parent_category": "Loans"},
        {"parent_category_guid": PARENT_GUID},
    ],
    ids=["short", "long", "parent", "parent-guid"],
)
def test_atlas_glossary_category_module_absent_rejects_attribute_options(
    module_args,
    client,
    option,
):
    """Test the descriptive and parent options cannot be combined with state absent."""
    result = _fail(
        module_args,
        glossary="Bank",
        name="Customer",
        state="absent",
        **option,
    )

    assert "cannot be used with state 'absent'" in result["msg"]
    client["delete_category"].assert_not_called()


# ---------------------------------------------------------------- check and diff mode


def test_atlas_glossary_category_module_check_mode_create(module_args, client):
    """Test check mode reports a create without writing."""
    client["find_categories"].return_value = []

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="short",
        _ansible_check_mode=True,
    )

    assert result["changed"] is True
    assert result["category"]["name"] == "Customer"
    assert "guid" not in result["category"]
    client["create_category"].assert_not_called()


def test_atlas_glossary_category_module_check_mode_update(module_args, client):
    """Test check mode reports an update and a re-parent without writing."""
    client["find_categories"].return_value = [NESTED]
    client["get_category"].return_value = NEW_PARENT

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="changed",
        parent_category_guid=OTHER_PARENT_GUID,
        _ansible_check_mode=True,
    )

    assert result["changed"] is True
    assert result["category"]["short_description"] == "changed"
    assert result["category"]["parent_category"]["category_guid"] == OTHER_PARENT_GUID
    client["partial_update_category"].assert_not_called()
    client["unlink_category_parent"].assert_not_called()
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_check_mode_absent(module_args, client):
    """Test check mode reports a delete without writing."""
    client["find_categories"].return_value = [EXISTING]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        state="absent",
        _ansible_check_mode=True,
    )

    assert result["changed"] is True
    client["delete_category"].assert_not_called()


def test_atlas_glossary_category_module_diff_of_a_create_has_an_empty_before(
    module_args,
    client,
):
    """Test a create diff has nothing before."""
    client["find_categories"].side_effect = [[], [NEW_PARENT]]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="short",
        parent_category="Accounts",
        _ansible_check_mode=True,
        _ansible_diff=True,
    )

    assert result["diff"] == {
        "before": {},
        "after": {
            "category": {
                "name": "Customer",
                "short_description": "short",
                "parent_category": OTHER_PARENT_GUID,
            },
        },
    }


def test_atlas_glossary_category_module_diff_covers_the_managed_fields_only(
    module_args,
    client,
):
    """Test the diff shows before and after for the fields that change."""
    client["find_categories"].side_effect = [[NESTED], [NEW_PARENT]]
    client["get_category"].return_value = NESTED

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        short_description="changed",
        long_description="",
        parent_category="Accounts",
        _ansible_check_mode=True,
        _ansible_diff=True,
    )

    assert result["diff"] == {
        "before": {
            "category": {"short_description": "short", "parent_category": PARENT_GUID},
        },
        "after": {
            "category": {
                "short_description": "changed",
                "parent_category": OTHER_PARENT_GUID,
            },
        },
    }


def test_atlas_glossary_category_module_diff_of_a_delete_lists_the_children(
    module_args,
    client,
):
    """Test a delete diff names the children that move up to the top level."""
    with_children = AtlasGlossaryCategory(
        name="Customer",
        guid=CATEGORY_GUID,
        anchor=ANCHOR,
        children_categories=[
            AtlasRelatedCategoryHeader(category_guid="c1", display_text="Retail"),
        ],
    )
    client["find_categories"].return_value = [with_children]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        state="absent",
        _ansible_check_mode=True,
        _ansible_diff=True,
    )

    assert result["diff"] == {
        "before": {"category": {"name": "Customer", "children_categories": ["Retail"]}},
        "after": {},
    }


# ---------------------------------------------------------------- failures and arguments


@pytest.mark.parametrize(
    "method, extra",
    [
        ("create_category", {"glossary": "Bank", "name": "New"}),
        ("partial_update_category", {"guid": CATEGORY_GUID, "name": "Client"}),
        ("delete_category", {"guid": CATEGORY_GUID, "state": "absent"}),
    ],
    ids=["create", "update", "delete"],
)
def test_atlas_glossary_category_module_reports_a_failed_write(
    module_args,
    client,
    method,
    extra,
):
    """Test an Atlas error on a write ends the task with the error message."""
    from ansible_collections.cloudera.services.plugins.module_utils.common import (
        ServicesError,
    )

    client["find_categories"].return_value = []
    client["get_category"].return_value = EXISTING
    client[method].side_effect = ServicesError("Atlas said no")

    result = _fail(module_args, **extra)

    assert "Atlas said no" in result["msg"]


def test_atlas_glossary_category_module_reports_a_failed_lookup(module_args, client):
    """Test an Atlas error on a read ends the task with the error message."""
    from ansible_collections.cloudera.services.plugins.module_utils.common import (
        ServicesError,
    )

    client["find_categories"].side_effect = ServicesError("Atlas is down")

    result = _fail(module_args, glossary="Bank", name="Customer")

    assert "Atlas is down" in result["msg"]


@pytest.mark.parametrize(
    "extra",
    [
        {"guid": CATEGORY_GUID, "glossary": "Bank"},
        {"guid": CATEGORY_GUID, "glossary_qualified_name": "Bank"},
        {"guid": CATEGORY_GUID, "glossary_guid": GLOSSARY_GUID},
        {"glossary": "Bank", "glossary_guid": GLOSSARY_GUID, "name": "c"},
        {
            "glossary": "Bank",
            "name": "c",
            "parent_category": "Loans",
            "parent_category_guid": PARENT_GUID,
        },
        {"name": "c"},
    ],
    ids=[
        "guid-glossary",
        "guid-qualified-name",
        "guid-glossary-guid",
        "two-glossaries",
        "two-parents",
        "no-identity",
    ],
)
def test_atlas_glossary_category_module_rejects_bad_argument_combinations(
    module_args,
    client,
    extra,
):
    """Test conflicting or missing identity options fail before any request."""
    _fail(module_args, **extra)

    for mock in client.values():
        mock.assert_not_called()


# ---------------------------------------------------------------- absent: children

CHILD_GUID = "11111111-1111-4111-8111-111111111111"
GRANDCHILD_GUID = "22222222-2222-4222-8222-222222222222"
SIBLING_GUID = "33333333-3333-4333-8333-333333333333"


def _with_children(parent=None):
    return AtlasGlossaryCategory(
        name="Customer",
        guid=CATEGORY_GUID,
        anchor=ANCHOR,
        parent_category=parent,
        children_categories=[
            AtlasRelatedCategoryHeader(category_guid=CHILD_GUID, display_text="Retail"),
            AtlasRelatedCategoryHeader(
                category_guid=SIBLING_GUID,
                display_text="Corporate",
            ),
        ],
    )


def test_atlas_glossary_category_module_delete_moves_children_to_the_parent(
    module_args,
    client,
):
    """Test the children of a deleted nested category move up to its parent."""
    calls = []
    client["delete_category"].side_effect = lambda *a: calls.append("delete")
    client["link_category_parent"].side_effect = lambda *a: calls.append("link")
    client["find_categories"].return_value = [
        _with_children(
            AtlasRelatedCategoryHeader(
                category_guid=PARENT_GUID,
                relation_guid=RELATION_GUID,
            ),
        ),
    ]
    client["get_category"].return_value = None

    result = _run(module_args, glossary="Bank", name="Customer", state="absent")

    assert result["changed"] is True
    assert calls == ["delete", "link", "link"]
    assert [c.args for c in client["link_category_parent"].call_args_list] == [
        (PARENT_GUID, CHILD_GUID),
        (PARENT_GUID, SIBLING_GUID),
    ]


def test_atlas_glossary_category_module_delete_leaves_children_top_level_without_a_parent(
    module_args,
    client,
):
    """Test the children of a deleted top-level category stay top-level."""
    client["find_categories"].return_value = [_with_children()]
    client["get_category"].return_value = None

    _run(module_args, glossary="Bank", name="Customer", state="absent")

    client["delete_category"].assert_called_once_with(CATEGORY_GUID)
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_cascade_deletes_descendants_first(
    module_args,
    client,
):
    """Test a cascade deletes the descendants, deepest first, then the category."""
    client["find_categories"].return_value = [_with_children()]
    client["get_category"].return_value = None
    client["list_category_headers"].return_value = [
        AtlasRelatedCategoryHeader(
            category_guid=CATEGORY_GUID,
            display_text="Customer",
        ),
        AtlasRelatedCategoryHeader(
            category_guid=CHILD_GUID,
            parent_category_guid=CATEGORY_GUID,
            display_text="Retail",
        ),
        AtlasRelatedCategoryHeader(
            category_guid=GRANDCHILD_GUID,
            parent_category_guid=CHILD_GUID,
            display_text="Gold",
        ),
        AtlasRelatedCategoryHeader(
            category_guid=SIBLING_GUID,
            parent_category_guid=CATEGORY_GUID,
            display_text="Corporate",
        ),
        AtlasRelatedCategoryHeader(category_guid="other", display_text="Unrelated"),
    ]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        state="absent",
        cascade=True,
    )

    assert result["changed"] is True
    assert [c.args[0] for c in client["delete_category"].call_args_list] == [
        GRANDCHILD_GUID,
        CHILD_GUID,
        SIBLING_GUID,
        CATEGORY_GUID,
    ]
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_cascade_without_children_deletes_the_category(
    module_args,
    client,
):
    """Test a cascade on a childless category is a plain delete."""
    client["find_categories"].return_value = [EXISTING]
    client["get_category"].return_value = None

    _run(module_args, glossary="Bank", name="Customer", state="absent", cascade=True)

    client["delete_category"].assert_called_once_with(CATEGORY_GUID)


def test_atlas_glossary_category_module_cascade_check_mode_and_diff(
    module_args,
    client,
):
    """Test check mode deletes nothing and the diff names the categories that go."""
    client["find_categories"].return_value = [_with_children()]
    client["list_category_headers"].return_value = [
        AtlasRelatedCategoryHeader(
            category_guid=CHILD_GUID,
            parent_category_guid=CATEGORY_GUID,
            display_text="Retail",
        ),
    ]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        state="absent",
        cascade=True,
        _ansible_check_mode=True,
        _ansible_diff=True,
    )

    assert result["changed"] is True
    client["delete_category"].assert_not_called()
    assert result["diff"] == {
        "before": {
            "category": {"name": "Customer", "descendant_categories": ["Retail"]},
        },
        "after": {},
    }


def test_atlas_glossary_category_module_check_mode_delete_moves_nothing(
    module_args,
    client,
):
    """Test check mode neither deletes nor re-links the children."""
    client["find_categories"].return_value = [
        _with_children(AtlasRelatedCategoryHeader(category_guid=PARENT_GUID)),
    ]

    result = _run(
        module_args,
        glossary="Bank",
        name="Customer",
        state="absent",
        _ansible_check_mode=True,
    )

    assert result["changed"] is True
    client["delete_category"].assert_not_called()
    client["link_category_parent"].assert_not_called()


def test_atlas_glossary_category_module_cascade_needs_state_absent(module_args, client):
    """Test cascade is refused with state present."""
    result = _fail(module_args, glossary="Bank", name="Customer", cascade=True)

    assert "'cascade' can only be used with state 'absent'" in result["msg"]
    for mock in client.values():
        mock.assert_not_called()


def test_atlas_glossary_category_module_cascade_delete_failure_is_reported(
    module_args,
    client,
):
    """Test an Atlas error while deleting a descendant ends the task."""
    from ansible_collections.cloudera.services.plugins.module_utils.common import (
        ServicesError,
    )

    client["find_categories"].return_value = [_with_children()]
    client["list_category_headers"].return_value = [
        AtlasRelatedCategoryHeader(
            category_guid=CHILD_GUID,
            parent_category_guid=CATEGORY_GUID,
            display_text="Retail",
        ),
    ]
    client["delete_category"].side_effect = ServicesError("Atlas said no")

    result = _fail(
        module_args,
        glossary="Bank",
        name="Customer",
        state="absent",
        cascade=True,
    )

    assert "Atlas said no" in result["msg"]
