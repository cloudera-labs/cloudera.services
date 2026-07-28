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
import re

from unittest.mock import Mock

from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbTable,
)
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

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
def ansible_module(env_context) -> Mock:
    """Fixture to create a mock AnsibleModule for the SSB endpoint."""
    module = Mock()
    module.params = {}
    module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "fail_json called"}),
    )
    module.exit_json = Mock(
        side_effect=AnsibleExitJson({"msg": "exit_json called"}),
    )

    module.params.update(
        {
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": env_context["SSB_SSE_API_PASSWORD"],
        },
    )
    return module


def test_create_table_kafka(
    request,
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
    existing_data_source_kafka,
    existing_data_source_kafka_schema,
    purge_table,
):
    """Test creating a Hive Data Source"""
    ssb_rest_client.module = ansible_module

    table_name = request.node.name.lower()

    # Create the test data source
    table = ssb_table_client.create_table(
        project_id=existing_data_source_kafka.project_id,
        table=SsbTable(
            table_name=table_name,
            type="kafka",
            metadata={
                "kafka_source_name": existing_data_source_kafka.name,
                "format": "JSON",
                "schema": json.dumps(existing_data_source_kafka_schema),
                "topic": table_name,
            },
        ),
    )

    # Register the data source for cleanup
    purge_table(table)

    assert isinstance(table, SsbTable)
    assert table.table_name == table_name


def test_describe_table_kafka(
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
    existing_table_kafka,
):
    """Test describing a Kafka Table"""
    ssb_rest_client.module = ansible_module

    table = ssb_table_client.describe_table(
        project_id=existing_table_kafka.project_id,
        table_id=existing_table_kafka.id,
    )

    assert isinstance(table, SsbTable)
    assert table.id == existing_table_kafka.id
    assert table.table_name == existing_table_kafka.table_name


def test_describe_table_nonexistent(
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test describing a non-existent Table"""
    ssb_rest_client.module = ansible_module

    table = ssb_table_client.describe_table(
        project_id=existing_project.id,
        table_id=1234,
    )

    assert table is None


def test_describe_table_nonexistent_project(
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
):
    """Test describing a Table with a non-existent project"""
    ssb_rest_client.module = ansible_module

    table = ssb_table_client.describe_table(
        project_id="nonexistent-project-id-12345",
        table_id=1234,
    )

    assert table is None


def test_list_tables(
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
    existing_table_kafka,
):
    """Test listing Tables"""
    ssb_rest_client.module = ansible_module

    tables = ssb_table_client.list_tables(project_id=existing_table_kafka.project_id)

    assert isinstance(tables, list)
    assert len(tables) == 1
    assert isinstance(tables[0], SsbTable)
    assert tables[0].id == existing_table_kafka.id


def test_list_tables_nonexistent_project(
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
):
    """Test listing Tables"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        ssb_table_client.list_tables(project_id="nonexistent-project-id-12345")

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )


def test_delete_table(
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
    existing_table_kafka,
):
    """Test deleting a Table"""
    ssb_rest_client.module = ansible_module

    # Delete the table
    ssb_table_client.delete_table(
        project_id=existing_table_kafka.project_id,
        table_id=existing_table_kafka.id,
    )

    # Verify the table no longer exists
    table = ssb_table_client.describe_table(
        project_id=existing_table_kafka.project_id,
        table_id=existing_table_kafka.id,
    )

    assert table is None


def test_delete_table_nonexistent_project(
    ssb_table_client,
    ansible_module,
    ssb_rest_client,
):
    """Test deleting a Table"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        ssb_table_client.delete_table(
            project_id="nonexistent-project-id-12345",
            table_id=12345,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )
