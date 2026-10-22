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
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasTypeDefClient,
)

# Atlas returns typedef objects with camelCase keys.
CLASSIFICATION_RESPONSE = {
    "category": "CLASSIFICATION",
    "guid": "cls-guid-1",
    "createdBy": "admin",
    "updatedBy": "admin",
    "createTime": 1700000000000,
    "updateTime": 1700000000000,
    "version": 1,
    "name": "test_classification",
    "description": "Test classification",
    "typeVersion": "1.0",
    "options": {"k": "v"},
    "attributeDefs": [
        {
            "name": "level",
            "typeName": "string",
            "isOptional": True,
            "cardinality": "SINGLE",
            "valuesMinCount": 0,
            "valuesMaxCount": 1,
            "isUnique": False,
            "isIndexable": True,
            "includeInNotification": False,
            "searchWeight": -1,
        },
    ],
    "superTypes": ["parent_classification"],
    "entityTypes": ["hive_table"],
    "subTypes": [],
}


def test_get_classification_def_by_name(mocker):
    """Test an Atlas classification typedef response maps onto AtlasClassificationDef."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = CLASSIFICATION_RESPONSE

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.get_classification_def_by_name("test_classification")

    assert result == AtlasClassificationDef(
        name="test_classification",
        description="Test classification",
        type_version="1.0",
        options={"k": "v"},
        attribute_defs=[
            AtlasAttributeDef(
                name="level",
                type_name="string",
                is_optional=True,
                cardinality="SINGLE",
                values_min_count=0,
                values_max_count=1,
                is_unique=False,
                is_indexable=True,
                include_in_notification=False,
                search_weight=-1,
            ),
        ],
        super_types=["parent_classification"],
        entity_types=["hive_table"],
        sub_types=[],
        category="CLASSIFICATION",
        guid="cls-guid-1",
        version=1,
        create_time=1700000000000,
        update_time=1700000000000,
        created_by="admin",
        updated_by="admin",
    )

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/types/classificationdef/name/test_classification",
        squelch={404: None},
    )


def test_get_classification_def_by_name_not_found(mocker):
    """Test a missing classification typedef returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.get_classification_def_by_name("missing") is None


def test_create_classification_def(mocker):
    """Test create POSTs a classificationDefs bundle and returns the created def."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "enumDefs": [],
        "classificationDefs": [CLASSIFICATION_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_classification_def(
        AtlasClassificationDef(
            name="test_classification",
            super_types=["parent_classification"],
            options={"my_key": "v"},
            attribute_defs=[
                AtlasAttributeDef(
                    name="level",
                    type_name="string",
                    is_optional=True,
                    options={"my_opt": "x"},
                ),
            ],
        ),
    )

    assert isinstance(result, AtlasClassificationDef)
    assert result.guid == "cls-guid-1"

    api_client.post.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "classificationDefs": [
                {
                    "name": "test_classification",
                    "superTypes": ["parent_classification"],
                    "options": {"my_key": "v"},
                    "attributeDefs": [
                        {
                            "name": "level",
                            "typeName": "string",
                            "isOptional": True,
                            "options": {"my_opt": "x"},
                        },
                    ],
                },
            ],
        },
    )


def test_constraint_params_round_trip_verbatim(mocker):
    """Test constraint params keys are neither camelCased nor snake_cased."""
    response = dict(CLASSIFICATION_RESPONSE)
    response["attributeDefs"] = [
        {
            "name": "ref",
            "typeName": "string",
            "constraints": [{"type": "ownedRef", "params": {"someKey": "v"}}],
        },
    ]
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"classificationDefs": [response]}

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_classification_def(
        AtlasClassificationDef(
            name="test_classification",
            attribute_defs=[
                AtlasAttributeDef(
                    name="ref",
                    type_name="string",
                    constraints=[
                        AtlasConstraintDef(type="ownedRef", params={"someKey": "v"}),
                    ],
                ),
            ],
        ),
    )

    sent = api_client.post.call_args.kwargs["data"]["classificationDefs"][0]
    assert sent["attributeDefs"][0]["constraints"] == [
        {"type": "ownedRef", "params": {"someKey": "v"}},
    ]
    assert result.attribute_defs == [
        AtlasAttributeDef(
            name="ref",
            type_name="string",
            constraints=[AtlasConstraintDef(type="ownedRef", params={"someKey": "v"})],
        ),
    ]


def test_update_classification_def(mocker):
    """Test update PUTs a classificationDefs bundle and returns the updated def."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"classificationDefs": [CLASSIFICATION_RESPONSE]}

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.update_classification_def(
        AtlasClassificationDef(name="test_classification", description="new"),
    )

    assert result.guid == "cls-guid-1"
    api_client.put.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "classificationDefs": [
                {"name": "test_classification", "description": "new"},
            ],
        },
    )


def test_create_classification_def_picks_written_def_from_bundle(mocker):
    """Test the created classification is matched by name, not taken from position."""
    other = dict(
        CLASSIFICATION_RESPONSE,
        name="other_classification",
        guid="other-guid",
    )
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "classificationDefs": [other, CLASSIFICATION_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_classification_def(
        AtlasClassificationDef(name="test_classification"),
    )

    assert result.guid == "cls-guid-1"


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"classificationDefs": []},
        {
            "classificationDefs": [
                dict(CLASSIFICATION_RESPONSE, name="other_classification"),
            ],
        },
    ],
    ids=["empty-bundle", "no-classification-defs", "other-classification-only"],
)
def test_create_classification_def_missing_from_bundle(mocker, response):
    """Test a bundle without the written classification raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = response

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="test_classification"):
        client.create_classification_def(
            AtlasClassificationDef(name="test_classification"),
        )


def test_update_classification_def_picks_written_def_from_bundle(mocker):
    """Test the updated classification is matched by name, not taken from position."""
    other = dict(
        CLASSIFICATION_RESPONSE,
        name="other_classification",
        guid="other-guid",
    )
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {
        "classificationDefs": [other, CLASSIFICATION_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.update_classification_def(
        AtlasClassificationDef(name="test_classification"),
    )

    assert result.guid == "cls-guid-1"


def test_update_classification_def_missing_from_bundle(mocker):
    """Test an update response without the classification raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"classificationDefs": []}

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="test_classification"):
        client.update_classification_def(
            AtlasClassificationDef(name="test_classification"),
        )
