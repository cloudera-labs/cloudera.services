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

from ansible_collections.cloudera.services.plugins.modules import smm_kafka_topic
from ansible_collections.cloudera.services.plugins.module_utils.smm import (
    SmmKafkaTopic,
)

BASE_URL = "https://smm.example"

CLIENT = "ansible_collections.cloudera.services.plugins.modules.smm_kafka_topic.SmmKafkaTopicClient"

CONNECTION = {
    "endpoint": BASE_URL,
    "url_username": "admin",
    "url_password": "changeme",
}


def _existing_topic(**overrides):
    values = dict(
        name="orders",
        partitions=2,
        replication_factor=2,
        configs={"retention.ms": "604800000"},
        internal=False,
        partition_details=[],
    )
    values.update(overrides)
    return SmmKafkaTopic(**values)


def test_smm_kafka_topic_module_create_minimal(module_args, mocker):
    """Test SmmKafkaTopicModule creating a new topic with the required fields only."""
    mock_get = mocker.patch(f"{CLIENT}.get_topic", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_topic",
        return_value=_existing_topic(configs={}),
    )

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 2,
            "replication_factor": 2,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["name"] == "orders"
    assert result["topic"]["partitions"] == 2
    assert result["topic"]["replication_factor"] == 2
    assert "diff" not in result

    mock_get.assert_called_once_with("orders")
    mock_create.assert_called_once()

    sent = mock_create.call_args[0][0]
    assert sent.name == "orders"
    assert sent.partitions == 2
    assert sent.replication_factor == 2


def test_smm_kafka_topic_module_create_full(module_args, mocker):
    """Test SmmKafkaTopicModule creating a new topic with configs, converted to strings."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_topic",
        return_value=_existing_topic(
            configs={"retention.ms": "604800000", "cleanup.policy": "compact"},
        ),
    )

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 2,
            "replication_factor": 2,
            "configs": {"retention.ms": 604800000, "cleanup.policy": "compact"},
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["configs"] == {
        "retention.ms": "604800000",
        "cleanup.policy": "compact",
    }

    sent = mock_create.call_args[0][0]
    assert sent.configs == {"retention.ms": "604800000", "cleanup.policy": "compact"}


def test_smm_kafka_topic_module_create_partitions_alias(module_args, mocker):
    """Test the num_partitions alias sets the partition count."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=None)
    mock_create = mocker.patch(
        f"{CLIENT}.create_topic",
        return_value=_existing_topic(partitions=4),
    )

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "num_partitions": 4,
            "replication_factor": 2,
        },
    )

    with pytest.raises(AnsibleExitJson):
        smm_kafka_topic.main()

    assert mock_create.call_args[0][0].partitions == 4


@pytest.mark.parametrize(
    "missing",
    [
        {"replication_factor": 2},
        {"partitions": 2},
        {},
    ],
)
def test_smm_kafka_topic_module_create_requires_partitions_and_replication_factor(
    module_args,
    mocker,
    missing,
):
    """Test creating a topic fails when partitions or replication_factor is missing."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_topic")

    module_args({**CONNECTION, "name": "orders", **missing})

    with pytest.raises(AnsibleFailJson) as e:
        smm_kafka_topic.main()

    assert "partitions" in e.value["msg"]
    assert "replication_factor" in e.value["msg"]
    mock_create.assert_not_called()


def test_smm_kafka_topic_module_create_check_mode(module_args, mocker):
    """Test SmmKafkaTopicModule create in check mode does not call the API."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=None)
    mock_create = mocker.patch(f"{CLIENT}.create_topic")

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 3,
            "replication_factor": 1,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["name"] == "orders"
    assert result["topic"]["partitions"] == 3

    mock_create.assert_not_called()


