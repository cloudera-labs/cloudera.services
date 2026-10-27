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

from dataclasses import dataclass, fields, replace
from typing import Any, Callable, Dict, Iterable, List, Optional, Union, cast

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


def snake_preserving_options(
    value: Any,
    verbatim_keys: Iterable[str] = VERBATIM_KEYS,
    verbatim_map_keys: Iterable[str] = VERBATIM_MAP_KEYS,
    verbatim_values: Iterable[str] = (),
) -> Any:
    """
    Convert camelCase keys to snake_case at any depth.

    A key in `verbatim_keys` and the value under it are left untouched. The value
    under a key in `verbatim_values` is left untouched but the key is converted.
    The map under a key in `verbatim_map_keys` keeps its own keys while its values
    are converted.
    """

    def convert(item: Any) -> Any:
        return snake_preserving_options(
            item,
            verbatim_keys,
            verbatim_map_keys,
            verbatim_values,
        )

    if isinstance(value, list):
        return [convert(item) for item in value]
    if isinstance(value, dict):
        return {
            (
                key
                if key in verbatim_keys
                else next(iter(camel_dict_to_snake_dict({key: None}, reversible=True)))
            ): (
                val
                if key in verbatim_keys or key in verbatim_values
                else (
                    _convert_map_values(val, convert)
                    if key in verbatim_map_keys
                    else convert(val)
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


def _camel_key(key: str) -> str:
    """Convert one snake_case key to camelCase."""
    return next(iter(cast(Dict[str, Any], snake_dict_to_camel_dict({key: None}))))


def camel_preserving_options(
    value: Any,
    verbatim_keys: Iterable[str] = VERBATIM_KEYS,
    verbatim_map_keys: Iterable[str] = VERBATIM_MAP_KEYS,
    verbatim_values: Iterable[str] = (),
) -> Any:
    """
    Convert snake_case keys to camelCase at any depth.

    A key in `verbatim_keys` and the value under it are left untouched. The value
    under a key in `verbatim_values` is left untouched but the key is converted.
    The map under a key in `verbatim_map_keys` keeps its own keys while its values
    are converted.
    """

    def convert(item: Any) -> Any:
        return camel_preserving_options(
            item,
            verbatim_keys,
            verbatim_map_keys,
            verbatim_values,
        )

    if isinstance(value, list):
        return [convert(item) for item in value]
    if isinstance(value, dict):
        return {
            (key if key in verbatim_keys else _camel_key(key)): (
                val
                if key in verbatim_keys or key in verbatim_values
                else (
                    _convert_map_values(val, convert)
                    if key in verbatim_map_keys
                    else convert(val)
                )
            )
            for key, val in value.items()
        }
    return value


def _written_def(result: Any, key: str, name: str) -> Dict[str, Any]:
    """Pick the def Atlas returned for a written typedef, or raise if the bundle lacks it."""
    defs = result.get(key) if isinstance(result, dict) else None
    for candidate in defs or []:
        if candidate.get("name") == name:
            return candidate
    raise ServicesError(f"Atlas did not return '{name}' in '{key}' after the write")


@dataclass(frozen=True)
class _TypeDefKind:
    """How the client marshals and converts one Atlas typedef category."""

    cls: type
    segment: str
    bundle_key: str
    # Set only where a category needs more than the generic conversion.
    to_payload: Optional[Callable[[Any], Dict[str, Any]]] = None
    from_response: Optional[Callable[[Dict[str, Any]], Any]] = None

    def build_payload(self, typedef: Any) -> Dict[str, Any]:
        """Serialise a typedef into a camelCase Atlas request payload."""
        if self.to_payload is not None:
            return self.to_payload(typedef)
        return camel_preserving_options(to_dict(typedef))

    def parse_response(self, raw: Dict[str, Any]) -> Any:
        """Deserialise an Atlas typedef response into this category's dataclass."""
        if self.from_response is not None:
            return self.from_response(raw)
        return from_dict(self.cls, snake_preserving_options(raw))


_ENUM = _TypeDefKind(
    AtlasEnumDef,
    "enumdef",
    "enumDefs",
    _enum_def_to_payload,
    _enum_def_from_response,
)
_CLASSIFICATION = _TypeDefKind(
    AtlasClassificationDef,
    "classificationdef",
    "classificationDefs",
)
_ENTITY = _TypeDefKind(AtlasEntityDef, "entitydef", "entityDefs")
_STRUCT = _TypeDefKind(AtlasStructDef, "structdef", "structDefs")
_RELATIONSHIP = _TypeDefKind(
    AtlasRelationshipDef,
    "relationshipdef",
    "relationshipDefs",
)
_BUSINESS_METADATA = _TypeDefKind(
    AtlasBusinessMetadataDef,
    "businessmetadatadef",
    "businessMetadataDefs",
)


class AtlasTypeDefClient:
    """Apache Atlas typedef API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def _get_def(self, kind: _TypeDefKind, name: str) -> Optional[Any]:
        """Retrieve a typedef of the given category by name, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/{kind.segment}/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return kind.parse_response(result)

    def _write_def(
        self,
        write: Callable[..., Any],
        kind: _TypeDefKind,
        typedef: Any,
    ) -> Any:
        """Create (POST) or update (PUT) a typedef and return the def Atlas wrote."""
        result = write(
            f"{TYPES_API}/typedefs",
            data={kind.bundle_key: [kind.build_payload(typedef)]},
        )
        return kind.parse_response(
            _written_def(result, kind.bundle_key, typedef.name),
        )

    def get_enum_def_by_name(self, name: str) -> Optional[AtlasEnumDef]:
        """Retrieve a single enum typedef by name, or None if not found."""
        return self._get_def(_ENUM, name)

    def get_classification_def_by_name(
        self,
        name: str,
    ) -> Optional[AtlasClassificationDef]:
        """Retrieve a single classification typedef by name, or None if not found."""
        return self._get_def(_CLASSIFICATION, name)

    def get_entity_def_by_name(self, name: str) -> Optional[AtlasEntityDef]:
        """Retrieve a single entity typedef by name, or None if not found."""
        return self._get_def(_ENTITY, name)

    def get_struct_def_by_name(self, name: str) -> Optional[AtlasStructDef]:
        """Retrieve a single struct typedef by name, or None if not found."""
        return self._get_def(_STRUCT, name)

    def get_relationship_def_by_name(
        self,
        name: str,
    ) -> Optional[AtlasRelationshipDef]:
        """Retrieve a single relationship typedef by name, or None if not found."""
        return self._get_def(_RELATIONSHIP, name)

    def get_business_metadata_def_by_name(
        self,
        name: str,
    ) -> Optional[AtlasBusinessMetadataDef]:
        """Retrieve a single business metadata typedef by name, or None if not found."""
        return self._get_def(_BUSINESS_METADATA, name)

    def list_typedef_headers(self) -> List[Dict[str, Any]]:
        """List the headers (guid, name, category, service type) of all typedefs."""
        result = self.api_client.get(f"{TYPES_API}/typedefs/headers")
        return snake_preserving_options(result or [])

    def get_typedef_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve any typedef by name as a snake_case dict, or None if not found."""
        result = self.api_client.get(
            f"{TYPES_API}/typedef/name/{name}",
            squelch={404: None},
        )

        if result is None:
            return None

        return snake_preserving_options(result)

    def create_enum_def(self, enum_def: AtlasEnumDef) -> AtlasEnumDef:
        """Create a new enum typedef."""
        return self._write_def(self.api_client.post, _ENUM, enum_def)

    def update_enum_def(self, enum_def: AtlasEnumDef) -> AtlasEnumDef:
        """Update an existing enum typedef."""
        return self._write_def(self.api_client.put, _ENUM, enum_def)

    def create_classification_def(
        self,
        classification_def: AtlasClassificationDef,
    ) -> AtlasClassificationDef:
        """Create a new classification typedef."""
        return self._write_def(
            self.api_client.post,
            _CLASSIFICATION,
            classification_def,
        )

    def update_classification_def(
        self,
        classification_def: AtlasClassificationDef,
    ) -> AtlasClassificationDef:
        """Update an existing classification typedef."""
        return self._write_def(self.api_client.put, _CLASSIFICATION, classification_def)

    def create_entity_def(self, entity_def: AtlasEntityDef) -> AtlasEntityDef:
        """Create a new entity typedef."""
        return self._write_def(self.api_client.post, _ENTITY, entity_def)

    def update_entity_def(self, entity_def: AtlasEntityDef) -> AtlasEntityDef:
        """Update an existing entity typedef."""
        return self._write_def(self.api_client.put, _ENTITY, entity_def)

    def create_struct_def(self, struct_def: AtlasStructDef) -> AtlasStructDef:
        """Create a new struct typedef."""
        return self._write_def(self.api_client.post, _STRUCT, struct_def)

    def update_struct_def(self, struct_def: AtlasStructDef) -> AtlasStructDef:
        """Update an existing struct typedef."""
        return self._write_def(self.api_client.put, _STRUCT, struct_def)

    def create_relationship_def(
        self,
        relationship_def: AtlasRelationshipDef,
    ) -> AtlasRelationshipDef:
        """Create a new relationship typedef."""
        return self._write_def(self.api_client.post, _RELATIONSHIP, relationship_def)

    def update_relationship_def(
        self,
        relationship_def: AtlasRelationshipDef,
    ) -> AtlasRelationshipDef:
        """Update an existing relationship typedef."""
        return self._write_def(self.api_client.put, _RELATIONSHIP, relationship_def)

    def create_business_metadata_def(
        self,
        business_metadata_def: AtlasBusinessMetadataDef,
    ) -> AtlasBusinessMetadataDef:
        """Create a new business metadata typedef."""
        return self._write_def(
            self.api_client.post,
            _BUSINESS_METADATA,
            business_metadata_def,
        )

    def update_business_metadata_def(
        self,
        business_metadata_def: AtlasBusinessMetadataDef,
    ) -> AtlasBusinessMetadataDef:
        """Update an existing business metadata typedef."""
        return self._write_def(
            self.api_client.put,
            _BUSINESS_METADATA,
            business_metadata_def,
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


def _fill_unset(incoming: Any, existing: Any) -> Any:
    """Return `incoming` with each unset (NULLABLE) field taken from `existing`."""
    return replace(
        incoming,
        **{
            field.name: getattr(existing, field.name)
            for field in fields(incoming)
            if getattr(incoming, field.name) is NULLABLE
        },
    )


def _align_by_key(incoming: List[Any], existing: List[Any], key: str) -> List[Any]:
    """Fill unset fields of each incoming item from the existing item with the same `key`."""
    existing_by_key = {getattr(item, key): item for item in existing}

    return [
        (
            _fill_unset(item, existing_by_key[getattr(item, key)])
            if getattr(item, key) in existing_by_key
            else item
        )
        for item in incoming
    ]


def align_enum_elements(
    incoming: List[AtlasEnumElementDef],
    existing: List[AtlasEnumElementDef],
) -> List[AtlasEnumElementDef]:
    """
    Fill unset ordinal/description of incoming elements from the existing element
    with the same value, so Atlas-assigned ordinals do not register as a change.
    """
    return _align_by_key(incoming, existing, "value")


def align_attribute_defs(
    incoming: List[AtlasAttributeDef],
    existing: List[AtlasAttributeDef],
) -> List[AtlasAttributeDef]:
    """
    Fill unset fields of incoming attributes from the existing attribute with the
    same name, so Atlas-assigned defaults do not register as a change.
    """
    return _align_by_key(incoming, existing, "name")


def align_relationship_end_def(
    incoming: AtlasRelationshipEndDef,
    existing: AtlasRelationshipEndDef,
) -> AtlasRelationshipEndDef:
    """
    Fill unset fields of an incoming relationship end from the existing end, so
    Atlas-assigned defaults do not register as a change.
    """
    return _fill_unset(incoming, existing)


def _drop_none(item: Dict[str, Any]) -> Dict[str, Any]:
    """Drop the unset (None) top-level keys of a suboption dict."""
    return {k: v for k, v in item.items() if v is not None}


def _clean_attribute(attribute: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keys from an attribute and from each of its constraints."""
    attribute = _drop_none(attribute)
    if "constraints" in attribute:
        attribute["constraints"] = [
            _drop_none(constraint) for constraint in attribute["constraints"]
        ]
    return attribute


# Ansible fills unset suboptions with None; drop them so they stay unset
# (NULLABLE) rather than serialising as explicit nulls. Cleaning stops at these
# levels: `options` and constraint `params` are user data and are left untouched.
_LIST_PARAM_CLEANERS = {"attribute_defs": _clean_attribute, "element_defs": _drop_none}
_DICT_PARAM_CLEANERS = {"end_def1": _drop_none, "end_def2": _drop_none}


def _extract_params(module_instance, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Read the spec'd parameters off a module instance, dropping unset suboptions."""
    params: Dict[str, Any] = {key: getattr(module_instance, key, None) for key in spec}

    for key, clean in _LIST_PARAM_CLEANERS.items():
        if params.get(key) is not None:
            params[key] = [clean(item) for item in params[key]]

    for key, clean in _DICT_PARAM_CLEANERS.items():
        if params.get(key) is not None:
            params[key] = clean(params[key])

    return params


def extract_enum_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable enum typedef parameters from a module instance into a dict."""
    return _extract_params(module_instance, AtlasEnumDef.argument_spec())


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
    return _extract_params(module_instance, AtlasRelationshipDef.argument_spec())


def extract_business_metadata_def_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable business metadata typedef parameters from a module instance into a dict."""
    return _extract_params(module_instance, AtlasBusinessMetadataDef.argument_spec())
