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
    ATLAS_ERROR_MESSAGE,
    FETCH_URL,
    AnsibleExitJson,
    AnsibleFailJson,
    atlas_error_result,
    http_result,
)

from ansible_collections.cloudera.services.plugins.modules import (
    atlas_business_metadata_def,
)
from ansible_collections.cloudera.services.plugins.module_utils.atlas import (
    AtlasAttributeDef,
    AtlasConstraintDef,
    AtlasBusinessMetadataDef,
)

BASE_URL = "https://atlas.example"
CLIENT = "ansible_collections.cloudera.services.plugins.modules.atlas_business_metadata_def.AtlasTypeDefClient"

# Atlas fills attribute defaults on the server; the existing def carries them.
EXISTING = AtlasBusinessMetadataDef(
    name="test_business_metadata",
    description="An existing business metadata",
    type_version="1.0",
    category="BUSINESS_METADATA",
    guid="bm-guid-1",
    version=1,
    attribute_defs=[
        AtlasAttributeDef(
            name="owner",
            type_name="string",
            is_optional=True,
            cardinality="SINGLE",
            values_min_count=0,
            values_max_count=1,
            is_unique=False,
            is_indexable=True,
        ),
    ],
)


def _args(**extra):
    return {
        "endpoint": BASE_URL,
        "url_username": "admin",
        "url_password": "changeme",
        **extra,
    }


def test_atlas_business_metadata_def_module_create(module_args, mocker):
    """Test the module creates a business metadata typedef that does not exist."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_business_metadata_def_by_name",
        return_value=None,
    )
    mock_create = mocker.patch(
        f"{CLIENT}.create_business_metadata_def",
        return_value=AtlasBusinessMetadataDef(
            name="test_business_metadata",
            guid="new",
        ),
    )

    module_args(
        _args(
            name="test_business_metadata",
            attribute_defs=[{"name": "owner", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    result = e.value
    assert result["changed"] is True
    assert result["business_metadata_def"]["guid"] == "new"
    assert "diff" not in result

    mock_get.assert_called_once_with("test_business_metadata")
    created = mock_create.call_args[0][0]
    assert created.attribute_defs == [
        AtlasAttributeDef(name="owner", type_name="string"),
    ]


def test_atlas_business_metadata_def_module_present_no_changes(module_args, mocker):
    """Test unset attribute fields keep Atlas-filled defaults, so no change is reported."""
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_business_metadata_def")

    module_args(
        _args(
            name="test_business_metadata",
            description="An existing business metadata",
            attribute_defs=[{"name": "owner", "type_name": "string"}],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is False
    assert e.value["business_metadata_def"]["guid"] == "bm-guid-1"
    mock_update.assert_not_called()


def test_atlas_business_metadata_def_module_present_attribute_added(
    module_args,
    mocker,
):
    """Test adding an attribute updates and keeps the existing attribute intact."""
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(
        f"{CLIENT}.update_business_metadata_def",
        return_value=AtlasBusinessMetadataDef(name="test_business_metadata"),
    )

    module_args(
        _args(
            name="test_business_metadata",
            attribute_defs=[
                {"name": "owner", "type_name": "string"},
                {
                    "name": "ref",
                    "type_name": "string",
                    "constraints": [{"type": "ownedRef", "params": {"a": "b"}}],
                },
            ],
            _ansible_diff=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is True
    assert e.value["diff"]["before"] != e.value["diff"]["after"]
    sent = mock_update.call_args[0][0]
    assert sent.attribute_defs[0].cardinality == "SINGLE"
    assert sent.attribute_defs[1].constraints == [
        AtlasConstraintDef(type="ownedRef", params={"a": "b"}),
    ]
    assert sent.guid == "bm-guid-1"


def test_atlas_business_metadata_def_module_attribute_options_sent_verbatim(
    module_args,
    mocker,
):
    """Test Atlas's string-valued attribute options reach the client unchanged."""
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_business_metadata_def",
        return_value=AtlasBusinessMetadataDef(name="test_business_metadata"),
    )
    options = {"applicableEntityTypes": '["hive_table"]', "maxStrLength": "50"}

    module_args(
        _args(
            name="test_business_metadata",
            attribute_defs=[
                {"name": "owner", "type_name": "string", "options": options},
            ],
        ),
    )

    with pytest.raises(AnsibleExitJson):
        atlas_business_metadata_def.main()

    created = mock_create.call_args[0][0]
    assert created.attribute_defs[0].options == options


