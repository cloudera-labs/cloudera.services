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

from ansible_collections.cloudera.services.plugins.modules import ml_runtime
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    MlRuntimeRegistration,
    MlRuntimeValidation,
)

BASE_URL = "https://ml-workspace.example.com"
API_KEY = "test-api-key"

RUNTIMES = (
    "ansible_collections.cloudera.services.plugins.modules.ml_runtime.MlRuntimeClient"
)


def _base_args(overrides=None):
    args = {"url": BASE_URL, "api_key": API_KEY}
    if overrides:
        args.update(overrides)
    return args


def test_register(module_args, mocker):
    """Registering a runtime reports changed on insert."""
    mock_register = mocker.patch(
        f"{RUNTIMES}.register_runtime",
        return_value=MlRuntimeRegistration(
            validation_success=True,
            insert_success=True,
            details={"editor": "PBJ"},
        ),
    )
    mock_validate = mocker.patch(f"{RUNTIMES}.validate_runtime")

    module_args(_base_args({"image_url": "registry.example.com/rt:1"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime.main()

    assert e.value["changed"] is True
    mock_register.assert_called_once_with("registry.example.com/rt:1", None)
    mock_validate.assert_not_called()


def test_register_validate_first(module_args, mocker):
    """validate=true validates before registering."""
    mock_validate = mocker.patch(
        f"{RUNTIMES}.validate_runtime",
        return_value=MlRuntimeValidation(success=True),
    )
    mock_register = mocker.patch(
        f"{RUNTIMES}.register_runtime",
        return_value=MlRuntimeRegistration(
            validation_success=True,
            insert_success=True,
        ),
    )

    module_args(
        _base_args({"image_url": "registry.example.com/rt:1", "validate": True}),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime.main()

    assert e.value["changed"] is True
    mock_validate.assert_called_once()
    mock_register.assert_called_once()


def test_register_validation_fails(module_args, mocker):
    """A failed validation aborts before registering."""
    mocker.patch(
        f"{RUNTIMES}.validate_runtime",
        return_value=MlRuntimeValidation(success=False, reason="bad image"),
    )
    mock_register = mocker.patch(f"{RUNTIMES}.register_runtime")

    module_args(
        _base_args({"image_url": "registry.example.com/rt:1", "validate": True}),
    )

    with pytest.raises(AnsibleFailJson, match="bad image"):
        ml_runtime.main()

    mock_register.assert_not_called()


def test_register_already_exists(module_args, mocker):
    """An already-registered runtime reports no change."""
    mocker.patch(
        f"{RUNTIMES}.register_runtime",
        return_value=MlRuntimeRegistration(
            validation_success=True,
            insert_success=False,
            reason="already exists",
        ),
    )

    module_args(_base_args({"image_url": "registry.example.com/rt:1"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime.main()

    assert e.value["changed"] is False


def test_status_by_image(module_args, mocker):
    """Setting status by image identifier updates and reports changed."""
    mock_status = mocker.patch(f"{RUNTIMES}.update_runtime_status", return_value=1)

    module_args(
        _base_args(
            {"image_identifier": "registry.example.com/rt:1", "status": "DISABLED"},
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime.main()

    assert e.value["changed"] is True
    mock_status.assert_called_once_with(
        "DISABLED",
        runtime_id=None,
        image_identifier=["registry.example.com/rt:1"],
    )


def test_status_no_rows_is_idempotent(module_args, mocker):
    """A status change affecting no rows reports no change."""
    mocker.patch(f"{RUNTIMES}.update_runtime_status", return_value=0)

    module_args(_base_args({"runtime_id": 5, "status": "ENABLED"}))

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime.main()

    assert e.value["changed"] is False


def test_status_requires_target(module_args, mocker):
    """status without image_identifier/runtime_id fails."""
    mocker.patch(f"{RUNTIMES}.update_runtime_status")

    module_args(_base_args({"status": "DISABLED"}))

    with pytest.raises(AnsibleFailJson, match="image_identifier.*runtime_id"):
        ml_runtime.main()


def test_check_mode_register(module_args, mocker):
    """Check mode does not register."""
    mock_register = mocker.patch(f"{RUNTIMES}.register_runtime")

    module_args(
        _base_args(
            {"image_url": "registry.example.com/rt:1", "_ansible_check_mode": True},
        ),
    )

    with pytest.raises(AnsibleExitJson) as e:
        ml_runtime.main()

    assert e.value["changed"] is True
    mock_register.assert_not_called()


def test_requires_one_of(module_args, mocker):
    """One of image_url/status is required."""
    module_args(_base_args())

    with pytest.raises(AnsibleFailJson):
        ml_runtime.main()