def test_smm_kafka_topic_module_create_diff_mode(module_args, mocker):
    """Test SmmKafkaTopicModule create in diff mode reports before/after."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=None)
    mocker.patch(f"{CLIENT}.create_topic", return_value=_existing_topic())

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 2,
            "replication_factor": 2,
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"] == {}
    assert result["diff"]["after"]["name"] == "orders"
    assert result["diff"]["after"]["partitions"] == 2


def test_smm_kafka_topic_module_present_no_changes(module_args, mocker):
    """Test SmmKafkaTopicModule present with no drift is a no-op."""
    existing = _existing_topic()
    mock_get = mocker.patch(f"{CLIENT}.get_topic", return_value=existing)
    mock_create = mocker.patch(f"{CLIENT}.create_topic")
    mock_update = mocker.patch(f"{CLIENT}.update_topic")

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 2,
            "replication_factor": 2,
            "configs": {"retention.ms": 604800000},
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is False
    assert result["topic"]["name"] == "orders"
    assert result["topic"]["partitions"] == 2

    mock_get.assert_called_once_with("orders")
    mock_create.assert_not_called()
    mock_update.assert_not_called()


def test_smm_kafka_topic_module_present_name_only_is_a_no_op(module_args, mocker):
    """Test an existing topic is left alone when only the name is given."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mock_update = mocker.patch(f"{CLIENT}.update_topic")

    module_args({**CONNECTION, "name": "orders"})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_smm_kafka_topic_module_update_partitions(module_args, mocker):
    """Test SmmKafkaTopicModule increasing the partitions of an existing topic."""
    existing = _existing_topic()
    mocker.patch(f"{CLIENT}.get_topic", return_value=existing)
    mock_update = mocker.patch(
        f"{CLIENT}.update_topic",
        return_value=_existing_topic(partitions=6),
    )

    module_args({**CONNECTION, "name": "orders", "partitions": 6})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["partitions"] == 6

    mock_update.assert_called_once()
    sent_existing, sent_incoming = mock_update.call_args[0]
    assert sent_existing is existing
    assert sent_incoming.partitions == 6
    assert sent_incoming.replication_factor == 2
    assert sent_incoming.configs == {"retention.ms": "604800000"}


def test_smm_kafka_topic_module_update_configs_keeps_other_overrides(
    module_args,
    mocker,
):
    """Test listed configs are changed and the other topic-level overrides are kept."""
    existing = _existing_topic(
        configs={"retention.ms": "604800000", "cleanup.policy": "delete"},
    )
    mocker.patch(f"{CLIENT}.get_topic", return_value=existing)
    mock_update = mocker.patch(
        f"{CLIENT}.update_topic",
        return_value=_existing_topic(),
    )

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "configs": {"retention.ms": 1000, "max.message.bytes": 2048},
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is True

    sent_incoming = mock_update.call_args[0][1]
    assert sent_incoming.configs == {
        "retention.ms": "1000",
        "cleanup.policy": "delete",
        "max.message.bytes": "2048",
    }


