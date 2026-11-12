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

from ansible_collections.cloudera.services.plugins.modules import atlas_glossary
from ansible_collections.cloudera.services.plugins.module_utils.common import NULLABLE
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    GLOSSARY_API,
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


def _add_term(atlas_rest_client, glossary, name: str) -> str:
    """Set up a term through the REST API, since the client has no term methods yet."""
    term = atlas_rest_client.post(
        f"{GLOSSARY_API}/term",
        data={"name": name, "anchor": {"glossaryGuid": glossary.guid}},
    )
    return term["guid"]


def _assign_term(atlas_rest_client, term_guid: str, entity_guid: str) -> None:
    atlas_rest_client.post(
        f"{GLOSSARY_API}/terms/{term_guid}/assignedEntities",
        data=[{"guid": entity_guid}],
    )


# ---------------------------------------------------------------- create


def test_atlas_glossary_module_create(
    atlas_module_args,
    atlas_glossary_client,
    atlas_cleanup_glossary,
    atlas_glossary_name,
):
    """Test a glossary that does not exist is created."""
    atlas_module_args({"name": atlas_glossary_name, "short_description": "first"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    guid = atlas_cleanup_glossary(e.value["glossary"]["guid"])
    glossary = atlas_glossary_client.get_glossary(guid)
    assert glossary is not None
    assert glossary.name == atlas_glossary_name
    assert glossary.qualified_name == atlas_glossary_name
    assert glossary.short_description == "first"


def test_atlas_glossary_module_create_with_a_qualified_name(
    atlas_module_args,
    atlas_glossary_client,
    atlas_cleanup_glossary,
    atlas_glossary_name,
):
    """Test the qualified name is stored as given, apart from the name."""
    atlas_module_args(
        {"name": atlas_glossary_name, "qualified_name": f"{atlas_glossary_name}_qn"},
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    guid = atlas_cleanup_glossary(e.value["glossary"]["guid"])
    glossary = atlas_glossary_client.get_glossary(guid)
    assert glossary is not None
    assert glossary.qualified_name == f"{atlas_glossary_name}_qn"
    assert glossary.name == atlas_glossary_name


def test_atlas_glossary_module_create_is_idempotent(
    atlas_module_args,
    atlas_deletable_glossary,
):
    """Test a glossary that exists with the requested values is left alone."""
    atlas_module_args(
        {
            "name": atlas_deletable_glossary.name,
            "short_description": atlas_deletable_glossary.short_description,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is False
    assert e.value["glossary"]["guid"] == atlas_deletable_glossary.guid


def test_atlas_glossary_module_create_with_an_invalid_name_fails(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_name,
):
    """Test a name with a reserved character fails and nothing is created."""
    atlas_module_args({"name": f"{atlas_glossary_name}.x"})

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "may not contain" in e.value["msg"]
    assert atlas_glossary_client.find_glossaries(name=f"{atlas_glossary_name}.x") == []


def test_atlas_glossary_module_create_needs_a_name_when_given_a_qualified_name(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_name,
):
    """Test a missing glossary cannot be created from a qualified name alone."""
    atlas_module_args({"qualified_name": atlas_glossary_name})

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "'name' is required" in e.value["msg"]
    assert (
        atlas_glossary_client.find_glossaries(qualified_name=atlas_glossary_name) == []
    )


def test_atlas_glossary_module_unknown_guid_fails(atlas_module_args):
    """Test a guid nothing carries fails rather than creating a glossary."""
    atlas_module_args({"guid": UNKNOWN_GUID, "name": "ansible_test_unknown_guid"})

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert UNKNOWN_GUID in e.value["msg"]


def test_atlas_glossary_module_ambiguous_name_fails(
    atlas_module_args,
    atlas_glossary_client,
    atlas_cleanup_glossary,
    atlas_deletable_glossary,
):
    """Test a name two glossaries carry is refused rather than guessed."""
    twin = atlas_glossary_client.create_glossary(
        AtlasGlossary(
            name=str(atlas_deletable_glossary.name),
            qualified_name=f"{atlas_deletable_glossary.name}_twin",
        ),
    )
    atlas_cleanup_glossary(str(twin.guid))

    atlas_module_args({"name": atlas_deletable_glossary.name, "usage": "u"})

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "qualified_name" in e.value["msg"]


# ---------------------------------------------------------------- update


def test_atlas_glossary_module_update(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test a changed description is updated in place."""
    atlas_module_args(
        {"name": atlas_deletable_glossary.name, "long_description": "new"},
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    assert e.value["glossary"]["guid"] == atlas_deletable_glossary.guid
    glossary = atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
    assert glossary is not None
    assert glossary.long_description == "new"
    assert glossary.short_description == atlas_deletable_glossary.short_description


def test_atlas_glossary_module_update_is_idempotent(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test a glossary already holding the updated value is left alone."""
    atlas_glossary_client.partial_update_glossary(
        str(atlas_deletable_glossary.guid),
        {"language": "French"},
    )

    atlas_module_args({"name": atlas_deletable_glossary.name, "language": "French"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is False


def test_atlas_glossary_module_update_keeps_the_fields_not_named(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test an update leaves the fields the task does not mention as they are."""
    atlas_module_args({"name": atlas_deletable_glossary.name, "usage": "u"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    glossary = atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
    assert glossary is not None
    assert glossary.usage == "u"
    assert glossary.short_description == atlas_deletable_glossary.short_description
    assert glossary.qualified_name == atlas_deletable_glossary.qualified_name


def test_atlas_glossary_module_empty_string_clears_a_field(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test an empty string clears a field that holds a value."""
    atlas_module_args(
        {"name": atlas_deletable_glossary.name, "short_description": ""},
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    glossary = atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
    assert glossary is not None
    assert glossary.short_description in (NULLABLE, None, "")


def test_atlas_glossary_module_rename_by_guid(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
    atlas_glossary_name,
):
    """Test a guid identity lets the name change; the qualified name stays."""
    atlas_module_args(
        {"guid": atlas_deletable_glossary.guid, "name": atlas_glossary_name},
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    glossary = atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
    assert glossary is not None
    assert glossary.name == atlas_glossary_name
    assert glossary.qualified_name == atlas_deletable_glossary.qualified_name


def test_atlas_glossary_module_rename_by_qualified_name(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
    atlas_glossary_name,
):
    """Test a qualified name identity lets the name change too."""
    atlas_module_args(
        {
            "qualified_name": atlas_deletable_glossary.qualified_name,
            "name": atlas_glossary_name,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    glossary = atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
    assert glossary is not None
    assert glossary.name == atlas_glossary_name


# ---------------------------------------------------------------- check mode


def test_atlas_glossary_module_check_mode_create(
    atlas_module_args,
    atlas_glossary_client,
    atlas_glossary_name,
):
    """Test check mode reports a create without creating the glossary."""
    atlas_module_args({"name": atlas_glossary_name, "_ansible_check_mode": True})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    assert atlas_glossary_client.find_glossaries(name=atlas_glossary_name) == []


def test_atlas_glossary_module_check_mode_update(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test check mode reports an update without changing the glossary."""
    atlas_module_args(
        {
            "name": atlas_deletable_glossary.name,
            "usage": "changed",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    glossary = atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
    assert glossary is not None
    assert glossary.usage in (NULLABLE, None, "")


def test_atlas_glossary_module_check_mode_delete(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test check mode reports a delete without deleting the glossary."""
    atlas_module_args(
        {
            "name": atlas_deletable_glossary.name,
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    assert (
        atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
        is not None
    )


# ---------------------------------------------------------------- absent


def test_atlas_glossary_module_absent(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test absent deletes an empty glossary for good."""
    atlas_module_args({"name": atlas_deletable_glossary.name, "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    assert e.value["glossary"] == {}
    assert (
        atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid)) is None
    )


def test_atlas_glossary_module_absent_by_guid(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test absent can delete a glossary identified by its guid."""
    atlas_module_args({"guid": atlas_deletable_glossary.guid, "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    assert (
        atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid)) is None
    )


def test_atlas_glossary_module_absent_is_idempotent(
    atlas_module_args,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test absent for a glossary that is already deleted reports no change."""
    atlas_glossary_client.delete_glossary(str(atlas_deletable_glossary.guid))

    atlas_module_args({"name": atlas_deletable_glossary.name, "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is False


def test_atlas_glossary_module_absent_of_a_missing_glossary(
    atlas_module_args,
    atlas_glossary_name,
):
    """Test absent succeeds without a change for a glossary that never existed."""
    atlas_module_args({"name": atlas_glossary_name, "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is False
    assert e.value["glossary"] == {}


def test_atlas_glossary_module_absent_refuses_a_glossary_with_a_term(
    atlas_module_args,
    atlas_rest_client,
    atlas_glossary_client,
    atlas_deletable_glossary,
    atlas_glossary_name,
):
    """Test a glossary with a term is not deleted unless cascade is set."""
    _add_term(atlas_rest_client, atlas_deletable_glossary, atlas_glossary_name)

    atlas_module_args({"name": atlas_deletable_glossary.name, "state": "absent"})

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "cascade" in e.value["msg"]
    assert (
        atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
        is not None
    )


def test_atlas_glossary_module_absent_with_cascade_deletes_the_terms_too(
    atlas_module_args,
    atlas_rest_client,
    atlas_glossary_client,
    atlas_deletable_glossary,
    atlas_glossary_name,
):
    """Test cascade deletes a glossary together with its term."""
    _add_term(atlas_rest_client, atlas_deletable_glossary, atlas_glossary_name)

    atlas_module_args(
        {"name": atlas_deletable_glossary.name, "state": "absent", "cascade": True},
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()

    assert e.value["changed"] is True
    assert (
        atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid)) is None
    )


def test_atlas_glossary_module_absent_refuses_when_a_term_is_assigned(
    atlas_module_args,
    atlas_rest_client,
    atlas_glossary_client,
    atlas_deletable_glossary,
    atlas_deletable_entity,
    atlas_glossary_name,
):
    """Test a term assigned to an entity blocks the delete, even with cascade."""
    term_guid = _add_term(
        atlas_rest_client,
        atlas_deletable_glossary,
        atlas_glossary_name,
    )
    _assign_term(atlas_rest_client, term_guid, str(atlas_deletable_entity.guid))

    atlas_module_args(
        {"name": atlas_deletable_glossary.name, "state": "absent", "cascade": True},
    )

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "assigned" in e.value["msg"]
    assert (
        atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))
        is not None
    )
