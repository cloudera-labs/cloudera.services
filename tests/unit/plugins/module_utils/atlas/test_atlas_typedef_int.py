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

from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasEnumDef,
    AtlasEnumElementDef,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]


def test_create_enum_def(request, atlas_typedef_client, atlas_purge_typedef):
    """Test creating an enum typedef."""
    name = atlas_purge_typedef(f"ansible_test_create_{request.node.name.lower()}")

    response = atlas_typedef_client.create_enum_def(
        AtlasEnumDef(
            name=name,
            element_defs=[AtlasEnumElementDef(value="RED")],
        ),
    )

    assert isinstance(response, AtlasEnumDef)
    assert response.name == name
    assert response.guid is not None
    assert isinstance(response.element_defs, list)
    assert all(isinstance(e, AtlasEnumElementDef) for e in response.element_defs)
    assert [e.value for e in response.element_defs] == ["RED"]


def test_get_enum_def_by_name_not_found(atlas_typedef_client):
    """Test a missing enum typedef returns None (verifies Atlas 404 behavior)."""
    assert atlas_typedef_client.get_enum_def_by_name("ansible_test_missing") is None


def test_update_enum_def_add_element(atlas_typedef_client, atlas_deletable_enum_def):
    """Test adding an enum element."""
    existing = atlas_typedef_client.get_enum_def_by_name(atlas_deletable_enum_def.name)
    existing.element_defs.append(AtlasEnumElementDef(value="BLUE"))

    response = atlas_typedef_client.update_enum_def(existing)

    assert [e.value for e in response.element_defs] == ["RED", "BLUE"]


def test_delete_typedef_by_name(atlas_typedef_client, atlas_deletable_enum_def):
    """Test deleting a typedef, and that deleting again is a no-op."""
    atlas_typedef_client.delete_typedef_by_name(atlas_deletable_enum_def.name)
    atlas_typedef_client.delete_typedef_by_name(atlas_deletable_enum_def.name)

    assert (
        atlas_typedef_client.get_enum_def_by_name(atlas_deletable_enum_def.name) is None
    )


def test_list_typedef_headers(atlas_typedef_client, atlas_existing_enum_def):
    """Test the existing enum appears in the header list."""
    headers = atlas_typedef_client.list_typedef_headers()

    assert any(
        h["name"] == atlas_existing_enum_def.name and h["category"] == "ENUM"
        for h in headers
    )


def test_get_typedef_by_name(atlas_typedef_client, atlas_existing_enum_def):
    """Test retrieving any typedef by name."""
    typedef = atlas_typedef_client.get_typedef_by_name(atlas_existing_enum_def.name)

    assert typedef["category"] == "ENUM"
    assert typedef["name"] == atlas_existing_enum_def.name
