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
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
)

REQUIRED_ENV_VARS = [
    "ATLAS_API_URL",
    "ATLAS_API_USERNAME",
    "ATLAS_API_PASSWORD",
]


def test_create_relationship_def(
    request,
    atlas_typedef_client,
    atlas_relationship_end_types,
    atlas_purge_typedef,
):
    """Test creating a relationship typedef."""
    parent, child = atlas_relationship_end_types
    name = f"ansible_test_create_{request.node.name.lower()}"

    atlas_purge_typedef(name)

    response = atlas_typedef_client.create_relationship_def(
        AtlasRelationshipDef(
            name=name,
            relationship_category="ASSOCIATION",
            propagate_tags="NONE",
            end_def1=AtlasRelationshipEndDef(
                type=parent,
                name="ansible_test_children",
                cardinality="SET",
            ),
            end_def2=AtlasRelationshipEndDef(
                type=child,
                name="ansible_test_parent",
                cardinality="SINGLE",
            ),
        ),
    )

    assert isinstance(response, AtlasRelationshipDef)
    assert response.name == name
    assert response.guid is not None
    assert isinstance(response.end_def1, AtlasRelationshipEndDef)
    assert (response.end_def1.type, response.end_def1.name) == (
        parent,
        "ansible_test_children",
    )
    assert isinstance(response.end_def2, AtlasRelationshipEndDef)
    assert (response.end_def2.type, response.end_def2.name) == (
        child,
        "ansible_test_parent",
    )


def test_get_relationship_def_by_name_not_found(atlas_typedef_client):
    """Test a missing relationship typedef returns None (verifies Atlas 404 behavior)."""
    assert (
        atlas_typedef_client.get_relationship_def_by_name("ansible_test_missing")
        is None
    )


def test_update_relationship_def(
    atlas_typedef_client,
    atlas_deletable_relationship_def,
):
    """Test updating a relationship typedef description."""
    existing = atlas_deletable_relationship_def

    updated = atlas_typedef_client.update_relationship_def(
        AtlasRelationshipDef(
            name=existing.name,
            description="updated",
            relationship_category=existing.relationship_category,
            propagate_tags=existing.propagate_tags,
            end_def1=existing.end_def1,
            end_def2=existing.end_def2,
        ),
    )

    assert updated.description == "updated"
