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
    AtlasAttributeDef,
    AtlasStructDef,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]


def test_create_struct_def(request, atlas_typedef_client, atlas_purge_typedef):
    """Test creating a struct typedef."""
    name = atlas_purge_typedef(f"ansible_test_create_{request.node.name.lower()}")

    response = atlas_typedef_client.create_struct_def(
        AtlasStructDef(
            name=name,
            attribute_defs=[AtlasAttributeDef(name="street", type_name="string")],
        ),
    )

    assert isinstance(response, AtlasStructDef)
    assert response.name == name
    assert response.guid is not None
    assert isinstance(response.attribute_defs, list)
    assert all(isinstance(a, AtlasAttributeDef) for a in response.attribute_defs)
    assert [a.name for a in response.attribute_defs] == ["street"]


def test_get_struct_def_by_name_not_found(atlas_typedef_client):
    """Test a missing struct typedef returns None (verifies Atlas 404 behavior)."""
    assert atlas_typedef_client.get_struct_def_by_name("ansible_test_missing") is None


def test_update_struct_def(
    atlas_typedef_client,
    atlas_deletable_struct_def,
):
    """Test updating a struct typedef description."""
    updated = atlas_typedef_client.update_struct_def(
        AtlasStructDef(
            name=atlas_deletable_struct_def.name,
            description="updated",
            attribute_defs=atlas_deletable_struct_def.attribute_defs,
        ),
    )

    assert updated.description == "updated"
