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

"""
REST clients for the Cloudera Streams Messaging Manager (SMM) API.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
)

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    NULLABLE,
    ServicesClient,
    ServicesError,
)

# Source SMM reports for a topic config that was explicitly set on the topic,
# as opposed to inherited from the broker or a built-in default.
TOPIC_CONFIG_SOURCE = "DYNAMIC_TOPIC_CONFIG"

# SMM reports an hours variant next to these topic overrides, for example
# retention.hours: 24 beside retention.ms: 86400000. It is derived from the
# other one, so it must not be sent back next to a changed value.
DERIVED_TOPIC_CONFIGS = {
    "retention.ms": "retention.hours",
    "retention.hours": "retention.ms",
    "delete.retention.ms": "delete.retention.hours",
    "delete.retention.hours": "delete.retention.ms",
}


@dataclass
class SmmBrokerNode:
    """Representation of a Kafka broker referenced by a topic partition."""

    id: Union[int, None, NULLABLE] = NULLABLE
    host: Union[str, None, NULLABLE] = NULLABLE
    port: Union[int, None, NULLABLE] = NULLABLE
    rack: Union[str, None, NULLABLE] = NULLABLE
    is_controller: Union[bool, None, NULLABLE] = NULLABLE


@dataclass
class SmmTopicPartition:
    """Representation of a single partition of a Kafka topic."""

    partition: Union[int, None, NULLABLE] = NULLABLE
    leader: Union[SmmBrokerNode, None, NULLABLE] = NULLABLE
    replicas: Union[List[SmmBrokerNode], None, NULLABLE] = NULLABLE
    isr: Union[List[SmmBrokerNode], None, NULLABLE] = NULLABLE


@dataclass
class SmmKafkaTopic:
    """Representation of a Kafka topic managed through SMM."""

    # Mutable - required when creating a topic
    name: str

    # Mutable - partitions can only be increased, the replication factor is fixed
    partitions: Union[int, None, NULLABLE] = NULLABLE
    replication_factor: Union[int, None, NULLABLE] = NULLABLE

    # Mutable - topic-level config overrides only (broker defaults are not included)
    configs: Union[Dict[str, str], None, NULLABLE] = NULLABLE

    # Read-only (set by Kafka)
    internal: Union[bool, None, NULLABLE] = NULLABLE
    partition_details: Union[List[SmmTopicPartition], None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the Ansible argument spec for the mutable SmmKafkaTopic parameters."""
        return dict(
            name=dict(type="str", required=False),
            partitions=dict(
                type="int",
                required=False,
                aliases=["num_partitions"],
            ),
            replication_factor=dict(type="int", required=False),
            configs=dict(type="dict", required=False),
        )


def normalize_topic_configs(
    configs: Optional[Dict[str, Any]],
) -> Optional[Dict[str, str]]:
    """Convert topic config values to the strings Kafka stores (None stays None)."""
    if configs is None:
        return None

    normalized = {}
    for key, value in configs.items():
        if isinstance(value, bool):
            normalized[str(key)] = "true" if value else "false"
        elif value is None:
            normalized[str(key)] = ""
        else:
            normalized[str(key)] = str(value)
    return normalized


def merge_topic_configs(
    existing: Dict[str, str],
    desired: Dict[str, str],
) -> Dict[str, str]:
    """Overlay the desired topic configs on the existing overrides.

    When a value changes, the counterpart SMM derived from the old value is
    dropped so it is not sent back next to the new one.
    """
    merged = dict(existing)
    for key, value in desired.items():
        counterpart = DERIVED_TOPIC_CONFIGS.get(key)
        if counterpart and counterpart not in desired and merged.get(key) != value:
            merged.pop(counterpart, None)
        merged[key] = value
    return merged


def _broker_from_response(raw: Dict[str, Any]) -> SmmBrokerNode:
    """Deserialise an SMM broker node into a SmmBrokerNode."""
    return from_dict(SmmBrokerNode, camel_dict_to_snake_dict(raw, reversible=True))


def _partition_from_response(raw: Dict[str, Any]) -> SmmTopicPartition:
    """Deserialise an SMM topic partition into a SmmTopicPartition."""
    leader = raw.get("leader")
    return SmmTopicPartition(
        partition=raw.get("partition", NULLABLE),
        leader=_broker_from_response(leader) if leader else None,
        replicas=[_broker_from_response(r) for r in raw.get("replicas") or []],
        isr=[_broker_from_response(r) for r in raw.get("isr") or []],
    )


