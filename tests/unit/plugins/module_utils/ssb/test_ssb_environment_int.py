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

import json
import logging
import os
import pytest
import re

from typing import Dict, Generator, Callable
from unittest.mock import Mock

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    NULLABLE,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbEnvironment,
    SsbEnvironmentFile,
    SsbEnvironmentRequest,
    SsbEnvironmentSecuredProperty,
)
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleExitJson,
    AnsibleFailJson,
)

REQUIRED_ENV_VARS = [
    "SSB_SSE_API_URL",
    "SSB_SSE_API_USERNAME",
    "SSB_SSE_API_PASSWORD",
]

ENVIRONMENT_FILE = os.path.join(os.path.dirname(__file__), "sample_environment.json")
ENVIRONMENT_FILE_SENSITIVE = os.path.join(
    os.path.dirname(__file__),
    "sample_environment_sensitive.json",
)

ENVIRONMENT_DATA = {
    "name": "sample_environment",
    "properties": {
        "prop1": {
            "value": "value1",
            "sensitive": False,
        },
    },
}
ENVIRONMENT_DATA_SENSITIVE = {
    "name": "sample_environment",
    "properties": {
        "prop1": {
            "value": "value1",
            "sensitive": False,
        },
        "prop2": {
            "value": "value2",
            "sensitive": True,
        },
    },
}

log = logging.getLogger("ssb_conftest")


@pytest.fixture
def ansible_module(env_context) -> Mock:
    """Fixture to create a mock AnsibleModule for the SSB endpoint."""
    module = Mock()
    module.params = {}
    module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "fail_json called"}),
    )
    module.exit_json = Mock(
        side_effect=AnsibleExitJson({"msg": "exit_json called"}),
    )

    module.params.update(
        {
            "url_username": env_context["SSB_SSE_API_USERNAME"],
            "url_password": env_context["SSB_SSE_API_PASSWORD"],
        },
    )
    return module


@pytest.fixture
def purge_environment(
    environment_client,
) -> Generator[Callable[[str, SsbEnvironment], SsbEnvironment], None, None]:
    """Fixture to purge a test environment after the test."""
    environments: Dict[str, SsbEnvironment] = {}

    def _add_environment(
        project_id: str,
        environment: SsbEnvironment,
    ) -> SsbEnvironment:
        environments.update({project_id: environment})
        return environment

    yield _add_environment

    # Clean up after the test
    for project_id, environment in environments.items():
        try:
            environment_client.delete_environment(
                project_id=project_id,
                environment_id=environment.id,
            )
        except Exception as e:
            log.info(
                f"Failed to delete environment {environment.id} during cleanup: {str(e)}",
            )


@pytest.fixture
def existing_environment(
    request,
    environment_client,
    existing_project,
    purge_environment,
) -> Generator[SsbEnvironment, None, None]:
    """Fixture to create a test SSB Environment and clean it up after the test."""
    environment_name = request.node.name.lower()

    # Clean up any existing test environments with the same name
    environments = environment_client.list_environments(existing_project.id)
    for environment in environments:
        if environment.name == environment_name:
            environment_client.delete_environment(
                environment.project_id,
                environment.id,
            )

    environment = environment_client.create_environment(
        project_id=existing_project.id,
        environment=SsbEnvironmentRequest(
            name=environment_name,
            properties={
                "prop1": SsbEnvironmentSecuredProperty(value="value1"),
                "prop2": SsbEnvironmentSecuredProperty(value="value2", sensitive=True),
            },
        ),
    )

    # Register the environment for cleanup
    purge_environment(existing_project.id, environment)

    yield environment


@pytest.fixture
def deactivate_environment(
    environment_client,
    existing_project,
) -> Generator[None, None, None]:
    """Fixture to deactivate the active SSB environment after the test."""
    yield

    environment_client.deactivate_environment(
        project_id=existing_project.id,
    )


