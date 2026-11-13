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
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryClient,
    AtlasGlossaryHeader,
    AtlasGlossaryTerm,
    AtlasRelatedCategoryHeader,
    AtlasRelatedObjectId,
    AtlasRelatedTermHeader,
    validate_glossary_name,
)

GUID = "4b4117f6-dd77-419d-9b8d-b120891ff2b4"
OTHER_GUID = "f6b31a7e-c521-4270-8c7f-c33fe674f56d"
TERM_GUID = "5932c81e-0258-4bdc-a49f-8d3370e62f79"
CATEGORY_GUID = "5b292b6f-0983-4e43-8508-7115b9d9361d"

# Shaped after real Atlas 2.4 responses: empty sets and null fields are omitted.
GLOSSARY_RESPONSE = {
    "guid": GUID,
    "qualifiedName": "bank_qn",
    "name": "Bank",
    "longDescription": "long",
    "language": "French",
    "usage": "uu",
    "additionalAttributes": {"someKey": "someValue"},
    "terms": [
        {
            "termGuid": TERM_GUID,
            "relationGuid": "0c437486-2b95-451f-9e5a-2fe337b4a721",
            "displayText": "Account",
        },
    ],
    "categories": [
        {
            "categoryGuid": CATEGORY_GUID,
            "parentCategoryGuid": "ac37096b-6021-402d-8a65-7f3538615d27",
            "relationGuid": "91fa3630-dc43-4a32-8076-15ba80f55f25",
            "displayText": "Customer",
        },
    ],
}

EXPECTED_GLOSSARY = AtlasGlossary(
    name="Bank",
    guid=GUID,
    qualified_name="bank_qn",
    long_description="long",
    language="French",
    usage="uu",
    additional_attributes={"someKey": "someValue"},
    terms=[
        AtlasRelatedTermHeader(
            term_guid=TERM_GUID,
            relation_guid="0c437486-2b95-451f-9e5a-2fe337b4a721",
            display_text="Account",
        ),
    ],
    categories=[
        AtlasRelatedCategoryHeader(
            category_guid=CATEGORY_GUID,
            parent_category_guid="ac37096b-6021-402d-8a65-7f3538615d27",
            relation_guid="91fa3630-dc43-4a32-8076-15ba80f55f25",
            display_text="Customer",
        ),
    ],
)

SECOND_RESPONSE = {
    "guid": OTHER_GUID,
    "qualifiedName": "Bank",
    "name": "Bank",
}

EXPECTED_SECOND = AtlasGlossary(name="Bank", guid=OTHER_GUID, qualified_name="Bank")

PARENT_GUID = "ac37096b-6021-402d-8a65-7f3538615d27"
CHILD_GUID = "d1f3a1d0-6a6e-4a6d-9a16-5b0c3c1f7a11"

# Shaped after a real Atlas 2.4 category response: empty sets and null fields are omitted.
CATEGORY_RESPONSE = {
    "guid": CATEGORY_GUID,
    "qualifiedName": "Customer@bank_qn",
    "name": "Customer",
    "shortDescription": "short",
    "additionalAttributes": {"someKey": "someValue"},
    "anchor": {
        "glossaryGuid": GUID,
        "relationGuid": "e4a1f6c0-3a58-4f7e-8d7b-0e5b3a9c1d22",
        "displayText": "Bank",
    },
    "parentCategory": {
        "categoryGuid": PARENT_GUID,
        "relationGuid": "b6c2d1aa-7b0f-4b1e-9e55-2d6f9d6d8f33",
        "displayText": "Party",
    },
    "childrenCategories": [
        {
            "categoryGuid": CHILD_GUID,
            "parentCategoryGuid": CATEGORY_GUID,
            "relationGuid": "c7d3e2bb-8c10-4c2f-8f66-3e7a0e7e9a44",
            "displayText": "Retail",
        },
    ],
    "terms": [
        {
            "termGuid": TERM_GUID,
            "relationGuid": "0c437486-2b95-451f-9e5a-2fe337b4a721",
            "displayText": "Account",
        },
    ],
}

