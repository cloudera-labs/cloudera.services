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

from types import SimpleNamespace

import pytest

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasStructDef,
    AtlasTypeDefClient,
    align_attribute_defs,
    align_enum_elements,
    camel_preserving_options,
    extract_business_metadata_def_params,
    extract_classification_def_params,
    extract_entity_def_params,
    extract_enum_def_params,
    extract_relationship_def_params,
    extract_struct_def_params,
    snake_preserving_options,
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

    assert isinstance(result, AtlasEnumDef)
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


def test_extract_enum_def_params_drops_unset_element_fields():
    """Test unset element fields are dropped so they stay unset, not explicit nulls."""
    module = SimpleNamespace(
        name="test_enum",
        element_defs=[
            {"value": "RED", "ordinal": None, "description": None},
            {"value": "GREEN", "ordinal": 2, "description": "go"},
        ],
    )

    params = extract_enum_def_params(module)

    assert params["element_defs"] == [
        {"value": "RED"},
        {"value": "GREEN", "ordinal": 2, "description": "go"},
    ]
    assert params["name"] == "test_enum"
    assert params["description"] is None
    assert set(params) == set(AtlasEnumDef.argument_spec())


ATTRIBUTE_EXTRACTORS = [
    (extract_classification_def_params, AtlasClassificationDef),
    (extract_entity_def_params, AtlasEntityDef),
    (extract_struct_def_params, AtlasStructDef),
    (extract_relationship_def_params, AtlasRelationshipDef),
    (extract_business_metadata_def_params, AtlasBusinessMetadataDef),
]
ATTRIBUTE_EXTRACTOR_IDS = [
    "classification",
    "entity",
    "struct",
    "relationship",
    "business-metadata",
]


@pytest.mark.parametrize(
    "extract, cls",
    ATTRIBUTE_EXTRACTORS,
    ids=ATTRIBUTE_EXTRACTOR_IDS,
)
def test_extract_params_drops_unset_attribute_and_constraint_fields(extract, cls):
    """Test None is stripped from attributes and constraints but kept inside options and params."""
    module = SimpleNamespace(
        name="test_def",
        attribute_defs=[
            {
                "name": "a",
                "type_name": "string",
                "is_optional": None,
                "cardinality": "SINGLE",
                "options": {"keep_none": None},
                "constraints": [
                    {"type": "ownedRef", "params": {"keep_none": None}},
                    {"type": "inverseRef", "params": None},
                ],
            },
            {"name": "b", "type_name": "int", "constraints": None},
        ],
    )

    params = extract(module)

    assert params["attribute_defs"] == [
        {
            "name": "a",
            "type_name": "string",
            "cardinality": "SINGLE",
            "options": {"keep_none": None},
            "constraints": [
                {"type": "ownedRef", "params": {"keep_none": None}},
                {"type": "inverseRef"},
            ],
        },
        {"name": "b", "type_name": "int"},
    ]
    assert params["name"] == "test_def"
    assert set(params) == set(cls.argument_spec())


@pytest.mark.parametrize(
    "extract, cls",
    ATTRIBUTE_EXTRACTORS,
    ids=ATTRIBUTE_EXTRACTOR_IDS,
)
def test_extract_params_leaves_unset_attribute_defs_unset(extract, cls):
    """Test a module without attribute_defs extracts them as None."""
    params = extract(SimpleNamespace(name="test_def"))

    assert params["attribute_defs"] is None
    assert set(params) == set(cls.argument_spec())


def test_extract_relationship_def_params_drops_unset_end_fields():
    """Test unset end def fields are dropped, and an unset end stays None."""
    module = SimpleNamespace(
        name="test_relationship",
        end_def1={
            "type": "parent",
            "name": "children",
            "cardinality": None,
            "is_container": True,
        },
        end_def2=None,
    )

    params = extract_relationship_def_params(module)

    assert params["end_def1"] == {
        "type": "parent",
        "name": "children",
        "is_container": True,
    }
    assert params["end_def2"] is None


