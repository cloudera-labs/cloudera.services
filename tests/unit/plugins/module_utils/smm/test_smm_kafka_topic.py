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

from types import SimpleNamespace

import pytest

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesClient,
    ServicesError,
)
from ansible_collections.cloudera.services.plugins.module_utils.smm import (
    SmmBrokerNode,
    SmmKafkaTopic,
    SmmKafkaTopicClient,
    _topic_from_response,
    _topic_to_create_payload,
    extract_topic_params,
    merge_topic_configs,
    normalize_topic_configs,
    validate_topic_update,
)

TOPICS_PATH = "/api/v1/admin/topics"
CONFIGS_PATH = "/api/v1/admin/configs/topics"

BROKER_1 = {
    "id": 1,
    "host": "broker-1.example",
    "port": 9093,
    "rack": None,
    "isController": True,
}
BROKER_2 = {
    "id": 2,
    "host": "broker-2.example",
    "port": 9093,
    "rack": None,
    "isController": False,
}

# SMM returns TopicInfo objects with camelCase keys.
TOPIC_INFO_RESPONSE = {
    "name": "orders",
    "internal": False,
    "partitions": [
        {
            "partition": 0,
            "leader": BROKER_1,
            "replicas": [BROKER_1, BROKER_2],
            "isr": [BROKER_1, BROKER_2],
        },
        {
            "partition": 1,
            "leader": BROKER_2,
            "replicas": [BROKER_2, BROKER_1],
            "isr": [BROKER_2],
        },
    ],
}

# SMM reports every config of the topic, only the DYNAMIC_TOPIC_CONFIG ones are overrides.
TOPIC_CONFIG_RESPONSE = {
    "resourceType": "TOPIC",
    "resourceName": "orders",
    "resourceConfigs": [
        {
            "name": "retention.ms",
            "value": "604800000",
            "source": "DYNAMIC_TOPIC_CONFIG",
            "isDefault": False,
            "isReadOnly": False,
            "isSensitive": False,
        },
        {
            "name": "cleanup.policy",
            "value": "delete",
            "source": "DEFAULT_CONFIG",
            "isDefault": True,
            "isReadOnly": False,
            "isSensitive": False,
        },
        {
            "name": "min.insync.replicas",
            "value": "1",
            "source": "STATIC_BROKER_CONFIG",
            "isDefault": False,
            "isReadOnly": False,
            "isSensitive": False,
        },
    ],
}


def _existing_topic(**overrides):
    topic = _topic_from_response(TOPIC_INFO_RESPONSE, TOPIC_CONFIG_RESPONSE)
    for key, value in overrides.items():
        setattr(topic, key, value)
    return topic


def _mock_get(api_client, topic_info=TOPIC_INFO_RESPONSE, config=TOPIC_CONFIG_RESPONSE):
    responses = {
        f"{TOPICS_PATH}/orders": topic_info,
        f"{CONFIGS_PATH}/orders": config,
    }
    api_client.get.side_effect = lambda path, **kwargs: responses[path]


def test_create_topic(mocker):
    """Test creating a topic posts a NewTopics payload and returns the created topic."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}
    _mock_get(api_client)

    client = SmmKafkaTopicClient(api_client=api_client)

    response = client.create_topic(
        SmmKafkaTopic(
            name="orders",
            partitions=2,
            replication_factor=2,
            configs={"retention.ms": "604800000"},
        ),
    )

    assert response == _topic_from_response(TOPIC_INFO_RESPONSE, TOPIC_CONFIG_RESPONSE)

    api_client.post.assert_called_once_with(
        TOPICS_PATH,
        data={
            "newTopics": [
                {
                    "name": "orders",
                    "numPartitions": 2,
                    "replicationFactor": 2,
                    "configs": {"retention.ms": "604800000"},
                },
            ],
        },
    )


def test_create_topic_minimal(mocker):
    """Test creating a topic with only a name omits all NULLABLE fields."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}
    _mock_get(api_client)

    client = SmmKafkaTopicClient(api_client=api_client)

    response = client.create_topic(SmmKafkaTopic(name="orders"))

    assert isinstance(response, SmmKafkaTopic)

    api_client.post.assert_called_once_with(
        TOPICS_PATH,
        data={"newTopics": [{"name": "orders"}]},
    )


