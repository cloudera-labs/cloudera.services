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

import os

from typing import Callable

import pytest

from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

from ansible_collections.cloudera.services.plugins.modules import smm_kafka_topic

REQUIRED_ENV_VARS = [
    "SMM_API_URL",
    "SMM_API_USERNAME",
    "SMM_API_PASSWORD",
]


@pytest.fixture
def smm_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args for SMM Kafka topic tests."""

    def _smm_module_args(overrides: dict = {}) -> None:
        args = {
            "url": env_context["SMM_API_URL"],
            "url_username": env_context["SMM_API_USERNAME"],
            "url_password": env_context["SMM_API_PASSWORD"],
            "force_basic_auth": True,
            "validate_certs": os.environ.get("SMM_VALIDATE_CERTS", "false").lower()
            == "true",
        }
        if overrides:
            args.update(overrides)
        module_args(args)

    return _smm_module_args


def test_smm_kafka_topic_module_create(
    smm_module_args,
    smm_topic_client,
    smm_topic_name,
    smm_wait_until,
    purge_smm_topic,
):
    """Test SmmKafkaTopicModule creates a new topic."""
    topic_name = purge_smm_topic(smm_topic_name("module-create"))

    smm_module_args(
        {
            "name": topic_name,
            "partitions": 1,
            "replication_factor": 1,
            "configs": {"retention.ms": 86400000},
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["name"] == topic_name

    # Kafka creates topics asynchronously
    assert smm_wait_until(lambda: smm_topic_client.get_topic(topic_name) is not None)

    created = smm_topic_client.get_topic(topic_name)
    assert created.partitions == 1
    assert created.replication_factor == 1
    # SMM also reports values it derives from retention.ms (e.g. retention.hours)
    assert created.configs["retention.ms"] == "86400000"


def test_smm_kafka_topic_module_create_check_mode(
    smm_module_args,
    smm_topic_client,
    smm_topic_name,
    purge_smm_topic,
):
    """Test SmmKafkaTopicModule create in check mode does not create a topic."""
    topic_name = purge_smm_topic(smm_topic_name("module-checkmode"))

    smm_module_args(
        {
            "name": topic_name,
            "partitions": 1,
            "replication_factor": 1,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["name"] == topic_name

    # The topic must not actually exist remotely
    assert smm_topic_client.get_topic(topic_name) is None


def test_smm_kafka_topic_module_create_requires_partitions(
    smm_module_args,
    smm_topic_client,
    smm_topic_name,
    purge_smm_topic,
):
    """Test SmmKafkaTopicModule fails to create a topic without partitions."""
    topic_name = purge_smm_topic(smm_topic_name("module-nopartitions"))

    smm_module_args({"name": topic_name, "replication_factor": 1})

    with pytest.raises(AnsibleFailJson) as e:
        smm_kafka_topic.main()

    assert "partitions" in e.value["msg"]
    assert smm_topic_client.get_topic(topic_name) is None


def test_smm_kafka_topic_module_present_no_changes(
    smm_module_args,
    deletable_smm_topic,
):
    """Test SmmKafkaTopicModule present against an unchanged topic is a no-op."""
    smm_module_args(
        {
            "name": deletable_smm_topic.name,
            "partitions": deletable_smm_topic.partitions,
            "replication_factor": deletable_smm_topic.replication_factor,
            "configs": deletable_smm_topic.configs,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is False
    assert result["topic"]["name"] == deletable_smm_topic.name
    assert result["topic"]["partitions"] == deletable_smm_topic.partitions


def test_smm_kafka_topic_module_update_partitions(
    smm_module_args,
    smm_topic_client,
    smm_wait_until,
    deletable_smm_topic,
):
    """Test SmmKafkaTopicModule increases the partitions of an existing topic."""
    smm_module_args({"name": deletable_smm_topic.name, "partitions": 2})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["name"] == deletable_smm_topic.name

    assert smm_wait_until(
        lambda: smm_topic_client.get_topic(deletable_smm_topic.name).partitions == 2,
    )


def test_smm_kafka_topic_module_update_configs(
    smm_module_args,
    smm_topic_client,
    smm_wait_until,
    deletable_smm_topic,
):
    """Test SmmKafkaTopicModule adds a config and keeps the other overrides."""
    smm_module_args(
        {
            "name": deletable_smm_topic.name,
            "configs": {"cleanup.policy": "compact"},
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is True

    def _configs():
        return smm_topic_client.get_topic(deletable_smm_topic.name).configs

    assert smm_wait_until(lambda: _configs().get("cleanup.policy") == "compact")
    assert _configs()["retention.ms"] == "86400000"


def test_smm_kafka_topic_module_update_config_value_is_idempotent(
    smm_module_args,
    smm_topic_client,
    smm_wait_until,
    deletable_smm_topic,
):
    """Test a changed config value is applied and a second run reports no change."""
    args = {"name": deletable_smm_topic.name, "configs": {"retention.ms": 3600000}}

    smm_module_args(args)

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is True

    assert smm_wait_until(
        lambda: smm_topic_client.get_topic(deletable_smm_topic.name).configs.get(
            "retention.ms",
        )
        == "3600000",
    )

    smm_module_args(args)

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is False


def test_smm_kafka_topic_module_update_check_mode(
    smm_module_args,
    smm_topic_client,
    deletable_smm_topic,
):
    """Test SmmKafkaTopicModule update in check mode does not modify the topic."""
    smm_module_args(
        {
            "name": deletable_smm_topic.name,
            "configs": {"retention.ms": 1000},
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is True

    fetched = smm_topic_client.get_topic(deletable_smm_topic.name)
    assert fetched.configs["retention.ms"] == "86400000"


def test_smm_kafka_topic_module_update_replication_factor_fails(
    smm_module_args,
    deletable_smm_topic,
):
    """Test SmmKafkaTopicModule refuses to change the replication factor."""
    smm_module_args({"name": deletable_smm_topic.name, "replication_factor": 2})

    with pytest.raises(AnsibleFailJson) as e:
        smm_kafka_topic.main()

    assert "Cannot change the replication factor" in e.value["msg"]


def test_smm_kafka_topic_module_delete(
    smm_module_args,
    smm_topic_client,
    smm_wait_until,
    deletable_smm_topic,
):
    """Test SmmKafkaTopicModule deletes an existing topic."""
    smm_module_args({"name": deletable_smm_topic.name, "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"] == {}

    # Kafka deletes topics asynchronously
    assert smm_wait_until(
        lambda: smm_topic_client.get_topic(deletable_smm_topic.name) is None,
    )


def test_smm_kafka_topic_module_delete_check_mode(
    smm_module_args,
    smm_topic_client,
    deletable_smm_topic,
):
    """Test SmmKafkaTopicModule delete in check mode does not delete the topic."""
    smm_module_args(
        {
            "name": deletable_smm_topic.name,
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is True
    assert smm_topic_client.get_topic(deletable_smm_topic.name) is not None


def test_smm_kafka_topic_module_delete_nonexistent(
    smm_module_args,
    smm_topic_name,
):
    """Test SmmKafkaTopicModule deleting a topic that does not exist is a no-op."""
    smm_module_args({"name": smm_topic_name("module-missing"), "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is False
    assert result["topic"] == {}
