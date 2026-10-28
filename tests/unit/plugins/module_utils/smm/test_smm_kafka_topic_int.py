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


def test_create_topic(
    smm_topic_name,
    smm_topic_client,
    purge_smm_topic,
):
    """Test creating a topic."""
    topic_name = purge_smm_topic(smm_topic_name("create"))

    response = smm_topic_client.create_topic(
        SmmKafkaTopic(
            name=topic_name,
            partitions=2,
            replication_factor=1,
            configs={"retention.ms": "86400000"},
        ),
    )

    assert isinstance(response, SmmKafkaTopic)
    assert response.name == topic_name
    assert response.partitions == 2
    assert response.replication_factor == 1
    # SMM also reports values it derives from retention.ms (e.g. retention.hours)
    assert response.configs["retention.ms"] == "86400000"


def test_create_topic_without_configs(
    smm_topic_name,
    smm_topic_client,
    purge_smm_topic,
):
    """Test creating a topic without configs leaves it with no topic-level overrides."""
    topic_name = purge_smm_topic(smm_topic_name("noconfigs"))

    response = smm_topic_client.create_topic(
        SmmKafkaTopic(name=topic_name, partitions=1, replication_factor=1),
    )

    assert response.name == topic_name
    assert response.partitions == 1
    assert response.configs == {}


def test_update_topic_configs(smm_topic_client, deletable_smm_topic):
    """Test updating the configs of an existing topic."""
    incoming = SmmKafkaTopic(
        name=deletable_smm_topic.name,
        partitions=deletable_smm_topic.partitions,
        replication_factor=deletable_smm_topic.replication_factor,
        configs={"retention.ms": "43200000", "cleanup.policy": "compact"},
    )

    response = smm_topic_client.update_topic(deletable_smm_topic, incoming)

    assert isinstance(response, SmmKafkaTopic)
    assert response.configs["retention.ms"] == "43200000"
    assert response.configs["cleanup.policy"] == "compact"

    # Verify by fetching the topic again
    fetched = smm_topic_client.get_topic(deletable_smm_topic.name)
    assert fetched.configs["retention.ms"] == "43200000"
    assert fetched.configs["cleanup.policy"] == "compact"


def test_update_topic_partitions(
    smm_topic_client,
    smm_wait_until,
    deletable_smm_topic,
):
    """Test increasing the partitions of an existing topic."""
    incoming = SmmKafkaTopic(
        name=deletable_smm_topic.name,
        partitions=3,
        replication_factor=deletable_smm_topic.replication_factor,
        configs=deletable_smm_topic.configs,
    )

    smm_topic_client.update_topic(deletable_smm_topic, incoming)

    # Verify by fetching the topic again
    assert smm_wait_until(
        lambda: smm_topic_client.get_topic(deletable_smm_topic.name).partitions == 3,
    )


def test_delete_topic(smm_topic_client, smm_wait_until, deletable_smm_topic):
    """Test deleting a topic."""
    response = smm_topic_client.delete_topic(deletable_smm_topic.name)
    assert response is None

    # Kafka deletes topics asynchronously
    assert smm_wait_until(
        lambda: smm_topic_client.get_topic(deletable_smm_topic.name) is None,
    )


def test_delete_topic_not_found(smm_topic_client, smm_topic_name):
    """Test deleting a non-existent topic (idempotent)."""
    response = smm_topic_client.delete_topic(smm_topic_name("missing"))
    assert response is None
