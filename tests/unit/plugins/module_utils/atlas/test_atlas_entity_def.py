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
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasEntityDef,
    AtlasRelationshipAttributeDef,
    AtlasTypeDefClient,
)

# Atlas returns typedef objects with camelCase keys.
ENTITY_RESPONSE = {
    "category": "ENTITY",
    "guid": "ent-guid-1",
    "createdBy": "admin",
    "updatedBy": "admin",
    "createTime": 1700000000000,
    "updateTime": 1700000000000,
    "version": 1,
    "name": "test_entity",
    "description": "Test entity",
    "typeVersion": "1.0",
    "options": {"k": "v"},
    "attributeDefs": [
        {
            "name": "owner",
            "typeName": "string",
            "isOptional": True,
            "cardinality": "SINGLE",
        },
    ],
    "superTypes": ["DataSet"],
    "subTypes": ["child_entity"],
    "relationshipAttributeDefs": [
        {
            "name": "columns",
            "typeName": "array<hive_column>",
            "isOptional": True,
            "relationshipTypeName": "hive_table_columns",
            "isLegacyAttribute": True,
        },
    ],
    "businessAttributeDefs": {},
}

CLASSIFICATION_LIKE = {"category": "CLASSIFICATION", "name": "test_entity"}


def test_get_entity_def_by_name(mocker):
    """Test an Atlas entity typedef response maps onto AtlasEntityDef."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = ENTITY_RESPONSE

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.get_entity_def_by_name("test_entity")

    assert result == AtlasEntityDef(
        name="test_entity",
        description="Test entity",
        type_version="1.0",
        options={"k": "v"},
        attribute_defs=[
            AtlasAttributeDef(
                name="owner",
                type_name="string",
                is_optional=True,
                cardinality="SINGLE",
            ),
        ],
        super_types=["DataSet"],
        sub_types=["child_entity"],
        relationship_attribute_defs=[
            AtlasRelationshipAttributeDef(
                name="columns",
                type_name="array<hive_column>",
                is_optional=True,
                relationship_type_name="hive_table_columns",
                is_legacy_attribute=True,
            ),
        ],
        business_attribute_defs={},
        category="ENTITY",
        guid="ent-guid-1",
        version=1,
        create_time=1700000000000,
        update_time=1700000000000,
        created_by="admin",
        updated_by="admin",
    )

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/types/entitydef/name/test_entity",
        squelch={404: None},
    )


def test_get_entity_def_by_name_not_found(mocker):
    """Test a missing entity typedef returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.get_entity_def_by_name("missing") is None


def test_create_entity_def(mocker):
    """Test create POSTs an entityDefs bundle and returns the created def."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "classificationDefs": [],
        "entityDefs": [ENTITY_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_entity_def(
        AtlasEntityDef(
            name="test_entity",
            super_types=["DataSet"],
            options={"my_key": "v"},
            attribute_defs=[
                AtlasAttributeDef(
                    name="owner",
                    type_name="string",
                    is_optional=True,
                    options={"my_opt": "x"},
                ),
            ],
        ),
    )

    assert isinstance(result, AtlasEntityDef)
    assert result.guid == "ent-guid-1"

    api_client.post.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "entityDefs": [
                {
                    "name": "test_entity",
                    "superTypes": ["DataSet"],
                    "options": {"my_key": "v"},
                    "attributeDefs": [
                        {
                            "name": "owner",
                            "typeName": "string",
                            "isOptional": True,
                            "options": {"my_opt": "x"},
                        },
                    ],
                },
            ],
        },
    )


def test_update_entity_def(mocker):
    """Test update PUTs an entityDefs bundle and returns the updated def."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"entityDefs": [ENTITY_RESPONSE]}

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.update_entity_def(
        AtlasEntityDef(name="test_entity", description="new"),
    )

    assert result.guid == "ent-guid-1"
    api_client.put.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={"entityDefs": [{"name": "test_entity", "description": "new"}]},
    )


def test_business_attribute_defs_keys_round_trip_verbatim(mocker):
    """Test business metadata names (map keys) are never case-converted, but their attributes are."""
    response = dict(ENTITY_RESPONSE)
    response["businessAttributeDefs"] = {
        "myMetadata": [{"name": "cost", "typeName": "int", "isOptional": True}],
    }
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"entityDefs": [response]}

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.update_entity_def(
        AtlasEntityDef(
            name="test_entity",
            business_attribute_defs={
                "myMetadata": [
                    {"name": "cost", "type_name": "int", "is_optional": True},
                ],
            },
        ),
    )

    sent = api_client.put.call_args.kwargs["data"]["entityDefs"][0]
    assert sent["businessAttributeDefs"] == {
        "myMetadata": [{"name": "cost", "typeName": "int", "isOptional": True}],
    }
    assert result.business_attribute_defs == {
        "myMetadata": [{"name": "cost", "type_name": "int", "is_optional": True}],
    }


@pytest.mark.parametrize(
    "bundle",
    [{}, {"entityDefs": []}, {"classificationDefs": [CLASSIFICATION_LIKE]}],
    ids=["empty", "empty-entity-defs", "wrong-category"],
)
@pytest.mark.parametrize("method", ["create_entity_def", "update_entity_def"])
def test_write_entity_def_without_entity_in_response_raises(mocker, method, bundle):
    """Test a bundle that lacks the written entity def raises a ServicesError, not a KeyError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = bundle
    api_client.put.return_value = bundle

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="test_entity"):
        getattr(client, method)(AtlasEntityDef(name="test_entity"))


@pytest.mark.parametrize(
    "method, verb",
    [
        ("create_entity_def", "post"),
        ("update_entity_def", "put"),
    ],
)
def test_write_entity_def_error_propagates(mocker, method, verb):
    """Test an Atlas error on write propagates as a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    getattr(api_client, verb).side_effect = ServicesError(
        "ATLAS-400-00-0AB: bad type",
        status=400,
    )

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="bad type"):
        getattr(client, method)(AtlasEntityDef(name="test_entity"))


def test_delete_typedef_error_propagates(mocker):
    """Test an Atlas error on delete (e.g. type still referenced) propagates."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.side_effect = ServicesError("type is referenced", status=400)

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="referenced"):
        client.delete_typedef_by_name("test_entity")