def test_align_attribute_defs_fills_unset_fields_from_matching_attribute():
    """Test unset fields take Atlas's values, set fields win, and unmatched attributes pass through."""
    existing = [
        AtlasAttributeDef(
            name="a",
            type_name="string",
            is_optional=True,
            cardinality="SINGLE",
            options={"o": "1"},
        ),
        AtlasAttributeDef(name="removed", type_name="int"),
    ]
    new = AtlasAttributeDef(name="new", type_name="int")
    incoming = [
        AtlasAttributeDef(name="a", type_name="string", cardinality="LIST"),
        new,
    ]

    aligned = align_attribute_defs(incoming, existing)

    assert aligned == [
        AtlasAttributeDef(
            name="a",
            type_name="string",
            is_optional=True,
            cardinality="LIST",
            options={"o": "1"},
        ),
        new,
    ]
    assert aligned[1] is new


def test_align_attribute_defs_treats_explicit_none_as_set():
    """Test an explicit None is a value to send, not an unset field to fill in."""
    existing = [AtlasAttributeDef(name="a", type_name="string", is_optional=True)]
    incoming = [AtlasAttributeDef(name="a", type_name="string", is_optional=None)]

    aligned = align_attribute_defs(incoming, existing)

    assert aligned[0].is_optional is None


def test_align_enum_elements_fills_unset_ordinal_and_description():
    """Test matching elements take Atlas's ordinal and description when unset."""
    existing = [
        AtlasEnumElementDef(value="RED", ordinal=1, description="r"),
        AtlasEnumElementDef(value="GREEN", ordinal=2),
        AtlasEnumElementDef(value="removed", ordinal=3),
    ]
    blue = AtlasEnumElementDef(value="BLUE")
    incoming = [
        AtlasEnumElementDef(value="GREEN", description="g"),
        blue,
        AtlasEnumElementDef(value="RED", ordinal=9),
    ]

    aligned = align_enum_elements(incoming, existing)

    assert aligned == [
        AtlasEnumElementDef(value="GREEN", ordinal=2, description="g"),
        blue,
        AtlasEnumElementDef(value="RED", ordinal=9, description="r"),
    ]
    assert aligned[1] is blue


def test_preserving_options_converters_keep_default_verbatim_keys():
    """Test options and params stay verbatim by default, in both directions."""
    camel = {
        "fooBar": 1,
        "options": {"kK": 1},
        "items": [{"params": {"pK": 2}, "innerKey": 3}],
    }
    snake = {
        "foo_bar": 1,
        "options": {"kK": 1},
        "items": [{"params": {"pK": 2}, "inner_key": 3}],
    }

    assert snake_preserving_options(camel) == snake
    assert camel_preserving_options(snake) == camel


def test_preserving_options_converters_accept_custom_verbatim_keys():
    """Test a custom verbatim set replaces the defaults and applies at every depth."""
    camel = {
        "typeName": "t",
        "options": {"kK": 1},
        "attributes": {"qualifiedName": "q", "nestedKey": {"innerKey": 1}},
        "classifications": [
            {"typeName": "c", "attributes": {"levelOne": {"levelTwo": 2}}},
        ],
    }
    snake = {
        "type_name": "t",
        "options": {"k_k": 1},
        "attributes": {"qualifiedName": "q", "nestedKey": {"innerKey": 1}},
        "classifications": [
            {"type_name": "c", "attributes": {"levelOne": {"levelTwo": 2}}},
        ],
    }

    assert snake_preserving_options(camel, verbatim_keys=("attributes",)) == snake
    assert camel_preserving_options(snake, verbatim_keys=("attributes",)) == camel


def test_preserving_options_converters_accept_custom_verbatim_map_keys():
    """Test the keys of a verbatim map are kept while its values are converted."""
    camel = {"groups": {"My_Group": {"someKey": 1}}}
    snake = {"groups": {"My_Group": {"some_key": 1}}}

    assert snake_preserving_options(camel, verbatim_map_keys=("groups",)) == snake
    assert camel_preserving_options(snake, verbatim_map_keys=("groups",)) == camel


def test_preserving_options_converters_accept_verbatim_values():
    """Test the key is converted while the value under it is left untouched."""
    camel = {
        "typeName": "t",
        "businessAttributes": {"myBm": {"ownerName": "alice"}},
        "labels": ["x"],
    }
    snake = {
        "type_name": "t",
        "business_attributes": {"myBm": {"ownerName": "alice"}},
        "labels": ["x"],
    }
    options = dict(
        verbatim_keys=(),
        verbatim_map_keys=(),
        verbatim_values=("businessAttributes", "business_attributes"),
    )

    assert snake_preserving_options(camel, **options) == snake
    assert camel_preserving_options(snake, **options) == camel