@pytest.fixture
def active_environment(
    environment_client,
    existing_project,
    existing_environment,
    deactivate_environment,
) -> SsbEnvironment:
    """Fixture to return an active SSB environment."""
    environment_client.activate_environment(
        project_id=existing_project.id,
        environment_id=existing_environment.id,
    )

    return existing_environment


def test_create_environment(
    request,
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    purge_environment,
):
    """Test creating an Environment"""
    ssb_rest_client.module = ansible_module

    environment_name = request.node.name.lower()

    # Create the test environment
    environment = environment_client.create_environment(
        project_id=existing_project.id,
        environment=SsbEnvironmentRequest(
            name=environment_name,
            properties={
                "prop1": SsbEnvironmentSecuredProperty(value="value1"),
                "prop2": SsbEnvironmentSecuredProperty(value="value2", sensitive=True),
            },
        ),
    )

    # Register the data source for cleanup
    purge_environment(existing_project.id, environment)

    assert isinstance(environment, SsbEnvironment)
    assert environment.name == environment_name
    assert "prop1" in environment.secured_props
    assert environment.secured_props["prop1"].value == "value1"
    assert not environment.secured_props["prop1"].sensitive
    assert "prop2" in environment.secured_props
    assert environment.secured_props["prop2"].value == "******"
    assert environment.secured_props["prop2"].sensitive


def test_create_environment_existing(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
):
    """Test creating a Hive Data Source"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Environment already exists"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.create_environment(
            project_id=existing_project.id,
            environment=SsbEnvironmentRequest(
                name=existing_environment.name,
                properties={
                    "prop1": SsbEnvironmentSecuredProperty(value="value1"),
                    "prop2": SsbEnvironmentSecuredProperty(
                        value="value2",
                        sensitive=True,
                    ),
                },
            ),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        rf"\[400\] Environment with the name `{existing_environment.name}` already exists",
        call_args.kwargs["msg"],
    )


def test_describe_environment(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
):
    """Test describing an Environment"""
    ssb_rest_client.module = ansible_module

    environment = environment_client.describe_environment(
        project_id=existing_project.id,
        environment_id=existing_environment.id,
    )

    assert isinstance(environment, SsbEnvironment)
    assert environment.id == existing_environment.id
    assert environment.name == existing_environment.name


def test_describe_environment_nonexistent(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test describing an Environment that does not exist"""
    ssb_rest_client.module = ansible_module

    environment = environment_client.describe_environment(
        project_id=existing_project.id,
        environment_id=12345,
    )

    assert environment is None


def test_describe_environment_nonexistent_project(
    environment_client,
    ansible_module,
    ssb_rest_client,
):
    """Test describing an Environment with a non-existent project"""
    ssb_rest_client.module = ansible_module

    environment = environment_client.describe_environment(
        project_id="nonexistent-project-id-12345",
        environment_id=12345,
    )

    assert environment is None


def test_list_environments(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
):
    """Test listing Environments"""
    ssb_rest_client.module = ansible_module

    environments = environment_client.list_environments(
        project_id=existing_project.id,
    )

    assert isinstance(environments, list)
    assert len(environments) == 1
    assert isinstance(environments[0], SsbEnvironment)
    assert environments[0].id == existing_environment.id


def test_list_environments_nonexistent_project(
    environment_client,
    ansible_module,
    ssb_rest_client,
):
    """Test listing Environments"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project does not exists"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.list_environments(
            project_id="nonexistent-project-id-12345",
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )


def test_delete_environment(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
):
    """Test deleting an Environment"""
    ssb_rest_client.module = ansible_module

    environment_client.delete_environment(
        project_id=existing_project.id,
        environment_id=existing_environment.id,
    )

    # Verify the environment is deleted
    environment = environment_client.describe_environment(
        project_id=existing_project.id,
        environment_id=existing_environment.id,
    )

    assert environment is None


def test_delete_environment_nonexistent_project(
    environment_client,
    ansible_module,
    ssb_rest_client,
):
    """Test deleting an Environment"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project does not exists"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.delete_environment(
            project_id="nonexistent-project-id-12345",
            environment_id=12345,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )


