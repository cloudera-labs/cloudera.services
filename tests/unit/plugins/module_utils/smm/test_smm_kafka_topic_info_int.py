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

from ansible_collections.cloudera.services.plugins.module_utils.smm import (
    SmmKafkaTopic,
)

REQUIRED_ENV_VARS = [
    "SMM_API_URL",
    "SMM_API_USERNAME",
    "SMM_API_PASSWORD",
]


def test_list_topics(smm_topic_client, existing_smm_topic):
    """Test listing all topics includes the existing test topic."""
    response = smm_topic_client.list_topics()

    assert isinstance(response, list)
    assert all(isinstance(topic, SmmKafkaTopic) for topic in response)

    match = [topic for topic in response if topic.name == existing_smm_topic.name]
    assert len(match) == 1
    assert match[0].partitions == existing_smm_topic.partitions
    assert match[0].configs == existing_smm_topic.configs


def test_get_topic(smm_topic_client, existing_smm_topic):
    """Test retrieving a topic by name."""
    response = smm_topic_client.get_topic(existing_smm_topic.name)

    assert isinstance(response, SmmKafkaTopic)
    assert response.name == existing_smm_topic.name
    assert response.internal is False
    assert response.partitions == 1
    assert response.replication_factor == 1
    # SMM also reports values it derives from retention.ms (e.g. retention.hours)
    assert response.configs["retention.ms"] == "86400000"
    assert len(response.partition_details) == 1
    assert response.partition_details[0].leader is not None
    assert len(response.partition_details[0].replicas) == 1


def test_get_topic_not_found(smm_topic_client, smm_topic_name):
    """Test retrieving a non-existent topic returns None."""
    assert smm_topic_client.get_topic(smm_topic_name("missing")) is None