EXPECTED_CATEGORY = AtlasGlossaryCategory(
    name="Customer",
    guid=CATEGORY_GUID,
    qualified_name="Customer@bank_qn",
    short_description="short",
    additional_attributes={"someKey": "someValue"},
    anchor=AtlasGlossaryHeader(
        glossary_guid=GUID,
        relation_guid="e4a1f6c0-3a58-4f7e-8d7b-0e5b3a9c1d22",
        display_text="Bank",
    ),
    parent_category=AtlasRelatedCategoryHeader(
        category_guid=PARENT_GUID,
        relation_guid="b6c2d1aa-7b0f-4b1e-9e55-2d6f9d6d8f33",
        display_text="Party",
    ),
    children_categories=[
        AtlasRelatedCategoryHeader(
            category_guid=CHILD_GUID,
            parent_category_guid=CATEGORY_GUID,
            relation_guid="c7d3e2bb-8c10-4c2f-8f66-3e7a0e7e9a44",
            display_text="Retail",
        ),
    ],
    terms=[
        AtlasRelatedTermHeader(
            term_guid=TERM_GUID,
            relation_guid="0c437486-2b95-451f-9e5a-2fe337b4a721",
            display_text="Account",
        ),
    ],
)

MALFORMED_GLOSSARIES = [
    [],
    "not json",
    {},
    {"guid": GUID},
    {"name": "no guid"},
    {"guid": 5, "name": "Bank"},
]
MALFORMED_IDS = ["list", "string", "empty", "no-name", "no-guid", "bad-guid"]


def test_list_glossaries(mocker):
    """Test every glossary Atlas lists maps onto AtlasGlossary, headers included."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [GLOSSARY_RESPONSE, SECOND_RESPONSE]

    result = AtlasGlossaryClient(api_client).list_glossaries()

    assert result == [EXPECTED_GLOSSARY, EXPECTED_SECOND]
    api_client.get.assert_called_once_with(
        "/api/atlas/v2/glossary",
        params={"limit": "-1"},
    )


@pytest.mark.parametrize("empty", [[], None], ids=["empty-list", "no-content"])
def test_list_glossaries_without_glossaries(mocker, empty):
    """Test an empty (or contentless) listing is an empty list."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = empty

    assert AtlasGlossaryClient(api_client).list_glossaries() == []


@pytest.mark.parametrize(
    "body",
    ["not json", {"guid": GUID}, [GLOSSARY_RESPONSE, "oops"], [{"name": "x"}]],
    ids=["string", "dict", "non-dict-item", "item-without-guid"],
)
def test_list_glossaries_rejects_malformed_responses(mocker, body):
    """Test an unexpected listing body becomes a ServicesError, not a TypeError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).list_glossaries()


def test_get_glossary(mocker):
    """Test a glossary response maps onto AtlasGlossary with user maps left verbatim."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = GLOSSARY_RESPONSE

    assert AtlasGlossaryClient(api_client).get_glossary(GUID) == EXPECTED_GLOSSARY

    api_client.get.assert_called_once_with(
        f"/api/atlas/v2/glossary/{GUID}",
        squelch={404: None},
    )


def test_get_glossary_not_found(mocker):
    """Test an unknown (or deleted) glossary guid returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    assert AtlasGlossaryClient(api_client).get_glossary(GUID) is None


def test_get_glossary_quotes_the_path_segment(mocker):
    """Test a guid with reserved characters cannot change the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    AtlasGlossaryClient(api_client).get_glossary("a/b c")

    assert api_client.get.call_args.args[0] == "/api/atlas/v2/glossary/a%2Fb%20c"


@pytest.mark.parametrize("body", MALFORMED_GLOSSARIES, ids=MALFORMED_IDS)
def test_get_glossary_rejects_malformed_responses(mocker, body):
    """Test an unexpected body becomes a ServicesError, not a TypeError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).get_glossary(GUID)


def test_find_glossaries_by_name_returns_every_match(mocker):
    """Test a name can match several glossaries, since only the qualified name is unique."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [
        GLOSSARY_RESPONSE,
        SECOND_RESPONSE,
        {"guid": "x", "qualifiedName": "other", "name": "Other"},
    ]

    result = AtlasGlossaryClient(api_client).find_glossaries(name="Bank")

    assert result == [EXPECTED_GLOSSARY, EXPECTED_SECOND]
    api_client.get.assert_called_once()


