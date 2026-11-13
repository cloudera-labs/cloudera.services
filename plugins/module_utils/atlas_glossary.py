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
REST client for the Apache Atlas glossary (glossaries, categories, and terms).
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

GLOSSARY_API = "/api/atlas/v2/glossary"

# `additionalAttributes` is a user-defined map, so its names are never case-converted.
# Each name is listed in both casings because requests are snake_case and responses
# are camelCase.
GLOSSARY_VERBATIM_VALUES = (
    "additionalAttributes",
    "additional_attributes",
)


@dataclass
class AtlasRelatedTermHeader:
    """Reference to a glossary term, as listed on a glossary, category, or term."""

    term_guid: Union[str, None, NULLABLE] = NULLABLE
    relation_guid: Union[str, None, NULLABLE] = NULLABLE
    display_text: Union[str, None, NULLABLE] = NULLABLE
    qualified_name: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    expression: Union[str, None, NULLABLE] = NULLABLE
    steward: Union[str, None, NULLABLE] = NULLABLE
    source: Union[str, None, NULLABLE] = NULLABLE
    status: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class AtlasRelatedCategoryHeader:
    """Reference to a glossary category, as listed on a glossary or category."""

    category_guid: Union[str, None, NULLABLE] = NULLABLE
    parent_category_guid: Union[str, None, NULLABLE] = NULLABLE
    relation_guid: Union[str, None, NULLABLE] = NULLABLE
    display_text: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class AtlasGlossary:
    """Representation of an Apache Atlas glossary."""

    name: str

    qualified_name: Union[str, None, NULLABLE] = NULLABLE
    short_description: Union[str, None, NULLABLE] = NULLABLE
    long_description: Union[str, None, NULLABLE] = NULLABLE
    language: Union[str, None, NULLABLE] = NULLABLE
    usage: Union[str, None, NULLABLE] = NULLABLE
    additional_attributes: Union[Dict[str, Any], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    guid: Union[str, None, NULLABLE] = NULLABLE
    terms: Union[List[AtlasRelatedTermHeader], None, NULLABLE] = NULLABLE
    categories: Union[List[AtlasRelatedCategoryHeader], None, NULLABLE] = NULLABLE


@dataclass
class AtlasGlossaryHeader:
    """Reference to the glossary a category or term is anchored to."""

    glossary_guid: Union[str, None, NULLABLE] = NULLABLE
    relation_guid: Union[str, None, NULLABLE] = NULLABLE
    display_text: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class AtlasGlossaryCategory:
    """Representation of an Apache Atlas glossary category."""

    name: str

    qualified_name: Union[str, None, NULLABLE] = NULLABLE
    short_description: Union[str, None, NULLABLE] = NULLABLE
    long_description: Union[str, None, NULLABLE] = NULLABLE
    additional_attributes: Union[Dict[str, Any], None, NULLABLE] = NULLABLE

    # Read-only (set by Atlas)
    guid: Union[str, None, NULLABLE] = NULLABLE
    anchor: Union[AtlasGlossaryHeader, None, NULLABLE] = NULLABLE
    parent_category: Union[AtlasRelatedCategoryHeader, None, NULLABLE] = NULLABLE
    children_categories: Union[List[AtlasRelatedCategoryHeader], None, NULLABLE] = (
        NULLABLE
    )
    terms: Union[List[AtlasRelatedTermHeader], None, NULLABLE] = NULLABLE


@dataclass
class AtlasRelatedObjectId:
    """Reference to an entity a term is assigned to, with the assignment relationship."""

    guid: Union[str, None, NULLABLE] = NULLABLE
    type_name: Union[str, None, NULLABLE] = NULLABLE
    qualified_name: Union[str, None, NULLABLE] = NULLABLE
    display_text: Union[str, None, NULLABLE] = NULLABLE
    entity_status: Union[str, None, NULLABLE] = NULLABLE
    relationship_type: Union[str, None, NULLABLE] = NULLABLE
    relationship_guid: Union[str, None, NULLABLE] = NULLABLE
    relationship_status: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class AtlasGlossaryTerm:
    """Representation of an Apache Atlas glossary term (as far as the glossary needs it)."""

    name: str

    guid: Union[str, None, NULLABLE] = NULLABLE
    qualified_name: Union[str, None, NULLABLE] = NULLABLE
    assigned_entities: Union[List[AtlasRelatedObjectId], None, NULLABLE] = NULLABLE


_RESERVED_NAME_CHARACTERS = frozenset("@.<>")


def validate_glossary_name(kind: str, name: str) -> None:
    """Raise ServicesError for a name Atlas would reject (ATLAS-400-00-083)."""
    if not name:
        raise ServicesError(f"The {kind} name may not be empty")

    if _RESERVED_NAME_CHARACTERS.intersection(name):
        raise ServicesError(
            f"Invalid {kind} name {name!r}: a name may not contain '@', '.', '<' or '>'",
        )


def _require_identity(raw: Any, kind: str) -> None:
    """Raise ServicesError unless an Atlas response is an object with a guid and a name."""
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("guid"), str)
        or not isinstance(raw.get("name"), str)
    ):
        raise ServicesError(f"Atlas returned an unexpected response for the {kind}")


