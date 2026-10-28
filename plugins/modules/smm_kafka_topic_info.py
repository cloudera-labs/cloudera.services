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
module: smm_kafka_topic_info
short_description: Retrieve Kafka topic details from Streams Messaging Manager
description:
  - Retrieve details of a specific Kafka topic by name.
  - If no name is provided, retrieves all Kafka topics.
  - The module supports C(check_mode).
version_added: "1.1.0"
author:
  - "Ronald Suplina (@rsuplina)"
options:
  name:
    description:
      - Name of the Kafka topic.
      - If the topic does not exist, an empty list is returned.
    type: str
    required: false
extends_documentation_fragment:
  - cloudera.services.services_client
"""

EXAMPLES = r"""
# NOTE: Examples do not include connection and authentication fields

- name: Retrieve a Kafka topic by name
  cloudera.services.smm_kafka_topic_info:
    name: "orders"

- name: Retrieve all Kafka topics
  cloudera.services.smm_kafka_topic_info:
"""

RETURN = r"""
topics:
  description:
    - List of Kafka topics matching the given criteria, or all topics if no filter is applied.
  type: list
  elements: dict
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
      returned: when the topic has at least one partition
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
      returned: always
    partition_details:
      description:
        - Leader, replicas and in-sync replicas of every partition.
      type: list
      elements: dict
      returned: always
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
            - Brokers holding a replica of the partition, in the same format as O(topics[].partition_details[].leader).
          type: list
          elements: dict
          returned: always
        isr:
          description:
            - Brokers whose replica is in sync, in the same format as O(topics[].partition_details[].leader).
          type: list
          elements: dict
          returned: always
"""

from typing import Any, Dict, List

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    ServicesModule,
    to_dict,
)
from ansible_collections.cloudera.services.plugins.module_utils.smm import (
    SmmKafkaTopic,
    SmmKafkaTopicClient,
)


class SmmKafkaTopicInfoModule(ServicesModule):
    def __init__(self):
        super().__init__(
            argument_spec=dict(
                name=dict(type="str", required=False),
            ),
            supports_check_mode=True,
        )

        # Set parameters
        self.name = self.get_param("name")

        # Initialize result variables
        self.topic_list: List[SmmKafkaTopic] = []

    def process(self) -> None:
        client = SmmKafkaTopicClient(self.api_client)

        if self.name:
            topic = client.get_topic(self.name)
            if topic:
                self.topic_list.append(topic)

        else:
            self.topic_list.extend(client.list_topics())


def main():
    result = SmmKafkaTopicInfoModule()

    output: Dict[str, Any] = dict(
        changed=False,
        topics=[to_dict(topic) for topic in result.topic_list],
    )

    if result.debug_log:
        output.update(
            sdk_out=result.log_out,
            sdk_out_lines=result.log_lines,
        )

    result.module.exit_json(**output)


if __name__ == "__main__":
    main()