def test_find_glossaries_by_qualified_name(mocker):
    """Test the qualified name is matched exactly, not against the name."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [GLOSSARY_RESPONSE, SECOND_RESPONSE]

    result = AtlasGlossaryClient(api_client).find_glossaries(qualified_name="Bank")

    assert result == [EXPECTED_SECOND]


def test_find_glossaries_by_name_and_qualified_name(mocker):
    """Test both criteria must match when both are given."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [GLOSSARY_RESPONSE, SECOND_RESPONSE]

    client = AtlasGlossaryClient(api_client)

    assert client.find_glossaries(name="Bank", qualified_name="bank_qn") == [
        EXPECTED_GLOSSARY,
    ]
    assert client.find_glossaries(name="Other", qualified_name="bank_qn") == []


def test_find_glossaries_without_criteria_lists_everything(mocker):
    """Test no criteria matches every glossary."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [GLOSSARY_RESPONSE, SECOND_RESPONSE]

    result = AtlasGlossaryClient(api_client).find_glossaries()

    assert result == [EXPECTED_GLOSSARY, EXPECTED_SECOND]


def test_find_glossaries_without_a_match(mocker):
    """Test a name nothing carries returns an empty list."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [GLOSSARY_RESPONSE]

    assert AtlasGlossaryClient(api_client).find_glossaries(name="Nope") == []


def test_create_glossary(mocker):
    """Test the glossary is posted in camelCase and returned as Atlas stored it."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = GLOSSARY_RESPONSE

    result = AtlasGlossaryClient(api_client).create_glossary(
        AtlasGlossary(
            name="Bank",
            qualified_name="bank_qn",
            long_description="long",
            language="French",
            usage="uu",
        ),
    )

    assert result == EXPECTED_GLOSSARY
    api_client.post.assert_called_once_with(
        "/api/atlas/v2/glossary",
        data={
            "name": "Bank",
            "qualifiedName": "bank_qn",
            "longDescription": "long",
            "language": "French",
            "usage": "uu",
        },
    )


def test_create_glossary_sends_only_what_is_set(mocker):
    """Test unset fields are left out of the body so Atlas derives them."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = SECOND_RESPONSE

    AtlasGlossaryClient(api_client).create_glossary(AtlasGlossary(name="Bank"))

    assert api_client.post.call_args.kwargs["data"] == {"name": "Bank"}


def test_create_glossary_keeps_additional_attributes_verbatim(mocker):
    """Test user-defined attribute names keep their casing in the request."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = GLOSSARY_RESPONSE

    AtlasGlossaryClient(api_client).create_glossary(
        AtlasGlossary(name="Bank", additional_attributes={"someKey": "v"}),
    )

    assert api_client.post.call_args.kwargs["data"]["additionalAttributes"] == {
        "someKey": "v",
    }


@pytest.mark.parametrize("body", MALFORMED_GLOSSARIES, ids=MALFORMED_IDS)
def test_create_glossary_rejects_malformed_responses(mocker, body):
    """Test a create response without the glossary becomes a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).create_glossary(AtlasGlossary(name="Bank"))


def test_delete_glossary(mocker):
    """Test the delete addresses the guid and tolerates an already-missing glossary."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.delete.return_value = None

    AtlasGlossaryClient(api_client).delete_glossary(GUID)

    api_client.delete.assert_called_once_with(
        f"/api/atlas/v2/glossary/{GUID}",
        squelch={404: None},
    )


def test_delete_glossary_quotes_the_path_segment(mocker):
    """Test a guid with reserved characters cannot change the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    AtlasGlossaryClient(api_client).delete_glossary("a/b c")

    assert api_client.delete.call_args.args[0] == "/api/atlas/v2/glossary/a%2Fb%20c"


