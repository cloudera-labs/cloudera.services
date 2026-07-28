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
import logging
import pytest

from typing import Generator, Callable, List

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
)

from ansible_collections.cloudera.services.plugins.modules import ssb_table

log = logging.getLogger("cloudera.services.conftest")

REQUIRED_ENV_VARS = [
    "SSB_SSE_API_URL",
    "SSB_SSE_API_USERNAME",
    "SSB_SSE_API_PASSWORD",
    "SMM_KAFKA_BROKERS",
    "SMM_KAFKA_USERNAME",
    "SMM_KAFKA_PASSWORD",
    "SMM_KAFKA_SSL_CAFILE",
]


@pytest.fixture
def ssb_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args for SSB tests."""

    def _ssb_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["SSB_SSE_API_URL"],
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": env_context["SSB_SSE_API_PASSWORD"],
            "force_basic_auth": True,
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _ssb_module_args


@pytest.fixture
def purge_table_by_name(
    ssb_table_client,
) -> Generator[Callable[[str, str], None], None, None]:
    """Fixture to purge a test job after the test."""
    tables: List[List[str]] = []

    def _add_table(project_id: str, table_name: str) -> None:
        tables.append([project_id, table_name])

    yield _add_table

    # Clean up after the test
    for table in tables:
        try:
            t = ssb_table_client.describe_table(
                table[0],
                table[1],
            )  # Get the table to retrieve its ID for deletion
            ssb_table_client.delete_table(table[0], t.id)
        except Exception as e:
            log.info(f"Failed to delete table {table[1]} during cleanup: {str(e)}")


def test_ssb_table_module_create_minimal_int(
    request,
    ssb_module_args,
    existing_project,
    existing_data_source_kafka,
    existing_data_source_kafka_schema,
    purge_table_by_name,
):
    """Test SsbTableModule creating a table with minimal parameters."""
    table_name = request.node.name.lower()
    purge_table_by_name(existing_project.id, table_name)

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": table_name,
            "type": "kafka",
            "metadata": {
                "kafka_source_name": existing_data_source_kafka.name,
                "format": "JSON",
                "schema": json.dumps(existing_data_source_kafka_schema),
                "topic": table_name,
            },
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert result["table"]["table_name"] == table_name
    assert result["table"]["type"] == "ssb"  # TODO Why is this not 'kafka'?
    assert isinstance(result["table"]["id"], int)


def test_ssb_table_module_create_with_transform_int(
    ssb_module_args,
    existing_project,
    purge_table_by_name,
):
    """Test SsbTableModule creating a table with transformation code."""
    table_name = "test_table_transform"
    purge_table_by_name(existing_project.id, table_name)

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": table_name,
            "type": "ssb",
            "metadata": {"columns": []},
            "transform_code": "SELECT 1 AS id",
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert result["table"]["table_name"] == table_name
    # No longer returns transform_code in the result, so we can't assert on it
    # assert "transform_code" in result["table"]


def test_ssb_table_module_present_idempotent_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
):
    """Test SsbTableModule with existing table (idempotent)."""
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": existing_table_kafka.table_name,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False
    assert result["table"]["table_name"] == existing_table_kafka.table_name
    if isinstance(existing_table_kafka.id, int):
        assert result["table"]["id"] == existing_table_kafka.id


def test_ssb_table_module_by_id_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
):
    """Test SsbTableModule retrieving table by ID."""
    if not isinstance(existing_table_kafka.id, int):
        pytest.skip("existing_table must have an integer id")

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "id": existing_table_kafka.id,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False
    assert result["table"]["id"] == existing_table_kafka.id
    assert result["table"]["table_name"] == existing_table_kafka.table_name


def test_ssb_table_module_delete_by_name_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
):
    """Test SsbTableModule deleting a table by name."""
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": existing_table_kafka.table_name,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True


def test_ssb_table_module_delete_by_id_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
):
    """Test SsbTableModule deleting a table by ID."""
    if not isinstance(existing_table_kafka.id, int):
        pytest.skip("existing_table must have an integer id")

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "id": existing_table_kafka.id,
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True


def test_ssb_table_module_delete_nonexistent_int(
    ssb_module_args,
    existing_project,
):
    """Test SsbTableModule deleting a non-existent table."""
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": "nonexistent_table_test",
            "state": "absent",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False


def test_ssb_table_module_check_mode_create_int(
    ssb_module_args,
    existing_project,
    ssb_table_client,
):
    """Test SsbTableModule in check mode for creation."""
    table_name = "test_table_check_mode"

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": table_name,
            "type": "ssb",
            "metadata": {"columns": [{"name": "id", "type": "INT"}]},
            "state": "present",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True

    # Verify table was NOT actually created
    tables = ssb_table_client.list_tables(existing_project.id)
    assert not any(t.table_name == table_name for t in tables)


def test_ssb_table_module_check_mode_delete_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
    ssb_table_client,
):
    """Test SsbTableModule in check mode for deletion."""
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": existing_table_kafka.table_name,
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True

    # Verify table still exists
    tables = ssb_table_client.list_tables(existing_project.id)
    assert any(t.table_name == existing_table_kafka.table_name for t in tables)


def test_ssb_table_module_diff_mode_create_int(
    ssb_module_args,
    existing_project,
    purge_table_by_name,
):
    """Test SsbTableModule with diff mode for creation."""
    table_name = "test_table_diff"
    purge_table_by_name(existing_project.id, table_name)

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": table_name,
            "type": "ssb",
            "metadata": {"columns": [{"name": "id", "type": "INT"}]},
            "state": "present",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"] == ""
    assert "after" in result["diff"]
    assert result["diff"]["after"]["table_name"] == table_name


def test_ssb_table_module_diff_mode_delete_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
):
    """Test SsbTableModule with diff mode for deletion."""
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": existing_table_kafka.table_name,
            "state": "absent",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert "before" in result["diff"]
    assert result["diff"]["before"]["table_name"] == existing_table_kafka.table_name
    assert result["diff"]["after"] == ""


def test_ssb_table_module_update_with_update_enabled_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
    ssb_table_client,
    purge_table_by_name,
):
    """Test SsbTableModule updating a table with update_enabled=True."""
    original_table_name = existing_table_kafka.table_name
    purge_table_by_name(existing_project.id, original_table_name)

    # Update the table with different metadata
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": original_table_name,
            "type": "ssb",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "updated_field", "type": "STRING"},
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
    assert result["table"]["table_name"] == original_table_name

    # Verify table was recreated with new metadata
    tables = ssb_table_client.list_tables(existing_project.id)
    updated_table = next(
        (t for t in tables if t.table_name == original_table_name),
        None,
    )
    assert updated_table is not None
    # ID should be different after recreation
    if isinstance(existing_table_kafka.id, int) and isinstance(updated_table.id, int):
        assert updated_table.id != existing_table_kafka.id


def test_ssb_table_module_update_with_update_disabled_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
    ssb_table_client,
):
    """Test SsbTableModule with update_enabled=False (should not update)."""
    original_id = existing_table_kafka.id

    # Try to update the table with update_enabled=False
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": existing_table_kafka.table_name,
            "type": "ssb",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "new_field", "type": "STRING"},
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

    # Verify table was not modified
    tables = ssb_table_client.list_tables(existing_project.id)
    current_table = next(
        (t for t in tables if t.table_name == existing_table_kafka.table_name),
        None,
    )
    assert current_table is not None
    # ID should be the same (not recreated)
    if isinstance(original_id, int) and isinstance(current_table.id, int):
        assert current_table.id == original_id


def test_ssb_table_module_no_update_needed_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
):
    """Test SsbTableModule with identical parameters (no update needed)."""
    # Call with same parameters
    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": existing_table_kafka.table_name,
            "type": existing_table_kafka.type,
            "metadata": existing_table_kafka.metadata,
            "update_enabled": True,
            "state": "present",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is False
    assert result["table"]["table_name"] == existing_table_kafka.table_name


def test_ssb_table_module_update_check_mode_with_update_enabled_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
    ssb_table_client,
):
    """Test SsbTableModule in check mode with update_enabled=True."""
    original_id = existing_table_kafka.id

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": existing_table_kafka.table_name,
            "type": "ssb",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "check_mode_field", "type": "STRING"},
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

    # Verify table was NOT actually modified
    tables = ssb_table_client.list_tables(existing_project.id)
    current_table = next(
        (t for t in tables if t.table_name == existing_table_kafka.table_name),
        None,
    )
    assert current_table is not None
    # ID should be the same (not recreated in check mode)
    if isinstance(original_id, int) and isinstance(current_table.id, int):
        assert current_table.id == original_id


def test_ssb_table_module_update_diff_mode_int(
    ssb_module_args,
    existing_project,
    existing_table_kafka,
):
    """Test SsbTableModule with diff mode during update."""
    original_table_name = existing_table_kafka.table_name

    ssb_module_args(
        {
            "project_id": existing_project.id,
            "table_name": original_table_name,
            "type": "ssb",
            "metadata": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "diff_field", "type": "STRING"},
                ],
            },
            "update_enabled": True,
            "state": "present",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_table.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert "before" in result["diff"]
    assert "after" in result["diff"]
    # Verify metadata changed in diff
    assert (
        "metadata" in result["diff"]["before"] or "metadata" in result["diff"]["after"]
    )
