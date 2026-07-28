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

from ansible_collections.cloudera.services.plugins.modules import ssb_user
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbUser,
)

BASE_URL = "https://api.cloudera.internal"


def test_ssb_user_module_set_project(module_args, mocker):
    """Test SsbUserModule setting active project."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
            project_id="old-project-456",
        ),
    )

    mock_set_project = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.set_current_user_project",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
            project_id="new-project-789",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "new-project-789",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is True
    assert result["user"]["project_id"] == "new-project-789"

    mock_get_current_user.assert_called_once()
    mock_set_project.assert_called_once_with("new-project-789")


def test_ssb_user_module_set_project_idempotent(module_args, mocker):
    """Test SsbUserModule setting same project (idempotent)."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
            project_id="project-789",
        ),
    )

    mock_set_project = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.set_current_user_project",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "project-789",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is False
    assert result["user"]["project_id"] == "project-789"

    mock_get_current_user.assert_called_once()
    mock_set_project.assert_not_called()


def test_ssb_user_module_change_password(module_args, mocker):
    """Test SsbUserModule changing password."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
        ),
    )

    mock_set_password = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.set_current_user_password",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "current_password": "old-password",
            "new_password": "new-password",
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is True
    assert result["user"]["username"] == "testuser"

    mock_get_current_user.assert_called_once()
    mock_set_password.assert_called_once_with("old-password", "new-password")


def test_ssb_user_module_no_changes(module_args, mocker):
    """Test SsbUserModule with no parameters (no changes)."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
            project_id="project-789",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is False
    assert result["user"]["username"] == "testuser"

    mock_get_current_user.assert_called_once()


def test_ssb_user_module_check_mode_set_project(module_args, mocker):
    """Test SsbUserModule in check mode when setting project."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
            project_id="old-project",
        ),
    )

    mock_set_project = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.set_current_user_project",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "new-project",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is True
    assert result["user"]["project_id"] == "old-project"  # Not changed in check mode

    mock_get_current_user.assert_called_once()
    mock_set_project.assert_not_called()


def test_ssb_user_module_check_mode_change_password(module_args, mocker):
    """Test SsbUserModule in check mode when changing password."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
        ),
    )

    mock_set_password = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.set_current_user_password",
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "current_password": "old-password",
            "new_password": "new-password",
            "_ansible_check_mode": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is True

    mock_get_current_user.assert_called_once()
    mock_set_password.assert_not_called()


def test_ssb_user_module_diff_mode_set_project(module_args, mocker):
    """Test SsbUserModule with diff mode when setting project."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
            project_id="old-project",
        ),
    )

    mock_set_project = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.set_current_user_project",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
            project_id="new-project",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "project_id": "new-project",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"]["project_id"] == "old-project"
    assert result["diff"]["after"]["project_id"] == "new-project"

    mock_get_current_user.assert_called_once()
    mock_set_project.assert_called_once_with("new-project")


def test_ssb_user_module_diff_mode_change_password(module_args, mocker):
    """Test SsbUserModule with diff mode when changing password."""
    mock_get_current_user = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.get_current_user",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
        ),
    )

    mock_set_password = mocker.patch(
        "ansible_collections.cloudera.services.plugins.modules.ssb_user.SsbUserClient.set_current_user_password",
        return_value=SsbUser(
            id="user-123",
            username="testuser",
        ),
    )

    module_args(
        {
            "endpoint": BASE_URL,
            "current_password": "old-password",
            "new_password": "new-password",
            "_ansible_diff": True,
        },
    )

    with pytest.raises(AnsibleExitJson) as e:
        ssb_user.main()

    result = e.value
    assert result["changed"] is True
    assert "diff" in result
    assert result["diff"]["before"]["password"] == "***"
    assert result["diff"]["after"]["password"] == "***"

    mock_get_current_user.assert_called_once()
    mock_set_password.assert_called_once_with("old-password", "new-password")


def test_ssb_user_module_password_requires_both(module_args):
    """Test that current_password and new_password must be provided together."""
    module_args(
        {
            "endpoint": BASE_URL,
            "current_password": "old-password",
        },
    )

    with pytest.raises(
        AnsibleFailJson,
        match="parameters are required together: current_password, new_password",
    ):
        ssb_user.main()
