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
)

from ansible_collections.cloudera.services.plugins.modules import smm_kafka_topic_info

REQUIRED_ENV_VARS = [
    "SMM_API_URL",
    "SMM_API_USERNAME",
    "SMM_API_PASSWORD",
]


@pytest.fixture
def smm_module_args(module_args, env_context) -> Callable[[dict], None]:
    """Fixture to set common module args for SMM Kafka topic info tests."""

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


def test_smm_kafka_topic_info_module_by_name(smm_module_args, existing_smm_topic):
    """Test SmmKafkaTopicInfoModule retrieves a topic by name."""
    smm_module_args({"name": existing_smm_topic.name})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert len(result["topics"]) == 1

    topic = result["topics"][0]
    assert topic["name"] == existing_smm_topic.name
    assert topic["partitions"] == 1
    assert topic["replication_factor"] == 1
    # SMM also reports values it derives from retention.ms (e.g. retention.hours)
    assert topic["configs"]["retention.ms"] == "86400000"
    assert topic["internal"] is False
    assert len(topic["partition_details"]) == 1


def test_smm_kafka_topic_info_module_list_all(smm_module_args, existing_smm_topic):
    """Test SmmKafkaTopicInfoModule lists every topic, including the test one."""
    smm_module_args()

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False

    by_name = {topic["name"]: topic for topic in result["topics"]}
    assert existing_smm_topic.name in by_name
    assert by_name[existing_smm_topic.name]["configs"]["retention.ms"] == "86400000"


def test_smm_kafka_topic_info_module_by_name_not_found(
    smm_module_args,
    smm_topic_name,
):
    """Test SmmKafkaTopicInfoModule returns an empty list for an unknown topic."""
    smm_module_args({"name": smm_topic_name("info-missing")})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert result["topics"] == []


def test_smm_kafka_topic_info_module_check_mode(smm_module_args, existing_smm_topic):
    """Test SmmKafkaTopicInfoModule returns topics in check mode."""
    smm_module_args({"name": existing_smm_topic.name, "_ansible_check_mode": True})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic_info.main()

    result = e.value
    assert result["changed"] is False
    assert [topic["name"] for topic in result["topics"]] == [existing_smm_topic.name]
