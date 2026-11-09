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
    AtlasGlossaryClient,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
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
