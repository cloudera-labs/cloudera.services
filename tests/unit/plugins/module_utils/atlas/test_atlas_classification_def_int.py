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
    AtlasClassificationDef,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]


def test_create_classification_def(request, atlas_typedef_client, atlas_purge_typedef):
    """Test creating a classification typedef."""
    name = atlas_purge_typedef(f"ansible_test_create_{request.node.name.lower()}")

    response = atlas_typedef_client.create_classification_def(
        AtlasClassificationDef(
            name=name,
            attribute_defs=[AtlasAttributeDef(name="level", type_name="string")],
        ),
    )

    assert isinstance(response, AtlasClassificationDef)
    assert response.name == name
    assert response.guid is not None
    assert isinstance(response.attribute_defs, list)
    assert all(isinstance(a, AtlasAttributeDef) for a in response.attribute_defs)
    assert [a.name for a in response.attribute_defs] == ["level"]


def test_get_classification_def_by_name_not_found(atlas_typedef_client):
    """Test a missing classification typedef returns None (verifies Atlas 404 behavior)."""
    assert (
        atlas_typedef_client.get_classification_def_by_name("ansible_test_missing")
        is None
    )


def test_update_classification_def(
    atlas_typedef_client,
    atlas_deletable_classification_def,
):
    """Test updating a classification typedef description."""
    updated = atlas_typedef_client.update_classification_def(
        AtlasClassificationDef(
            name=atlas_deletable_classification_def.name,
            description="updated",
            attribute_defs=atlas_deletable_classification_def.attribute_defs,
        ),
    )

    assert updated.description == "updated"
