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
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasTypeDefClient,
)

# Atlas returns typedef objects with camelCase keys.
ENUM_RESPONSE = {
    "category": "ENUM",
    "guid": "enum-guid-1",
    "createdBy": "admin",
    "updatedBy": "admin",
    "createTime": 1700000000000,
    "updateTime": 1700000000000,
    "version": 1,
    "name": "test_enum",
    "description": "Test enum",
    "typeVersion": "1.0",
    "options": {},
    "elementDefs": [
        {"value": "RED", "ordinal": 1},
        {"value": "GREEN", "ordinal": 2, "description": "go"},
    ],
}


def test_get_enum_def_by_name(mocker):
    """Test an Atlas enum typedef response maps onto AtlasEnumDef."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = ENUM_RESPONSE

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.get_enum_def_by_name("test_enum")

    assert result == AtlasEnumDef(
        name="test_enum",
        description="Test enum",
        type_version="1.0",
        options={},
        element_defs=[
            AtlasEnumElementDef(value="RED", ordinal=1),
            AtlasEnumElementDef(value="GREEN", ordinal=2, description="go"),
        ],
        category="ENUM",
        guid="enum-guid-1",
        version=1,
        create_time=1700000000000,
        update_time=1700000000000,
        created_by="admin",
        updated_by="admin",
    )

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/types/enumdef/name/test_enum",
        squelch={404: None},
    )


def test_get_enum_def_by_name_not_found(mocker):
    """Test a missing enum typedef (404 squelched by the api client) gives None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.get_enum_def_by_name("missing") is None


def test_create_enum_def(mocker):
    """Test creating an enum typedef posts a camelCase enumDefs bundle."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"enumDefs": [ENUM_RESPONSE]}

    client = AtlasTypeDefClient(api_client=api_client)

    response = client.create_enum_def(
        AtlasEnumDef(
            name="test_enum",
            description="Test enum",
            options={"my_custom_key": "v"},
            element_defs=[
                AtlasEnumElementDef(value="RED", ordinal=1),
                AtlasEnumElementDef(value="GREEN", description="go"),
            ],
        ),
    )

    assert response.guid == "enum-guid-1"
    assert response.name == "test_enum"

    api_client.post.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "enumDefs": [
                {
                    "name": "test_enum",
                    "description": "Test enum",
                    "options": {"my_custom_key": "v"},
                    "elementDefs": [
                        {"value": "RED", "ordinal": 1},
                        {"value": "GREEN", "ordinal": 2, "description": "go"},
                    ],
                },
            ],
        },
    )


def test_enum_def_options_preserved_on_read(mocker):
    """Test free-form option keys are not converted between camel and snake case."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {
        "name": "test_enum",
        "options": {"someCamelKey": "v", "other_key": "w"},
    }

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.get_enum_def_by_name("test_enum")

    assert result.options == {"someCamelKey": "v", "other_key": "w"}


def test_update_enum_def(mocker):
    """Test updating an enum typedef PUTs an enumDefs bundle."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"enumDefs": [ENUM_RESPONSE]}

    client = AtlasTypeDefClient(api_client=api_client)

    response = client.update_enum_def(
        AtlasEnumDef(
            name="test_enum",
            guid="enum-guid-1",
            element_defs=[AtlasEnumElementDef(value="RED", ordinal=1)],
        ),
    )

    assert response.guid == "enum-guid-1"

    api_client.put.assert_called_once_with(
        "/api/atlas/v2/types/typedefs",
        data={
            "enumDefs": [
                {
                    "name": "test_enum",
                    "guid": "enum-guid-1",
                    "elementDefs": [{"value": "RED", "ordinal": 1}],
                },
            ],
        },
    )


def test_delete_typedef_by_name(mocker):
    """Test deleting a typedef by name; a missing typedef is a no-op."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.delete_typedef_by_name("test_enum") is None

    api_client.delete.assert_called_once_with(
        "/api/atlas/v2/types/typedef/name/test_enum",
        squelch={404: None},
    )


def test_delete_typedef_by_name_force(mocker):
    """Test force is sent to Atlas as a query parameter."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.delete_typedef_by_name("test_bm", force=True) is None

    api_client.delete.assert_called_once_with(
        "/api/atlas/v2/types/typedef/name/test_bm",
        params={"force": "true"},
        squelch={404: None},
    )


def test_list_typedef_headers(mocker):
    """Test listing typedef headers returns snake_case dicts."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [
        {"guid": "g1", "name": "test_enum", "category": "ENUM", "serviceType": "svc"},
        {"guid": "g2", "name": "test_tag", "category": "CLASSIFICATION"},
    ]

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.list_typedef_headers() == [
        {"guid": "g1", "name": "test_enum", "category": "ENUM", "service_type": "svc"},
        {"guid": "g2", "name": "test_tag", "category": "CLASSIFICATION"},
    ]

    api_client.get.assert_called_once_with("/api/atlas/v2/types/typedefs/headers")


def test_get_typedef_by_name(mocker):
    """Test a generic typedef keeps free-form option keys at any depth."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {
        "category": "ENTITY",
        "name": "test_entity",
        "typeVersion": "1.0",
        "options": {"someKey": "v"},
        "attributeDefs": [
            {"name": "attr", "isOptional": True, "options": {"maxStrLength": "10"}},
        ],
    }

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.get_typedef_by_name("test_entity") == {
        "category": "ENTITY",
        "name": "test_entity",
        "type_version": "1.0",
        "options": {"someKey": "v"},
        "attribute_defs": [
            {"name": "attr", "is_optional": True, "options": {"maxStrLength": "10"}},
        ],
    }

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/types/typedef/name/test_entity",
        squelch={404: None},
    )


def test_get_typedef_by_name_not_found(mocker):
    """Test a missing typedef gives None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = AtlasTypeDefClient(api_client=api_client)

    assert client.get_typedef_by_name("missing") is None


def test_create_enum_def_picks_written_def_from_bundle(mocker):
    """Test the created enum is matched by name, not taken from position."""
    other = dict(ENUM_RESPONSE, name="other_enum", guid="other-guid")
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {"enumDefs": [other, ENUM_RESPONSE]}

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.create_enum_def(AtlasEnumDef(name="test_enum"))

    assert result.guid == "enum-guid-1"


@pytest.mark.parametrize(
    "response",
    [{}, {"enumDefs": []}, {"enumDefs": [dict(ENUM_RESPONSE, name="other_enum")]}],
    ids=["empty-bundle", "no-enum-defs", "other-enum-only"],
)
def test_create_enum_def_missing_from_bundle(mocker, response):
    """Test a bundle without the written enum raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = response

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="test_enum"):
        client.create_enum_def(AtlasEnumDef(name="test_enum"))


def test_update_enum_def_picks_written_def_from_bundle(mocker):
    """Test the updated enum is matched by name, not taken from position."""
    other = dict(ENUM_RESPONSE, name="other_enum", guid="other-guid")
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"enumDefs": [other, ENUM_RESPONSE]}

    client = AtlasTypeDefClient(api_client=api_client)

    result = client.update_enum_def(AtlasEnumDef(name="test_enum"))

    assert result.guid == "enum-guid-1"


def test_update_enum_def_missing_from_bundle(mocker):
    """Test an update response without the enum raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {"enumDefs": []}

    client = AtlasTypeDefClient(api_client=api_client)

    with pytest.raises(ServicesError, match="test_enum"):
        client.update_enum_def(AtlasEnumDef(name="test_enum"))