def test_atlas_business_metadata_def_module_attribute_options_changed(
    module_args,
    mocker,
):
    """Test changing only an attribute's scope options updates the business metadata."""
    existing = AtlasBusinessMetadataDef(
        name="test_business_metadata",
        guid="bm-guid-1",
        attribute_defs=[
            AtlasAttributeDef(
                name="owner",
                type_name="string",
                is_optional=True,
                options={"applicableEntityTypes": '["hive_table"]'},
            ),
        ],
    )
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=existing)
    mock_update = mocker.patch(
        f"{CLIENT}.update_business_metadata_def",
        return_value=AtlasBusinessMetadataDef(name="test_business_metadata"),
    )

    module_args(
        _args(
            name="test_business_metadata",
            attribute_defs=[
                {
                    "name": "owner",
                    "type_name": "string",
                    "options": {"applicableEntityTypes": '["hive_table","hive_db"]'},
                },
            ],
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is True
    sent = mock_update.call_args[0][0]
    assert sent.attribute_defs[0].options == {
        "applicableEntityTypes": '["hive_table","hive_db"]',
    }
    assert sent.attribute_defs[0].is_optional is True


def test_atlas_business_metadata_def_module_check_mode(module_args, mocker):
    """Test create in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_business_metadata_def")

    module_args(_args(name="test_business_metadata", _ansible_check_mode=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is True
    mock_create.assert_not_called()


def test_atlas_business_metadata_def_module_update_check_mode(module_args, mocker):
    """Test update in check mode reports a change without calling the API."""
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=EXISTING)
    mock_update = mocker.patch(f"{CLIENT}.update_business_metadata_def")

    module_args(
        _args(
            name="test_business_metadata",
            description="new",
            _ansible_check_mode=True,
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is True
    mock_update.assert_not_called()


def test_atlas_business_metadata_def_module_create_diff(module_args, mocker):
    """Test create in diff mode reports an empty before and the new definition after."""
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=None)
    mocker.patch(
        f"{CLIENT}.create_business_metadata_def",
        return_value=AtlasBusinessMetadataDef(name="test_business_metadata"),
    )

    module_args(_args(name="test_business_metadata", _ansible_diff=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["diff"]["before"] == {}
    assert e.value["diff"]["after"]["name"] == "test_business_metadata"


def test_atlas_business_metadata_def_module_absent(module_args, mocker):
    """Test absent deletes an existing business metadata and is a no-op when missing."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_business_metadata_def_by_name",
        return_value=EXISTING,
    )
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_business_metadata", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()
    assert e.value["changed"] is True
    mock_delete.assert_called_once_with("test_business_metadata", force=False)

    mock_get.return_value = None
    mock_delete.reset_mock()
    module_args(_args(name="test_business_metadata", state="absent"))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()
    assert e.value["changed"] is False
    mock_delete.assert_not_called()


def test_atlas_business_metadata_def_module_absent_check_mode(module_args, mocker):
    """Test absent in check mode reports a change without deleting."""
    mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name", return_value=EXISTING)
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(
        _args(name="test_business_metadata", state="absent", _ansible_check_mode=True),
    )
    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is True
    mock_delete.assert_not_called()


def test_atlas_business_metadata_def_module_present_requires_name(module_args):
    """Test present without a name fails."""
    module_args(_args())

    with pytest.raises(AnsibleFailJson):
        atlas_business_metadata_def.main()


def test_atlas_business_metadata_def_module_absent_requires_name(module_args, mocker):
    """Test absent without a name fails instead of silently doing nothing."""
    mock_get = mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name")
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(state="absent"))

    with pytest.raises(AnsibleFailJson):
        atlas_business_metadata_def.main()

    mock_get.assert_not_called()
    mock_delete.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"attribute_defs": [{"name": "owner"}]},
        {
            "attribute_defs": [
                {"name": "owner", "type_name": "string", "cardinality": "MANY"},
            ],
        },
        {
            "attribute_defs": [
                {"name": "owner", "type_name": "string", "index_type": "FULLTEXT"},
            ],
        },
        {"state": "unknown"},
        {"super_types": ["parent"]},
        {"entity_types": ["hive_table"]},
    ],
    ids=[
        "attribute-missing-type-name",
        "invalid-cardinality",
        "invalid-index-type",
        "invalid-state",
        "entity-only-parameter",
        "classification-only-parameter",
    ],
)
def test_atlas_business_metadata_def_module_invalid_arguments_fail(
    module_args,
    mocker,
    extra,
):
    """Test invalid arguments fail before any Atlas call is made."""
    mock_get = mocker.patch(f"{CLIENT}.get_business_metadata_def_by_name")

    module_args(_args(name="test_business_metadata", **extra))

    with pytest.raises(AnsibleFailJson):
        atlas_business_metadata_def.main()

    mock_get.assert_not_called()