def test_create_topic_stringifies_config_values(mocker):
    """Test that non-string config values are sent to SMM as strings."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}
    _mock_get(api_client)

    client = SmmKafkaTopicClient(api_client=api_client)

    client.create_topic(
        SmmKafkaTopic(
            name="orders",
            configs={
                "retention.ms": 604800000,
                "unclean.leader.election.enable": False,
            },
        ),
    )

    sent = api_client.post.call_args[1]["data"]["newTopics"][0]["configs"]
    assert sent == {
        "retention.ms": "604800000",
        "unclean.leader.election.enable": "false",
    }


def test_create_topic_not_yet_visible_returns_requested_topic(mocker):
    """Test the requested topic is returned when SMM does not list it right after creation."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.post.return_value = {}
    api_client.get.return_value = None

    client = SmmKafkaTopicClient(api_client=api_client)

    requested = SmmKafkaTopic(name="orders", partitions=2, replication_factor=2)
    response = client.create_topic(requested)

    assert response is requested


def test_update_topic_increases_partitions(mocker):
    """Test raising the partition count puts the new total to the topics endpoint."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {}
    _mock_get(api_client)

    client = SmmKafkaTopicClient(api_client=api_client)

    existing = _existing_topic()
    incoming = _existing_topic(partitions=5)

    response = client.update_topic(existing, incoming)

    assert isinstance(response, SmmKafkaTopic)

    api_client.put.assert_called_once_with(
        TOPICS_PATH,
        data={"topicWithNewPartitions": {"orders": {"totalCount": 5}}},
    )


def test_update_topic_alters_configs(mocker):
    """Test changed configs are put to the topic config endpoint."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {}
    _mock_get(api_client)

    client = SmmKafkaTopicClient(api_client=api_client)

    existing = _existing_topic()
    incoming = _existing_topic(
        configs={"retention.ms": "1000", "cleanup.policy": "compact"},
    )

    client.update_topic(existing, incoming)

    api_client.put.assert_called_once_with(
        f"{CONFIGS_PATH}/orders",
        data={"retention.ms": "1000", "cleanup.policy": "compact"},
    )


def test_update_topic_configs_and_partitions(mocker):
    """Test a change to both configs and partitions issues both requests."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {}
    _mock_get(api_client)

    client = SmmKafkaTopicClient(api_client=api_client)

    existing = _existing_topic()
    incoming = _existing_topic(partitions=3, configs={"retention.ms": "1000"})

    client.update_topic(existing, incoming)

    assert api_client.put.call_count == 2
    paths = [call.args[0] for call in api_client.put.call_args_list]
    assert f"{CONFIGS_PATH}/orders" in paths
    assert TOPICS_PATH in paths


def test_update_topic_no_changes(mocker):
    """Test an update with nothing to change does not call the API."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    _mock_get(api_client)

    client = SmmKafkaTopicClient(api_client=api_client)

    client.update_topic(_existing_topic(), _existing_topic())

    api_client.put.assert_not_called()
    api_client.post.assert_not_called()


def test_update_topic_decrease_partitions_fails(mocker):
    """Test decreasing the partition count raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = SmmKafkaTopicClient(api_client=api_client)

    with pytest.raises(ServicesError, match="Cannot decrease the partitions"):
        client.update_topic(_existing_topic(), _existing_topic(partitions=1))

    api_client.put.assert_not_called()


def test_update_topic_replication_factor_change_fails(mocker):
    """Test changing the replication factor raises a ServicesError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = SmmKafkaTopicClient(api_client=api_client)

    with pytest.raises(ServicesError, match="Cannot change the replication factor"):
        client.update_topic(_existing_topic(), _existing_topic(replication_factor=3))

    api_client.put.assert_not_called()