def test_update_environment(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
):
    """Test updating an Environment"""
    ssb_rest_client.module = ansible_module

    updated_environment = environment_client.update_environment(
        project_id=existing_project.id,
        environment_id=existing_environment.id,
        environment=SsbEnvironmentRequest(
            name=existing_environment.name,
            properties={
                "prop1": SsbEnvironmentSecuredProperty(value="new_value1"),
                "prop3": SsbEnvironmentSecuredProperty(value="value3", sensitive=True),
            },
        ),
    )

    assert isinstance(updated_environment, SsbEnvironment)
    assert updated_environment.id == existing_environment.id
    assert "prop1" in updated_environment.secured_props
    assert updated_environment.secured_props["prop1"].value == "new_value1"
    assert not updated_environment.secured_props["prop1"].sensitive
    assert "prop2" not in updated_environment.secured_props
    assert "prop3" in updated_environment.secured_props
    assert updated_environment.secured_props["prop3"].value == "******"
    assert updated_environment.secured_props["prop3"].sensitive


def test_update_environment_nonexistent_project(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_environment,
):
    """Test updating an Environment"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project does not exists"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.update_environment(
            project_id="nonexistent-project-id-12345",
            environment_id=existing_environment.id,
            environment=SsbEnvironmentRequest(
                name=existing_environment.name,
                properties={
                    "prop1": SsbEnvironmentSecuredProperty(value="new_value1"),
                    "prop3": SsbEnvironmentSecuredProperty(
                        value="value3",
                        sensitive=True,
                    ),
                },
            ),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )


def test_activate_environment(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
    ssb_project_client,
    deactivate_environment,
):
    """Test activating an Environment"""
    ssb_rest_client.module = ansible_module

    environment_client.activate_environment(
        project_id=existing_project.id,
        environment_id=existing_environment.id,
    )

    # Verify the environment is activated
    project = ssb_project_client.describe_project(existing_project.id)
    assert project.active_environment == existing_environment.id


def test_activate_environment_already_active(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    active_environment,
    ssb_project_client,
):
    """Test activating an Environment that is already active"""
    ssb_rest_client.module = ansible_module

    # Activate the environment again
    environment_client.activate_environment(
        project_id=existing_project.id,
        environment_id=active_environment.id,
    )

    # Verify no errors occurred and the environment is still active
    project = ssb_project_client.describe_project(existing_project.id)

    assert project.active_environment == active_environment.id


def test_activate_environment_nonexistent(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test activating a non-existent Environment"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Environment not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.activate_environment(
            project_id=existing_project.id,
            environment_id=12345,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Environment 12345 not found in active project",
        call_args.kwargs["msg"],
    )


def test_activate_environment_nonexistent_project(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_environment,
):
    """Test activating an Environment"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project does not exists"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.activate_environment(
            project_id="nonexistent-project-id-12345",
            environment_id=existing_environment.id,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )


def test_deactivate_environment(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    active_environment,
    ssb_project_client,
):
    """Test deactivating an Environment"""
    ssb_rest_client.module = ansible_module

    environment_client.deactivate_environment(
        project_id=existing_project.id,
    )

    # Verify the environment is deactivated
    project = ssb_project_client.describe_project(existing_project.id)
    assert project.active_environment is NULLABLE


def test_deactivate_environment_not_active(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    ssb_project_client,
):
    """Test deactivating an Environment when no Environment is active"""
    ssb_rest_client.module = ansible_module

    # Deactivate when no environment is active
    environment_client.deactivate_environment(
        project_id=existing_project.id,
    )

    # Verify no errors occurred and no environment is active
    project = ssb_project_client.describe_project(existing_project.id)
    assert project.active_environment is NULLABLE


