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

from ansible_collections.cloudera.services.plugins.modules import smm_kafka_topic_info
from ansible_collections.cloudera.services.plugins.module_utils.smm import (
    SmmBrokerNode,
    SmmKafkaTopic,
    SmmTopicPartition,
)

BASE_URL = "https://smm.example"

CLIENT = "ansible_collections.cloudera.services.plugins.modules.smm_kafka_topic_info.SmmKafkaTopicClient"

CONNECTION = {
    "endpoint": BASE_URL,
    "url_username": "admin",
    "url_password": "changeme",
}

BROKER = SmmBrokerNode(
    id=1,
    host="broker-1.example",
    port=9093,
    rack=None,
    is_controller=True,
)


def _topic(name, partitions=1, configs=None):
    return SmmKafkaTopic(
        name=name,
        partitions=partitions,
        replication_factor=1,
        configs=configs if configs is not None else {},
        internal=False,
        partition_details=[
            SmmTopicPartition(
                partition=index,
                leader=BROKER,
                replicas=[BROKER],
                isr=[BROKER],
            )
            for index in range(partitions)
        ],
    )


def test_smm_kafka_topic_info_module_list_all(module_args, mocker):
    """Test SmmKafkaTopicInfoModule listing every topic."""
    mock_list = mocker.patch(
        f"{CLIENT}.list_topics",
        return_value=[
            _topic("orders", partitions=2, configs={"retention.ms": "1000"}),
            _topic("payments"),
        ],
    )
    mock_get = mocker.patch(f"{CLIENT}.get_topic")

    module_args(CONNECTION)

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert [topic["name"] for topic in result["topics"]] == ["orders", "payments"]
    assert result["topics"][0]["partitions"] == 2
    assert result["topics"][0]["configs"] == {"retention.ms": "1000"}
    assert result["topics"][1]["configs"] == {}

    mock_list.assert_called_once_with()
    mock_get.assert_not_called()


def test_smm_kafka_topic_info_module_list_all_empty(module_args, mocker):
    """Test SmmKafkaTopicInfoModule listing when there are no topics."""
    mocker.patch(f"{CLIENT}.list_topics", return_value=[])

    module_args(CONNECTION)

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["topics"] == []


def test_smm_kafka_topic_info_module_by_name(module_args, mocker):
    """Test SmmKafkaTopicInfoModule retrieving a single topic by name."""
    mock_get = mocker.patch(
        f"{CLIENT}.get_topic",
        return_value=_topic("orders", partitions=2, configs={"retention.ms": "1000"}),
    )
    mock_list = mocker.patch(f"{CLIENT}.list_topics")

    module_args({**CONNECTION, "name": "orders"})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["topics"]) == 1

    topic = result["topics"][0]
    assert topic["name"] == "orders"
    assert topic["partitions"] == 2
    assert topic["replication_factor"] == 1
    assert topic["configs"] == {"retention.ms": "1000"}
    assert topic["internal"] is False
    assert len(topic["partition_details"]) == 2
    assert topic["partition_details"][0]["leader"]["host"] == "broker-1.example"
    assert topic["partition_details"][0]["leader"]["is_controller"] is True

    mock_get.assert_called_once_with("orders")
    mock_list.assert_not_called()


def test_smm_kafka_topic_info_module_by_name_not_found(module_args, mocker):
    """Test SmmKafkaTopicInfoModule returns an empty list for an unknown topic."""
    mock_get = mocker.patch(f"{CLIENT}.get_topic", return_value=None)

    module_args({**CONNECTION, "name": "missing"})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["topics"] == []

    mock_get.assert_called_once_with("missing")


def test_smm_kafka_topic_info_module_check_mode(module_args, mocker):
    """Test SmmKafkaTopicInfoModule still reads in check mode."""
    mocker.patch(f"{CLIENT}.list_topics", return_value=[_topic("orders")])

    module_args({**CONNECTION, "_ansible_check_mode": True})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert [topic["name"] for topic in result["topics"]] == ["orders"]


def test_smm_kafka_topic_info_module_missing_url_fails(module_args, mocker):
    """Test SmmKafkaTopicInfoModule fails without connection parameters."""
    mock_list = mocker.patch(f"{CLIENT}.list_topics")

    module_args({"url_username": "admin", "url_password": "changeme"})

    with pytest.raises(AnsibleFailJson):
        smm_kafka_topic_info.main()

    mock_list.assert_not_called()