BUSINESS_METADATA_EXISTING_JSON = {
    "category": "BUSINESS_METADATA",
    "guid": "bm-guid-1",
    "name": "test_business_metadata",
    "attributeDefs": [],
}


def test_atlas_business_metadata_def_module_create_atlas_error_fails(
    module_args,
    mocker,
):
    """Test an Atlas 400 on create fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 404)
        assert method == "POST"
        return atlas_error_result(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_business_metadata"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_business_metadata_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_business_metadata_def_module_update_atlas_error_fails(
    module_args,
    mocker,
):
    """Test an Atlas 400 on update fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 200, BUSINESS_METADATA_EXISTING_JSON)
        assert method == "PUT"
        return atlas_error_result(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_business_metadata", description="new"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_business_metadata_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_business_metadata_def_module_delete_atlas_error_fails(
    module_args,
    mocker,
):
    """Test an Atlas 400 on delete fails the module with Atlas's message."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 200, BUSINESS_METADATA_EXISTING_JSON)
        assert method == "DELETE"
        return atlas_error_result(mocker)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_business_metadata", state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_business_metadata_def.main()

    assert ATLAS_ERROR_MESSAGE in e.value["msg"]


def test_atlas_business_metadata_def_module_unexpected_response_fails(
    module_args,
    mocker,
):
    """Test a 200 response lacking the written business metadata def fails the module cleanly."""

    def fake_fetch_url(module, url, method="GET", **kwargs):
        if method == "GET":
            return http_result(mocker, 404)
        return http_result(mocker, 200, {"businessMetadataDefs": []})

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_business_metadata"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_business_metadata_def.main()

    assert "test_business_metadata" in e.value["msg"]


NON_INDEXABLE_MESSAGE = (
    "Deletion not allowed for non-indexable Business Metadata 'test_business_metadata' "
    "without force=true. Non-indexable attributes cannot be validated efficiently for "
    "references; use force=true to skip validation and delete (warning: orphaned "
    "references may remain)."
)


def test_atlas_business_metadata_def_module_absent_force(module_args, mocker):
    """Test force is handed to the client when deleting."""
    mocker.patch(
        f"{CLIENT}.get_business_metadata_def_by_name",
        return_value=EXISTING,
    )
    mock_delete = mocker.patch(f"{CLIENT}.delete_typedef_by_name")

    module_args(_args(name="test_business_metadata", state="absent", force=True))
    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is True
    mock_delete.assert_called_once_with("test_business_metadata", force=True)


def test_atlas_business_metadata_def_module_absent_non_indexable_fails_without_force(
    module_args,
    mocker,
):
    """Test Atlas's refusal to delete non-indexable business metadata surfaces, hinting at force."""
    requests = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        requests.append((method, url))
        if method == "GET":
            return http_result(mocker, 200, BUSINESS_METADATA_EXISTING_JSON)
        assert method == "DELETE"
        return http_result(
            mocker,
            400,
            {"errorCode": "ATLAS-400-00-114", "errorMessage": NON_INDEXABLE_MESSAGE},
        )

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_business_metadata", state="absent"))

    with pytest.raises(AnsibleFailJson) as e:
        atlas_business_metadata_def.main()

    assert "force=true" in e.value["msg"]
    delete_url = next(url for method, url in requests if method == "DELETE")
    assert "force" not in delete_url


def test_atlas_business_metadata_def_module_absent_force_sends_query_parameter(
    module_args,
    mocker,
):
    """Test force=true reaches Atlas as a query parameter and the delete succeeds."""
    requests = []

    def fake_fetch_url(module, url, method="GET", **kwargs):
        requests.append((method, url))
        if method == "GET":
            return http_result(mocker, 200, BUSINESS_METADATA_EXISTING_JSON)
        assert method == "DELETE"
        return http_result(mocker, 204)

    mocker.patch(FETCH_URL, side_effect=fake_fetch_url)

    module_args(_args(name="test_business_metadata", state="absent", force=True))

    with pytest.raises(AnsibleExitJson) as e:
        atlas_business_metadata_def.main()

    assert e.value["changed"] is True
    delete_url = next(url for method, url in requests if method == "DELETE")
    assert delete_url.endswith("/typedef/name/test_business_metadata?force=true")