def _glossary_to_payload(glossary: AtlasGlossary) -> Dict[str, Any]:
    """Serialise an AtlasGlossary into the camelCase body of an Atlas glossary request."""
    return camel_preserving_options(
        to_dict(glossary),
        verbatim_keys=(),
        verbatim_map_keys=(),
        verbatim_values=GLOSSARY_VERBATIM_VALUES,
    )


def _category_to_payload(category: AtlasGlossaryCategory) -> Dict[str, Any]:
    """Serialise an AtlasGlossaryCategory into the camelCase body of an Atlas category request."""
    return camel_preserving_options(
        to_dict(category),
        verbatim_keys=(),
        verbatim_map_keys=(),
        verbatim_values=GLOSSARY_VERBATIM_VALUES,
    )


def _glossary_from_response(raw: Any) -> AtlasGlossary:
    """Deserialise an Atlas glossary response into an AtlasGlossary."""
    _require_identity(raw, "glossary")

    return from_dict(
        AtlasGlossary,
        snake_preserving_options(
            raw,
            verbatim_keys=(),
            verbatim_map_keys=(),
            verbatim_values=GLOSSARY_VERBATIM_VALUES,
        ),
    )


def _category_from_response(raw: Any) -> AtlasGlossaryCategory:
    """Deserialise an Atlas glossary category response into an AtlasGlossaryCategory."""
    _require_identity(raw, "category")

    return from_dict(
        AtlasGlossaryCategory,
        snake_preserving_options(
            raw,
            verbatim_keys=(),
            verbatim_map_keys=(),
            verbatim_values=GLOSSARY_VERBATIM_VALUES,
        ),
    )


def _term_from_response(raw: Any) -> AtlasGlossaryTerm:
    """Deserialise an Atlas glossary term response into an AtlasGlossaryTerm."""
    _require_identity(raw, "term")

    return from_dict(
        AtlasGlossaryTerm,
        snake_preserving_options(
            raw,
            verbatim_keys=(),
            verbatim_map_keys=(),
            verbatim_values=GLOSSARY_VERBATIM_VALUES,
        ),
    )


def resolve_glossary(
    client: "AtlasGlossaryClient",
    name: Optional[str] = None,
    qualified_name: Optional[str] = None,
    guid: Optional[str] = None,
) -> AtlasGlossary:
    """Return the one glossary that matches, or raise ServicesError."""
    if guid:
        glossary = client.get_glossary(guid)
        if glossary is None:
            raise ServicesError(f"No glossary with guid '{guid}' exists.")
        return glossary

    matches = client.find_glossaries(name=name, qualified_name=qualified_name)

    if not matches:
        raise ServicesError(f"No glossary named '{name or qualified_name}' exists.")

    if len(matches) > 1:
        raise ServicesError(
            f"More than one glossary is named '{name}'; "
            "identify it with glossary_guid or glossary_qualified_name.",
        )

    return matches[0]


