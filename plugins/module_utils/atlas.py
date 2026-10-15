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

from dataclasses import dataclass
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
)

TYPES_API = "/api/atlas/v2/types"


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


def _snake_preserving_options(value: Any) -> Any:
    """Convert camelCase keys to snake_case at any depth, leaving 'options' maps verbatim."""
    if isinstance(value, list):
        return [_snake_preserving_options(item) for item in value]
    if isinstance(value, dict):
        return {
            (
                key
                if key == "options"
                else next(iter(camel_dict_to_snake_dict({key: None}, reversible=True)))
            ): (val if key == "options" else _snake_preserving_options(val))
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

    def delete_typedef_by_name(self, name: str) -> None:
        """Delete a typedef by name (idempotent)."""
        self.api_client.delete(
            f"{TYPES_API}/typedef/name/{name}",
            squelch={404: None},
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
