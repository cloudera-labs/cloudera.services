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

"""
REST clients for the Apache Atlas API.
"""

from dataclasses import dataclass, fields
from typing import Any, Dict, List, Optional, Union, cast

from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
    snake_dict_to_camel_dict,
)

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    NULLABLE,
    ServicesClient,
    ServicesError,
)

TYPES_API = "/api/atlas/v2/types"

# Free-form maps whose keys must never be case-converted.
VERBATIM_KEYS = ("options", "params")

# Maps keyed by user-chosen names: the map keys stay verbatim, the values are converted.
VERBATIM_MAP_KEYS = ("business_attribute_defs", "businessAttributeDefs")


@dataclass
class AtlasEnumElementDef:
    """Representation of an element of an Apache Atlas enum typedef."""

    value: str
    ordinal: Union[int, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable element parameters."""
        return dict(
            value=dict(type="str", required=True),
            ordinal=dict(type="int", required=False),
            description=dict(type="str", required=False),
        )


@dataclass
class AtlasEnumDef:
    """Representation of an Apache Atlas enum typedef."""

    name: str

    description: Union[str, None, NULLABLE] = NULLABLE
    type_version: Union[str, None, NULLABLE] = NULLABLE
    service_type: Union[str, None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    default_value: Union[str, None, NULLABLE] = NULLABLE
    element_defs: Union[List[AtlasEnumElementDef], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    category: Union[str, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable AtlasEnumDef parameters."""
        return dict(
            name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            type_version=dict(type="str", required=False),
            service_type=dict(type="str", required=False),
            options=dict(type="dict", required=False),
            default_value=dict(type="str", required=False),
            element_defs=dict(
                type="list",
                elements="dict",
                required=False,
                options=AtlasEnumElementDef.argument_spec(),
            ),
        )


@dataclass
class AtlasConstraintDef:
    """Representation of a constraint on an Apache Atlas attribute."""

    type: str
    params: Union[Dict[str, Any], None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable constraint parameters."""
        return dict(
            type=dict(type="str", required=True),
            params=dict(type="dict", required=False),
        )


@dataclass
class AtlasAttributeDef:
    """Representation of an attribute of an Apache Atlas struct-like typedef."""

    name: str
    type_name: str

    is_optional: Union[bool, None, NULLABLE] = NULLABLE
    is_unique: Union[bool, None, NULLABLE] = NULLABLE
    is_indexable: Union[bool, None, NULLABLE] = NULLABLE
    cardinality: Union[str, None, NULLABLE] = NULLABLE
    values_min_count: Union[int, None, NULLABLE] = NULLABLE
    values_max_count: Union[int, None, NULLABLE] = NULLABLE
    default_value: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    display_name: Union[str, None, NULLABLE] = NULLABLE
    include_in_notification: Union[bool, None, NULLABLE] = NULLABLE
    index_type: Union[str, None, NULLABLE] = NULLABLE
    search_weight: Union[int, None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    constraints: Union[List[AtlasConstraintDef], None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable attribute parameters."""
        return dict(
            name=dict(type="str", required=True),
            type_name=dict(type="str", required=True),
            is_optional=dict(type="bool", required=False),
            is_unique=dict(type="bool", required=False),
            is_indexable=dict(type="bool", required=False),
            cardinality=dict(
                type="str",
                required=False,
                choices=["SINGLE", "LIST", "SET"],
            ),
            values_min_count=dict(type="int", required=False),
            values_max_count=dict(type="int", required=False),
            default_value=dict(type="str", required=False),
            description=dict(type="str", required=False),
            display_name=dict(type="str", required=False),
            include_in_notification=dict(type="bool", required=False),
            index_type=dict(
                type="str",
                required=False,
                choices=["DEFAULT", "STRING"],
            ),
            search_weight=dict(type="int", required=False),
            options=dict(type="dict", required=False),
            constraints=dict(
                type="list",
                elements="dict",
                required=False,
                options=AtlasConstraintDef.argument_spec(),
            ),
        )


@dataclass
class AtlasClassificationDef:
    """Representation of an Apache Atlas classification typedef."""

    name: str

    description: Union[str, None, NULLABLE] = NULLABLE
    type_version: Union[str, None, NULLABLE] = NULLABLE
    service_type: Union[str, None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    attribute_defs: Union[List[AtlasAttributeDef], None, NULLABLE] = NULLABLE
    super_types: Union[List[str], None, NULLABLE] = NULLABLE
    entity_types: Union[List[str], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    sub_types: Union[List[str], None, NULLABLE] = NULLABLE
    category: Union[str, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable AtlasClassificationDef parameters."""
        return dict(
            name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            type_version=dict(type="str", required=False),
            service_type=dict(type="str", required=False),
            options=dict(type="dict", required=False),
            attribute_defs=dict(
                type="list",
                elements="dict",
                required=False,
                options=AtlasAttributeDef.argument_spec(),
            ),
            super_types=dict(type="list", elements="str", required=False),
            entity_types=dict(type="list", elements="str", required=False),
        )


@dataclass
class AtlasStructDef:
    """Representation of an Apache Atlas struct typedef."""

    name: str

    description: Union[str, None, NULLABLE] = NULLABLE
    type_version: Union[str, None, NULLABLE] = NULLABLE
    service_type: Union[str, None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    attribute_defs: Union[List[AtlasAttributeDef], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    category: Union[str, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable AtlasStructDef parameters."""
        return dict(
            name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            type_version=dict(type="str", required=False),
            service_type=dict(type="str", required=False),
            options=dict(type="dict", required=False),
            attribute_defs=dict(
                type="list",
                elements="dict",
                required=False,
                options=AtlasAttributeDef.argument_spec(),
            ),
        )


@dataclass
class AtlasBusinessMetadataDef:
    """Representation of an Apache Atlas business metadata typedef."""

    name: str

    description: Union[str, None, NULLABLE] = NULLABLE
    type_version: Union[str, None, NULLABLE] = NULLABLE
    service_type: Union[str, None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    attribute_defs: Union[List[AtlasAttributeDef], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    category: Union[str, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable AtlasBusinessMetadataDef parameters."""
        return dict(
            name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            type_version=dict(type="str", required=False),
            service_type=dict(type="str", required=False),
            options=dict(type="dict", required=False),
            attribute_defs=dict(
                type="list",
                elements="dict",
                required=False,
                options=AtlasAttributeDef.argument_spec(),
            ),
        )


@dataclass
class AtlasRelationshipEndDef:
    """Representation of one end of an Apache Atlas relationship typedef."""

    type: str
    name: str

    cardinality: Union[str, None, NULLABLE] = NULLABLE
    is_container: Union[bool, None, NULLABLE] = NULLABLE
    is_legacy_attribute: Union[bool, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable end parameters."""
        return dict(
            type=dict(type="str", required=True),
            name=dict(type="str", required=True),
            cardinality=dict(
                type="str",
                required=False,
                choices=["SINGLE", "LIST", "SET"],
            ),
            is_container=dict(type="bool", required=False),
            is_legacy_attribute=dict(type="bool", required=False),
            description=dict(type="str", required=False),
        )


@dataclass
class AtlasRelationshipDef:
    """Representation of an Apache Atlas relationship typedef."""

    name: str

    description: Union[str, None, NULLABLE] = NULLABLE
    type_version: Union[str, None, NULLABLE] = NULLABLE
    service_type: Union[str, None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    attribute_defs: Union[List[AtlasAttributeDef], None, NULLABLE] = NULLABLE
    end_def1: Union[AtlasRelationshipEndDef, None, NULLABLE] = NULLABLE
    end_def2: Union[AtlasRelationshipEndDef, None, NULLABLE] = NULLABLE
    relationship_category: Union[str, None, NULLABLE] = NULLABLE
    relationship_label: Union[str, None, NULLABLE] = NULLABLE
    propagate_tags: Union[str, None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    category: Union[str, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable AtlasRelationshipDef parameters."""
        return dict(
            name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            type_version=dict(type="str", required=False),
            service_type=dict(type="str", required=False),
            options=dict(type="dict", required=False),
            attribute_defs=dict(
                type="list",
                elements="dict",
                required=False,
                options=AtlasAttributeDef.argument_spec(),
            ),
            end_def1=dict(
                type="dict",
                required=False,
                options=AtlasRelationshipEndDef.argument_spec(),
            ),
            end_def2=dict(
                type="dict",
                required=False,
                options=AtlasRelationshipEndDef.argument_spec(),
            ),
            relationship_category=dict(
                type="str",
                required=False,
                choices=["ASSOCIATION", "AGGREGATION", "COMPOSITION"],
            ),
            relationship_label=dict(type="str", required=False),
            propagate_tags=dict(
                type="str",
                required=False,
                choices=["NONE", "ONE_TO_TWO", "TWO_TO_ONE", "BOTH"],
            ),
        )


@dataclass
class AtlasRelationshipAttributeDef(AtlasAttributeDef):
    """Representation of a relationship attribute of an Apache Atlas entity typedef."""

    relationship_type_name: Union[str, None, NULLABLE] = NULLABLE
    is_legacy_attribute: Union[bool, None, NULLABLE] = NULLABLE


@dataclass
class AtlasEntityDef:
    """Representation of an Apache Atlas entity typedef."""

    name: str

    description: Union[str, None, NULLABLE] = NULLABLE
    type_version: Union[str, None, NULLABLE] = NULLABLE
    service_type: Union[str, None, NULLABLE] = NULLABLE
    options: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    attribute_defs: Union[List[AtlasAttributeDef], None, NULLABLE] = NULLABLE
    super_types: Union[List[str], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    sub_types: Union[List[str], None, NULLABLE] = NULLABLE
    relationship_attribute_defs: Union[
        List[AtlasRelationshipAttributeDef],
        None,
        NULLABLE,
    ] = NULLABLE
    business_attribute_defs: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    category: Union[str, None, NULLABLE] = NULLABLE
    guid: Union[str, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable AtlasEntityDef parameters."""
        return dict(
            name=dict(type="str", required=False),
            description=dict(type="str", required=False),
            type_version=dict(type="str", required=False),
            service_type=dict(type="str", required=False),
            options=dict(type="dict", required=False),
            attribute_defs=dict(
                type="list",
                elements="dict",
                required=False,
                options=AtlasAttributeDef.argument_spec(),
            ),
            super_types=dict(type="list", elements="str", required=False),
        )


def _convert_map_values(value: Any, convert: Any) -> Any:
    """Apply `convert` to the values of a map, leaving its keys untouched."""
    if isinstance(value, dict):
        return {key: convert(val) for key, val in value.items()}
    return convert(value)


def _snake_preserving_options(value: Any) -> Any:
    """Convert camelCase keys to snake_case at any depth, leaving free-form maps verbatim."""
    if isinstance(value, list):
        return [_snake_preserving_options(item) for item in value]
    if isinstance(value, dict):
        return {
            (
                key
                if key in VERBATIM_KEYS
                else next(iter(camel_dict_to_snake_dict({key: None}, reversible=True)))
            ): (
                val
                if key in VERBATIM_KEYS
                else (
                    _convert_map_values(val, _snake_preserving_options)
                    if key in VERBATIM_MAP_KEYS
                    else _snake_preserving_options(val)
                )
            )
            for key, val in value.items()
        }
    return value


def _enum_def_to_payload(enum_def: AtlasEnumDef) -> Dict[str, Any]:
    """Serialise an AtlasEnumDef into a camelCase Atlas request payload."""
    data = to_dict(enum_def)
    options = data.pop("options", None)
    # Atlas rejects elements without an ordinal; number unset ones after the highest set.
    elements = data.get("element_defs")
    if isinstance(elements, list):
        next_ordinal = max((e.get("ordinal", 0) for e in elements), default=0) + 1
        for element in elements:
            if element.get("ordinal") is None:
                element["ordinal"] = next_ordinal
                next_ordinal += 1
    payload: Dict[str, Any] = cast(Dict[str, Any], snake_dict_to_camel_dict(data))
    if options is not None:
        payload["options"] = options
    return payload


def _enum_def_from_response(raw: Dict[str, Any]) -> AtlasEnumDef:
    """Deserialise an Atlas enum typedef response into an AtlasEnumDef."""
    data = dict(raw)
    options = data.pop("options", None)
    enum_def = from_dict(
        AtlasEnumDef,
        camel_dict_to_snake_dict(data, reversible=True),
    )
    if options is not None:
        enum_def.options = options
    return enum_def


def _camel_preserving_options(value: Any) -> Any:
    """Convert snake_case keys to camelCase at any depth, leaving free-form maps verbatim."""
    if isinstance(value, list):
        return [_camel_preserving_options(item) for item in value]
    if isinstance(value, dict):
        return {
            (
                key
                if key in VERBATIM_KEYS
                else next(iter(snake_dict_to_camel_dict({key: None})))
            ): (
                val
                if key in VERBATIM_KEYS
                else (
                    _convert_map_values(val, _camel_preserving_options)
                    if key in VERBATIM_MAP_KEYS
                    else _camel_preserving_options(val)
                )
            )
            for key, val in value.items()
        }
    return value


def _classification_def_to_payload(
    classification_def: AtlasClassificationDef,
) -> Dict[str, Any]:
    """Serialise an AtlasClassificationDef into a camelCase Atlas request payload."""
    return _camel_preserving_options(to_dict(classification_def))


def _classification_def_from_response(raw: Dict[str, Any]) -> AtlasClassificationDef:
    """Deserialise an Atlas classification typedef response."""
    return from_dict(AtlasClassificationDef, _snake_preserving_options(raw))


def _entity_def_to_payload(entity_def: AtlasEntityDef) -> Dict[str, Any]:
    """Serialise an AtlasEntityDef into a camelCase Atlas request payload."""
    return _camel_preserving_options(to_dict(entity_def))


def _written_def(result: Any, key: str, name: str) -> Dict[str, Any]:
    """Pick the def Atlas returned for a written typedef, or raise if the bundle lacks it."""
    defs = result.get(key) if isinstance(result, dict) else None
    for candidate in defs or []:
        if candidate.get("name") == name:
            return candidate
    raise ServicesError(f"Atlas did not return '{name}' in '{key}' after the write")


def _entity_def_from_response(raw: Dict[str, Any]) -> AtlasEntityDef:
    """Deserialise an Atlas entity typedef response."""
    return from_dict(AtlasEntityDef, _snake_preserving_options(raw))


def _struct_def_to_payload(struct_def: AtlasStructDef) -> Dict[str, Any]:
    """Serialise an AtlasStructDef into a camelCase Atlas request payload."""
    return _camel_preserving_options(to_dict(struct_def))


def _struct_def_from_response(raw: Dict[str, Any]) -> AtlasStructDef:
    """Deserialise an Atlas struct typedef response."""
    return from_dict(AtlasStructDef, _snake_preserving_options(raw))


def _relationship_def_to_payload(
    relationship_def: AtlasRelationshipDef,
) -> Dict[str, Any]:
    """Serialise an AtlasRelationshipDef into a camelCase Atlas request payload."""
    return _camel_preserving_options(to_dict(relationship_def))


def _relationship_def_from_response(raw: Dict[str, Any]) -> AtlasRelationshipDef:
    """Deserialise an Atlas relationship typedef response."""
    return from_dict(AtlasRelationshipDef, _snake_preserving_options(raw))


def _business_metadata_def_to_payload(
    business_metadata_def: AtlasBusinessMetadataDef,
) -> Dict[str, Any]:
    """Serialise an AtlasBusinessMetadataDef into a camelCase Atlas request payload."""
    return _camel_preserving_options(to_dict(business_metadata_def))


def _business_metadata_def_from_response(
    raw: Dict[str, Any],
) -> AtlasBusinessMetadataDef:
    """Deserialise an Atlas business metadata typedef response."""
    return from_dict(AtlasBusinessMetadataDef, _snake_preserving_options(raw))


class AtlasTypeDefClient:
    """Apache Atlas typedef API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def get_enum_def_by_name(self, name: str) -> Optional[AtlasEnumDef]:
        """Retrieve a single enum typedef by name, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/enumdef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _enum_def_from_response(result)

    def get_classification_def_by_name(
        self,
        name: str,
    ) -> Optional[AtlasClassificationDef]:
        """Retrieve a single classification typedef by name, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/classificationdef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _classification_def_from_response(result)

    def get_entity_def_by_name(self, name: str) -> Optional[AtlasEntityDef]:
        """Retrieve a single entity typedef by name, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/entitydef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _entity_def_from_response(result)

    def get_struct_def_by_name(self, name: str) -> Optional[AtlasStructDef]:
        """Retrieve a single struct typedef by name, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/structdef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _struct_def_from_response(result)

    def get_relationship_def_by_name(
        self,
        name: str,
    ) -> Optional[AtlasRelationshipDef]:
        """Retrieve a single relationship typedef by name, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/relationshipdef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _relationship_def_from_response(result)

    def get_business_metadata_def_by_name(
        self,
        name: str,
    ) -> Optional[AtlasBusinessMetadataDef]:
        """Retrieve a single business metadata typedef by name, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/businessmetadatadef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _business_metadata_def_from_response(result)

    def list_typedef_headers(self) -> List[Dict[str, Any]]:
        """List the headers (guid, name, category, service type) of all typedefs."""
        result = self.api_client.get(f"{TYPES_API}/typedefs/headers")
        return _snake_preserving_options(result or [])

    def get_typedef_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve any typedef by name as a snake_case dict, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/typedef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _snake_preserving_options(result)

    def create_enum_def(self, enum_def: AtlasEnumDef) -> AtlasEnumDef:
        """Create a new enum typedef."""
        result = self.api_client.post(
            f"{TYPES_API}/typedefs",
            data={"enumDefs": [_enum_def_to_payload(enum_def)]},
        )
        return _enum_def_from_response(result["enumDefs"][0])

    def update_enum_def(self, enum_def: AtlasEnumDef) -> AtlasEnumDef:
        """Update an existing enum typedef."""
        result = self.api_client.put(
            f"{TYPES_API}/typedefs",
            data={"enumDefs": [_enum_def_to_payload(enum_def)]},
        )
        return _enum_def_from_response(result["enumDefs"][0])

    def create_classification_def(
        self,
        classification_def: AtlasClassificationDef,
    ) -> AtlasClassificationDef:
        """Create a new classification typedef."""
        result = self.api_client.post(
            f"{TYPES_API}/typedefs",
            data={
                "classificationDefs": [
                    _classification_def_to_payload(classification_def),
                ],
            },
        )
        return _classification_def_from_response(result["classificationDefs"][0])

    def update_classification_def(
        self,
        classification_def: AtlasClassificationDef,
    ) -> AtlasClassificationDef:
        """Update an existing classification typedef."""
        result = self.api_client.put(
            f"{TYPES_API}/typedefs",
            data={
                "classificationDefs": [
                    _classification_def_to_payload(classification_def),
                ],
            },
        )
        return _classification_def_from_response(result["classificationDefs"][0])

    def create_entity_def(self, entity_def: AtlasEntityDef) -> AtlasEntityDef:
        """Create a new entity typedef."""
        result = self.api_client.post(
            f"{TYPES_API}/typedefs",
            data={"entityDefs": [_entity_def_to_payload(entity_def)]},
        )
        return _entity_def_from_response(
            _written_def(result, "entityDefs", entity_def.name),
        )

    def update_entity_def(self, entity_def: AtlasEntityDef) -> AtlasEntityDef:
        """Update an existing entity typedef."""
        result = self.api_client.put(
            f"{TYPES_API}/typedefs",
            data={"entityDefs": [_entity_def_to_payload(entity_def)]},
        )
        return _entity_def_from_response(
            _written_def(result, "entityDefs", entity_def.name),
        )

    def create_struct_def(self, struct_def: AtlasStructDef) -> AtlasStructDef:
        """Create a new struct typedef."""
        result = self.api_client.post(
            f"{TYPES_API}/typedefs",
            data={"structDefs": [_struct_def_to_payload(struct_def)]},
        )
        return _struct_def_from_response(
            _written_def(result, "structDefs", struct_def.name),
        )

    def update_struct_def(self, struct_def: AtlasStructDef) -> AtlasStructDef:
        """Update an existing struct typedef."""
        result = self.api_client.put(
            f"{TYPES_API}/typedefs",
            data={"structDefs": [_struct_def_to_payload(struct_def)]},
        )
        return _struct_def_from_response(
            _written_def(result, "structDefs", struct_def.name),
        )

    def create_relationship_def(
        self,
        relationship_def: AtlasRelationshipDef,
    ) -> AtlasRelationshipDef:
        """Create a new relationship typedef."""
        result = self.api_client.post(
            f"{TYPES_API}/typedefs",
            data={
                "relationshipDefs": [_relationship_def_to_payload(relationship_def)],
            },
        )
        return _relationship_def_from_response(
            _written_def(result, "relationshipDefs", relationship_def.name),
        )

    def update_relationship_def(
        self,
        relationship_def: AtlasRelationshipDef,
    ) -> AtlasRelationshipDef:
        """Update an existing relationship typedef."""
        result = self.api_client.put(
            f"{TYPES_API}/typedefs",
            data={
                "relationshipDefs": [_relationship_def_to_payload(relationship_def)],
            },
        )
        return _relationship_def_from_response(
            _written_def(result, "relationshipDefs", relationship_def.name),
        )

    def create_business_metadata_def(
        self,
        business_metadata_def: AtlasBusinessMetadataDef,
    ) -> AtlasBusinessMetadataDef:
        """Create a new business metadata typedef."""
        result = self.api_client.post(
            f"{TYPES_API}/typedefs",
            data={
                "businessMetadataDefs": [
                    _business_metadata_def_to_payload(business_metadata_def),
                ],
            },
        )
        return _business_metadata_def_from_response(
            _written_def(
                result,
                "businessMetadataDefs",
                business_metadata_def.name,
            ),
        )

    def update_business_metadata_def(
        self,
        business_metadata_def: AtlasBusinessMetadataDef,
    ) -> AtlasBusinessMetadataDef:
        """Update an existing business metadata typedef."""
        result = self.api_client.put(
            f"{TYPES_API}/typedefs",
            data={
                "businessMetadataDefs": [
                    _business_metadata_def_to_payload(business_metadata_def),
                ],
            },
        )
        return _business_metadata_def_from_response(
            _written_def(
                result,
                "businessMetadataDefs",
                business_metadata_def.name,
            ),
        )

    def delete_typedef_by_name(self, name: str, force: bool = False) -> None:
        """
        Delete a typedef by name (idempotent).

        With `force`, Atlas skips reference validation, which it otherwise
        requires for types such as business metadata with non-indexable attributes.
        """
        extra: Dict[str, Any] = {"params": {"force": "true"}} if force else {}
        self.api_client.delete(
            f"{TYPES_API}/typedef/name/{name}",
            squelch={404: None},
            **extra,
        )


def align_enum_elements(
    incoming: List[AtlasEnumElementDef],
    existing: List[AtlasEnumElementDef],
) -> List[AtlasEnumElementDef]:
    """
    Fill unset ordinal/description of incoming elements from the existing element
    with the same value, so Atlas-assigned ordinals do not register as a change.
    """
    existing_by_value = {element.value: element for element in existing}

    aligned = []
    for element in incoming:
        match = existing_by_value.get(element.value)
        if match is None:
            aligned.append(element)
            continue
        aligned.append(
            AtlasEnumElementDef(
                value=element.value,
                ordinal=(
                    match.ordinal if element.ordinal is NULLABLE else element.ordinal
                ),
                description=(
                    match.description
                    if element.description is NULLABLE
                    else element.description
                ),
            ),
        )
    return aligned


def align_attribute_defs(
    incoming: List[AtlasAttributeDef],
    existing: List[AtlasAttributeDef],
) -> List[AtlasAttributeDef]:
    """
    Fill unset fields of incoming attributes from the existing attribute with the
    same name, so Atlas-assigned defaults do not register as a change.
    """
    existing_by_name = {attribute.name: attribute for attribute in existing}

    aligned = []
    for attribute in incoming:
        match = existing_by_name.get(attribute.name)
        if match is None:
            aligned.append(attribute)
            continue
        aligned.append(
            AtlasAttributeDef(
                **{
                    field.name: (
                        getattr(match, field.name)
                        if getattr(attribute, field.name) is NULLABLE
                        else getattr(attribute, field.name)
                    )
                    for field in fields(AtlasAttributeDef)
                },
            ),
        )
    return aligned


def align_relationship_end_def(
    incoming: AtlasRelationshipEndDef,
    existing: AtlasRelationshipEndDef,
) -> AtlasRelationshipEndDef:
    """
    Fill unset fields of an incoming relationship end from the existing end, so
    Atlas-assigned defaults do not register as a change.
    """
    return AtlasRelationshipEndDef(
        **{
            field.name: (
                getattr(existing, field.name)
                if getattr(incoming, field.name) is NULLABLE
                else getattr(incoming, field.name)
            )
            for field in fields(AtlasRelationshipEndDef)
        },
    )


def extract_enum_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable enum typedef parameters from a module instance into a dict."""
    params: Dict[str, Any] = {
        key: getattr(module_instance, key, None) for key in AtlasEnumDef.argument_spec()
    }

    # Ansible fills unset suboptions with None; drop them so they stay unset
    # (NULLABLE) rather than serialising as explicit nulls.
    element_defs: Optional[List[Dict[str, Any]]] = params.get("element_defs")
    if element_defs is not None:
        params["element_defs"] = [
            {k: v for k, v in element.items() if v is not None}
            for element in element_defs
        ]

    return params


def _extract_params(module_instance, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Read the spec'd parameters off a module instance, dropping unset attribute suboptions."""
    params: Dict[str, Any] = {key: getattr(module_instance, key, None) for key in spec}

    # Ansible fills unset suboptions with None; drop them so they stay unset
    # (NULLABLE) rather than serialising as explicit nulls.
    attribute_defs: Optional[List[Dict[str, Any]]] = params.get("attribute_defs")
    if attribute_defs is not None:
        cleaned = []
        for attribute in attribute_defs:
            attribute = {k: v for k, v in attribute.items() if v is not None}
            if "constraints" in attribute:
                attribute["constraints"] = [
                    {k: v for k, v in constraint.items() if v is not None}
                    for constraint in attribute["constraints"]
                ]
            cleaned.append(attribute)
        params["attribute_defs"] = cleaned

    return params


def extract_classification_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable classification typedef parameters from a module instance into a dict."""
    return _extract_params(module_instance, AtlasClassificationDef.argument_spec())


def extract_entity_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable entity typedef parameters from a module instance into a dict."""
    return _extract_params(module_instance, AtlasEntityDef.argument_spec())


def extract_struct_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable struct typedef parameters from a module instance into a dict."""
    return _extract_params(module_instance, AtlasStructDef.argument_spec())


def extract_relationship_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable relationship typedef parameters from a module instance into a dict."""
    params = _extract_params(module_instance, AtlasRelationshipDef.argument_spec())

    # Ansible fills unset suboptions with None; drop them so they stay unset.
    for key in ("end_def1", "end_def2"):
        end = params.get(key)
        if end is not None:
            params[key] = {k: v for k, v in end.items() if v is not None}

    return params


def extract_business_metadata_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable business metadata typedef parameters from a module instance into a dict."""
    return _extract_params(module_instance, AtlasBusinessMetadataDef.argument_spec())