class AtlasGlossaryClient:
    """Apache Atlas glossary API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def list_glossaries(self) -> List[AtlasGlossary]:
        """List every glossary, each with the headers of its terms and categories."""
        result = self.api_client.get(GLOSSARY_API, params={"limit": "-1"})

        if result is None:
            return []

        if not isinstance(result, list):
            raise ServicesError(
                "Atlas returned an unexpected response for the glossaries",
            )

        return [_glossary_from_response(item) for item in result]

    def get_glossary(self, guid: str) -> Optional[AtlasGlossary]:
        """
        Retrieve a glossary by guid, or None if the guid is unknown.

        Atlas deletes glossaries for good, so a deleted glossary is simply unknown.
        """
        result = self.api_client.get(
            f"{GLOSSARY_API}/{quote(guid, safe='')}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _glossary_from_response(result)

    def find_glossaries(
        self,
        name: Optional[str] = None,
        qualified_name: Optional[str] = None,
    ) -> List[AtlasGlossary]:
        """
        Find the glossaries whose name and qualified name equal the given values.

        Only the qualified name is unique, so a name can match several glossaries.
        A criterion left as None matches everything.
        """
        return [
            glossary
            for glossary in self.list_glossaries()
            if (name is None or glossary.name == name)
            and (qualified_name is None or glossary.qualified_name == qualified_name)
        ]

    def create_glossary(self, glossary: AtlasGlossary) -> AtlasGlossary:
        """Create a glossary and return it as Atlas stored it."""
        result = self.api_client.post(
            GLOSSARY_API,
            data=_glossary_to_payload(glossary),
        )

        return _glossary_from_response(result)

    def partial_update_glossary(
        self,
        guid: str,
        attributes: Dict[str, str],
    ) -> AtlasGlossary:
        """
        Change only the given primitive fields of a glossary and return it.

        Atlas accepts name, short_description, long_description, language and usage,
        and an empty string clears a field. The full PUT is deliberately not offered:
        it deletes every field the body leaves out.
        """
        if not attributes:
            raise ServicesError("A glossary update needs at least one attribute")

        result = self.api_client.put(
            f"{GLOSSARY_API}/{quote(guid, safe='')}/partial",
            data=camel_preserving_options(
                attributes,
                verbatim_keys=(),
                verbatim_map_keys=(),
            ),
        )

        return _glossary_from_response(result)

    def list_terms(self, glossary_guid: str) -> List[AtlasGlossaryTerm]:
        """List the terms of a glossary, each with the entities it is assigned to."""
        result = self.api_client.get(
            f"{GLOSSARY_API}/{quote(glossary_guid, safe='')}/terms",
            params={"limit": "-1"},
        )

        if result is None:
            return []

        if not isinstance(result, list):
            raise ServicesError("Atlas returned an unexpected response for the terms")

        return [_term_from_response(item) for item in result]

    def list_category_headers(
        self,
        glossary_guid: str,
    ) -> List[AtlasRelatedCategoryHeader]:
        """List the headers (guid, current name, parent guid) of a glossary's categories."""
        result = self.api_client.get(
            f"{GLOSSARY_API}/{quote(glossary_guid, safe='')}/categories/headers",
            params={"limit": "-1"},
        )

        if result is None:
            return []

        if not isinstance(result, list):
            raise ServicesError(
                "Atlas returned an unexpected response for the category headers",
            )

        for item in result:
            if not isinstance(item, dict) or not isinstance(
                item.get("categoryGuid"),
                str,
            ):
                raise ServicesError(
                    "Atlas returned an unexpected response for the category headers",
                )

        return [
            from_dict(AtlasRelatedCategoryHeader, snake_preserving_options(item))
            for item in result
        ]

    def find_categories(
        self,
        glossary_guid: str,
        name: Optional[str] = None,
    ) -> List[AtlasGlossaryCategory]:
        """
        Find the categories of a glossary whose name equals the given name.

        Matches on the name field (the headers' display text), never the qualified
        name, which Atlas leaves stale after a re-parent. A name can match several
        categories under different parents. Left as None, every category matches.
        """
        categories = []
        for header in self.list_category_headers(glossary_guid):
            if name is not None and header.display_text != name:
                continue
            category = self.get_category(str(header.category_guid))
            if category is not None:
                categories.append(category)
        return categories

    def create_category(self, category: AtlasGlossaryCategory) -> AtlasGlossaryCategory:
        """Create a category in the glossary named by its anchor and return it as stored."""
        result = self.api_client.post(
            f"{GLOSSARY_API}/category",
            data=_category_to_payload(category),
        )

        return _category_from_response(result)

    def get_category(self, guid: str) -> Optional[AtlasGlossaryCategory]:
        """Retrieve a category by guid, or None if the guid is unknown."""
        result = self.api_client.get(
            f"{GLOSSARY_API}/category/{quote(guid, safe='')}",
            squelch={404: None},
        )

        if result is None:
            return None

        return _category_from_response(result)

    def delete_glossary(self, guid: str) -> None:
        """
        Delete a glossary together with all of its terms and categories.

        Atlas refuses (HTTP 400) while any of its terms is assigned to an entity.
        A glossary that is already gone is not an error.
        """
        self.api_client.delete(
            f"{GLOSSARY_API}/{quote(guid, safe='')}",
            squelch={404: None},
        )
