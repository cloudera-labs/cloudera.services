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

import json

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import atlas_glossary
from ansible_collections.cloudera.services.plugins.module_utils.atlas_glossary import (
    AtlasGlossary,
    AtlasGlossaryTerm,
    AtlasRelatedCategoryHeader,
    AtlasRelatedObjectId,
    AtlasRelatedTermHeader,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_glossary.AtlasGlossaryClient"
GUID = "4b4117f6-dd77-419d-9b8d-b120891ff2b4"

EXISTING = AtlasGlossary(
    name="Bank",
    guid=GUID,
    qualified_name="Bank",
    short_description="short",
    usage="uu",
)
OTHER = AtlasGlossary(name="Bank", guid="other-guid", qualified_name="Bank_emea")

WITH_CONTENT = AtlasGlossary(
    name="Bank",
    guid=GUID,
    qualified_name="Bank",
    terms=[
        AtlasRelatedTermHeader(term_guid="t1", display_text="Account"),
        AtlasRelatedTermHeader(term_guid="t2", display_text="Loan"),
    ],
    categories=[AtlasRelatedCategoryHeader(category_guid="c1", display_text="Retail")],
)


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def _run(module_args, **extra):
    module_args(_args(**extra))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_glossary.main()
    return e.value


@pytest.fixture
def client(mocker):
    """Patch every AtlasGlossaryClient method the module uses."""
    return {
        name: mocker.patch(f"{CLIENT}.{name}")
        for name in (
            "get_glossary",
            "find_glossaries",
            "create_glossary",
            "partial_update_glossary",
            "list_terms",
            "delete_glossary",
        )
    }


# ---------------------------------------------------------------- present: create


def test_atlas_glossary_module_creates_a_missing_glossary(module_args, client):
    """Test a glossary that does not exist is created with only the fields given."""
    created = AtlasGlossary(name="Bank", guid=GUID, qualified_name="Bank")
    client["find_glossaries"].return_value = []
    client["create_glossary"].return_value = created
    client["get_glossary"].return_value = created

    result = _run(module_args, name="Bank", short_description="short")

    assert result["changed"] is True
    assert result["glossary"]["guid"] == GUID
    client["find_glossaries"].assert_called_once_with(name="Bank")
    client["create_glossary"].assert_called_once_with(
        AtlasGlossary(name="Bank", short_description="short"),
    )
    client["partial_update_glossary"].assert_not_called()


def test_atlas_glossary_module_creates_with_an_explicit_qualified_name(
    module_args,
    client,
):
    """Test the qualified name is the identity when given, and is sent on create."""
    created = AtlasGlossary(name="Bank", guid=GUID, qualified_name="bank_emea")
    client["find_glossaries"].return_value = []
    client["create_glossary"].return_value = created
    client["get_glossary"].return_value = created

    result = _run(
        module_args,
        name="Bank",
        qualified_name="bank_emea",
        language="English",
        long_description="long",
        usage="u",
    )

    assert result["changed"] is True
    client["find_glossaries"].assert_called_once_with(qualified_name="bank_emea")
    client["create_glossary"].assert_called_once_with(
        AtlasGlossary(
            name="Bank",
            qualified_name="bank_emea",
            language="English",
            long_description="long",
            usage="u",
        ),
    )


def test_atlas_glossary_module_create_needs_a_name(module_args, client):
    """Test a missing glossary cannot be created from a qualified name alone."""
    client["find_glossaries"].return_value = []

    module_args(_args(qualified_name="bank_emea"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "'name' is required" in e.value["msg"]
    client["create_glossary"].assert_not_called()


def test_atlas_glossary_module_unknown_guid_fails(module_args, client):
    """Test a guid nothing carries fails instead of creating a glossary."""
    client["get_glossary"].return_value = None

    module_args(_args(guid=GUID, name="Bank"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert GUID in e.value["msg"]
    client["create_glossary"].assert_not_called()


def test_atlas_glossary_module_create_fails_when_atlas_does_not_return_it(
    module_args,
    client,
):
    """Test a created glossary that cannot be read back is reported."""
    client["find_glossaries"].return_value = []
    client["create_glossary"].return_value = AtlasGlossary(name="Bank", guid=GUID)
    client["get_glossary"].return_value = None

    module_args(_args(name="Bank"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "could not be read back" in e.value["msg"]


@pytest.mark.parametrize("character", ["@", ".", "<", ">"])
def test_atlas_glossary_module_invalid_name_fails_before_any_request(
    module_args,
    client,
    character,
):
    """Test a name Atlas would reject fails without a request."""
    module_args(_args(name=f"a{character}b"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "may not contain" in e.value["msg"]
    for mock in client.values():
        mock.assert_not_called()


# ---------------------------------------------------------------- present: update


def test_atlas_glossary_module_unchanged_glossary_is_left_alone(module_args, client):
    """Test a glossary that already holds the requested values is not written."""
    client["find_glossaries"].return_value = [EXISTING]

    result = _run(
        module_args,
        name="Bank",
        short_description="short",
        usage="uu",
    )

    assert result["changed"] is False
    assert result["glossary"]["guid"] == GUID
    client["partial_update_glossary"].assert_not_called()
    client["create_glossary"].assert_not_called()


def test_atlas_glossary_module_unmentioned_fields_are_not_managed(module_args, client):
    """Test only the fields the task names are compared and sent."""
    updated = AtlasGlossary(
        name="Bank",
        guid=GUID,
        qualified_name="Bank",
        short_description="short",
        usage="uu",
        language="French",
    )
    client["find_glossaries"].return_value = [EXISTING]
    client["partial_update_glossary"].return_value = updated
    client["get_glossary"].return_value = updated

    result = _run(module_args, name="Bank", language="French")

    assert result["changed"] is True
    client["partial_update_glossary"].assert_called_once_with(
        GUID,
        {"language": "French"},
    )
    assert result["glossary"]["short_description"] == "short"


def test_atlas_glossary_module_renames_by_guid(module_args, client):
    """Test a guid identity lets the name change."""
    renamed = AtlasGlossary(name="Retail", guid=GUID, qualified_name="Bank")
    client["get_glossary"].side_effect = [EXISTING, renamed]
    client["partial_update_glossary"].return_value = renamed

    result = _run(module_args, guid=GUID, name="Retail")

    assert result["changed"] is True
    assert result["glossary"]["name"] == "Retail"
    client["partial_update_glossary"].assert_called_once_with(GUID, {"name": "Retail"})
    client["find_glossaries"].assert_not_called()


def test_atlas_glossary_module_renames_by_qualified_name(module_args, client):
    """Test a qualified name identity lets the name change too."""
    renamed = AtlasGlossary(name="Retail", guid=GUID, qualified_name="Bank")
    client["find_glossaries"].return_value = [EXISTING]
    client["get_glossary"].return_value = renamed
    client["partial_update_glossary"].return_value = renamed

    result = _run(module_args, qualified_name="Bank", name="Retail")

    assert result["changed"] is True
    client["find_glossaries"].assert_called_once_with(qualified_name="Bank")
    client["partial_update_glossary"].assert_called_once_with(GUID, {"name": "Retail"})


def test_atlas_glossary_module_empty_string_clears_a_field(module_args, client):
    """Test "" clears a field that holds a value."""
    cleared = AtlasGlossary(name="Bank", guid=GUID, qualified_name="Bank")
    client["find_glossaries"].return_value = [EXISTING]
    client["partial_update_glossary"].return_value = cleared
    client["get_glossary"].return_value = cleared

    result = _run(module_args, name="Bank", short_description="")

    assert result["changed"] is True
    client["partial_update_glossary"].assert_called_once_with(
        GUID,
        {"short_description": ""},
    )


def test_atlas_glossary_module_empty_string_equals_an_unset_field(module_args, client):
    """Test "" for a field Atlas omits is no change."""
    client["find_glossaries"].return_value = [EXISTING]

    result = _run(module_args, name="Bank", language="")

    assert result["changed"] is False
    client["partial_update_glossary"].assert_not_called()


def test_atlas_glossary_module_update_fails_when_atlas_does_not_return_it(
    module_args,
    client,
):
    """Test an updated glossary that cannot be read back is reported."""
    client["find_glossaries"].return_value = [EXISTING]
    client["partial_update_glossary"].return_value = EXISTING
    client["get_glossary"].return_value = None

    module_args(_args(name="Bank", language="French"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "could not be read back" in e.value["msg"]


def test_atlas_glossary_module_ambiguous_name_fails(module_args, client):
    """Test a name several glossaries carry asks for a qualified name or guid."""
    client["find_glossaries"].return_value = [EXISTING, OTHER]

    module_args(_args(name="Bank", language="French"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "qualified_name" in e.value["msg"]
    client["partial_update_glossary"].assert_not_called()
    client["create_glossary"].assert_not_called()


# ---------------------------------------------------------------- check and diff mode


def test_atlas_glossary_module_check_mode_create(module_args, client):
    """Test check mode reports a create and writes nothing."""
    client["find_glossaries"].return_value = []

    result = _run(module_args, name="Bank", usage="u", _ansible_check_mode=True)

    assert result["changed"] is True
    assert result["glossary"]["name"] == "Bank"
    assert result["glossary"]["usage"] == "u"
    client["create_glossary"].assert_not_called()


def test_atlas_glossary_module_check_mode_update(module_args, client):
    """Test check mode reports the updated glossary and writes nothing."""
    client["find_glossaries"].return_value = [EXISTING]

    result = _run(module_args, name="Bank", language="French", _ansible_check_mode=True)

    assert result["changed"] is True
    assert result["glossary"]["language"] == "French"
    assert result["glossary"]["short_description"] == "short"
    client["partial_update_glossary"].assert_not_called()


def test_atlas_glossary_module_diff_covers_the_managed_fields_only(module_args, client):
    """Test the diff shows the before and after of the fields the task names."""
    updated = AtlasGlossary(name="Bank", guid=GUID, qualified_name="Bank", language="x")
    client["find_glossaries"].return_value = [EXISTING]
    client["partial_update_glossary"].return_value = updated
    client["get_glossary"].return_value = updated

    result = _run(
        module_args,
        name="Bank",
        language="x",
        usage="u2",
        _ansible_diff=True,
    )

    assert result["diff"] == {
        "before": {"glossary": {"language": None, "usage": "uu"}},
        "after": {"glossary": {"language": "x", "usage": "u2"}},
    }


def test_atlas_glossary_module_diff_of_a_create_has_an_empty_before(
    module_args,
    client,
):
    """Test a create diff has nothing before."""
    client["find_glossaries"].return_value = []

    result = _run(
        module_args,
        name="Bank",
        usage="u",
        _ansible_check_mode=True,
        _ansible_diff=True,
    )

    assert result["diff"]["before"] == {}
    assert result["diff"]["after"] == {"glossary": {"name": "Bank", "usage": "u"}}


# ---------------------------------------------------------------- absent


def test_atlas_glossary_module_absent_of_a_missing_glossary(module_args, client):
    """Test absent for a glossary that does not exist reports no change."""
    client["find_glossaries"].return_value = []

    result = _run(module_args, name="Bank", state="absent")

    assert result["changed"] is False
    assert result["glossary"] == {}
    client["delete_glossary"].assert_not_called()


def test_atlas_glossary_module_absent_deletes_an_empty_glossary(module_args, client):
    """Test an empty glossary is deleted and verified gone."""
    client["find_glossaries"].return_value = [EXISTING]
    client["get_glossary"].return_value = None

    result = _run(module_args, name="Bank", state="absent")

    assert result["changed"] is True
    assert result["glossary"] == {}
    client["delete_glossary"].assert_called_once_with(GUID)
    client["list_terms"].assert_not_called()


def test_atlas_glossary_module_absent_by_guid(module_args, client):
    """Test a guid identifies the glossary to delete."""
    client["get_glossary"].side_effect = [EXISTING, None]

    result = _run(module_args, guid=GUID, state="absent")

    assert result["changed"] is True
    client["delete_glossary"].assert_called_once_with(GUID)


def test_atlas_glossary_module_absent_refuses_a_glossary_with_content(
    module_args,
    client,
):
    """Test a glossary with terms or categories is not deleted unless cascade is set."""
    client["find_glossaries"].return_value = [WITH_CONTENT]

    module_args(_args(name="Bank", state="absent"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "2 terms and 1 category" in e.value["msg"]
    assert "cascade" in e.value["msg"]
    client["delete_glossary"].assert_not_called()


def test_atlas_glossary_module_absent_with_cascade_deletes_the_content_too(
    module_args,
    client,
):
    """Test cascade deletes a glossary with unassigned terms."""
    client["find_glossaries"].return_value = [WITH_CONTENT]
    client["list_terms"].return_value = [
        AtlasGlossaryTerm(name="Account", guid="t1"),
        AtlasGlossaryTerm(name="Loan", guid="t2", assigned_entities=[]),
    ]
    client["get_glossary"].return_value = None

    result = _run(module_args, name="Bank", state="absent", cascade=True)

    assert result["changed"] is True
    client["list_terms"].assert_called_once_with(GUID)
    client["delete_glossary"].assert_called_once_with(GUID)


def test_atlas_glossary_module_absent_refuses_when_a_term_is_assigned(
    module_args,
    client,
):
    """Test a term assigned to an entity blocks the delete before Atlas is asked."""
    client["find_glossaries"].return_value = [WITH_CONTENT]
    client["list_terms"].return_value = [
        AtlasGlossaryTerm(name="Account", guid="t1"),
        AtlasGlossaryTerm(
            name="Loan",
            guid="t2",
            assigned_entities=[
                AtlasRelatedObjectId(guid="e1", relationship_status="ACTIVE"),
            ],
        ),
    ]

    module_args(_args(name="Bank", state="absent", cascade=True))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "Loan" in e.value["msg"]
    assert "Account" not in e.value["msg"]
    assert "assigned" in e.value["msg"]
    client["delete_glossary"].assert_not_called()


def test_atlas_glossary_module_absent_ignores_a_deleted_assignment(module_args, client):
    """Test an assignment that is itself deleted does not block the delete."""
    client["find_glossaries"].return_value = [WITH_CONTENT]
    client["list_terms"].return_value = [
        AtlasGlossaryTerm(
            name="Loan",
            guid="t2",
            assigned_entities=[
                AtlasRelatedObjectId(guid="e1", relationship_status="DELETED"),
            ],
        ),
    ]
    client["get_glossary"].return_value = None

    result = _run(module_args, name="Bank", state="absent", cascade=True)

    assert result["changed"] is True


def test_atlas_glossary_module_absent_fails_if_the_glossary_remains(
    module_args,
    client,
):
    """Test a glossary that is still there after the delete is reported."""
    client["find_glossaries"].return_value = [EXISTING]
    client["get_glossary"].return_value = EXISTING

    module_args(_args(name="Bank", state="absent"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "still exists" in e.value["msg"]


def test_atlas_glossary_module_absent_check_mode(module_args, client):
    """Test check mode reports the delete and writes nothing."""
    client["find_glossaries"].return_value = [EXISTING]

    result = _run(module_args, name="Bank", state="absent", _ansible_check_mode=True)

    assert result["changed"] is True
    assert result["glossary"] == {}
    client["delete_glossary"].assert_not_called()


def test_atlas_glossary_module_absent_check_mode_predicts_the_refusal(
    module_args,
    client,
):
    """Test check mode fails the way a real run would for a glossary with content."""
    client["find_glossaries"].return_value = [WITH_CONTENT]

    module_args(_args(name="Bank", state="absent", _ansible_check_mode=True))
    with pytest.raises(AnsibleFailJson):
        atlas_glossary.main()


def test_atlas_glossary_module_absent_diff_lists_what_goes(module_args, client):
    """Test the delete diff names the glossary, its terms and its categories."""
    client["find_glossaries"].return_value = [WITH_CONTENT]
    client["list_terms"].return_value = []
    client["get_glossary"].return_value = None

    result = _run(
        module_args,
        name="Bank",
        state="absent",
        cascade=True,
        _ansible_diff=True,
    )

    assert result["diff"] == {
        "before": {
            "glossary": {
                "name": "Bank",
                "terms": ["Account", "Loan"],
                "categories": ["Retail"],
            },
        },
        "after": {},
    }


# ---------------------------------------------------------------- argument validation


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"guid": GUID, "qualified_name": "Bank"},
        {"name": "Bank", "state": "absent", "usage": "u"},
        {"name": "Bank", "state": "absent", "short_description": ""},
        {"name": "Bank", "state": "present", "cascade": True},
    ],
    ids=[
        "no-identity",
        "guid-and-qualified-name",
        "absent-with-usage",
        "absent-with-short-description",
        "present-with-cascade",
    ],
)
def test_atlas_glossary_module_invalid_arguments_fail_before_any_request(
    module_args,
    client,
    extra,
):
    """Test contradictory or incomplete arguments fail without an Atlas call."""
    module_args(_args(**extra))
    with pytest.raises(AnsibleFailJson):
        atlas_glossary.main()

    for mock in client.values():
        mock.assert_not_called()


# ---------------------------------------------------------------- real requests and errors


def _fetch(mocker, routes):
    """Stub FETCH_URL: `routes` maps (method, path) to (status, body); record the calls."""
    calls = []

    def fake_fetch_url(module, url, method="GET", data=None, **kwargs):
        path = url.replace(BASE_URL, "")
        calls.append((method, path, json.loads(data) if data else None))
        status, body = routes[(method, path)]
        return http_result(mocker, status, body)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)
    return calls


def test_atlas_glossary_module_create_requests(module_args, mocker):
    """Test the real calls: list to look up, POST the body, GET to verify."""
    created = {"guid": GUID, "qualifiedName": "Bank", "name": "Bank", "usage": "u"}
    calls = _fetch(
        mocker,
        {
            ("GET", "/api/atlas/v2/glossary?limit=-1"): (200, []),
            ("POST", "/api/atlas/v2/glossary"): (200, created),
            ("GET", f"/api/atlas/v2/glossary/{GUID}"): (200, created),
        },
    )

    result = _run(module_args, name="Bank", usage="u")

    assert result["changed"] is True
    assert calls == [
        ("GET", "/api/atlas/v2/glossary?limit=-1", None),
        ("POST", "/api/atlas/v2/glossary", {"name": "Bank", "usage": "u"}),
        ("GET", f"/api/atlas/v2/glossary/{GUID}", None),
    ]


def test_atlas_glossary_module_update_requests_use_the_partial_endpoint(
    module_args,
    mocker,
):
    """Test an update PUTs only the changed field to the partial endpoint."""
    before = {"guid": GUID, "qualifiedName": "Bank", "name": "Bank"}
    after = {**before, "language": "French"}
    calls = _fetch(
        mocker,
        {
            ("GET", "/api/atlas/v2/glossary?limit=-1"): (200, [before]),
            ("PUT", f"/api/atlas/v2/glossary/{GUID}/partial"): (200, after),
            ("GET", f"/api/atlas/v2/glossary/{GUID}"): (200, after),
        },
    )

    result = _run(module_args, name="Bank", language="French")

    assert result["glossary"]["language"] == "French"
    assert calls[1] == (
        "PUT",
        f"/api/atlas/v2/glossary/{GUID}/partial",
        {"language": "French"},
    )


def test_atlas_glossary_module_duplicate_qualified_name_fails(module_args, mocker):
    """Test Atlas's 409 for a taken qualified name is reported with its message."""
    message = "Glossary with name Bank already exists"
    _fetch(
        mocker,
        {
            ("GET", "/api/atlas/v2/glossary?limit=-1"): (200, []),
            ("POST", "/api/atlas/v2/glossary"): (
                409,
                {"errorCode": "ATLAS-409-00-007", "errorMessage": message},
            ),
        },
    )

    module_args(_args(name="Bank"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert message in e.value["msg"]


def test_atlas_glossary_module_delete_blocked_by_atlas_fails(module_args, mocker):
    """Test Atlas's 400 for a term that is still assigned is reported."""
    message = "Term (guid=t1) cannot be deleted as it has been assigned to 1 entities."
    _fetch(
        mocker,
        {
            ("GET", "/api/atlas/v2/glossary?limit=-1"): (
                200,
                [{"guid": GUID, "qualifiedName": "Bank", "name": "Bank"}],
            ),
            ("DELETE", f"/api/atlas/v2/glossary/{GUID}"): (
                400,
                {"errorCode": "ATLAS-400-00-084", "errorMessage": message},
            ),
        },
    )

    module_args(_args(name="Bank", state="absent"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert message in e.value["msg"]


def test_atlas_glossary_module_forbidden_fails(module_args, mocker):
    """Test an authorization failure is reported."""
    _fetch(
        mocker,
        {
            ("GET", "/api/atlas/v2/glossary?limit=-1"): (
                403,
                {"errorMessage": "Forbidden"},
            ),
        },
    )

    module_args(_args(name="Bank"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "Forbidden" in e.value["msg"]


def test_atlas_glossary_module_malformed_listing_fails(module_args, mocker):
    """Test a listing that is not a list of glossaries fails the module cleanly."""
    _fetch(mocker, {("GET", "/api/atlas/v2/glossary?limit=-1"): (200, "unexpected")})

    module_args(_args(name="Bank"))
    with pytest.raises(AnsibleFailJson) as e:
        atlas_glossary.main()

    assert "unexpected" in e.value["msg"]
