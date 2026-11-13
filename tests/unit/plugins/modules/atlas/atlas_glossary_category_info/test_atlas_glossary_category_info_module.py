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

from ansible_collections.cloudera.services.tests.unit import (
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_glossary_category_info,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_glossary_category_info.AtlasGlossaryClient"
GLOSSARY_GUID = "4b4117f6-dd77-419d-9b8d-b120891ff2b4"
GUID = "5b292b6f-0983-4e43-8508-7115b9d9361d"

CATEGORY = AtlasGlossaryCategory(
    name="Customer",
    guid=GUID,
    qualified_name="Customer@bank_qn",
    additional_attributes={"someCamel": {"innerKey": 1}},
    anchor=AtlasGlossaryHeader(glossary_guid=GLOSSARY_GUID, display_text="Bank"),
    parent_category=AtlasRelatedCategoryHeader(
        category_guid="p1", display_text="Party"
    ),
    children_categories=[
        AtlasRelatedCategoryHeader(category_guid="c1", display_text="Retail"),
    ],
    terms=[AtlasRelatedTermHeader(term_guid="t1", display_text="Account")],
)


GLOSSARY_JSON = {"guid": GLOSSARY_GUID, "qualifiedName": "bank_qn", "name": "Bank"}
CATEGORY_JSON = {
    "guid": GUID,
    "qualifiedName": "Customer@bank_qn",
    "name": "Customer",
    "anchor": {"glossaryGuid": GLOSSARY_GUID, "displayText": "Bank"},
}
HEADERS_JSON = [{"categoryGuid": GUID, "displayText": "Customer"}]


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_glossary_category_info_module_by_guid(module_args, mocker):
    """Test a guid alone returns the category with its hierarchy and user data intact."""
    mock_get = mocker.patch(f"{CLIENT}.get_category", return_value=CATEGORY)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["categories"]) == 1
    category = result["categories"][0]
    assert category["name"] == "Customer"
    assert category["guid"] == GUID
    assert category["additional_attributes"] == {"someCamel": {"innerKey": 1}}
    assert category["anchor"] == {
        "glossary_guid": GLOSSARY_GUID,
        "display_text": "Bank",
    }
    assert category["parent_category"] == {
        "category_guid": "p1",
        "display_text": "Party",
    }
    assert category["children_categories"] == [
        {"category_guid": "c1", "display_text": "Retail"},
    ]
    assert category["terms"] == [{"term_guid": "t1", "display_text": "Account"}]
    mock_get.assert_called_once_with(GUID)


def test_atlas_glossary_category_info_module_by_guid_not_found(module_args, mocker):
    """Test an unknown guid returns no categories rather than failing."""
    mocker.patch(f"{CLIENT}.get_category", return_value=None)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert e.value["categories"] == []
    assert e.value["changed"] is False


