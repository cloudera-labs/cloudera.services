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
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import ssb_table
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbTable,
)

BASE_URL = "https://api.cloudera.internal"


def test_ssb_table_module_create_minimal(module_args, mocker):
    """Test SsbTableModule creating a table with minimal parameters."""
    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[],
    )
    mock_create_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.create_table",
        return_value=SsbTable(
            id=1,
            table_name="test_table",
            type="TABLE",
            metadata={
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "STRING"},
                ],
            },
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "test_table",
            "type": "TABLE",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "STRING"},
                ],
            },
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert result["table"]["id"] == 1
    assert result["table"]["table_name"] == "test_table"

    mock_list_tables.assert_called_once_with("12345")
    mock_create_table.assert_called_once()


def test_ssb_table_module_create_with_transform(module_args, mocker):
    """Test SsbTableModule creating a table with transformation code."""
    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[],
    )
    mock_create_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.create_table",
        return_value=SsbTable(
            id=1,
            table_name="transformed_table",
            type="TABLE",
            metadata={"columns": []},
            transform_code="SELECT * FROM source",
            transform_code_b64_encoded=False,
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "transformed_table",
            "type": "TABLE",
            "metadata": {"columns": []},
            "transform_code": "SELECT * FROM source",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert result["table"]["table_name"] == "transformed_table"
    assert result["table"]["transform_code"] == "SELECT * FROM source"

    mock_list_tables.assert_called_once_with("12345")
    mock_create_table.assert_called_once()


def test_ssb_table_module_present_idempotent(module_args, mocker):
    """Test SsbTableModule with existing table (idempotent)."""
    existing_table = SsbTable(
        id=1,
        table_name="existing_table",
        type="TABLE",
        metadata={"columns": []},
        transform_code_b64_encoded=False,
    )

    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[existing_table],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "existing_table",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False
    assert result["table"]["id"] == 1
    assert result["table"]["table_name"] == "existing_table"

    mock_list_tables.assert_called_once_with("12345")


def test_ssb_table_module_by_id(module_args, mocker):
    """Test SsbTableModule retrieving table by ID."""
    existing_table = SsbTable(
        id=1,
        table_name="existing_table",
        type="TABLE",
        metadata={},
        transform_code_b64_encoded=False,
    )

    mock_describe_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.describe_table",
        return_value=existing_table,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "id": 1,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False
    assert result["table"]["id"] == 1
    assert result["table"]["table_name"] == "existing_table"

    mock_describe_table.assert_called_once_with("12345", 1)


def test_ssb_table_module_delete_by_name(module_args, mocker):
    """Test SsbTableModule deleting a table by name."""
    existing_table = SsbTable(
        id=1,
        table_name="table_to_delete",
        type="TABLE",
        metadata={},
    )

    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[existing_table],
    )
    mock_delete_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.delete_table",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "table_to_delete",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True

    mock_list_tables.assert_called_once_with("12345")
    mock_delete_table.assert_called_once_with("12345", 1)


def test_ssb_table_module_delete_by_id(module_args, mocker):
    """Test SsbTableModule deleting a table by ID."""
    existing_table = SsbTable(
        id=1,
        table_name="table_to_delete",
        type="TABLE",
        metadata={},
    )

    mock_describe_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.describe_table",
        return_value=existing_table,
    )
    mock_delete_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.delete_table",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "id": 1,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True

    mock_describe_table.assert_called_once_with("12345", 1)
    mock_delete_table.assert_called_once_with("12345", 1)


def test_ssb_table_module_delete_nonexistent(module_args, mocker):
    """Test SsbTableModule deleting a non-existent table."""
    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "nonexistent_table",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False

    mock_list_tables.assert_called_once_with("12345")


def test_ssb_table_module_check_mode_create(module_args, mocker):
    """Test SsbTableModule in check mode for creation."""
    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[],
    )
    mock_create_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.create_table",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "new_table",
            "type": "TABLE",
            "metadata": {"columns": []},
            "state": "present",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert result["table"] == {}

    mock_list_tables.assert_called_once_with("12345")
    mock_create_table.assert_not_called()


def test_ssb_table_module_check_mode_delete(module_args, mocker):
    """Test SsbTableModule in check mode for deletion."""
    existing_table = SsbTable(
        id=1,
        table_name="table_to_delete",
        type="TABLE",
        metadata={},
    )

    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[existing_table],
    )
    mock_delete_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.delete_table",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "table_to_delete",
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True

    mock_list_tables.assert_called_once_with("12345")
    mock_delete_table.assert_not_called()


