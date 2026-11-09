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

from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
)
from ansible_collections.cloudera.services.tests.unit import AnsibleFailJson

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]

UNKNOWN_GUID = "00000000-0000-0000-0000-000000000000"


def test_create_glossary(
    atlas_glossary_client,
    atlas_cleanup_glossary,
    atlas_glossary_name,
):
    """Test creating a glossary returns it as Atlas stored it, qualified name derived."""
    glossary = atlas_glossary_client.create_glossary(
        AtlasGlossary(name=atlas_glossary_name),
    )
    atlas_cleanup_glossary(str(glossary.guid))

    assert isinstance(glossary, AtlasGlossary)
    assert glossary.guid
    assert glossary.name == atlas_glossary_name
    assert glossary.qualified_name == atlas_glossary_name


def test_create_glossary_with_attributes(
    atlas_glossary_client,
    atlas_cleanup_glossary,
    atlas_glossary_name,
):
    """Test an explicit qualified name and the descriptive fields are stored."""
    glossary = atlas_glossary_client.create_glossary(
        AtlasGlossary(
            name=atlas_glossary_name,
            qualified_name=f"{atlas_glossary_name}_qn",
            short_description="short",
            long_description="long",
            language="English",
            usage="testing",
        ),
    )
    atlas_cleanup_glossary(str(glossary.guid))

    assert glossary.qualified_name == f"{atlas_glossary_name}_qn"
    assert glossary.short_description == "short"
    assert glossary.long_description == "long"
    assert glossary.language == "English"
    assert glossary.usage == "testing"


def test_create_glossary_with_the_name_of_an_existing_one_fails(
    atlas_rest_client,
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test a second glossary with the same qualified name is refused."""
    # The real client turns the HTTP 409 into a fail_json call; the fixture's mock
    # raises AnsibleFailJson and keeps Atlas's message in the call arguments.
    with pytest.raises(AnsibleFailJson):
        atlas_glossary_client.create_glossary(
            AtlasGlossary(name=str(atlas_deletable_glossary.name)),
        )

    assert (
        "already exists" in atlas_rest_client.module.fail_json.call_args.kwargs["msg"]
    )


@pytest.mark.parametrize("character", ["@", ".", "<", ">"])
def test_create_glossary_with_a_reserved_character_fails(
    atlas_rest_client,
    atlas_glossary_client,
    atlas_glossary_name,
    character,
):
    """Test a name containing @ . < > is refused, and nothing is created."""
    name = f"{atlas_glossary_name}{character}x"

    with pytest.raises(AnsibleFailJson):
        atlas_glossary_client.create_glossary(AtlasGlossary(name=name))

    assert "special chars" in atlas_rest_client.module.fail_json.call_args.kwargs["msg"]
    assert atlas_glossary_client.find_glossaries(name=name) == []


def test_get_glossary(atlas_glossary_client, atlas_deletable_glossary):
    """Test a guid lookup returns the glossary."""
    glossary = atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid))

    assert glossary is not None
    assert glossary.guid == atlas_deletable_glossary.guid
    assert glossary.name == atlas_deletable_glossary.name


def test_get_glossary_unknown_guid(atlas_glossary_client):
    """Test an unknown guid returns None."""
    assert atlas_glossary_client.get_glossary(UNKNOWN_GUID) is None


def test_list_glossaries(atlas_glossary_client, atlas_deletable_glossary):
    """Test the listing includes a glossary that was just created."""
    guids = [g.guid for g in atlas_glossary_client.list_glossaries()]

    assert atlas_deletable_glossary.guid in guids


def test_find_glossaries_by_name(atlas_glossary_client, atlas_deletable_glossary):
    """Test a name lookup finds the glossary."""
    found = atlas_glossary_client.find_glossaries(
        name=str(atlas_deletable_glossary.name),
    )

    assert [g.guid for g in found] == [atlas_deletable_glossary.guid]


def test_find_glossaries_by_qualified_name(
    atlas_glossary_client,
    atlas_deletable_glossary,
):
    """Test a qualified name lookup finds the glossary."""
    found = atlas_glossary_client.find_glossaries(
        qualified_name=str(atlas_deletable_glossary.qualified_name),
    )

    assert [g.guid for g in found] == [atlas_deletable_glossary.guid]


def test_find_glossaries_without_a_match(atlas_glossary_client, atlas_glossary_name):
    """Test a name nothing carries returns an empty list."""
    assert atlas_glossary_client.find_glossaries(name=atlas_glossary_name) == []


def test_delete_glossary(atlas_glossary_client, atlas_deletable_glossary):
    """Test a deleted glossary is gone for good: not found by guid, not listed."""
    atlas_glossary_client.delete_glossary(str(atlas_deletable_glossary.guid))

    assert (
        atlas_glossary_client.get_glossary(str(atlas_deletable_glossary.guid)) is None
    )
    assert atlas_deletable_glossary.guid not in [
        g.guid for g in atlas_glossary_client.list_glossaries()
    ]


def test_delete_glossary_unknown_guid(atlas_glossary_client):
    """Test deleting a glossary that does not exist is not an error."""
    atlas_glossary_client.delete_glossary(UNKNOWN_GUID)


def test_create_glossary_again_after_delete(
    atlas_glossary_client,
    atlas_cleanup_glossary,
    atlas_deletable_glossary,
):
    """Test the name of a deleted glossary can be used again, with a new guid."""
    atlas_glossary_client.delete_glossary(str(atlas_deletable_glossary.guid))

    again = atlas_glossary_client.create_glossary(
        AtlasGlossary(name=str(atlas_deletable_glossary.name)),
    )
    atlas_cleanup_glossary(str(again.guid))

    assert again.guid != atlas_deletable_glossary.guid
    assert again.name == atlas_deletable_glossary.name