def _explicit_configs(config_resource: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Pick the topic-level overrides out of an SMM KafkaResourceConfig."""
    entries = (config_resource or {}).get("resourceConfigs") or []
    return {
        entry["name"]: entry.get("value")
        for entry in entries
        if entry.get("source") == TOPIC_CONFIG_SOURCE
    }


def _topic_from_response(
    info: Dict[str, Any],
    config_resource: Optional[Dict[str, Any]] = None,
) -> SmmKafkaTopic:
    """Build a SmmKafkaTopic from an SMM TopicInfo and its KafkaResourceConfig."""
    details = [_partition_from_response(p) for p in info.get("partitions") or []]

    replication_factor = NULLABLE
    if details and details[0].replicas is not NULLABLE:
        replication_factor = len(details[0].replicas)

    return SmmKafkaTopic(
        name=info.get("name"),
        partitions=len(details),
        replication_factor=replication_factor,
        configs=_explicit_configs(config_resource),
        internal=info.get("internal", NULLABLE),
        partition_details=details,
    )


def _topic_to_create_payload(topic: SmmKafkaTopic) -> Dict[str, Any]:
    """Serialise a SmmKafkaTopic into an SMM NewTopic request payload."""
    payload: Dict[str, Any] = {"name": topic.name}
    if topic.partitions is not NULLABLE and topic.partitions is not None:
        payload["numPartitions"] = topic.partitions
    if (
        topic.replication_factor is not NULLABLE
        and topic.replication_factor is not None
    ):
        payload["replicationFactor"] = topic.replication_factor
    if topic.configs is not NULLABLE and topic.configs is not None:
        payload["configs"] = normalize_topic_configs(topic.configs)
    return payload


def validate_topic_update(existing: SmmKafkaTopic, incoming: SmmKafkaTopic) -> None:
    """Fail when the requested change is something Kafka cannot do to a live topic."""
    if (
        incoming.partitions not in (NULLABLE, None)
        and existing.partitions not in (NULLABLE, None)
        and incoming.partitions < existing.partitions
    ):
        raise ServicesError(
            f"Cannot decrease the partitions of topic '{existing.name}' "
            f"from {existing.partitions} to {incoming.partitions}; "
            "Kafka only supports increasing the number of partitions.",
        )

    if (
        incoming.replication_factor not in (NULLABLE, None)
        and existing.replication_factor not in (NULLABLE, None)
        and incoming.replication_factor != existing.replication_factor
    ):
        raise ServicesError(
            f"Cannot change the replication factor of topic '{existing.name}' "
            f"from {existing.replication_factor} to {incoming.replication_factor}.",
        )


class SmmKafkaTopicClient:
    """Streams Messaging Manager Kafka topic API client."""

    TOPICS_PATH = "/api/v1/admin/topics"
    CONFIGS_PATH = "/api/v1/admin/configs/topics"

    def __init__(self, api_client: ServicesClient) -> None:
        self.api_client: ServicesClient = api_client

    def list_topics(self) -> List[SmmKafkaTopic]:
        """List all topics, including their topic-level configs."""
        infos = self.api_client.get(self.TOPICS_PATH, squelch={404: []}) or []
        configs = self.api_client.get(self.CONFIGS_PATH, squelch={404: []}) or []
        configs_by_name = {c.get("resourceName"): c for c in configs}
        return [
            _topic_from_response(i, configs_by_name.get(i.get("name"))) for i in infos
        ]

    def get_topic(self, name: str) -> Optional[SmmKafkaTopic]:
        """Retrieve a single topic by name, or None if not found."""
        quoted = quote(name, safe="")
        info = self.api_client.get(
            f"{self.TOPICS_PATH}/{quoted}",
            squelch={404: None},
        )

        if not info:
            return None

        config_resource = self.api_client.get(
            f"{self.CONFIGS_PATH}/{quoted}",
            squelch={404: None},
        )
        return _topic_from_response(info, config_resource)

    def create_topic(self, topic: SmmKafkaTopic) -> SmmKafkaTopic:
        """Create a new topic."""
        self.api_client.post(
            self.TOPICS_PATH,
            data={"newTopics": [_topic_to_create_payload(topic)]},
        )
        created = self.get_topic(topic.name)
        return created if created is not None else topic

    def alter_topic_configs(self, name: str, configs: Dict[str, Any]) -> None:
        """Set the topic-level configs of an existing topic."""
        self.api_client.put(
            f"{self.CONFIGS_PATH}/{quote(name, safe='')}",
            data=normalize_topic_configs(configs),
        )

    def increase_partitions(self, name: str, total_count: int) -> None:
        """Increase the number of partitions of an existing topic to total_count."""
        self.api_client.put(
            self.TOPICS_PATH,
            data={"topicWithNewPartitions": {name: {"totalCount": total_count}}},
        )

    def update_topic(
        self,
        existing: SmmKafkaTopic,
        incoming: SmmKafkaTopic,
    ) -> SmmKafkaTopic:
        """Apply the partition and config differences between existing and incoming."""
        if existing.name is NULLABLE or existing.name is None:
            raise ValueError("Cannot update a topic without a name.")

        validate_topic_update(existing, incoming)

        if (
            incoming.configs not in (NULLABLE, None)
            and incoming.configs != existing.configs
        ):
            self.alter_topic_configs(existing.name, incoming.configs)

        if (
            incoming.partitions not in (NULLABLE, None)
            and incoming.partitions != existing.partitions
        ):
            self.increase_partitions(existing.name, incoming.partitions)

        updated = self.get_topic(existing.name)
        return updated if updated is not None else incoming

    def delete_topic(self, name: str) -> None:
        """Delete a topic by name (idempotent)."""
        # SMM answers a DELETE of an unknown topic with a 500, so check first
        exists = self.api_client.get(
            f"{self.TOPICS_PATH}/{quote(name, safe='')}",
            squelch={404: None},
        )
        if not exists:
            return None

        self.api_client.delete(
            self.TOPICS_PATH,
            params={"topicName": [name]},
        )


def extract_topic_params(module_instance) -> Dict[str, Any]:
    """Extract the mutable topic parameters from a module instance into a dict."""
    return {
        "name": getattr(module_instance, "name", None),
        "partitions": getattr(module_instance, "partitions", None),
        "replication_factor": getattr(module_instance, "replication_factor", None),
        "configs": normalize_topic_configs(getattr(module_instance, "configs", None)),
    }