def test_ssb_table_module_create_without_table_name(module_args, mocker):
    """Test SsbTableModule failing when creating without table_name."""
    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "type": "TABLE",
            "metadata": {"columns": []},
            "state": "present",
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        ssb_table.main()

    result = e.value
    assert "table_name" in result["msg"].lower()


def test_ssb_table_module_create_without_type(module_args, mocker):
    """Test SsbTableModule failing when creating without type."""
    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "test_table",
            "metadata": {"columns": []},
            "state": "present",
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        ssb_table.main()

    result = e.value
    assert "type" in result["msg"].lower()


def test_ssb_table_module_create_without_metadata(module_args, mocker):
    """Test SsbTableModule failing when creating without metadata."""
    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[],
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "test_table",
            "type": "TABLE",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        ssb_table.main()

    result = e.value
    assert "metadata" in result["msg"].lower()


def test_ssb_table_module_update_with_update_enabled(module_args, mocker):
    """Test SsbTableModule updating a table with update_enabled=True."""
    existing_table = SsbTable(
        id=1,
        table_name="test_table",
        type="TABLE",
        metadata={
            "columns": [
                {"name": "id", "type": "INT"},
            ],
        },
    )

    updated_table = SsbTable(
        id=2,
        table_name="test_table",
        type="TABLE",
        metadata={
            "columns": [
                {"name": "id", "type": "INT"},
                {"name": "new_column", "type": "STRING"},
            ],
        },
    )

    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[existing_table],
    )
    mock_delete_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.delete_table",
    )
    mock_create_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.create_table",
        return_value=updated_table,
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "test_table",
            "type": "TABLE",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "new_column", "type": "STRING"},
                ],
            },
            "update_enabled": True,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert result["table"]["table_name"] == "test_table"

    mock_list_tables.assert_called_once_with("12345")
    mock_delete_table.assert_called_once_with("12345", 1)
    mock_create_table.assert_called_once()


def test_ssb_table_module_update_with_update_disabled(module_args, mocker):
    """Test SsbTableModule with update_enabled=False (should warn and not update)."""
    existing_table = SsbTable(
        id=1,
        table_name="test_table",
        type="TABLE",
        metadata={
            "columns": [
                {"name": "id", "type": "INT"},
            ],
        },
        transform_code_b64_encoded=False,
    )

    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[existing_table],
    )
    mock_delete_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.delete_table",
    )
    mock_create_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.create_table",
    )
    mock_warn = mocker.patch(
        "ansible.module_utils.basic.AnsibleModule.warn",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "test_table",
            "type": "TABLE",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "new_column", "type": "STRING"},
                ],
            },
            "update_enabled": False,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False
    assert result["table"]["id"] == 1

    mock_list_tables.assert_called_once_with("12345")
    mock_delete_table.assert_not_called()
    mock_create_table.assert_not_called()
    mock_warn.assert_called_once()


def test_ssb_table_module_update_check_mode_with_update_enabled(module_args, mocker):
    """Test SsbTableModule in check mode with update_enabled=True."""
    existing_table = SsbTable(
        id=1,
        table_name="test_table",
        type="TABLE",
        metadata={
            "columns": [
                {"name": "id", "type": "INT"},
            ],
        },
        transform_code_b64_encoded=False,
    )

    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[existing_table],
    )
    mock_delete_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.delete_table",
    )
    mock_create_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.create_table",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "test_table",
            "type": "TABLE",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "new_column", "type": "STRING"},
                ],
            },
            "update_enabled": True,
            "state": "present",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True

    mock_list_tables.assert_called_once_with("12345")
    mock_delete_table.assert_not_called()
    mock_create_table.assert_not_called()


def test_ssb_table_module_no_update_needed(module_args, mocker):
    """Test SsbTableModule with identical table (no update needed)."""
    existing_table = SsbTable(
        id=1,
        table_name="test_table",
        type="TABLE",
        metadata={
            "columns": [
                {"name": "id", "type": "INT"},
                {"name": "name", "type": "STRING"},
            ],
        },
        transform_code_b64_encoded=False,
    )

    mock_list_tables = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.list_tables",
        return_value=[existing_table],
    )
    mock_delete_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.delete_table",
    )
    mock_create_table = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_table.SsbTableClient.create_table",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "12345",
            "table_name": "test_table",
            "type": "TABLE",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "STRING"},
                ],
            },
            "update_enabled": True,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False
    assert result["table"]["id"] == 1

    mock_list_tables.assert_called_once_with("12345")
    mock_delete_table.assert_not_called()
    mock_create_table.assert_not_called()