def test_deactivate_environment_nonexistent_project(
    environment_client,
    ansible_module,
    ssb_rest_client,
):
    """Test deactivating an Environment"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project does not exists"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.deactivate_environment(
            project_id="nonexistent-project-id-12345",
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )


def test_export_environment(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
):
    """Test exporting an Environment"""
    ssb_rest_client.module = ansible_module

    export_data = environment_client.export_environment(
        project_id=existing_project.id,
        environment_id=existing_environment.id,
    )

    assert isinstance(export_data, SsbEnvironmentFile)
    assert export_data.name == existing_environment.name
    assert "prop1" in export_data.properties
    assert export_data.properties["prop1"].value == "value1"
    assert export_data.properties["prop1"].sensitive is False
    assert "prop2" not in export_data.properties
    assert export_data.metadata.project_name == existing_project.name


def test_export_environment_nonexistent_project(
    environment_client,
    ansible_module,
    ssb_rest_client,
):
    """Test exporting an Environment"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Project not found"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.export_environment(
            project_id="nonexistent-project-id-12345",
            environment_id=12345,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[404\] Project with id nonexistent-project-id-12345 doesn't exist",
        call_args.kwargs["msg"],
    )


def test_import_environment_file(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    purge_environment,
):
    """Test importing an Environment"""
    ssb_rest_client.module = ansible_module

    environment = environment_client.import_environment(
        project_id=existing_project.id,
        environment_file=ENVIRONMENT_FILE,
    )

    # Register the environment for cleanup
    purge_environment(existing_project.id, environment)

    assert isinstance(environment, SsbEnvironment)
    assert environment.name == "sample_environment"
    assert len(environment.secured_props) == 1
    assert "prop1" in environment.secured_props
    assert environment.secured_props["prop1"].value == "value1"
    assert not environment.secured_props["prop1"].sensitive


def test_import_environment_file_sensitive(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test importing an Environment with sensitive properties"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Cannot import sensitive properties"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.import_environment(
            project_id=existing_project.id,
            environment_file=ENVIRONMENT_FILE_SENSITIVE,
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[400\] Environment files must not contain sensitive properties",
        call_args.kwargs["msg"],
    )


def test_import_environment_data(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    purge_environment,
):
    """Test importing an Environment"""
    ssb_rest_client.module = ansible_module

    environment = environment_client.import_environment(
        project_id=existing_project.id,
        environment_data=json.dumps(ENVIRONMENT_DATA).encode("utf-8"),
    )

    # Register the environment for cleanup
    purge_environment(existing_project.id, environment)

    assert isinstance(environment, SsbEnvironment)
    assert environment.name == "sample_environment"
    assert len(environment.secured_props) == 1
    assert "prop1" in environment.secured_props
    assert environment.secured_props["prop1"].value == "value1"
    assert not environment.secured_props["prop1"].sensitive


def test_import_environment_data_sensitive(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
):
    """Test importing an Environment with sensitive properties"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Cannot import sensitive properties"}),
    )

    with pytest.raises(AnsibleFailJson):
        environment_client.import_environment(
            project_id=existing_project.id,
            environment_data=json.dumps(ENVIRONMENT_DATA_SENSITIVE).encode("utf-8"),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        r"\[400\] Environment files must not contain sensitive properties",
        call_args.kwargs["msg"],
    )


def test_import_environment_existing(
    environment_client,
    ansible_module,
    ssb_rest_client,
    existing_project,
    existing_environment,
):
    """Test importing an Environment that already exists"""
    ssb_rest_client.module = ansible_module
    ssb_rest_client.module.fail_json = Mock(
        side_effect=AnsibleFailJson({"msg": "Environment already exists"}),
    )

    existing_environment_data = ENVIRONMENT_DATA.copy()
    existing_environment_data["name"] = existing_environment.name

    with pytest.raises(AnsibleFailJson):
        environment_client.import_environment(
            project_id=existing_project.id,
            environment_data=json.dumps(existing_environment_data).encode("utf-8"),
        )

    call_args = ssb_rest_client.module.fail_json.call_args
    assert call_args is not None
    assert "msg" in call_args.kwargs
    assert re.match(
        rf"\[400\] Environment with the name `{existing_environment.name}` already exists",
        call_args.kwargs["msg"],
    )
