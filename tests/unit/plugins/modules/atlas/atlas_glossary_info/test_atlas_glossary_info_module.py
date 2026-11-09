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

from ansible_collections.cloudera.services.plugins.modules import atlas_glossary_info
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_glossary_info.AtlasGlossaryClient"
GUID = "4b4117f6-dd77-419d-9b8d-b120891ff2b4"

GLOSSARY = AtlasGlossary(
    name="Bank",
    guid=GUID,
    qualified_name="bank_qn",
    additional_attributes={"someCamel": {"innerKey": 1}},
    terms=[AtlasRelatedTermHeader(term_guid="t1", display_text="Account")],
    categories=[AtlasRelatedCategoryHeader(category_guid="c1", display_text="Loans")],
)
OTHER = AtlasGlossary(name="Bank", guid="other-guid", qualified_name="Bank")

GLOSSARY_JSON = {"guid": GUID, "qualifiedName": "bank_qn", "name": "Bank"}


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_glossary_info_module_by_guid(module_args, mocker):
    """Test a guid lookup returns the glossary with its headers and user data intact."""
    mock_get = mocker.patch(f"{CLIENT}.get_glossary", return_value=GLOSSARY)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["glossaries"]) == 1
    glossary = result["glossaries"][0]
    assert glossary["name"] == "Bank"
    assert glossary["guid"] == GUID
    assert glossary["qualified_name"] == "bank_qn"
    assert glossary["additional_attributes"] == {"someCamel": {"innerKey": 1}}
    assert glossary["terms"] == [{"term_guid": "t1", "display_text": "Account"}]
    assert glossary["categories"] == [
        {"category_guid": "c1", "display_text": "Loans"},
    ]
    mock_get.assert_called_once_with(GUID)


def test_atlas_glossary_info_module_by_guid_not_found(module_args, mocker):
    """Test an unknown guid returns no glossaries rather than failing."""
    mocker.patch(f"{CLIENT}.get_glossary", return_value=None)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert e.value["glossaries"] == []
    assert e.value["changed"] is False


def test_atlas_glossary_info_module_by_name_returns_every_match(module_args, mocker):
    """Test a name that several glossaries carry returns all of them."""
    mock_find = mocker.patch(
        f"{CLIENT}.find_glossaries",
        return_value=[GLOSSARY, OTHER],
    )

    module_args(_args(name="Bank"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert [g["guid"] for g in e.value["glossaries"]] == [GUID, "other-guid"]
    mock_find.assert_called_once_with(name="Bank", qualified_name=None)


def test_atlas_glossary_info_module_by_qualified_name(module_args, mocker):
    """Test a qualified name is matched on its own."""
    mock_find = mocker.patch(f"{CLIENT}.find_glossaries", return_value=[GLOSSARY])

    module_args(_args(qualified_name="bank_qn"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert len(e.value["glossaries"]) == 1
    mock_find.assert_called_once_with(name=None, qualified_name="bank_qn")


def test_atlas_glossary_info_module_by_name_and_qualified_name(module_args, mocker):
    """Test both criteria are handed to the lookup when both are given."""
    mock_find = mocker.patch(f"{CLIENT}.find_glossaries", return_value=[])

    module_args(_args(name="Bank", qualified_name="bank_qn"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert e.value["glossaries"] == []
    mock_find.assert_called_once_with(name="Bank", qualified_name="bank_qn")


def test_atlas_glossary_info_module_lists_every_glossary_without_criteria(
    module_args,
    mocker,
):
    """Test no criteria returns all glossaries."""
    mock_find = mocker.patch(
        f"{CLIENT}.find_glossaries",
        return_value=[GLOSSARY, OTHER],
    )

    module_args(_args())

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert len(e.value["glossaries"]) == 2
    mock_find.assert_called_once_with(name=None, qualified_name=None)


def test_atlas_glossary_info_module_name_without_a_match(module_args, mocker):
    """Test a name nothing carries returns no glossaries rather than failing."""
    mocker.patch(f"{CLIENT}.find_glossaries", return_value=[])

    module_args(_args(name="Nope"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert e.value["glossaries"] == []


def test_atlas_glossary_info_module_check_mode(module_args, mocker):
    """Test the lookup also runs in check mode, since it changes nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_glossary", return_value=GLOSSARY)

    module_args(_args(guid=GUID, _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert len(e.value["glossaries"]) == 1
    mock_get.assert_called_once_with(GUID)


@pytest.mark.parametrize(
    "extra",
    [
        {"guid": GUID, "name": "Bank"},
        {"guid": GUID, "qualified_name": "bank_qn"},
    ],
    ids=["guid-and-name", "guid-and-qualified-name"],
)
def test_atlas_glossary_info_module_ambiguous_identity_fails(
    module_args,
    mocker,
    extra,
):
    """Test a guid together with another criterion fails before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_glossary")
    mock_find = mocker.patch(f"{CLIENT}.find_glossaries")

    module_args(_args(**extra))

    with pytest.raises(AnsibleFailJson):
        atlas_glossary_info.main()

    mock_get.assert_not_called()
    mock_find.assert_not_called()


def test_atlas_glossary_info_module_requests_by_guid(module_args, mocker):
    """Test the real request for a guid is a GET of that glossary."""
    urls = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        urls.append((method, url))
        return http_result(mocker, 200, GLOSSARY_JSON)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert len(e.value["glossaries"]) == 1
    assert urls == [("GET", f"{BASE_URL}/api/atlas/v2/glossary/{GUID}")]


def test_atlas_glossary_info_module_requests_the_whole_list(module_args, mocker):
    """Test a name lookup lists all glossaries (limit=-1) and filters them itself."""
    urls = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        urls.append((method, url))
        return http_result(
            mocker,
            200,
            [GLOSSARY_JSON, {"guid": "x", "qualifiedName": "Other", "name": "Other"}],
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="Bank"))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert [g["guid"] for g in e.value["glossaries"]] == [GUID]
    assert urls == [("GET", f"{BASE_URL}/api/atlas/v2/glossary?limit=-1")]


def test_atlas_glossary_info_module_unknown_guid_returns_no_glossaries(
    module_args,
    mocker,
):
    """Test Atlas's 404 for a glossary that does not exist is not an error."""

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
        atlas_glossary_info.main()

    assert e.value["glossaries"] == []


def test_atlas_glossary_info_module_forbidden_fails(module_args, mocker):
    """Test an authorization failure is reported, not mistaken for an empty result."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 403, {"errorMessage": "Forbidden Access"})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="Bank"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_info.main()

    assert "Forbidden" in e.value["msg"]


@pytest.mark.parametrize(
    "body",
    ["unexpected", {"guid": GUID}, [{"name": "no guid"}]],
    ids=["string", "no-name", "list-item-without-guid"],
)
def test_atlas_glossary_info_module_malformed_response_fails(module_args, mocker, body):
    """Test a 200 response that is not a glossary fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        return http_result(mocker, 200, body)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(guid=GUID) if isinstance(body, (str, dict)) else _args())

    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary_info.main()

    assert "unexpected" in e.value["msg"]


def test_atlas_glossary_info_module_debug_output(module_args, mocker):
    """Test the SDK log is returned when debug is requested."""
    mocker.patch(f"{CLIENT}.get_glossary", return_value=None)

    module_args(_args(guid=GUID, debug=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary_info.main()

    assert "sdk_out" in e.value
    assert "sdk_out_lines" in e.value