def test_atlas_glossary_category_info_module_by_name_in_a_named_glossary(
    module_args,
    mocker,
):
    """Test a glossary name resolves to its guid, then the category name is searched there."""
    mock_glossaries = mocker.patch(
        f"{CLIENT}.find_glossaries",
        return_value=[AtlasGlossary(name="Bank", guid=GLOSSARY_GUID)],
    )
    mock_find = mocker.patch(f"{CLIENT}.find_categories", return_value=[CATEGORY])

    module_args(_args(glossary="Bank", name="Customer"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert [c["guid"] for c in e.value["categories"]] == [GUID]
    mock_glossaries.assert_called_once_with(name="Bank", qualified_name=None)
    mock_find.assert_called_once_with(GLOSSARY_GUID, name="Customer")


def test_atlas_glossary_category_info_module_in_a_glossary_by_qualified_name(
    module_args,
    mocker,
):
    """Test a glossary qualified name is matched on its own."""
    mock_glossaries = mocker.patch(
        f"{CLIENT}.find_glossaries",
        return_value=[AtlasGlossary(name="Bank", guid=GLOSSARY_GUID)],
    )
    mocker.patch(f"{CLIENT}.find_categories", return_value=[CATEGORY])

    module_args(_args(glossary_qualified_name="bank_qn", name="Customer"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert len(e.value["categories"]) == 1
    mock_glossaries.assert_called_once_with(name=None, qualified_name="bank_qn")


def test_atlas_glossary_category_info_module_in_a_glossary_by_guid(
    module_args,
    mocker,
):
    """Test a glossary guid is verified and used without any listing."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_glossary",
        return_value=AtlasGlossary(name="Bank", guid=GLOSSARY_GUID),
    )
    mock_glossaries = mocker.patch(f"{CLIENT}.find_glossaries")
    mock_find = mocker.patch(f"{CLIENT}.find_categories", return_value=[CATEGORY])

    module_args(_args(glossary_guid=GLOSSARY_GUID, name="Customer"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert len(e.value["categories"]) == 1
    mock_get.assert_called_once_with(GLOSSARY_GUID)
    mock_glossaries.assert_not_called()
    mock_find.assert_called_once_with(GLOSSARY_GUID, name="Customer")


def test_atlas_glossary_category_info_module_lists_a_whole_glossary(
    module_args,
    mocker,
):
    """Test a glossary without a category name returns all of its categories."""
    mocker.patch(
        f"{CLIENT}.find_glossaries",
        return_value=[AtlasGlossary(name="Bank", guid=GLOSSARY_GUID)],
    )
    mock_find = mocker.patch(f"{CLIENT}.find_categories", return_value=[CATEGORY])

    module_args(_args(glossary="Bank"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert len(e.value["categories"]) == 1
    mock_find.assert_called_once_with(GLOSSARY_GUID, name=None)


@pytest.mark.parametrize(
    "extra",
    [
        {"glossary": "Nope"},
        {"glossary_qualified_name": "nope_qn"},
    ],
    ids=["by-name", "by-qualified-name"],
)
def test_atlas_glossary_category_info_module_unknown_glossary_fails(
    module_args,
    mocker,
    extra,
):
    """Test a glossary that does not exist fails rather than returning no categories."""
    mocker.patch(f"{CLIENT}.find_glossaries", return_value=[])
    mock_find = mocker.patch(f"{CLIENT}.find_categories")

    module_args(_args(**extra))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category_info.main()

    assert "No glossary" in e.value["msg"]
    mock_find.assert_not_called()


def test_atlas_glossary_category_info_module_unknown_glossary_guid_fails(
    module_args,
    mocker,
):
    """Test a glossary guid that does not exist fails."""
    mocker.patch(f"{CLIENT}.get_glossary", return_value=None)
    mock_find = mocker.patch(f"{CLIENT}.find_categories")

    module_args(_args(glossary_guid=GLOSSARY_GUID))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category_info.main()

    assert GLOSSARY_GUID in e.value["msg"]
    mock_find.assert_not_called()


def test_atlas_glossary_category_info_module_ambiguous_glossary_name_fails(
    module_args,
    mocker,
):
    """Test a glossary name several glossaries carry fails and asks for the guid."""
    mocker.patch(
        f"{CLIENT}.find_glossaries",
        return_value=[
            AtlasGlossary(name="Bank", guid=GLOSSARY_GUID),
            AtlasGlossary(name="Bank", guid="other-guid"),
        ],
    )
    mock_find = mocker.patch(f"{CLIENT}.find_categories")

    module_args(_args(glossary="Bank"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category_info.main()

    assert "glossary_guid" in e.value["msg"]
    mock_find.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"guid": GUID, "name": "Customer"},
        {"guid": GUID, "glossary": "Bank"},
        {"guid": GUID, "glossary_qualified_name": "bank_qn"},
        {"guid": GUID, "glossary_guid": GLOSSARY_GUID},
        {"glossary": "Bank", "glossary_qualified_name": "bank_qn"},
        {"glossary": "Bank", "glossary_guid": GLOSSARY_GUID},
        {"glossary_qualified_name": "bank_qn", "glossary_guid": GLOSSARY_GUID},
        {"name": "Customer"},
        {},
    ],
    ids=[
        "guid-and-name",
        "guid-and-glossary",
        "guid-and-glossary-qualified-name",
        "guid-and-glossary-guid",
        "glossary-and-qualified-name",
        "glossary-and-glossary-guid",
        "qualified-name-and-glossary-guid",
        "name-without-glossary",
        "nothing",
    ],
)
def test_atlas_glossary_category_info_module_invalid_arguments_fail(
    module_args,
    mocker,
    extra,
):
    """Test conflicting or incomplete criteria fail before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_category")
    mock_glossary = mocker.patch(f"{CLIENT}.get_glossary")
    mock_glossaries = mocker.patch(f"{CLIENT}.find_glossaries")
    mock_find = mocker.patch(f"{CLIENT}.find_categories")

    module_args(_args(**extra))

    with pytest.raises(AnsibleFailJson):
        atlas_glossary_category_info.main()

    mock_get.assert_not_called()
    mock_glossary.assert_not_called()
    mock_glossaries.assert_not_called()
    mock_find.assert_not_called()


def test_atlas_glossary_category_info_module_check_mode(module_args, mocker):
    """Test the lookup also runs in check mode, since it changes nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_category", return_value=CATEGORY)

    module_args(_args(guid=GUID, _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert len(e.value["categories"]) == 1
    mock_get.assert_called_once_with(GUID)


def test_atlas_glossary_category_info_module_requests_by_guid(module_args, mocker):
    """Test the real request for a guid is a single GET of that category."""
    urls = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        urls.append((method, url))
        return http_result(mocker, 200, CATEGORY_JSON)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert len(e.value["categories"]) == 1
    assert urls == [("GET", f"{BASE_URL}/api/atlas/v2/glossary/category/{GUID}")]


def test_atlas_glossary_category_info_module_requests_by_glossary_and_name(
    module_args,
    mocker,
):
    """Test a name lookup lists the glossaries, then the category headers, then fetches the match."""
    urls = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        urls.append((method, url))
        if url.endswith("/glossary?limit=-1"):
            return http_result(mocker, 200, [GLOSSARY_JSON])
        if url.endswith("/categories/headers?limit=-1"):
            return http_result(
                mocker,
                200,
                HEADERS_JSON + [{"categoryGuid": "other-guid", "displayText": "Party"}],
            )
        return http_result(mocker, 200, CATEGORY_JSON)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(glossary="Bank", name="Customer"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert [c["guid"] for c in e.value["categories"]] == [GUID]
    assert urls == [
        ("GET", f"{BASE_URL}/api/atlas/v2/glossary?limit=-1"),
        (
            "GET",
            f"{BASE_URL}/api/atlas/v2/glossary/{GLOSSARY_GUID}/categories/headers?limit=-1",
        ),
        ("GET", f"{BASE_URL}/api/atlas/v2/glossary/category/{GUID}"),
    ]


def test_atlas_glossary_category_info_module_unknown_guid_returns_no_categories(
    module_args,
    mocker,
):
    """Test Atlas's 404 for a category that does not exist is not an error."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(
            mocker,
            404,
            {
                "errorCode": "ATLAS-404-00-005",
                "errorMessage": f"Given instance guid {GUID} is invalid/not found",
            },
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert e.value["categories"] == []


def test_atlas_glossary_category_info_module_unknown_category_name_returns_none(
    module_args,
    mocker,
):
    """Test a category name nothing carries returns no categories rather than failing."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if url.endswith("/glossary?limit=-1"):
            return http_result(mocker, 200, [GLOSSARY_JSON])
        return http_result(mocker, 200, HEADERS_JSON)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(glossary="Bank", name="Nope"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert e.value["categories"] == []


def test_atlas_glossary_category_info_module_forbidden_fails(module_args, mocker):
    """Test an authorization failure is reported, not mistaken for an empty result."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 403, {"errorMessage": "Forbidden Access"})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category_info.main()

    assert "Forbidden" in e.value["msg"]


@pytest.mark.parametrize(
    "body",
    ["unexpected", {"guid": GUID}, ["oops"]],
    ids=["string", "no-name", "list"],
)
def test_atlas_glossary_category_info_module_malformed_response_fails(
    module_args,
    mocker,
    body,
):
    """Test a 200 response that is not a category fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 200, body)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_category_info.main()

    assert "unexpected" in e.value["msg"]


def test_atlas_glossary_category_info_module_debug_output(module_args, mocker):
    """Test the SDK log is returned when debug is requested."""
    mocker.patch(f"{CLIENT}.get_category", return_value=None)

    module_args(_args(guid=GUID, debug=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_category_info.main()

    assert "sdk_out" in e.value
    assert "sdk_out_lines" in e.value