def test_smm_kafka_topic_module_update_changed_config_drops_derived_value(
    module_args,
    mocker,
):
    """Test a changed retention.ms is not sent next to the stale derived retention.hours."""
    existing = _existing_topic(
        configs={"retention.ms": "86400000", "retention.hours": "24"},
    )
    mocker.patch(f"{CLIENT}.get_topic", return_value=existing)
    mock_update = mocker.patch(
        f"{CLIENT}.update_topic",
        return_value=_existing_topic(configs={"retention.ms": "3600000"}),
    )

    module_args(
        {**CONNECTION, "name": "orders", "configs": {"retention.ms": 3600000}},
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is True
    assert mock_update.call_args[0][1].configs == {"retention.ms": "3600000"}


def test_smm_kafka_topic_module_present_no_changes_with_derived_value(
    module_args,
    mocker,
):
    """Test a topic whose retention.ms is already set is a no-op despite retention.hours."""
    existing = _existing_topic(
        configs={"retention.ms": "86400000", "retention.hours": "24"},
    )
    mocker.patch(f"{CLIENT}.get_topic", return_value=existing)
    mock_update = mocker.patch(f"{CLIENT}.update_topic")

    module_args(
        {**CONNECTION, "name": "orders", "configs": {"retention.ms": 86400000}},
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is False
    mock_update.assert_not_called()


def test_smm_kafka_topic_module_update_check_mode(module_args, mocker):
    """Test SmmKafkaTopicModule update in check mode does not call the API."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mock_update = mocker.patch(f"{CLIENT}.update_topic")

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 4,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"]["partitions"] == 4

    mock_update.assert_not_called()


def test_smm_kafka_topic_module_update_diff_mode(module_args, mocker):
    """Test SmmKafkaTopicModule update in diff mode reports only the changed fields."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mocker.patch(f"{CLIENT}.update_topic", return_value=_existing_topic(partitions=4))

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 4,
            "configs": {"retention.ms": "1000"},
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["diff"]["before"]["partitions"] == 2
    assert result["diff"]["after"]["partitions"] == 4
    assert result["diff"]["before"]["configs"] == {"retention.ms": "604800000"}
    assert result["diff"]["after"]["configs"] == {"retention.ms": "1000"}
    assert "replication_factor" not in result["diff"]["after"]


def test_smm_kafka_topic_module_update_decrease_partitions_fails(module_args, mocker):
    """Test decreasing the partitions of an existing topic fails."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mock_update = mocker.patch(f"{CLIENT}.update_topic")

    module_args({**CONNECTION, "name": "orders", "partitions": 1})

    with pytest.raises(AnsibleFailJson) as e:
        smm_kafka_topic.main()

    assert "Cannot decrease the partitions" in e.value["msg"]
    mock_update.assert_not_called()


def test_smm_kafka_topic_module_update_decrease_partitions_fails_in_check_mode(
    module_args,
    mocker,
):
    """Test an impossible change is also reported as a failure in check mode."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "partitions": 1,
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleFailJson) as e:
        smm_kafka_topic.main()

    assert "Cannot decrease the partitions" in e.value["msg"]


def test_smm_kafka_topic_module_update_replication_factor_fails(module_args, mocker):
    """Test changing the replication factor of an existing topic fails."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mock_update = mocker.patch(f"{CLIENT}.update_topic")

    module_args({**CONNECTION, "name": "orders", "replication_factor": 3})

    with pytest.raises(AnsibleFailJson) as e:
        smm_kafka_topic.main()

    assert "Cannot change the replication factor" in e.value["msg"]
    mock_update.assert_not_called()


def test_smm_kafka_topic_module_delete_existing(module_args, mocker):
    """Test SmmKafkaTopicModule deleting an existing topic."""
    mock_get = mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mock_delete = mocker.patch(f"{CLIENT}.delete_topic", return_value=None)

    module_args({**CONNECTION, "name": "orders", "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["topic"] == {}
    assert "diff" not in result

    mock_get.assert_called_once_with("orders")
    mock_delete.assert_called_once_with("orders")


def test_smm_kafka_topic_module_delete_nonexistent(module_args, mocker):
    """Test SmmKafkaTopicModule deleting a topic that does not exist is a no-op."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=None)
    mock_delete = mocker.patch(f"{CLIENT}.delete_topic")

    module_args({**CONNECTION, "name": "orders", "state": "absent"})

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is False
    assert result["topic"] == {}

    mock_delete.assert_not_called()


def test_smm_kafka_topic_module_delete_check_mode(module_args, mocker):
    """Test SmmKafkaTopicModule delete in check mode does not call the API."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mock_delete = mocker.patch(f"{CLIENT}.delete_topic")

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "state": "absent",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    assert e.value["changed"] is True

    mock_delete.assert_not_called()


def test_smm_kafka_topic_module_delete_diff_mode(module_args, mocker):
    """Test SmmKafkaTopicModule delete in diff mode reports before/after."""
    mocker.patch(f"{CLIENT}.get_topic", return_value=_existing_topic())
    mocker.patch(f"{CLIENT}.delete_topic", return_value=None)

    module_args(
        {
            **CONNECTION,
            "name": "orders",
            "state": "absent",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        smm_kafka_topic.main()

    result = e.value
    assert result["changed"] is True
    assert result["diff"]["before"]["name"] == "orders"
    assert result["diff"]["before"]["partitions"] == 2
    assert result["diff"]["after"] == {}


def test_smm_kafka_topic_module_missing_name_fails(module_args, mocker):
    """Test SmmKafkaTopicModule fails fast when name is not provided."""
    mock_get = mocker.patch(f"{CLIENT}.get_topic")

    module_args(CONNECTION)

    with pytest.raises(AnsibleFailJson):
        smm_kafka_topic.main()

    mock_get.assert_not_called()
