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
REST client for Apache Atlas entity instances.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import quote

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    NULLABLE,
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasTypeDefClient,
    camel_preserving_options,
    snake_preserving_options,
)

_LABEL_PATTERN = re.compile(r"[A-Za-z0-9_-]+", re.ASCII)
_INTEGER_PATTERN = re.compile(r"[+-]?[0-9]+", re.ASCII)

_INTEGER_TYPES = frozenset({"byte", "short", "int", "long", "date"})
_FLOAT_TYPES = frozenset({"float", "double"})
_ARRAY_PATTERN = re.compile(r"array<(.+)>")
_PRIMITIVE_TYPES = _INTEGER_TYPES | _FLOAT_TYPES | {"boolean", "string"}

ENTITY_API = "/api/atlas/v2/entity"
ADMIN_API = "/api/atlas/admin"

# Entity attribute maps hold user data (attribute names such as `qualifiedName`), so
# the maps themselves are never case-converted, though their own key is. Each name
# is listed in both casings because requests are snake_case and responses are
# camelCase.
ENTITY_VERBATIM_VALUES = (
    "attributes",
    "relationshipAttributes",
    "relationship_attributes",
    "businessAttributes",
    "business_attributes",
    "customAttributes",
    "custom_attributes",
)


@dataclass
class AtlasClassification:
    """Representation of a classification attached to an Apache Atlas entity."""

    type_name: str

    attributes: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    propagate: Union[bool, None, NULLABLE] = NULLABLE
    remove_propagations_on_entity_delete: Union[bool, None, NULLABLE] = NULLABLE
    validity_periods: Union[List[Dict[str, Any]], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    entity_guid: Union[str, None, NULLABLE] = NULLABLE
    entity_status: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class AtlasEntity:
    """Representation of an Apache Atlas entity instance."""

    type_name: str

    attributes: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    relationship_attributes: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    custom_attributes: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    business_attributes: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    labels: Union[List[str], None, NULLABLE] = NULLABLE
    classifications: Union[List[AtlasClassification], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    guid: Union[str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE
    is_incomplete: Union[bool, None, NULLABLE] = NULLABLE
    version: Union[int, None, NULLABLE] = NULLABLE
    create_time: Union[int, None, NULLABLE] = NULLABLE
    update_time: Union[int, None, NULLABLE] = NULLABLE
    created_by: Union[str, None, NULLABLE] = NULLABLE
    updated_by: Union[str, None, NULLABLE] = NULLABLE


def validate_labels(labels: List[str]) -> None:
    """Raise ServicesError for a label Atlas would reject (ATLAS-400-00-090)."""
    for label in labels:
        if not _LABEL_PATTERN.fullmatch(label):
            raise ServicesError(
                f"Invalid label {label!r}: labels may only contain letters, digits, '_' and '-'",
            )


def _normalize_value(attribute: str, type_name: str, value: Any) -> Any:
    """Convert one attribute value to the type Atlas stores for type_name."""
    array = _ARRAY_PATTERN.fullmatch(type_name)
    if array:
        if not isinstance(value, list):
            raise ServicesError(
                f"Attribute '{attribute}' must be a list ({type_name}), not {value!r}",
            )
        return [_normalize_value(attribute, array.group(1), item) for item in value]

    if type_name not in _PRIMITIVE_TYPES:
        # Enums, maps, structs and the like: only Atlas can check them.
        return value

    invalid = ServicesError(
        f"Attribute '{attribute}' must be of type {type_name}, not {value!r}",
    )

    if isinstance(value, (dict, list)):
        raise invalid

    if type_name in _INTEGER_TYPES:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and _INTEGER_PATTERN.fullmatch(value.strip()):
            return int(value)
        raise invalid

    if type_name in _FLOAT_TYPES:
        if isinstance(value, bool):
            raise invalid
        if isinstance(value, (int, float)):
            return value
        try:
            return float(value)
        except ValueError:
            raise invalid

    if type_name == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise invalid

    return value if isinstance(value, str) else str(value)


def normalize_attributes(
    owner: str,
    name: str,
    attribute_defs: Any,
    attributes: Dict[str, Any],
    null_hint: str = "",
) -> Dict[str, Any]:
    """
    Check attributes against the typedef that defines them and convert the values to
    the types Atlas stores.

    Atlas silently ignores attributes the typedef does not define, and stores the
    string "5" of an int attribute as 5, so both would otherwise show up as a
    change on every run.

    `owner` ("Business metadata", "Classification") and `name` label the errors.
    Raises ServicesError for an unknown attribute, a null, or a value that cannot
    be the attribute's type.
    """
    types: Dict[str, str] = {
        attribute_def.name: attribute_def.type_name
        for attribute_def in (
            attribute_defs if isinstance(attribute_defs, list) else []
        )
    }

    unknown = sorted(set(attributes) - set(types))
    if unknown:
        raise ServicesError(
            f"{owner} '{name}' does not define attribute(s) "
            f"{', '.join(unknown)}; it defines: {', '.join(sorted(types)) or 'none'}",
        )

    normalized: Dict[str, Any] = {}
    for attribute, value in attributes.items():
        if value is None:
            raise ServicesError(
                f"{owner} '{name}' attribute '{attribute}' cannot be null{null_hint}",
            )
        try:
            normalized[attribute] = _normalize_value(
                attribute,
                types[attribute],
                value,
            )
        except ServicesError as e:
            raise ServicesError(f"{owner} '{name}': {e}")

    return normalized


def normalize_business_attributes(
    name: str,
    attribute_defs: Any,
    attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """Check business attributes against their business metadata typedef; see normalize_attributes()."""
    return normalize_attributes(
        "Business metadata",
        name,
        attribute_defs,
        attributes,
        null_hint="; remove the whole business metadata with state 'absent' instead",
    )


def _inherited_attribute_defs(
    get_def: Callable[[str], Any],
    name: str,
) -> Optional[List[AtlasAttributeDef]]:
    """Collect the attributes of a typedef and of all its super types, or None if there is no such typedef."""
    root = get_def(name)
    if root is None:
        return None

    attribute_defs: List[AtlasAttributeDef] = []
    seen = {name}
    pending = [root]
    while pending:
        typedef = pending.pop(0)
        if isinstance(typedef.attribute_defs, list):
            attribute_defs.extend(typedef.attribute_defs)
        if isinstance(typedef.super_types, list):
            for super_type in typedef.super_types:
                if super_type in seen:
                    continue
                seen.add(super_type)
                super_def = get_def(super_type)
                if super_def is not None:
                    pending.append(super_def)

    return attribute_defs


def classification_attribute_defs(
    typedef_client: AtlasTypeDefClient,
    name: str,
) -> Optional[List[AtlasAttributeDef]]:
    """
    Return the attributes of a classification typedef and of all its super types,
    or None if there is no such classification.

    A classification inherits the attributes of its super types, and Atlas silently
    drops an attribute that is not among them.
    """
    return _inherited_attribute_defs(
        typedef_client.get_classification_def_by_name,
        name,
    )


def entity_attribute_defs(
    typedef_client: AtlasTypeDefClient,
    name: str,
) -> Optional[List[AtlasAttributeDef]]:
    """
    Return the attributes of an entity typedef and of all its super types (such as
    `qualifiedName` from Referenceable), or None if there is no such entity type.
    """
    return _inherited_attribute_defs(typedef_client.get_entity_def_by_name, name)


def _classification_payload(classification: AtlasClassification) -> Dict[str, Any]:
    """Serialise a classification into the camelCase body Atlas expects, without the read-only fields."""
    payload = camel_preserving_options(
        to_dict(classification),
        verbatim_keys=(),
        verbatim_map_keys=(),
        verbatim_values=ENTITY_VERBATIM_VALUES,
    )
    payload.pop("entityGuid", None)
    payload.pop("entityStatus", None)
    return payload


def _entity_to_payload(entity: AtlasEntity) -> Dict[str, Any]:
    """Serialise an AtlasEntity into the camelCase body of an Atlas entity request."""
    return {
        "entity": camel_preserving_options(
            to_dict(entity),
            verbatim_keys=(),
            verbatim_map_keys=(),
            verbatim_values=ENTITY_VERBATIM_VALUES,
        ),
    }


def _entity_from_response(raw: Any) -> AtlasEntity:
    """Deserialise an Atlas entity-with-ext-info response into an AtlasEntity."""
    entity = raw.get("entity") if isinstance(raw, dict) else None
    if not isinstance(entity, dict) or not isinstance(entity.get("typeName"), str):
        raise ServicesError("Atlas returned an unexpected response for the entity")

    return from_dict(
        AtlasEntity,
        snake_preserving_options(
            entity,
            verbatim_keys=(),
            verbatim_map_keys=(),
            verbatim_values=ENTITY_VERBATIM_VALUES,
        ),
    )


def _created_guid(result: Any) -> str:
    """Pick the guid of the created entity out of an entity mutation response."""
    mutated = result.get("mutatedEntities") if isinstance(result, dict) else None
    created = mutated.get("CREATE") if isinstance(mutated, dict) else None
    if isinstance(created, list) and created and isinstance(created[0], dict):
        guid = created[0].get("guid")
        if isinstance(guid, str) and guid:
            return guid
    raise ServicesError("Atlas did not report the created entity")


class AtlasEntityClient:
    """Apache Atlas entity instance API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def get_entity_by_guid(self, guid: str) -> Optional[AtlasEntity]:
        """
        Retrieve an entity by guid, or None if the guid is unknown.

        Atlas still returns a deleted entity by guid, with status DELETED.
        """
        result = self.api_client.get(
            f"{ENTITY_API}/guid/{quote(guid, safe='')}",
            params={"minExtInfo": "true"},
            squelch={404: None},
        )

        if result is None:
            return None

        return _entity_from_response(result)

    def get_entity_by_unique_attributes(
        self,
        type_name: str,
        unique_attributes: Dict[str, Any],
    ) -> Optional[AtlasEntity]:
        """
        Retrieve an entity by type and unique attributes, or None if there is none.

        Atlas never returns a deleted entity by unique attributes.
        """
        params: Dict[str, Any] = {"minExtInfo": "true"}
        params.update(
            {f"attr:{name}": value for name, value in unique_attributes.items()},
        )

        result = self.api_client.get(
            f"{ENTITY_API}/uniqueAttribute/type/{quote(type_name, safe='')}",
            params=params,
            squelch={404: None},
        )

        if result is None:
            return None

        return _entity_from_response(result)

    def create_entity(self, entity: AtlasEntity) -> AtlasEntity:
        """Create an entity and return it as Atlas stored it."""
        result = self.api_client.post(ENTITY_API, data=_entity_to_payload(entity))

        guid = _created_guid(result)
        created = self.get_entity_by_guid(guid)
        if created is None:
            raise ServicesError(
                f"Atlas created entity '{guid}' but could not return it",
            )

        return created

    def update_entity_by_unique_attributes(
        self,
        type_name: str,
        unique_attributes: Dict[str, Any],
        entity: AtlasEntity,
    ) -> None:
        """
        Partially update an entity addressed by its unique attributes.

        Only the attributes in `entity` change. A POST of the entity would instead
        fail unless it carried every mandatory attribute.
        """
        params: Dict[str, Any] = {
            f"attr:{name}": value for name, value in unique_attributes.items()
        }

        self.api_client.put(
            f"{ENTITY_API}/uniqueAttribute/type/{quote(type_name, safe='')}",
            params=params,
            data=_entity_to_payload(entity),
        )

    def delete_entity_by_guid(self, guid: str) -> List[str]:
        """
        Delete an entity by guid and return the guids Atlas deleted.

        Atlas answers HTTP 200 whether or not the guid exists, and the delete is
        soft: the entity remains with status DELETED until it is purged. The list
        is empty for an unknown or deleted guid, and holds more than the guid when
        the delete cascades to owned entities.
        """
        result = self.api_client.delete(f"{ENTITY_API}/guid/{quote(guid, safe='')}")

        mutated = result.get("mutatedEntities") if isinstance(result, dict) else None
        deleted = mutated.get("DELETE") if isinstance(mutated, dict) else None
        if not isinstance(deleted, list):
            return []

        return [
            str(item["guid"])
            for item in deleted
            if isinstance(item, dict) and item.get("guid")
        ]

    def set_entity_labels(self, guid: str, labels: List[str]) -> None:
        """
        Replace all labels of an entity with the given list.

        An empty list removes every label. Atlas ignores a request body on DELETE
        when reached through Knox, so this POST is the only way to remove labels.
        """
        self.api_client.post(
            f"{ENTITY_API}/guid/{quote(guid, safe='')}/labels",
            data=labels,
        )

    def set_entity_business_metadata(
        self,
        guid: str,
        name: str,
        attributes: Dict[str, Any],
    ) -> None:
        """
        Set attributes of one business metadata on an entity, merging with its others.

        Never sends isOverwrite=true, which would also wipe every other business
        metadata on the entity.
        """
        self.api_client.post(
            f"{ENTITY_API}/guid/{quote(guid, safe='')}/businessmetadata/{quote(name, safe='')}",
            params={"isOverwrite": "false"},
            data=attributes,
        )

    def remove_entity_business_metadata(self, guid: str, name: str) -> None:
        """
        Remove one business metadata, with all its attributes, from an entity.

        Atlas ignores a request body on DELETE, so single attributes cannot be removed.
        """
        self.api_client.delete(
            f"{ENTITY_API}/guid/{quote(guid, safe='')}/businessmetadata/{quote(name, safe='')}",
        )

    def add_entity_classifications(
        self,
        guid: str,
        classifications: List[AtlasClassification],
    ) -> None:
        """
        Attach classifications to an entity.

        Atlas fails if one is already attached directly; use update_entity_classifications().
        """
        self.api_client.post(
            f"{ENTITY_API}/guid/{quote(guid, safe='')}/classifications",
            data=[_classification_payload(c) for c in classifications],
        )

    def update_entity_classifications(
        self,
        guid: str,
        classifications: List[AtlasClassification],
    ) -> None:
        """
        Update classifications already attached directly to an entity.

        Atlas merges the attributes given into the existing ones, and fails if a
        classification is not attached.
        """
        self.api_client.put(
            f"{ENTITY_API}/guid/{quote(guid, safe='')}/classifications",
            data=[_classification_payload(c) for c in classifications],
        )

    def remove_entity_classification(self, guid: str, name: str) -> None:
        """Remove the classification attached directly to an entity; Atlas fails if there is none."""
        self.api_client.delete(
            f"{ENTITY_API}/guid/{quote(guid, safe='')}/classification/{quote(name, safe='')}",
        )

    def purge_entities(self, guids: List[str]) -> None:
        """Permanently remove soft-deleted entities; needs Atlas administrator rights."""
        if not guids:
            return

        self.api_client.put(f"{ADMIN_API}/purge", data=guids)
