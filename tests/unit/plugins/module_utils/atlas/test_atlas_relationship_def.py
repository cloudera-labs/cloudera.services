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

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasTypeDefClient,
    align_relationship_end_def,
)

# Atlas returns typedef objects with camelCase keys.
RELATIONSHIP_RESPONSE = {
    "category": "RELATIONSHIP",
    "guid": "rel-guid-1",
    "createdBy": "admin",
    "updatedBy": "admin",
    "createTime": 1700000000000,
    "updateTime": 1700000000000,
    "version": 1,
    "name": "test_relationship",
    "description": "Test relationship",
    "typeVersion": "1.0",
    "options": {"k": "v"},
    "attributeDefs": [
        {
            "name": "weight",
            "typeName": "int",
            "isOptional": True,
            "cardinality": "SINGLE",
        },
    ],
    "relationshipCategory": "ASSOCIATION",
    "relationshipLabel": "r:test_relationship",
    "propagateTags": "NONE",
    "endDef1": {
        "type": "test_parent",
        "name": "children",
        "isContainer": True,
        "cardinality": "SET",
        "isLegacyAttribute": False,
        "description": "first end",
    },
    "endDef2": {
        "type": "test_child",
        "name": "parent",
        "isContainer": False,
        "cardinality": "SINGLE",
        "isLegacyAttribute": False,
    },
}


def test_get_relationship_def_by_name(mocker):
    """Test an Atlas relationship typedef response maps onto AtlasRelationshipDef."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = RELATIONSHIP_RESPONSE

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.get_relationship_def_by_name("test_relationship")

    assert result == AtlasRelationshipDef(
        name="test_relationship",
        description="Test relationship",
        type_version="1.0",
        options={"k": "v"},
        attribute_defs=[
            AtlasAttributeDef(
                name="weight",
                type_name="int",
                is_optional=True,
                cardinality="SINGLE",
            ),
        ],
        relationship_category="ASSOCIATION",
        relationship_label="r:test_relationship",
        propagate_tags="NONE",
        end_def1=AtlasRelationshipEndDef(
            type="test_parent",
            name="children",
            is_container=True,
            cardinality="SET",
            is_legacy_attribute=False,
            description="first end",
        ),
        end_def2=AtlasRelationshipEndDef(
            type="test_child",
            name="parent",
            is_container=False,
            cardinality="SINGLE",
            is_legacy_attribute=False,
        ),
        category="RELATIONSHIP",
        guid="rel-guid-1",
        version=1,
        create_time=1700000000000,
        update_time=1700000000000,
        created_by="admin",
        updated_by="admin",
    )

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/types/relationshipdef/name/test_relationship",
        squelch={404: None},
    )


def test_get_relationship_def_by_name_not_found(mocker):
    """Test a missing relationship typedef returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.get_relationship_def_by_name("missing") is None


def test_create_relationship_def(mocker):
    """Test create POSTs a relationshipDefs bundle with camelCase end defs."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "enumDefs": [],
        "relationshipDefs": [RELATIONSHIP_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_relationship_def(
        AtlasRelationshipDef(
            name="test_relationship",
            options={"my_key": "v"},
            relationship_category="ASSOCIATION",
            propagate_tags="NONE",
            end_def1=AtlasRelationshipEndDef(
                type="test_parent",
                name="children",
                is_container=True,
                cardinality="SET",
            ),
            end_def2=AtlasRelationshipEndDef(
                type="test_child",
                name="parent",
                cardinality="SINGLE",
            ),
        ),
    )

    assert isinstance(result, AtlasRelationshipDef)
    assert result.guid == "rel-guid-1"

    api_client.post.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "relationshipDefs": [
                {
                    "name": "test_relationship",
                    "options": {"my_key": "v"},
                    "relationshipCategory": "ASSOCIATION",
                    "propagateTags": "NONE",
                    "endDef1": {
                        "type": "test_parent",
                        "name": "children",
                        "isContainer": True,
                        "cardinality": "SET",
                    },
                    "endDef2": {
                        "type": "test_child",
                        "name": "parent",
                        "cardinality": "SINGLE",
                    },
                },
            ],
        },
    )


def test_create_relationship_def_picks_written_def_from_bundle(mocker):
    """Test the created def is matched by name, not taken from position."""
    other = dict(RELATIONSHIP_RESPONSE, name="other_relationship", guid="other-guid")
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "relationshipDefs": [other, RELATIONSHIP_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_relationship_def(
        AtlasRelationshipDef(name="test_relationship"),
    )

    assert result.guid == "rel-guid-1"


def test_create_relationship_def_missing_from_bundle(mocker):
    """Test a bundle without the written relationship raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"relationshipDefs": []}

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="test_relationship"):
        client.create_relationship_def(AtlasRelationshipDef(name="test_relationship"))


def test_update_relationship_def(mocker):
    """Test update PUTs a relationshipDefs bundle and returns the updated def."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"relationshipDefs": [RELATIONSHIP_RESPONSE]}

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.update_relationship_def(
        AtlasRelationshipDef(name="test_relationship", description="new"),
    )

    assert result.guid == "rel-guid-1"
    api_client.put.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "relationshipDefs": [
                {"name": "test_relationship", "description": "new"},
            ],
        },
    )


def test_align_relationship_end_def_fills_unset_from_existing():
    """Test unset end fields take Atlas's values while set fields win."""
    existing = AtlasRelationshipEndDef(
        type="test_parent",
        name="children",
        is_container=True,
        cardinality="SET",
        is_legacy_attribute=False,
        description="first end",
    )
    incoming = AtlasRelationshipEndDef(
        type="test_parent",
        name="children",
        cardinality="LIST",
    )

    aligned = align_relationship_end_def(incoming, existing)

    assert aligned == AtlasRelationshipEndDef(
        type="test_parent",
        name="children",
        is_container=True,
        cardinality="LIST",
        is_legacy_attribute=False,
        description="first end",
    )
    assert incoming.is_container is NULLABLE