def test_update_topic_without_name(mocker):
    """Test updating a topic without a name raises ValueError."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)

    client = SmmKafkaTopicClient(api_client=api_client)

    with pytest.raises(ValueError, match="Cannot update a topic without a name"):
        client.update_topic(SmmKafkaTopic(name=None), SmmKafkaTopic(name=None))

    api_client.put.assert_not_called()


def test_alter_topic_configs(mocker):
    """Test altering configs normalises the values to strings."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {}

    client = SmmKafkaTopicClient(api_client=api_client)

    client.alter_topic_configs("orders", {"retention.ms": 1000, "flag": True})

    api_client.put.assert_called_once_with(
        f"{CONFIGS_PATH}/orders",
        data={"retention.ms": "1000", "flag": "true"},
    )


def test_increase_partitions(mocker):
    """Test increasing partitions."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.put.return_value = {}

    client = SmmKafkaTopicClient(api_client=api_client)

    client.increase_partitions("orders", 4)

    api_client.put.assert_called_once_with(
        TOPICS_PATH,
        data={"topicWithNewPartitions": {"orders": {"totalCount": 4}}},
    )


def test_delete_topic(mocker):
    """Test deleting a topic sends the name as a repeated query parameter."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = TOPIC_INFO_RESPONSE
    api_client.delete.return_value = None

    client = SmmKafkaTopicClient(api_client=api_client)

    response = client.delete_topic("orders")

    assert response is None

    api_client.get.assert_called_once_with(
        f"{TOPICS_PATH}/orders",
        squelch={404: None},
    )
    api_client.delete.assert_called_once_with(
        TOPICS_PATH,
        params={"topicName": ["orders"]},
    )