def test_partial_update_glossary(mocker):
    """Test only the given fields are PUT, in camelCase, and the glossary is returned."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = GLOSSARY_RESPONSE

    result = AtlasGlossaryClient(api_client).partial_update_glossary(
        GUID,
        {"short_description": "short", "name": "Bank", "language": ""},
    )

    assert result == EXPECTED_GLOSSARY
    api_client.put.assert_called_once_with(
        f"/api/atlas/v2/glossary/{GUID}/partial",
        data={"shortDescription": "short", "name": "Bank", "language": ""},
    )


def test_partial_update_glossary_without_changes_fails(mocker):
    """Test an empty update is refused here, since Atlas answers it with HTTP 400."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    with pytest.raises(ServicesError, match="at least one"):
        AtlasGlossaryClient(api_client).partial_update_glossary(GUID, {})

    api_client.put.assert_not_called()


def test_partial_update_glossary_quotes_the_path_segment(mocker):
    """Test a guid with reserved characters cannot change the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = GLOSSARY_RESPONSE

    AtlasGlossaryClient(api_client).partial_update_glossary("a/b c", {"usage": "u"})

    assert (
        api_client.put.call_args.args[0] == "/api/atlas/v2/glossary/a%2Fb%20c/partial"
    )


@pytest.mark.parametrize("body", MALFORMED_GLOSSARIES, ids=MALFORMED_IDS)
def test_partial_update_glossary_rejects_malformed_responses(mocker, body):
    """Test an update response without the glossary becomes a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).partial_update_glossary(GUID, {"usage": "u"})


TERMS_RESPONSE = [
    {
        "guid": TERM_GUID,
        "qualifiedName": "Account@bank_qn",
        "name": "Account",
        "anchor": {"glossaryGuid": GUID, "relationGuid": "r1"},
        "assignedEntities": [
            {
                "guid": "e1",
                "typeName": "hive_table",
                "entityStatus": "ACTIVE",
                "displayText": "sales",
                "relationshipType": "AtlasGlossarySemanticAssignment",
                "relationshipGuid": "rel1",
                "relationshipStatus": "ACTIVE",
                "relationshipAttributes": {"typeName": "x", "attributes": {}},
                "qualifiedName": "default.sales@c1",
            },
        ],
    },
    {"guid": "t2", "qualifiedName": "Loan@bank_qn", "name": "Loan"},
]

EXPECTED_TERMS = [
    AtlasGlossaryTerm(
        name="Account",
        guid=TERM_GUID,
        qualified_name="Account@bank_qn",
        assigned_entities=[
            AtlasRelatedObjectId(
                guid="e1",
                type_name="hive_table",
                entity_status="ACTIVE",
                display_text="sales",
                relationship_type="AtlasGlossarySemanticAssignment",
                relationship_guid="rel1",
                relationship_status="ACTIVE",
                qualified_name="default.sales@c1",
            ),
        ],
    ),
    AtlasGlossaryTerm(name="Loan", guid="t2", qualified_name="Loan@bank_qn"),
]


def test_list_terms(mocker):
    """Test the terms of a glossary map onto AtlasGlossaryTerm with their assignments."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = TERMS_RESPONSE

    result = AtlasGlossaryClient(api_client).list_terms(GUID)

    assert result == EXPECTED_TERMS
    api_client.get.assert_called_once_with(
        f"/api/atlas/v2/glossary/{GUID}/terms",
        params={"limit": "-1"},
    )


@pytest.mark.parametrize("empty", [[], None], ids=["empty-list", "no-content"])
def test_list_terms_without_terms(mocker, empty):
    """Test a glossary without terms gives an empty list."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = empty

    assert AtlasGlossaryClient(api_client).list_terms(GUID) == []


def test_list_terms_quotes_the_path_segment(mocker):
    """Test a guid with reserved characters cannot change the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = []

    AtlasGlossaryClient(api_client).list_terms("a/b c")

    assert api_client.get.call_args.args[0] == "/api/atlas/v2/glossary/a%2Fb%20c/terms"


@pytest.mark.parametrize(
    "body",
    ["not json", {"guid": TERM_GUID}, [TERMS_RESPONSE[0], "oops"], [{"name": "x"}]],
    ids=["string", "dict", "non-dict-item", "item-without-guid"],
)
def test_list_terms_rejects_malformed_responses(mocker, body):
    """Test an unexpected listing body becomes a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).list_terms(GUID)


