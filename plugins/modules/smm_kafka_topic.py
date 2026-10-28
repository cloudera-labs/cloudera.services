#!/usr/bin/python
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

DOCUMENTATION = r"""
module: smm_kafka_topic
short_description: Manage Kafka topics in Streams Messaging Manager
description:
  - Create, update, or delete Kafka topics through Cloudera Streams Messaging Manager (SMM).
  - An existing topic can have its partitions increased and its topic-level configs changed.
  - Kafka cannot decrease the partitions or change the replication factor of an existing topic,
    so the module fails if either is requested.
author:
  - "Ronald Suplina (@rsuplina)"
version_added: "1.1.0"
options:
  name:
    description:
      - Name of the Kafka topic.
    required: true
    type: str
  partitions:
    description:
      - Number of partitions of the topic.
      - Required when the topic is created.
      - On an existing topic the number can only be increased.
    type: int
    required: false
    aliases:
      - num_partitions
  replication_factor:
    description:
      - Number of replicas of each partition.
      - Required when the topic is created.
      - It cannot be changed on an existing topic.
    type: int
    required: false
  configs:
    description:
      - A dictionary of topic-level configuration overrides, for example C(retention.ms) or C(cleanup.policy).
      - Values are converted to strings before they are sent to Kafka.
      - Only the listed configs are set, other topic-level overrides already present on the topic are kept.
      - SMM derives an hours variant for some configs, for example C(retention.hours) for C(retention.ms).
        When you change one of them, the old derived value is not sent back, so SMM recalculates it.
      - Config names are sent to SMM verbatim.
    type: dict
    required: false
  state:
    description:
      - Whether the topic should be present or absent.
    type: str
    required: false
    default: present
    choices: ["present", "absent"]
extends_documentation_fragment:
  - cloudera.services.services_client
attributes:
  check_mode:
    description:
      - This module supports check mode.
    support: full
  diff_mode:
    description:
      - This module supports diff mode.
    support: full
    platforms:
      - all
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields

- name: Create a Kafka topic
  cloudera.services.smm_kafka_topic:
    name: "orders"
    partitions: 3
    replication_factor: 2
    configs:
      retention.ms: 604800000
      cleanup.policy: "delete"

- name: Increase the partitions and change a config of an existing topic
  cloudera.services.smm_kafka_topic:
    name: "orders"
    partitions: 6
    configs:
      retention.ms: 86400000

- name: Delete a Kafka topic
  cloudera.services.smm_kafka_topic:
    name: "orders"
    state: "absent"
"""

RETURN = r"""
topic:
  description:
    - A dictionary containing details about the topic.
    - Empty when the topic is absent.
  type: dict
  returned: always
  contains:
    name:
      description:
        - Name of the topic.
      type: str
      returned: always
    partitions:
      description:
        - Number of partitions of the topic.
      type: int
      returned: always
    replication_factor:
      description:
        - Number of replicas of each partition.
      type: int
      returned: when the topic has at least one partition or the replication factor was requested
    configs:
      description:
        - Topic-level configuration overrides.
        - Settings inherited from the broker or built-in defaults are not included.
        - SMM can also report values it derives from a set config, such as C(retention.hours) for C(retention.ms).
      type: dict
      returned: always
    internal:
      description:
        - Whether the topic is a Kafka internal topic.
      type: bool
      returned: when the topic exists
    partition_details:
      description:
        - Leader, replicas and in-sync replicas of every partition.
      type: list
      elements: dict
      returned: when the topic exists
      contains:
        partition:
          description:
            - Partition number.
          type: int
          returned: always
        leader:
          description:
            - Broker currently leading the partition.
          type: dict
          returned: always
          contains:
            id:
              description:
                - Broker ID.
              type: int
              returned: always
            host:
              description:
                - Broker host name.
              type: str
              returned: always
            port:
              description:
                - Broker port.
              type: int
              returned: always
            rack:
              description:
                - Rack of the broker.
              type: str
              returned: always
            is_controller:
              description:
                - Whether the broker is the cluster controller.
              type: bool
              returned: always
        replicas:
          description:
            - Brokers holding a replica of the partition, in the same format as O(topic.partition_details[].leader).
          type: list
          elements: dict
          returned: always
        isr:
          description:
            - Brokers whose replica is in sync, in the same format as O(topic.partition_details[].leader).
          type: list
          elements: dict
          returned: always
"""

from typing import Any, Dict, Optional

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
    ServicesModule,
    build_from_params,
    diff_dict,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.smm import (
    SmmKafkaTopic,
    SmmKafkaTopicClient,
    extract_topic_params,
    merge_topic_configs,
    validate_topic_update,
)


class SmmKafkaTopicModule(ServicesModule):
    def __init__(self):
        argument_spec = SmmKafkaTopic.argument_spec()
        argument_spec["name"]["required"] = True

        super().__init__(
            argument_spec=dict(
                **argument_spec,
                state=dict(
                    type="str",
                    choices=["present", "absent"],
                    default="present",
                ),
            ),
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")
        self.partitions = self.get_param("partitions")
        self.replication_factor = self.get_param("replication_factor")
        self.configs = self.get_param("configs")
        self.state = self.get_param("state")

        # Initialize result variables
        self.changed = False
        self.diff = {}
        self.topic: Optional[SmmKafkaTopic] = None

    def process(self) -> None:
        client = SmmKafkaTopicClient(self.api_client)

        existing = client.get_topic(self.name)

        if self.state == "absent":
            if existing:
                self.changed = True

                if self.module._diff:
                    self.diff = {"before": to_dict(existing), "after": {}}

                if not self.module.check_mode:
                    client.delete_topic(existing.name)

        else:
            params = extract_topic_params(self)

            if not existing:
                if params["partitions"] is None or params["replication_factor"] is None:
                    self.module.fail_json(
                        msg="Both 'partitions' and 'replication_factor' are required to create a topic.",
                    )

                incoming = build_from_params(SmmKafkaTopic, params)

                self.changed = True

                if self.module._diff:
                    self.diff = {"before": {}, "after": to_dict(incoming)}

                if not self.module.check_mode:
                    self.topic = client.create_topic(incoming)
                else:
                    self.topic = incoming

            else:
                # Only the listed configs are managed, keep the other overrides
                if params["configs"] is not None and existing.configs not in (
                    NULLABLE,
                    None,
                ):
                    params["configs"] = merge_topic_configs(
                        existing.configs,
                        params["configs"],
                    )

                incoming = build_from_params(
                    SmmKafkaTopic,
                    params,
                    existing=existing,
                )

                validate_topic_update(existing, incoming)

                prev_config, next_config = diff_dict(existing, incoming)

                if prev_config or next_config:
                    self.changed = True

                    if self.module._diff:
                        self.diff = {
                            "before": prev_config,
                            "after": next_config,
                        }

                    if not self.module.check_mode:
                        self.topic = client.update_topic(existing, incoming)
                    else:
                        self.topic = incoming
                else:
                    self.topic = existing


def main():
    result = SmmKafkaTopicModule()

    output: Dict[str, Any] = dict(
        changed=result.changed,
        topic=to_dict(result.topic) if result.topic else {},
    )

    if result.module._diff:
        output.update(diff=result.diff)

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