def test_delete_topic_not_found(mocker):
    """Test deleting an unknown topic is a no-op, SMM would answer the DELETE with a 500."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = SmmKafkaTopicClient(api_client=api_client)

    assert client.delete_topic("missing") is None

    api_client.delete.assert_not_called()


def test_topic_from_response():
    """Test deserialisation derives counts and keeps only topic-level config overrides."""
    topic = _topic_from_response(TOPIC_INFO_RESPONSE, TOPIC_CONFIG_RESPONSE)

    assert isinstance(topic, SmmKafkaTopic)
    assert topic.name == "orders"
    assert topic.internal is False
    assert topic.partitions == 2
    assert topic.replication_factor == 2

    # Only the overrides set on the topic itself are kept
    assert topic.configs == {"retention.ms": "604800000"}

    assert len(topic.partition_details) == 2
    first = topic.partition_details[0]
    assert first.partition == 0
    assert first.leader == SmmBrokerNode(
        id=1,
        host="broker-1.example",
        port=9093,
        rack=None,
        is_controller=True,
    )
    assert [b.id for b in first.replicas] == [1, 2]
    assert [b.id for b in topic.partition_details[1].isr] == [2]


def test_topic_from_response_without_configs():
    """Test a missing config resource gives an empty config dict."""
    topic = _topic_from_response(TOPIC_INFO_RESPONSE, None)

    assert topic.configs == {}


def test_topic_from_response_without_partitions():
    """Test a topic without partitions has no replication factor."""
    topic = _topic_from_response({"name": "empty", "internal": False, "partitions": []})

    assert topic.partitions == 0
    assert topic.replication_factor is NULLABLE
    assert topic.partition_details == []


def test_topic_to_create_payload():
    """Test the create payload is camelCase and omits unset fields."""
    assert _topic_to_create_payload(SmmKafkaTopic(name="orders")) == {"name": "orders"}

    assert _topic_to_create_payload(
        SmmKafkaTopic(
            name="orders",
            partitions=3,
            replication_factor=2,
            configs={"cleanup.policy": "compact"},
            internal=False,
        ),
    ) == {
        "name": "orders",
        "numPartitions": 3,
        "replicationFactor": 2,
        "configs": {"cleanup.policy": "compact"},
    }


def test_normalize_topic_configs():
    """Test config values are converted to the strings Kafka stores."""
    assert normalize_topic_configs(None) is None
    assert normalize_topic_configs({}) == {}
    assert normalize_topic_configs(
        {"a": 1, "b": True, "c": False, "d": "x", "e": None, "f": 1.5},
    ) == {"a": "1", "b": "true", "c": "false", "d": "x", "e": "", "f": "1.5"}


def test_merge_topic_configs_keeps_other_overrides():
    """Test listed configs are overlaid and the other overrides are kept."""
    assert merge_topic_configs(
        {"cleanup.policy": "delete", "max.message.bytes": "1024"},
        {"max.message.bytes": "2048"},
    ) == {"cleanup.policy": "delete", "max.message.bytes": "2048"}


def test_merge_topic_configs_unchanged_value_keeps_derived_counterpart():
    """Test an unchanged value leaves the derived counterpart in place."""
    existing = {"retention.ms": "86400000", "retention.hours": "24"}

    assert merge_topic_configs(existing, {"retention.ms": "86400000"}) == existing


def test_merge_topic_configs_changed_value_drops_derived_counterpart():
    """Test a changed value does not send back the stale derived counterpart."""
    assert merge_topic_configs(
        {
            "retention.ms": "86400000",
            "retention.hours": "24",
            "cleanup.policy": "delete",
        },
        {"retention.ms": "3600000"},
    ) == {"retention.ms": "3600000", "cleanup.policy": "delete"}


def test_merge_topic_configs_changed_hours_drops_derived_ms():
    """Test the derivation also works in the other direction."""
    assert merge_topic_configs(
        {"retention.ms": "86400000", "retention.hours": "24"},
        {"retention.hours": "48"},
    ) == {"retention.hours": "48"}


def test_merge_topic_configs_both_counterparts_requested():
    """Test both values are kept when the user sets them explicitly."""
    assert merge_topic_configs(
        {"retention.ms": "86400000", "retention.hours": "24"},
        {"retention.ms": "3600000", "retention.hours": "1"},
    ) == {"retention.ms": "3600000", "retention.hours": "1"}


def test_merge_topic_configs_does_not_modify_inputs():
    """Test the existing and desired configs are left untouched."""
    existing = {"retention.ms": "86400000", "retention.hours": "24"}
    desired = {"retention.ms": "3600000"}

    merge_topic_configs(existing, desired)

    assert existing == {"retention.ms": "86400000", "retention.hours": "24"}
    assert desired == {"retention.ms": "3600000"}


def test_validate_topic_update_allows_increase():
    """Test increasing partitions and keeping the replication factor is valid."""
    validate_topic_update(_existing_topic(), _existing_topic(partitions=10))


def test_validate_topic_update_ignores_unset_values():
    """Test unset values are not treated as a decrease."""
    validate_topic_update(
        _existing_topic(),
        SmmKafkaTopic(name="orders"),
    )


def test_extract_topic_params():
    """Test extracting the mutable parameters from a module instance."""
    module = SimpleNamespace(
        name="orders",
        partitions=3,
        replication_factor=2,
        configs={"retention.ms": 1000},
    )

    assert extract_topic_params(module) == {
        "name": "orders",
        "partitions": 3,
        "replication_factor": 2,
        "configs": {"retention.ms": "1000"},
    }


def test_extract_topic_params_unset():
    """Test attributes missing from the module instance come back as None."""
    assert extract_topic_params(SimpleNamespace(name="orders")) == {
        "name": "orders",
        "partitions": None,
        "replication_factor": None,
        "configs": None,
    }


def test_argument_spec_matches_dataclass_fields():
    """Test the argument spec keys are dataclass fields, as build_from_params expects."""
    spec = SmmKafkaTopic.argument_spec()

    assert set(spec) == {"name", "partitions", "replication_factor", "configs"}
    assert spec["partitions"]["aliases"] == ["num_partitions"]
