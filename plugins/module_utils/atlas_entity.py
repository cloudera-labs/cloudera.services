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

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    NULLABLE,
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    camel_preserving_options,
    snake_preserving_options,
)

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

    def delete_entity_by_guid(self, guid: str) -> None:
        """
        Delete an entity by guid.

        Atlas answers HTTP 200 whether or not the guid exists, and the delete is
        soft: the entity remains with status DELETED until it is purged.
        """
        self.api_client.delete(f"{ENTITY_API}/guid/{quote(guid, safe='')}")

    def purge_entities(self, guids: List[str]) -> None:
        """Permanently remove soft-deleted entities; needs Atlas administrator rights."""
        if not guids:
            return

        self.api_client.put(f"{ADMIN_API}/purge", data=guids)
