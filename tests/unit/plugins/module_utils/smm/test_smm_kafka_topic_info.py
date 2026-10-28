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

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.smm import (
    SmmKafkaTopic,
    SmmKafkaTopicClient,
    _topic_from_response,
)

TOPICS_PATH = "/api/v1/admin/topics"
CONFIGS_PATH = "/api/v1/admin/configs/topics"

BROKER = {
    "id": 1,
    "host": "broker-1.example",
    "port": 9093,
    "rack": None,
    "isController": True,
}

# SMM returns TopicInfo objects with camelCase keys.
ORDERS_INFO = {
    "name": "orders",
    "internal": False,
    "partitions": [
        {"partition": 0, "leader": BROKER, "replicas": [BROKER], "isr": [BROKER]},
    ],
}
PAYMENTS_INFO = {
    "name": "payments",
    "internal": False,
    "partitions": [
        {"partition": 0, "leader": BROKER, "replicas": [BROKER], "isr": [BROKER]},
        {"partition": 1, "leader": BROKER, "replicas": [BROKER], "isr": [BROKER]},
    ],
}

ORDERS_CONFIG = {
    "resourceType": "TOPIC",
    "resourceName": "orders",
    "resourceConfigs": [
        {"name": "retention.ms", "value": "1000", "source": "DYNAMIC_TOPIC_CONFIG"},
        {"name": "cleanup.policy", "value": "delete", "source": "DEFAULT_CONFIG"},
    ],
}
PAYMENTS_CONFIG = {
    "resourceType": "TOPIC",
    "resourceName": "payments",
    "resourceConfigs": [
        {"name": "cleanup.policy", "value": "delete", "source": "DEFAULT_CONFIG"},
    ],
}


def test_list_topics(mocker):
    """Test listing all topics merges each topic with its config by name."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    responses = {
        TOPICS_PATH: [ORDERS_INFO, PAYMENTS_INFO],
        CONFIGS_PATH: [PAYMENTS_CONFIG, ORDERS_CONFIG],
    }
    api_client.get.side_effect = lambda path, **kwargs: responses[path]

    client = SmmKafkaTopicClient(api_client=api_client)

    response = client.list_topics()

    assert len(response) == 2
    assert all(isinstance(topic, SmmKafkaTopic) for topic in response)
    assert response[0] == _topic_from_response(ORDERS_INFO, ORDERS_CONFIG)
    assert response[1] == _topic_from_response(PAYMENTS_INFO, PAYMENTS_CONFIG)
    assert response[0].configs == {"retention.ms": "1000"}
    assert response[1].configs == {}
    assert response[1].partitions == 2

    assert api_client.get.call_count == 2
    api_client.get.assert_any_call(TOPICS_PATH, squelch={404: []})
    api_client.get.assert_any_call(CONFIGS_PATH, squelch={404: []})


def test_list_topics_empty(mocker):
    """Test listing topics when none exist."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = []

    client = SmmKafkaTopicClient(api_client=api_client)

    assert client.list_topics() == []


def test_list_topics_without_config_entry(mocker):
    """Test a topic missing from the config listing gets an empty config dict."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    responses = {TOPICS_PATH: [ORDERS_INFO], CONFIGS_PATH: []}
    api_client.get.side_effect = lambda path, **kwargs: responses[path]

    client = SmmKafkaTopicClient(api_client=api_client)

    response = client.list_topics()

    assert len(response) == 1
    assert response[0].configs == {}


def test_get_topic(mocker):
    """Test retrieving a single topic by name."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    responses = {
        f"{TOPICS_PATH}/orders": ORDERS_INFO,
        f"{CONFIGS_PATH}/orders": ORDERS_CONFIG,
    }
    api_client.get.side_effect = lambda path, **kwargs: responses[path]

    client = SmmKafkaTopicClient(api_client=api_client)

    response = client.get_topic("orders")

    assert isinstance(response, SmmKafkaTopic)
    assert response == _topic_from_response(ORDERS_INFO, ORDERS_CONFIG)

    assert api_client.get.call_count == 2
    api_client.get.assert_any_call(f"{TOPICS_PATH}/orders", squelch={404: None})
    api_client.get.assert_any_call(f"{CONFIGS_PATH}/orders", squelch={404: None})


def test_get_topic_not_found(mocker):
    """Test retrieving a non-existent topic returns None without fetching its config."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = SmmKafkaTopicClient(api_client=api_client)

    assert client.get_topic("missing") is None

    api_client.get.assert_called_once_with(
        f"{TOPICS_PATH}/missing",
        squelch={404: None},
    )


def test_get_topic_empty_body(mocker):
    """Test an empty response body is treated as a missing topic."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = {}

    client = SmmKafkaTopicClient(api_client=api_client)

    assert client.get_topic("missing") is None
    api_client.get.assert_called_once()


def test_get_topic_without_config(mocker):
    """Test a topic whose config cannot be found has an empty config dict."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    responses = {
        f"{TOPICS_PATH}/orders": ORDERS_INFO,
        f"{CONFIGS_PATH}/orders": None,
    }
    api_client.get.side_effect = lambda path, **kwargs: responses[path]

    client = SmmKafkaTopicClient(api_client=api_client)

    response = client.get_topic("orders")

    assert response.name == "orders"
    assert response.configs == {}


def test_get_topic_quotes_name(mocker):
    """Test a topic name is URL-quoted into the request path."""
    api_client = mocker.create_autospec(ServicesClient, instance=True)
    api_client.get.return_value = None

    client = SmmKafkaTopicClient(api_client=api_client)

    client.get_topic("my topic/1")

    api_client.get.assert_called_once_with(
        f"{TOPICS_PATH}/my%20topic%2F1",
        squelch={404: None},
    )