def test_get_category(mocker):
    """Test a category response maps onto AtlasGlossaryCategory, hierarchy included."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = CATEGORY_RESPONSE

    assert AtlasGlossaryClient(api_client).get_category(CATEGORY_GUID) == (
        EXPECTED_CATEGORY
    )

    api_client.get.assert_called_once_with(
        f"/api/atlas/v2/glossary/category/{CATEGORY_GUID}",
        squelch={404: None},
    )


def test_get_category_not_found(mocker):
    """Test an unknown (or deleted) category guid returns None."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    assert AtlasGlossaryClient(api_client).get_category(CATEGORY_GUID) is None


def test_get_category_quotes_the_path_segment(mocker):
    """Test a guid cannot escape its path segment."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    AtlasGlossaryClient(api_client).get_category("a/b")

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/glossary/category/a%2Fb",
        squelch={404: None},
    )


@pytest.mark.parametrize("body", MALFORMED_GLOSSARIES, ids=MALFORMED_IDS)
def test_get_category_rejects_malformed_responses(mocker, body):
    """Test an unexpected category body becomes a ServicesError, not a TypeError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).get_category(CATEGORY_GUID)


def test_list_category_headers(mocker):
    """Test the category headers of a glossary map onto AtlasRelatedCategoryHeader."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = [
        {
            "categoryGuid": CATEGORY_GUID,
            "parentCategoryGuid": PARENT_GUID,
            "displayText": "Customer",
        },
        {"categoryGuid": PARENT_GUID, "displayText": "Party"},
    ]

    result = AtlasGlossaryClient(api_client).list_category_headers(GUID)

    assert result == [
        AtlasRelatedCategoryHeader(
            category_guid=CATEGORY_GUID,
            parent_category_guid=PARENT_GUID,
            display_text="Customer",
        ),
        AtlasRelatedCategoryHeader(category_guid=PARENT_GUID, display_text="Party"),
    ]
    api_client.get.assert_called_once_with(
        f"/api/atlas/v2/glossary/{GUID}/categories/headers",
        params={"limit": "-1"},
    )


@pytest.mark.parametrize("empty", [[], None], ids=["empty-list", "no-content"])
def test_list_category_headers_without_categories(mocker, empty):
    """Test an empty (or contentless) headers listing is an empty list."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = empty

    assert AtlasGlossaryClient(api_client).list_category_headers(GUID) == []


@pytest.mark.parametrize(
    "body",
    ["not json", {"categoryGuid": CATEGORY_GUID}, ["oops"], [{"displayText": "x"}]],
    ids=["string", "dict", "non-dict-item", "item-without-guid"],
)
def test_list_category_headers_rejects_malformed_responses(mocker, body):
    """Test an unexpected headers body becomes a ServicesError, not a TypeError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).list_category_headers(GUID)


def test_list_category_headers_quotes_the_path_segment(mocker):
    """Test a glossary guid cannot escape its path segment."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = []

    AtlasGlossaryClient(api_client).list_category_headers("a/b")

    api_client.get.assert_called_once_with(
        "/api/atlas/v2/glossary/a%2Fb/categories/headers",
        params={"limit": "-1"},
    )


