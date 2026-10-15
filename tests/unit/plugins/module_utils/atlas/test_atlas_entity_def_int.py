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
    AtlasEntityDef,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]


def test_create_entity_def(request, atlas_typedef_client, atlas_purge_typedef):
    """Test creating an entity typedef."""
    name = atlas_purge_typedef(f"ansible_test_create_{request.node.name.lower()}")

    response = atlas_typedef_client.create_entity_def(
        AtlasEntityDef(
            name=name,
            attribute_defs=[AtlasAttributeDef(name="level", type_name="string")],
        ),
    )

    assert isinstance(response, AtlasEntityDef)
    assert response.name == name
    assert response.guid is not None
    assert [a.name for a in response.attribute_defs] == ["level"]


def test_get_entity_def_by_name_not_found(atlas_typedef_client):
    """Test a missing entity typedef returns None (verifies Atlas 404 behavior)."""
    assert atlas_typedef_client.get_entity_def_by_name("ansible_test_missing") is None


def test_update_entity_def(atlas_typedef_client, atlas_deletable_entity_def):
    """Test updating an entity typedef description."""
    updated = atlas_typedef_client.update_entity_def(
        AtlasEntityDef(
            name=atlas_deletable_entity_def.name,
            description="updated",
            attribute_defs=atlas_deletable_entity_def.attribute_defs,
        ),
    )

    assert updated.description == "updated"


def test_update_entity_def_round_trips_read_only_fields(
    atlas_typedef_client,
    atlas_deletable_entity_def,
):
    """Test sending back a def read from Atlas (relationship/business defs included) is accepted."""
    existing = atlas_typedef_client.get_entity_def_by_name(
        atlas_deletable_entity_def.name,
    )
    existing.description = "round trip"

    updated = atlas_typedef_client.update_entity_def(existing)

    assert updated.description == "round trip"
