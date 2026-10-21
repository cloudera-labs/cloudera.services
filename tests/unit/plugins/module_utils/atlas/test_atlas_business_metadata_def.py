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
    AtlasBusinessMetadataDef,
    AtlasTypeDefClient,
)

# Atlas returns typedef objects with camelCase keys. Business metadata attributes
# carry their scope in string-valued options.
BUSINESS_METADATA_RESPONSE = {
    "category": "BUSINESS_METADATA",
    "guid": "bm-guid-1",
    "createdBy": "admin",
    "updatedBy": "admin",
    "createTime": 1700000000000,
    "updateTime": 1700000000000,
    "version": 1,
    "name": "test_business_metadata",
    "description": "Test business metadata",
    "typeVersion": "1.0",
    "options": {"k": "v"},
    "attributeDefs": [
        {
            "name": "owner",
            "typeName": "string",
            "isOptional": True,
            "cardinality": "SINGLE",
            "valuesMinCount": 0,
            "valuesMaxCount": 1,
            "isUnique": False,
            "isIndexable": True,
            "includeInNotification": False,
            "searchWeight": -1,
            "options": {
                "applicableEntityTypes": '["hive_table"]',
                "maxStrLength": "50",
            },
        },
    ],
}


def test_get_business_metadata_def_by_name(mocker):
    """Test an Atlas business metadata typedef response maps onto AtlasBusinessMetadataDef."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = BUSINESS_METADATA_RESPONSE

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.get_business_metadata_def_by_name("test_business_metadata")

    assert result == AtlasBusinessMetadataDef(
        name="test_business_metadata",
        description="Test business metadata",
        type_version="1.0",
        options={"k": "v"},
        attribute_defs=[
            AtlasAttributeDef(
                name="owner",
                type_name="string",
                is_optional=True,
                cardinality="SINGLE",
                values_min_count=0,
                values_max_count=1,
                is_unique=False,
                is_indexable=True,
                include_in_notification=False,
                search_weight=-1,
                options={
                    "applicableEntityTypes": '["hive_table"]',
                    "maxStrLength": "50",
                },
            ),
        ],
        category="BUSINESS_METADATA",
        guid="bm-guid-1",
        version=1,
        create_time=1700000000000,
        update_time=1700000000000,
        created_by="admin",
        updated_by="admin",
    )

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/types/businessmetadatadef/name/test_business_metadata",
        squelch={404: None},
    )


def test_get_business_metadata_def_by_name_not_found(mocker):
    """Test a missing business metadata typedef returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.get_business_metadata_def_by_name("missing") is None


def test_create_business_metadata_def(mocker):
    """Test create POSTs a businessMetadataDefs bundle with attribute options verbatim."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "enumDefs": [],
        "businessMetadataDefs": [BUSINESS_METADATA_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_business_metadata_def(
        AtlasBusinessMetadataDef(
            name="test_business_metadata",
            options={"my_key": "v"},
            attribute_defs=[
                AtlasAttributeDef(
                    name="owner",
                    type_name="string",
                    is_optional=True,
                    options={
                        "applicableEntityTypes": '["hive_table"]',
                        "maxStrLength": "50",
                    },
                ),
            ],
        ),
    )

    assert isinstance(result, AtlasBusinessMetadataDef)
    assert result.guid == "bm-guid-1"

    api_client.post.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "businessMetadataDefs": [
                {
                    "name": "test_business_metadata",
                    "options": {"my_key": "v"},
                    "attributeDefs": [
                        {
                            "name": "owner",
                            "typeName": "string",
                            "isOptional": True,
                            "options": {
                                "applicableEntityTypes": '["hive_table"]',
                                "maxStrLength": "50",
                            },
                        },
                    ],
                },
            ],
        },
    )


def test_create_business_metadata_def_picks_written_def_from_bundle(mocker):
    """Test the created def is matched by name, not taken from position."""
    other = dict(BUSINESS_METADATA_RESPONSE, name="other_bm", guid="other-guid")
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {
        "businessMetadataDefs": [other, BUSINESS_METADATA_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_business_metadata_def(
        AtlasBusinessMetadataDef(name="test_business_metadata"),
    )

    assert result.guid == "bm-guid-1"


def test_create_business_metadata_def_missing_from_bundle(mocker):
    """Test a bundle without the written business metadata raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"businessMetadataDefs": []}

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="test_business_metadata"):
        client.create_business_metadata_def(
            AtlasBusinessMetadataDef(name="test_business_metadata"),
        )


def test_update_business_metadata_def(mocker):
    """Test update PUTs a businessMetadataDefs bundle and returns the updated def."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {
        "businessMetadataDefs": [BUSINESS_METADATA_RESPONSE],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.update_business_metadata_def(
        AtlasBusinessMetadataDef(name="test_business_metadata", description="new"),
    )

    assert result.guid == "bm-guid-1"
    api_client.put.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "businessMetadataDefs": [
                {"name": "test_business_metadata", "description": "new"},
            ],
        },
    )