def _category_api(mocker, headers, categories):
    """Build a mocked API: the headers listing, then one full response per guid."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    def get(path, **kwargs):
        if path.endswith("/categories/headers"):
            return headers
        return categories.get(path.rsplit("/", 1)[1])

    api_client.get.side_effect = get
    return api_client


def test_find_categories_by_name_fetches_every_match(mocker):
    """Test a name matches the current name in the headers, duplicates included."""
    other = dict(CATEGORY_RESPONSE, guid=OTHER_GUID)
    api_client = _category_api(
        mocker,
        headers=[
            {"categoryGuid": CATEGORY_GUID, "displayText": "Customer"},
            {"categoryGuid": PARENT_GUID, "displayText": "Party"},
            {"categoryGuid": OTHER_GUID, "displayText": "Customer"},
        ],
        categories={CATEGORY_GUID: CATEGORY_RESPONSE, OTHER_GUID: other},
    )

    result = AtlasGlossaryClient(api_client).find_categories(GUID, name="Customer")

    assert [category.guid for category in result] == [CATEGORY_GUID, OTHER_GUID]
    assert result[0] == EXPECTED_CATEGORY


def test_find_categories_without_a_name_lists_everything(mocker):
    """Test a missing name returns every category of the glossary."""
    other = dict(CATEGORY_RESPONSE, guid=OTHER_GUID, name="Party")
    api_client = _category_api(
        mocker,
        headers=[
            {"categoryGuid": CATEGORY_GUID, "displayText": "Customer"},
            {"categoryGuid": OTHER_GUID, "displayText": "Party"},
        ],
        categories={CATEGORY_GUID: CATEGORY_RESPONSE, OTHER_GUID: other},
    )

    result = AtlasGlossaryClient(api_client).find_categories(GUID)

    assert [category.name for category in result] == ["Customer", "Party"]


def test_find_categories_without_a_match(mocker):
    """Test an unknown name returns an empty list and fetches nothing."""
    api_client = _category_api(
        mocker,
        headers=[{"categoryGuid": CATEGORY_GUID, "displayText": "Customer"}],
        categories={CATEGORY_GUID: CATEGORY_RESPONSE},
    )

    assert AtlasGlossaryClient(api_client).find_categories(GUID, name="Nope") == []
    api_client.get.assert_called_once()


def test_find_categories_skips_a_category_deleted_after_the_listing(mocker):
    """Test a category that vanishes between the headers and the fetch is skipped."""
    api_client = _category_api(
        mocker,
        headers=[
            {"categoryGuid": CATEGORY_GUID, "displayText": "Customer"},
            {"categoryGuid": OTHER_GUID, "displayText": "Customer"},
        ],
        categories={CATEGORY_GUID: CATEGORY_RESPONSE},
    )

    result = AtlasGlossaryClient(api_client).find_categories(GUID, name="Customer")

    assert [category.guid for category in result] == [CATEGORY_GUID]


def test_create_category(mocker):
    """Test a category is created under its glossary (and parent) and returned as stored."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = CATEGORY_RESPONSE

    result = AtlasGlossaryClient(api_client).create_category(
        AtlasGlossaryCategory(
            name="Customer",
            short_description="short",
            additional_attributes={"someKey": "someValue"},
            anchor=AtlasGlossaryHeader(glossary_guid=GUID),
            parent_category=AtlasRelatedCategoryHeader(category_guid=PARENT_GUID),
        ),
    )

    assert result == EXPECTED_CATEGORY
    api_client.post.assert_called_once_with(
        "/api/atlas/v2/glossary/category",
        data={
            "name": "Customer",
            "shortDescription": "short",
            "additionalAttributes": {"someKey": "someValue"},
            "anchor": {"glossaryGuid": GUID},
            "parentCategory": {"categoryGuid": PARENT_GUID},
        },
    )


@pytest.mark.parametrize("body", MALFORMED_GLOSSARIES, ids=MALFORMED_IDS)
def test_create_category_rejects_malformed_responses(mocker, body):
    """Test an unexpected create response becomes a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = body

    with pytest.raises(ServicesError, match="unexpected"):
        AtlasGlossaryClient(api_client).create_category(
            AtlasGlossaryCategory(
                name="Customer",
                anchor=AtlasGlossaryHeader(glossary_guid=GUID),
            ),
        )


@pytest.mark.parametrize("name", ["Bank", "Retail banking", "Café", "a_b-c"])
def test_validate_glossary_name_accepts(name):
    """Test names Atlas accepts, spaces and accents included, pass."""
    validate_glossary_name("glossary", name)


@pytest.mark.parametrize("character", ["@", ".", "<", ">"])
def test_validate_glossary_name_rejects_reserved_characters(character):
    """Test a name Atlas would reject (ATLAS-400-00-083) fails before any request."""
    with pytest.raises(ServicesError, match="may not contain"):
        validate_glossary_name("glossary", f"a{character}b")


def test_validate_glossary_name_rejects_an_empty_name():
    """Test an empty name fails."""
    with pytest.raises(ServicesError, match="empty"):
        validate_glossary_name("glossary", "")
