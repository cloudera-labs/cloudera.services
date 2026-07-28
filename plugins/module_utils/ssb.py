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
REST clients for the Cloudera SQL Stream Builder (SSB) API.
"""

import json
import re

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ansible.module_utils.common.dict_transformations import snake_dict_to_camel_dict

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    from_dict,
    to_dict,
    NULLABLE,
    ServicesClient,
)


@dataclass
class SsbUser:
    """Configuration for SSB users."""

    id: str
    username: str
    email: Union[str, None, NULLABLE] = NULLABLE
    first_name: Union[str, None, NULLABLE] = NULLABLE
    last_name: Union[str, None, NULLABLE] = NULLABLE
    is_active: Union[bool, None, NULLABLE] = NULLABLE
    primary_project_id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    keytab: Union[str, None, NULLABLE] = NULLABLE
    keytab_principal: Union[str, None, NULLABLE] = NULLABLE
    keytab_last_modified: Union[str, None, NULLABLE] = NULLABLE
    granted_authorities: Union[List[str], None, NULLABLE] = NULLABLE


class SsbUserClient:
    """Cloudera SSB User API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client: ServicesClient = api_client

    def get_current_user(self) -> SsbUser:
        """
        Get information about the current authenticated user.
        """
        return from_dict(SsbUser, self.api_client.get("/api/v2/user"))

    def set_current_user_project(self, project_id: str) -> SsbUser:
        """Set the project for the current user."""
        return from_dict(
            SsbUser,
            self.api_client.patch(
                "/api/v2/user/project",
                data={"project_id": project_id},
            ),
        )

    def set_current_user_password(
        self,
        current_password: str,
        new_password: str,
    ) -> SsbUser:
        """Set the password for the current user."""
        return from_dict(
            SsbUser,
            self.api_client.patch(
                "/api/v2/user/password",
                data={
                    "current_password": current_password,
                    "new_password": new_password,
                },
            ),
        )


class SSBUserProjectsClient:
    """Cloudera SSB User Projects API client."""

    # def get_active_project(self) -> Dict[str, Any]:
    #     """Get the currently active project of the current user."""
    #     user_info = self.get_user()
    #     active_project_id = user_info.get("project_id")
    #     project_info = self.api_client.get(f"/api/v2/project/{active_project_id}")
    #     return project_info

    # def get_projects(self, project: Optional[str] = None) -> List[Dict[str, Any]]:
    #     """Get project(s) of the current user."""
    #     # Get the user
    #     user_info = self.get_user()
    #     user_id = user_info.get("id")

    #     # Retrieve permissioned projects
    #     permissions = self.api_client.get(
    #         "/api/v2/project-permissions",
    #         dict(user_id=user_id),
    #     )
    #     return [
    #         p["project"]
    #         for p in permissions["project_permissions"]
    #         if project is None
    #         or p["project"]["name"] == project
    #         or p["project"]["id"] == project
    #     ]


@dataclass
class SsbUserKeytab:
    principal: str


class SsbUserKeytabClient:
    """Cloudera SSB User Keytab API client."""

    def __init__(self, api_client: ServicesClient):
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client = api_client

    def delete_keytab(self) -> None:
        """Delete the keytab for the current user."""
        self.api_client.delete(
            "/api/v2/user/keytab",
        )

    def generate_keytab(self, principal: str, password: str) -> SsbUserKeytab:
        """Generate a keytab for the current user."""
        self.api_client.post(
            "/api/v2/user/keytab/generate",
            data={
                "principal": principal,
                "password": password,
            },
            squelch={
                200: None,  # Keytab generated successfully (emulate HTTP 204)
                400: {},  # Keytab already exists
            },
        )
        return SsbUserKeytab(principal=principal)

    def upload_keytab(
        self,
        principal: str,
        keytab_file: Optional[str] = None,
        keytab_data: Optional[bytes] = None,
    ) -> SsbUserKeytab:
        """Upload a keytab for the current user."""

        if (keytab_file is None) == (keytab_data is None):
            raise ValueError("Provide either keytab_file or keytab_data, not both.")

        file_payload = {}

        if keytab_file:
            file_payload.update(filename=keytab_file)
        else:
            file_payload.update(content=keytab_data)

        self.api_client.post(
            "/api/v2/user/keytab/upload",
            data={
                "principal": principal,
                "file": file_payload,
            },
            format="multipart",
            squelch={
                200: None,  # Keytab generated successfully (emulate HTTP 204)
                400: {},  # Keytab already exists
            },
        )

        return SsbUserKeytab(principal=principal)


@dataclass
class SsbSyncSourceCredential:
    """Configuration for project sync source credentials."""

    type: str
    username: Union[str, None, NULLABLE] = NULLABLE
    password: Union[str, None, NULLABLE] = NULLABLE
    ssh_private_key: Union[str, None, NULLABLE] = NULLABLE
    ssh_public_key: Union[str, None, NULLABLE] = NULLABLE
    ssh_passphrase: Union[str, None, NULLABLE] = NULLABLE

    def __post_init__(self):
        """Validate the credential fields based on type."""
        if self.type == "basic":
            if not self.username or not self.password:
                raise ValueError("Basic credentials require username and password.")
        elif self.type == "ssh":
            if not self.ssh_private_key or not self.ssh_public_key:
                raise ValueError("SSH credentials require private and public keys.")
        else:
            raise ValueError(f"Unsupported credential type: {self.type}")

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            type=dict(type="str", required=True),
            username=dict(type="str", required=False),
            password=dict(type="str", required=False, no_log=True),
            ssh_private_key=dict(type="str", required=False, no_log=True),
            ssh_public_key=dict(type="str", required=False),
            ssh_passphrase=dict(type="str", required=False, no_log=True),
        )


@dataclass
class SsbSyncSourceConfig:
    """Configuration for project sync source."""

    type: str
    clone_url: str
    branch: Union[str, None, NULLABLE] = NULLABLE
    allow_deletions: Union[bool, None, NULLABLE] = NULLABLE
    credential: Union[SsbSyncSourceCredential, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            type=dict(type="str", required=True),
            clone_url=dict(type="str", required=True),
            branch=dict(type="str", required=False),
            allow_deletions=dict(type="bool", required=False),
            credential=dict(
                type="dict",
                required=False,
                options=SsbSyncSourceCredential.argument_spec(),
            ),
        )


@dataclass
class SsbProject:
    """Configuration for SSB projects."""

    name: str
    id: Union[str, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    mv_prefix: Union[str, None, NULLABLE] = NULLABLE
    sync_source_config: Union[SsbSyncSourceConfig, None, NULLABLE] = NULLABLE
    active_environment: Union[int, None, NULLABLE] = NULLABLE

    @classmethod
    def argument_spec(cls) -> Dict[str, Any]:
        """Return the argument spec for Ansible module parameters."""
        return dict(
            name=dict(type="str", required=False),
            id=dict(type="str", required=False, aliases=["project_id"]),
            description=dict(type="str", required=False),
            mv_prefix=dict(type="str", required=False),
            sync_source_config=dict(
                type="dict",
                required=False,
                options=SsbSyncSourceConfig.argument_spec(),
            ),
            # Environments should not be set directly in the project module
            # active_environment=dict(type="str", required=False),
        )


class SsbProjectClient:
    """Cloudera SSB Project API client."""

    def __init__(self, api_client: ServicesClient):
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client = api_client

    def list_projects(self) -> List[SsbProject]:
        """List all projects available to the current user.

        This method retrieves all SQL Stream Builder (SSB) projects that the current
        authenticated user has access to from the SSB API.

        Returns:
            List[SsbProject]: A list of SsbProject objects representing all available
                projects for the current user. Returns an empty list if no projects
                are found or accessible.
        """
        results = self.api_client.get(
            "/api/v2/projects",
        )
        return [from_dict(SsbProject, project) for project in results]

    def create_project(self, project: SsbProject) -> SsbProject:
        """Create a new project in the SSB (SQL Stream Builder) service.

        Args:
            project (SsbProject): The project object containing the configuration
                and metadata for the new project to be created.

        Returns:
            SsbProject: The created project object with updated information from
                the server, including any generated IDs or timestamps.
        """
        results = self.api_client.post(
            "/api/v2/projects",
            data=to_dict(project),
        )
        return from_dict(SsbProject, results)

    def import_project(self, project: SsbProject) -> SsbProject:
        """Import a project from a source control repository.

        Creates a new project in the SSB (Streaming SQL Builder) environment by importing
        it from an external source control repository. The project configuration and
        metadata are sent to the SSB API for processing.

        Args:
            project (SsbProject): The project object containing the configuration
                and metadata for the project to be imported. This includes repository
                details, branch information, and other import settings.

        Returns:
            SsbProject: The imported project object with updated information from
                the SSB service, including any generated IDs, timestamps, or other
                server-assigned metadata.
        """
        results = self.api_client.post(
            f"/api/v2/projects/import",
            data=to_dict(project),
        )
        return from_dict(SsbProject, results)

    def describe_project(self, project_id: str) -> Optional[SsbProject]:
        """Get details of a specific project by ID.

        Args:
            project_id (str): The unique identifier of the project to retrieve.

        Returns:
            Optional[SsbProject]: An SsbProject object containing the project details, or None if the project does not exist.
        """
        results = self.api_client.get(
            f"/api/v2/projects/{project_id}",
            squelch={404: None},  # Project not found
        )
        return from_dict(SsbProject, results)

    def delete_project(self, project: SsbProject) -> None:
        """Delete a specific project by ID.

        Args:
            project (SsbProject): The project object to delete.

        Returns:
            None
        """
        self.api_client.delete(
            f"/api/v2/projects/{project.id}",
        )


@dataclass
class SsbUdfArtifact:
    """Configuration for UDF JAR files."""

    name: Union[str, None, NULLABLE] = NULLABLE
    storage_path: Union[str, None, NULLABLE] = NULLABLE
    scope: Union[str, None, NULLABLE] = NULLABLE
    id: Union[int, None, NULLABLE] = NULLABLE
    user_id: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE

    SCOPES = {"USER", "PROJECT", "GLOBAL"}

    def __post_init__(self):
        """Validate the artifact fields."""
        if self.scope is not None and self.scope not in self.SCOPES:
            valid_scopes = ", ".join(sorted(self.SCOPES))
            raise ValueError(
                f"Unsupported artifact scope: {self.scope}. "
                f"Must be one of: {valid_scopes}",
            )


@dataclass
class SsbUdf:
    """Configuration for SSB UDFs."""

    name: str
    project_id: str
    output_type: str
    id: Union[int, None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE
    language: Union[str, None, NULLABLE] = NULLABLE
    input_types: Union[List[str], None, NULLABLE] = NULLABLE
    code: Union[str, None, NULLABLE] = NULLABLE
    java_class_name: Union[str, None, NULLABLE] = NULLABLE
    jar_file: Union[SsbUdfArtifact, None, NULLABLE] = NULLABLE
    file_name: Union[str, None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE

    LANGUAGE_TYPES = {"JAVASCRIPT", "PYTHON"}

    JAVASCRIPT_TYPES = {
        "STRING",
        "BOOLEAN",
        "INT",
        "BIGINT",
        "FLOAT",
        "DECIMAL",
        "TIMESTAMP",
        "DATE",
    }

    PYTHON_TYPES = {"PYTHON_INFERRED"}

    def __post_init__(self):
        """Validate the UDF fields."""
        if (
            not isinstance(self.language, type(NULLABLE))
            and self.language is not None
            and self.language not in self.LANGUAGE_TYPES
        ):
            valid_languages = ", ".join(sorted(self.LANGUAGE_TYPES))
            raise ValueError(
                f"Unsupported UDF language: {self.language}. "
                f"Must be one of: {valid_languages}",
            )

        if self.language == "JAVASCRIPT":
            # Check output_type
            if self.output_type not in self.JAVASCRIPT_TYPES:
                valid_types = ", ".join(sorted(self.JAVASCRIPT_TYPES))
                raise ValueError(
                    f"Javascript UDFs require a valid output_type. "
                    f"Supported types are: {valid_types}",
                )

            # Check input_types
            if isinstance(self.input_types, list) and not all(
                t in self.JAVASCRIPT_TYPES for t in self.input_types
            ):
                valid_types = ", ".join(sorted(self.JAVASCRIPT_TYPES))
                raise ValueError(
                    f"Javascript UDFs require valid input_types. "
                    f"Supported types are: {valid_types}",
                )
        elif self.language == "PYTHON":
            # Check output_type
            if self.output_type not in self.PYTHON_TYPES:
                valid_types = ", ".join(sorted(self.PYTHON_TYPES))
                raise ValueError(
                    f"Python UDFs require a valid output_type. "
                    f"Supported types are: {valid_types}",
                )

            # Check input_types (none at the moment)


@dataclass
class SsbUdfTestParameter:
    """Configuration for UDF test parameters."""

    name: str
    type: str
    value: Any


@dataclass
class SsbUdfTestRun:
    """Configuration for UDF test runs."""

    udf_name: str
    output_type: str
    param_types: Union[List[str], None, NULLABLE] = NULLABLE
    code: Union[str, None, NULLABLE] = NULLABLE
    test_values: Union[List[SsbUdfTestParameter], None, NULLABLE] = NULLABLE


@dataclass
class SsbUdfRunResult:
    """Configuration for UDF run results."""

    result: Union[Any, None, NULLABLE] = NULLABLE


class SsbUdfClient:
    """Cloudera SSB UDF API client."""

    def __init__(self, api_client: ServicesClient):
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client = api_client

    def create_udf(self, udf: SsbUdf) -> SsbUdf:
        """
        Create a User Defined Function (UDF) in the specified project.
        Args:
            udf (SsbUdf): The UDF object containing the configuration and metadata
                          for the UDF to be created. Must include a valid project_id.
        Returns:
            SsbUdf: The created UDF object with updated information from the server,
                    including any server-generated fields like ID or timestamps.
        """
        return from_dict(
            SsbUdf,
            self.api_client.post(
                f"/api/v2/projects/{udf.project_id}/udfs",
                data=to_dict(udf),
            ),
        )

    def describe_udf(self, project_id: str, udf_id: int) -> Optional[SsbUdf]:
        """
        Retrieve detailed information about a specific User Defined Function (UDF).

        Args:
            project_id (str): The unique identifier of the project containing the UDF.
            udf_id (int): The unique identifier of the UDF to describe.

        Returns:
            Optional[SsbUdf]: An SsbUdf object containing the detailed information about the UDF, or None if not found.
        """
        return from_dict(
            SsbUdf,
            self.api_client.get(
                f"/api/v2/projects/{project_id}/udfs/{udf_id}",
                squelch={404: None},  # UDF not found
            ),
        )

    def list_udfs(self, project_id: str) -> List[SsbUdf]:
        """
        List all User Defined Functions (UDFs) for a specific project.

        Args:
            project_id (str): The unique identifier of the project to retrieve UDFs from.

        Returns:
            List[SsbUdf]: A list of SsbUdf objects representing all UDFs in the project.
        """
        return [
            from_dict(SsbUdf, udf)
            for udf in self.api_client.get(
                f"/api/v2/projects/{project_id}/udfs",
            )
        ]

    def update_udf(self, udf: SsbUdf) -> SsbUdf:
        """
        Update an existing User Defined Function (UDF) in a Streaming SQL Builder project.

        Args:
            udf (SsbUdf): The UDF object containing updated configuration and metadata
                         including the project_id where the UDF belongs.

        Returns:
            SsbUdf: The updated UDF object with the latest configuration from the server.
        """
        return from_dict(
            SsbUdf,
            self.api_client.put(
                f"/api/v2/projects/{udf.project_id}/udfs",
                data=to_dict(udf),
            ),
        )

    def delete_udf(self, project_id: str, udf_id: int) -> None:
        """
        Delete a User Defined Function (UDF) from a project.

        Args:
            project_id (str): The unique identifier of the project containing the UDF.
            udf_id (int): The unique identifier of the UDF to delete.

        Returns:
            None
        """
        self.api_client.delete(
            f"/api/v2/projects/{project_id}/udfs/{udf_id}",
        )


@dataclass
class SsbCustomLogConfig:
    """
    Configuration class for custom logging in Streaming SQL Builder (SSB).
    This class defines the structure for custom log configuration settings
    used in SSB environments.

    Attributes:
        type (Union[str, None, NULLABLE]): The type of custom log configuration.
            Can be a string specifying the log type, None, or NULLABLE.
        content (Union[str, None, NULLABLE]): The content or configuration details
            for the custom log. Can be a string containing the log configuration,
            None, or NULLABLE.
    """

    type: Union[str, None, NULLABLE] = NULLABLE
    content: Union[str, None, NULLABLE] = NULLABLE


class SsbRuntimeMode(str, Enum):
    """Enumeration of possible SSB runtime modes with set-like membership operations."""

    AUTOMATIC = "AUTOMATIC"
    BATCH = "BATCH"
    STREAMING = "STREAMING"


class SsbExecutionMode(str, Enum):
    """Enumeration of possible SSB execution modes with set-like membership operations."""

    APPLICATION = "APPLICATION"
    PER_JOB = "PER_JOB"
    SESSION = "SESSION"


@dataclass
class SsbRuntimeConfig:
    """
    Configuration for SQL Stream Builder (SSB) job runtime settings.

    This class defines the runtime configuration parameters for SSB jobs, including
    execution modes, parallelism settings, and savepoint management.

    Attributes:
        execution_mode (Union[str, None, NULLABLE]): Flink job YARN execution mode.
            Must be one of: APPLICATION, PER_JOB, SESSION.
        runtime_mode (Union[str, None, NULLABLE]): Flink job runtime mode.
            Must be one of: AUTOMATIC, BATCH, STREAMING.
        parallelism (Union[int, None, NULLABLE]): Flink job parallelism.
        sample_interval (Union[int, None, NULLABLE]): SSB result sampling interval in ms.
        sample_count (Union[int, None, NULLABLE]): SSB result sampling record count.
        window_size (Union[int, None, NULLABLE]): SSB result sampling window size.
        start_with_savepoint (Union[bool, None, NULLABLE]): Whether to start the Flink job from a savepoint.
        savepoint_directory_path (Union[str, None, NULLABLE]): Flink job savepoint directory path.
        log_config (Union[SsbCustomLogConfig, None, NULLABLE]): Custom logging configuration.

    Class Attributes:
        EXECUTION_MODE (set): Valid execution modes - SESSION, PER_JOB, APPLICATION.
        RUNTIME_MODE (set): Valid runtime modes - STREAMING, BATCH, AUTOMATIC.

    Raises:
        ValueError: If execution_mode is not one of the supported values.
    """

    execution_mode: Union[str, None, NULLABLE] = NULLABLE
    runtime_mode: Union[str, None, NULLABLE] = NULLABLE
    parallelism: Union[int, None, NULLABLE] = NULLABLE
    sample_interval: Union[int, None, NULLABLE] = NULLABLE
    sample_count: Union[int, None, NULLABLE] = NULLABLE
    window_size: Union[int, None, NULLABLE] = NULLABLE
    start_with_savepoint: Union[bool, None, NULLABLE] = NULLABLE
    savepoint_directory_path: Union[str, None, NULLABLE] = NULLABLE
    log_config: Union[SsbCustomLogConfig, None, NULLABLE] = NULLABLE

    VALID_EXECUTION_MODES = {mode.value for mode in SsbExecutionMode}
    VALID_RUNTIME_MODES = {mode.value for mode in SsbRuntimeMode}

    def __post_init__(self):
        """Validate the runtime fields."""
        if (
            not isinstance(self.execution_mode, type(NULLABLE))
            and self.execution_mode is not None
            and self.execution_mode not in self.VALID_EXECUTION_MODES
        ):
            valid_modes = ", ".join(sorted(self.VALID_EXECUTION_MODES))
            raise ValueError(
                f"Unsupported execution mode: {self.execution_mode}. "
                f"Must be one of: {valid_modes}",
            )

        if (
            not isinstance(self.runtime_mode, type(NULLABLE))
            and self.runtime_mode is not None
            and self.runtime_mode not in self.VALID_RUNTIME_MODES
        ):
            valid_modes = ", ".join(sorted(self.VALID_RUNTIME_MODES))
            raise ValueError(
                f"Unsupported runtime mode: {self.runtime_mode}. "
                f"Must be one of: {valid_modes}",
            )


@dataclass
class SsbMaterializedViewConfig:
    """
    Configuration class for SQL Stream Builder (SSB) Materialized Views.

    This class defines the configuration parameters for creating and managing
    materialized views in Cloudera's SQL Stream Builder service.

    Attributes:
        name (str): The name of the materialized view.
        key_column_name (str): The name of the column to use as the primary key.
        api_key (str): API key for authentication with the SSB service.
        retention (Union[int, None, NULLABLE], optional): Data retention period in days.
            Defaults to NULLABLE.
        min_row_retention_count (Union[int, None, NULLABLE], optional): Minimum number
            of rows to retain regardless of retention period. Defaults to NULLABLE.
        recreate (Union[bool, None, NULLABLE], optional): Whether to recreate the
            materialized view if it already exists. Defaults to NULLABLE.
        column_indices_disabled (bool, optional): Whether to disable column indexing.
            Defaults to False.
        indexed_columns (Union[List[str], None, NULLABLE], optional): List of columns
            to create indexes on. Defaults to NULLABLE.
        not_indexed_columns (Union[List[str], None, NULLABLE], optional): List of
            columns to exclude from indexing. Defaults to NULLABLE.
        ignore_nulls (Union[bool, None, NULLABLE], optional): Whether to ignore null
            values in the materialized view. Defaults to NULLABLE.
        batch_size (Union[int, None, NULLABLE], optional): Batch size for processing
            data updates. Defaults to NULLABLE.
        enabled (Union[bool, None, NULLABLE], optional): Whether the materialized
            view is enabled. Defaults to NULLABLE.

    Raises:
        ValueError: If both indexed_columns and not_indexed_columns are specified,
            as these options are mutually exclusive.

    Note:
        NULLABLE is a special sentinel value used to distinguish between None
        (explicitly set to null) and unset parameters.
    """

    name: str
    key_column_name: str
    api_key: str
    retention: Union[int, None, NULLABLE] = NULLABLE
    min_row_retention_count: Union[int, None, NULLABLE] = NULLABLE
    recreate: Union[bool, None, NULLABLE] = NULLABLE
    column_indices_disabled: bool = False
    indexed_columns: Union[List[str], None, NULLABLE] = NULLABLE
    not_indexed_columns: Union[List[str], None, NULLABLE] = NULLABLE
    ignore_nulls: Union[bool, None, NULLABLE] = NULLABLE
    batch_size: Union[int, None, NULLABLE] = NULLABLE
    enabled: Union[bool, None, NULLABLE] = NULLABLE

    def __post_init__(self):
        """Validate the materialized view fields."""
        if self.indexed_columns and self.not_indexed_columns:
            raise ValueError(
                "Cannot specify both indexed_columns and not_indexed_columns.",
            )


class SsbCheckpointMode(str, Enum):
    """Enumeration of possible SSB checkpoint modes with set-like membership operations."""

    EXACTLY_ONCE = "EXACTLY_ONCE"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"


class SsbRestartStrategy(str, Enum):
    """Enumeration of possible SSB restart strategies with set-like membership operations."""

    NONE = "none"
    EXPONENTIAL_DELAY = "exponential_delay"


@dataclass
class SsbCheckpointConfig:
    """
    Configuration class for SQL Stream Builder (SSB) checkpoint settings.
    This class manages checkpoint configuration parameters for streaming SQL jobs,
    including validation of checkpoint modes and restart strategies.

    Attributes:
        enable_checkpointing (Union[bool, None, NULLABLE]): Whether to enable checkpointing for the job.
        checkpoint_interval_millis (Union[int, None, NULLABLE]): Time interval between checkpoints in milliseconds.
        checkpoint_timeout_millis (Union[int, None, NULLABLE]): Maximum time to wait for a checkpoint to complete in milliseconds.
        tolerable_checkpoint_failures (Union[int, None, NULLABLE]): Number of checkpoint failures to tolerate before failing the job.
        checkpoint_mode (Union[str, None, NULLABLE]): The checkpoint mode to use. Must be one of the valid checkpoint modes.
        restart_strategy (Union[str, None, NULLABLE]): The restart strategy for job recovery. Must be one of the valid restart strategies.
        exponential_backoff_delay_max_seconds (Union[int, None, NULLABLE]): Maximum delay in seconds for exponential backoff restart strategy.
        checkpoint_directory_path (Union[str, None, NULLABLE]): Directory path where checkpoint data will be stored.
    Class Attributes:
        VALID_CHECKPOINT_MODES (set): Set of valid checkpoint mode values from SsbCheckpointMode enum.
        VALID_RESTART_STRATEGIES (set): Set of valid restart strategy values from SsbRestartStrategy enum.
    Raises:
        ValueError: If checkpoint_mode or restart_strategy contains invalid values during post-initialization validation.
    """

    enable_checkpointing: Union[bool, None, NULLABLE] = NULLABLE
    checkpoint_interval_millis: Union[int, None, NULLABLE] = NULLABLE
    checkpoint_timeout_millis: Union[int, None, NULLABLE] = NULLABLE
    tolerable_checkpoint_failures: Union[int, None, NULLABLE] = NULLABLE
    checkpoint_mode: Union[str, None, NULLABLE] = NULLABLE
    restart_strategy: Union[str, None, NULLABLE] = NULLABLE
    exponential_backoff_delay_max_seconds: Union[int, None, NULLABLE] = NULLABLE
    checkpoint_directory_path: Union[str, None, NULLABLE] = NULLABLE

    VALID_CHECKPOINT_MODES = {mode.value for mode in SsbCheckpointMode}
    VALID_RESTART_STRATEGIES = {mode.value for mode in SsbRestartStrategy}

    def __post_init__(self):
        """Validate the checkpoint fields."""
        if (
            not isinstance(self.checkpoint_mode, type(NULLABLE))
            and self.checkpoint_mode is not None
            and self.checkpoint_mode not in self.VALID_CHECKPOINT_MODES
        ):
            valid_modes = ", ".join(sorted(self.VALID_CHECKPOINT_MODES))
            raise ValueError(
                f"Unsupported checkpoint mode: {self.checkpoint_mode}. "
                f"Must be one of: {valid_modes}",
            )

        if (
            not isinstance(self.restart_strategy, type(NULLABLE))
            and self.restart_strategy is not None
            and self.restart_strategy not in self.VALID_RESTART_STRATEGIES
        ):
            valid_strategies = ", ".join(sorted(self.VALID_RESTART_STRATEGIES))
            raise ValueError(
                f"Unsupported restart strategy: {self.restart_strategy}. "
                f"Must be one of: {valid_strategies}",
            )


@dataclass
class SsbApiEndpoint:
    """
    Represents an API endpoint configuration for SQL Stream Builder (SSB).
    This class defines the structure and validation for SSB API endpoints, including
    endpoint URLs, dynamic parameters, SQL code, and optional configuration data.
    Attributes:
        endpoint (str): The API endpoint URL or path.
        dynamic_parameters (List[str]): List of dynamic parameters for the endpoint.
        code (str): SQL code or query string associated with the endpoint.
        bind_values (Union[List[str], None, NULLABLE], optional): List of bind values
            for parameterized queries. Must match the BIND_VALUE_REGEX pattern.
        builder_data (Union[Dict[str, Any], None, NULLABLE], optional): Additional
            configuration data that will be JSON serialized.
        description (Union[str, None, NULLABLE], optional): Human-readable description
            of the endpoint's purpose.
    Class Attributes:
        BIND_VALUE_REGEX (str): Regular expression pattern for validating bind values.
            Allows alphanumeric characters, underscores, hyphens, dots, and tildes.
    Raises:
        ValueError: If bind_values contain invalid characters that don't match the
            BIND_VALUE_REGEX pattern, or if builder_data cannot be JSON serialized.
    """

    endpoint: str
    dynamic_parameters: List[str]
    code: str
    bind_values: Union[List[str], None, NULLABLE] = NULLABLE
    builder_data: Union[Dict[str, Any], None, NULLABLE] = NULLABLE
    description: Union[str, None, NULLABLE] = NULLABLE

    BIND_VALUE_REGEX = r"[A-Za-z0-9\_\-\.\~]+]"

    def __post_init__(self):
        if isinstance(self.bind_values, list):
            for bind_value in self.bind_values:
                if not re.match(self.BIND_VALUE_REGEX, bind_value):
                    raise ValueError(
                        f"Invalid bind value: {bind_value}. "
                        f"Must match regex: {self.BIND_VALUE_REGEX}",
                    )
        if isinstance(self.builder_data, dict):
            try:
                self.builder_data = json.dumps(self.builder_data)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"builder_data must be JSON serializable. Error: {e}",
                )


@dataclass
class SsbKubernetesResourceConfig:
    """
    Configuration class for Kubernetes resource specifications in SSB (Streaming SQL Builder).

    This class defines the resource limits and requests that can be configured for
    Kubernetes containers running SSB workloads.

    Attributes:
        cpu_request (Union[Decimal, None, NULLABLE]): The minimum amount of CPU resources
            requested for the container. Can be specified as a decimal value representing
            CPU cores (e.g., 0.5 for half a core).
        memory_request (Union[str, None, NULLABLE]): The minimum amount of memory
            requested for the container. Should be specified as a string with units
            (e.g., "512Mi", "1Gi").
        cpu_limit (Union[Decimal, None, NULLABLE]): The maximum amount of CPU resources
            the container can use. Can be specified as a decimal value representing
            CPU cores.
        memory_limit (Union[Decimal, None, NULLABLE]): The maximum amount of memory
            the container can use. Should be specified as a decimal value.
        ephemeral_storage (Union[str, None, NULLABLE]): The amount of ephemeral storage
            available to the container. Should be specified as a string with units
            (e.g., "10Gi", "500Mi").

    Note:
        All attributes support NULLABLE values to indicate explicit null configuration.
    """

    cpu_request: Union[Decimal, None, NULLABLE] = NULLABLE
    memory_request: Union[str, None, NULLABLE] = NULLABLE
    cpu_limit: Union[Decimal, None, NULLABLE] = NULLABLE
    memory_limit: Union[Decimal, None, NULLABLE] = NULLABLE
    ephemeral_storage: Union[str, None, NULLABLE] = NULLABLE


class SsbKubernetesDeploymentMode(str, Enum):
    """Enumeration of possible SSB Kubernetes deployment modes with set-like membership operations."""

    NATIVE = "NATIVE"
    STANDALONE = "STANDALONE"


@dataclass
class SsbKubernetesConfig:
    """Configuration class for SQL Stream Builder (SSB) Kubernetes deployment settings.

    This class manages Kubernetes-specific configuration parameters for SSB deployments,
    including deployment mode, job management settings, and resource configurations.

    Attributes:
        kubernetes_deployment_mode (Union[str, None, NULLABLE]): The Kubernetes deployment
            mode for the SSB job. Must be one of the valid deployment modes defined in
            SsbKubernetesDeploymentMode enum.
        restart_failed_job (Union[bool, None, NULLABLE]): Whether to automatically restart
            failed jobs in the Kubernetes environment.
        job_manager_replicas (Union[int, None, NULLABLE]): Number of job manager replicas
            to deploy in the Kubernetes cluster.
        job_manager_resource_config (Union[SsbKubernetesResourceConfig, None, NULLABLE]):
            Resource configuration settings for the job manager pods.
        task_manager_resource_config (Union[SsbKubernetesResourceConfig, None, NULLABLE]):
            Resource configuration settings for the task manager pods.

    Class Attributes:
        VALID_DEPLOYMENT_MODES (set): Set of valid deployment modes extracted from
            SsbKubernetesDeploymentMode enum values.

    Raises:
        ValueError: If kubernetes_deployment_mode is not None and not in VALID_DEPLOYMENT_MODES.
    """

    kubernetes_deployment_mode: Union[str, None, NULLABLE] = NULLABLE
    restart_failed_job: Union[bool, None, NULLABLE] = NULLABLE
    job_manager_replicas: Union[int, None, NULLABLE] = NULLABLE
    job_manager_resource_config: Union[SsbKubernetesResourceConfig, None, NULLABLE] = (
        NULLABLE
    )
    task_manager_resource_config: Union[SsbKubernetesResourceConfig, None, NULLABLE] = (
        NULLABLE
    )

    VALID_DEPLOYMENT_MODES = {mode.value for mode in SsbKubernetesDeploymentMode}

    def __post_init__(self):
        """Validate the kubernetes fields."""
        if (
            not isinstance(self.kubernetes_deployment_mode, type(NULLABLE))
            and self.kubernetes_deployment_mode is not None
            and self.kubernetes_deployment_mode not in self.VALID_DEPLOYMENT_MODES
        ):
            valid_modes = ", ".join(sorted(self.VALID_DEPLOYMENT_MODES))
            raise ValueError(
                f"Unsupported kubernetes deployment mode: {self.kubernetes_deployment_mode}. "
                f"Must be one of: {valid_modes}",
            )


class SsbBusyTimeAggregator(str, Enum):
    """Enumeration of possible SSB busy time aggregators with set-like membership operations."""

    AVERAGE = "AVG"
    MAXIMUM = "MAX"


@dataclass
class SsbAutoscalerConfig:
    """
    Configuration class for SQL Stream Builder (SSB) autoscaler settings.

    This class defines the configuration parameters for autoscaling SSB jobs,
    including utilization targets, scaling factors, and parallelism constraints.

    Attributes:
        enabled (Union[bool, None, NULLABLE]): Whether autoscaling is enabled.
        busy_time_aggregator (Union[str, None, NULLABLE]): The aggregation method
            for busy time metrics. Must be one of the valid aggregators defined
            in SsbBusyTimeAggregator.
        target_utilization (Union[Decimal, None, NULLABLE]): The target CPU/resource
            utilization percentage for autoscaling decisions.
        target_utilization_boundary (Union[Decimal, None, NULLABLE]): The boundary
            threshold around the target utilization.
        metrics_window (Union[str, None, NULLABLE]): The time window for collecting
            metrics used in autoscaling decisions.
        scale_up_max_factor (Union[Decimal, None, NULLABLE]): Maximum factor by which
            the system can scale up in a single scaling operation.
        scale_down_max_factor (Union[Decimal, None, NULLABLE]): Maximum factor by which
            the system can scale down in a single scaling operation.
        vertex_max_parallelism (Union[int, None, NULLABLE]): Maximum parallelism
            allowed for job vertices.
        vertex_min_parallelism (Union[int, None, NULLABLE]): Minimum parallelism
            required for job vertices.

    Raises:
        ValueError: If busy_time_aggregator is not one of the valid aggregator types.
    """

    enabled: Union[bool, None, NULLABLE] = NULLABLE
    busy_time_aggregator: Union[str, None, NULLABLE] = NULLABLE
    target_utilization: Union[Decimal, None, NULLABLE] = NULLABLE
    target_utilization_boundary: Union[Decimal, None, NULLABLE] = NULLABLE
    metrics_window: Union[str, None, NULLABLE] = NULLABLE
    scale_up_max_factor: Union[Decimal, None, NULLABLE] = NULLABLE
    scale_down_max_factor: Union[Decimal, None, NULLABLE] = NULLABLE
    vertex_max_parallelism: Union[int, None, NULLABLE] = NULLABLE
    vertex_min_parallelism: Union[int, None, NULLABLE] = NULLABLE

    VALID_BUSY_TIME_AGGREGATORS = {mode.value for mode in SsbBusyTimeAggregator}

    def __post_init__(self):
        """Validate the autoscaler fields."""
        if (
            not isinstance(self.busy_time_aggregator, type(NULLABLE))
            and self.busy_time_aggregator is not None
            and self.busy_time_aggregator not in self.VALID_BUSY_TIME_AGGREGATORS
        ):
            valid_aggregators = ", ".join(sorted(self.VALID_BUSY_TIME_AGGREGATORS))
            raise ValueError(
                f"Unsupported busy time aggregator: {self.busy_time_aggregator}. "
                f"Must be one of: {valid_aggregators}",
            )


@dataclass
class SsbJobConfig:
    """
    Configuration class for SQL Stream Builder (SSB) jobs.

    This class encapsulates all configuration options needed to define and configure
    an SSB job, including runtime parameters, checkpointing, materialized views,
    autoscaling, and Kubernetes-specific settings.

    Attributes:
        job_name (str): The name of the SSB job. SQL job names may only contain letters, numbers,
            and underscores and must start with a letter or underscore.
        runtime_config (Union[SsbRuntimeConfig, None, NULLABLE], optional):
            Runtime configuration settings for the job. Defaults to NULLABLE.
        checkpoint_config (Union[SsbCheckpointConfig, None, NULLABLE], optional):
            Checkpoint configuration for job state persistence. Defaults to NULLABLE.
        mv_config (Union[SsbMaterializedViewConfig, None, NULLABLE], optional):
            Configuration for materialized views associated with the job. Defaults to NULLABLE.
        autoscaler_config (Union[SsbAutoscalerConfig, None, NULLABLE], optional):
            Autoscaling configuration for dynamic resource management. Defaults to NULLABLE.
        kubernetes_config (Union[SsbKubernetesConfig, None, NULLABLE], optional):
            Kubernetes-specific configuration settings. Defaults to NULLABLE.
    """

    job_name: str
    runtime_config: Union[SsbRuntimeConfig, None, NULLABLE] = NULLABLE
    checkpoint_config: Union[SsbCheckpointConfig, None, NULLABLE] = NULLABLE
    mv_config: Union[SsbMaterializedViewConfig, None, NULLABLE] = NULLABLE
    autoscaler_config: Union[SsbAutoscalerConfig, None, NULLABLE] = NULLABLE
    kubernetes_config: Union[SsbKubernetesConfig, None, NULLABLE] = NULLABLE

    def __post_init__(self):
        """Validate the job name field."""
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", self.job_name):
            raise ValueError(
                f"Invalid job name: {self.job_name}. "
                "Job names may only contain letters, numbers, and underscores "
                "and must start with a letter or underscore.",
            )


@dataclass
class SsbJobRequest:
    """
    Represents a request to execute SQL in Streaming SQL Builder (SSB).

    This class encapsulates the parameters needed to execute a SQL query in SSB,
    including the SQL statement itself and various execution options.

    Attributes:
        sql (str): The SQL query to be executed.
        selection (Union[bool, None, NULLABLE], optional): Whether to select specific
            parts of the query result. Defaults to NULLABLE.
        job_config (Union[SsbJobConfig, None, NULLABLE], optional): Configuration
            settings for the SQL job execution. Defaults to NULLABLE.
        add_to_history (Union[bool, None, NULLABLE], optional): Whether to add this
            query execution to the query history. Defaults to NULLABLE.
        mv_endpoints (Union[List[SsbApiEndpoint], None, NULLABLE], optional): List of
            materialized view endpoints associated with the query. Defaults to NULLABLE.
    """

    sql: str
    selection: Union[bool, None, NULLABLE] = NULLABLE
    job_config: Union[SsbJobConfig, None, NULLABLE] = NULLABLE
    add_to_history: Union[bool, None, NULLABLE] = NULLABLE
    mv_endpoints: Union[List[SsbApiEndpoint], None, NULLABLE] = NULLABLE


@dataclass
class SsbJob:
    name: str  # Read-only
    sql: str
    start_time: Union[int, None, NULLABLE] = NULLABLE
    end_time: Union[int, None, NULLABLE] = NULLABLE
    state: Union[str, None, NULLABLE] = NULLABLE
    job_id: Union[int, None, NULLABLE] = NULLABLE
    user_id: Union[str, None, NULLABLE] = NULLABLE
    username: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    flink_job_id: Union[str, None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    cluster_id: Union[str, None, NULLABLE] = NULLABLE
    sample_id: Union[str, None, NULLABLE] = NULLABLE
    jm_url: Union[str, None, NULLABLE] = NULLABLE
    mv_endpoints: Union[List[SsbApiEndpoint], None, NULLABLE] = NULLABLE
    mv_config: Union[SsbMaterializedViewConfig, None, NULLABLE] = NULLABLE
    checkpoint_config: Union[SsbCheckpointConfig, None, NULLABLE] = NULLABLE
    kubernetes_config: Union[SsbKubernetesConfig, None, NULLABLE] = NULLABLE
    autoscaler_config: Union[SsbAutoscalerConfig, None, NULLABLE] = NULLABLE
    savepoint_id: Union[int, None, NULLABLE] = NULLABLE


@dataclass
class SsbJobStart:
    """
    Represents the parameters required to start a Streaming SQL Builder (SSB) job.

    Attributes:
        sql (str): The SQL query to execute for the SSB job.
        selection (Union[bool, None, NULLABLE], optional): Indicates whether the job is a selection query.
            Defaults to NULLABLE.
        job_config (Union[SsbJobConfig, None, NULLABLE], optional): Configuration settings for the SSB job.
            Defaults to NULLABLE.
        add_to_history (Union[bool, None, NULLABLE], optional): Whether to add this job to execution history.
            Defaults to NULLABLE.
        mv_endpoints (Union[List[SsbApiEndpoint], None, NULLABLE], optional): List of materialized view endpoints
            associated with the job. Defaults to NULLABLE.
    """

    sql: str
    selection: Union[bool, None, NULLABLE] = NULLABLE
    job_config: Union[SsbJobConfig, None, NULLABLE] = NULLABLE
    add_to_history: Union[bool, None, NULLABLE] = NULLABLE
    mv_endpoints: Union[List[SsbApiEndpoint], None, NULLABLE] = NULLABLE


@dataclass
class SsbJobResponse:
    type: str  # Read-only
    message: Union[str, None, NULLABLE] = NULLABLE
    ssb_job_id: Union[int, None, NULLABLE] = NULLABLE
    job_name: Union[str, None, NULLABLE] = NULLABLE
    flink_job_id: Union[str, None, NULLABLE] = NULLABLE
    sample_id: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class SsbJobStop:
    """
    Represents the configuration for stopping a SQL Stream Builder (SSB) job.

    Attributes:
        savepoint (bool): Flag indicating whether to use a savepoint when stopping the job.
            Defaults to False.
        savepoint_path (Union[str, None, NULLABLE]): The path to the savepoint to restore from.
            Can be a string path, None, or NULLABLE sentinel value. Defaults to NULLABLE.
        timeout (Union[int, None, NULLABLE]): The timeout in seconds for the job stop operation.
            Can be an integer, None, or NULLABLE sentinel value. Defaults to NULLABLE.
    """

    savepoint: bool = False
    savepoint_path: Union[str, None, NULLABLE] = NULLABLE
    timeout: Union[int, None, NULLABLE] = NULLABLE


class SsbJobState(str, Enum):
    """Enumeration of possible SSB job states with set-like membership operations."""

    INITIALIZING = "INITIALIZING"
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    FAILING = "FAILING"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"
    CANCELED = "CANCELED"
    FINISHED = "FINISHED"
    RESTARTING = "RESTARTING"
    SUSPENDED = "SUSPENDED"
    RECONCILING = "RECONCILING"
    STOPPED = "STOPPED"


@dataclass
class SsbJobStateResponse:
    state: str  # Read-only
    sampleId: Union[str, None, NULLABLE] = NULLABLE

    ALL_STATES = {state.value for state in SsbJobState}

    def __post_init__(self):
        """Validate the job state field."""
        if self.state not in self.ALL_STATES:
            valid_states = ", ".join(sorted(self.ALL_STATES))
            raise ValueError(
                f"Invalid job state: {self.state}. " f"Must be one of: {valid_states}",
            )


class SsbJobClient:
    """Cloudera SSB Job API client."""

    READY_STATES = frozenset(
        [
            SsbJobState.RUNNING.value,
            SsbJobState.FAILING.value,
            SsbJobState.RESTARTING.value,
        ],
    )
    TERMINAL_STATES = frozenset(
        [
            SsbJobState.FAILED.value,
            SsbJobState.CANCELED.value,
            SsbJobState.FINISHED.value,
        ],
    )
    ACTIVE_STATES = frozenset(
        [
            SsbJobState.CREATED.value,
            SsbJobState.RUNNING.value,
            SsbJobState.FAILING.value,
            SsbJobState.RESTARTING.value,
        ],
    )
    TRANSITIONING_STATES = frozenset(
        [
            SsbJobState.INITIALIZING.value,
            SsbJobState.CANCELLING.value,
            SsbJobState.RESTARTING.value,
            SsbJobState.RECONCILING.value,
        ],
    )

    def __init__(self, api_client: ServicesClient) -> None:
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client = api_client

    def create_job(
        self,
        project_id: str,
        job: SsbJobRequest,
    ) -> SsbJob:
        return from_dict(
            SsbJob,
            self.api_client.post(
                f"/api/v2/projects/{project_id}/jobs",
                data=to_dict(job),
            ),
        )

    def describe_job(self, project_id: str, job_id: int) -> Optional[SsbJob]:
        """
        Describe a specific job by ID.

        Args:
            project_id (str): The ID of the project.
            job_id (int): The ID of the job to describe.
        """

        return from_dict(
            SsbJob,
            self.api_client.get(
                f"/api/v2/projects/{project_id}/jobs/{job_id}",
                squelch={
                    403: None,  # Job not in project
                    404: None,  # Job not found
                },
            ),
        )

    def list_jobs(self, project_id: str, state: Optional[str] = None) -> List[SsbJob]:
        """
        List all jobs available to the current user for a project.

        Args:
            project_id (str): The ID of the project.
            state (Optional[str]): Filter jobs by state (e.g., SsbJobState.RUNNING, SsbJobState.FAILED).
        """
        params = dict()

        if state:
            if state not in (
                self.READY_STATES
                | self.TERMINAL_STATES
                | self.ACTIVE_STATES
                | self.TRANSITIONING_STATES
            ):
                raise ValueError(f"Invalid job state: {state}")
            else:
                params["state"] = state

        return [
            from_dict(SsbJob, item)
            for item in self.api_client.get(
                f"/api/v2/projects/{project_id}/jobs",
                params=params,
            ).get("jobs", [])
        ]

    def update_job(
        self,
        project_id: str,
        job: SsbJob,
    ) -> SsbJob:
        return from_dict(
            SsbJob,
            self.api_client.put(
                f"/api/v2/projects/{project_id}/jobs/{job.job_id}",
                data=to_dict(job),
            ),
        )

    def delete_job(self, project_id: str, job_id: int) -> None:
        """
        Delete a specific job by ID.

        Args:
            project_id (str): The ID of the project.
            job_id (int): The ID of the job to delete.
        """

        self.api_client.delete(
            f"/api/v2/projects/{project_id}/jobs/{job_id}",
            squelch={
                403: {},  # Job not in project
                404: {},  # Job not found
            },
        )

    def start_job(
        self,
        project_id: str,
        job_id: int,
        config: SsbJobStart,
    ) -> List[SsbJobResponse]:
        """
        Start a new SQL Stream Builder job.

        Args:
            project_id (str): The unique identifier of the project in which to start the job.
            config (SsbJobStart): Configuration options for starting the job, including SQL and job settings.

        Returns:
            List[SsbJobResponse]: The responses from the job start operation.
        """
        return [
            from_dict(SsbJobResponse, response)
            for response in self.api_client.post(
                f"/api/v2/projects/{project_id}/jobs/{job_id}/execute",
                data=to_dict(config),
            ).get("responses", [])
        ]

    def stop_job(
        self,
        project_id: str,
        job_id: int,
        config: SsbJobStop,
    ) -> Union[int, None]:
        """
        Stop a running SQL Stream Builder job.

        Args:
            project_id (str): The unique identifier of the project containing the job.
            job_id (int): The unique identifier of the job to stop.
            config (SsbJobStop): Configuration options for stopping the job, including savepoint settings.

        Returns:
            int: The savepoint ID if a savepoint was created during the stop operation, otherwise None.
        """
        result = self.api_client.post(
            f"/api/v2/projects/{project_id}/jobs/{job_id}/stop",
            data=to_dict(config),
        )

        return result.get("savepoint_id", None)

    def get_job_state(
        self,
        project_id: str,
        job_id: int,
    ) -> SsbJobStateResponse:
        """
        Get the current state of a SQL Stream Builder job.

        Args:
            project_id (str): The unique identifier of the project containing the job.
            job_id (int): The unique identifier of the job.

        Returns:
            SsbJobStateResponse: The current state of the job.
        """
        return from_dict(
            SsbJobStateResponse,
            self.api_client.get(
                f"/api/v2/projects/{project_id}/jobs/{job_id}/state",
            ),
        )


@dataclass
class SsbDataSourceSync:
    name: str
    type: str
    properties: Dict[str, Any]
    id: Union[str, None, NULLABLE] = NULLABLE
    custom_truststore: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class SsbDataSource(SsbDataSourceSync):
    created_at: Union[str, None, NULLABLE] = NULLABLE
    updated_at: Union[str, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class SsbDataSourceValidationResponse:
    number_of_tables: Union[int, None, NULLABLE] = NULLABLE
    error: Union[str, None, NULLABLE] = NULLABLE


class SsbDataSourceClient:
    """Cloudera SSB Data Source API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client = api_client

    def create_data_source(
        self,
        project_id: str,
        data_source: SsbDataSourceSync,
    ) -> SsbDataSource:
        return from_dict(
            SsbDataSource,
            self.api_client.post(
                f"/api/v2/projects/{project_id}/data-sources",
                data=to_dict(data_source),
            ),
        )

    def describe_data_source(
        self,
        project_id: str,
        data_source_id: str,
    ) -> Optional[SsbDataSource]:
        """
        Describe a specific data source by ID.

        Args:
            project_id (str): The ID of the project.
            data_source_id (str): The ID of the data source to describe.
        """

        return from_dict(
            SsbDataSource,
            self.api_client.get(
                f"/api/v2/projects/{project_id}/data-sources/{data_source_id}",
                squelch={
                    403: None,  # Data source not in project
                    404: None,  # Data source not found
                },
            ),
        )

    def list_data_sources(
        self,
        project_id: str,
        kafka: bool = False,
    ) -> List[SsbDataSource]:
        """
        List all data sources available to the current user for a project.

        Args:
            project_id (str): The ID of the project.
            kafka (bool): If True, list Kafka data sources. Defaults to False.
        """
        if kafka:
            return [
                from_dict(SsbDataSource, item)
                for item in self.api_client.get(
                    f"/api/v2/projects/{project_id}/data-sources/kafka",
                )
            ]
        else:
            return [
                from_dict(SsbDataSource, item)
                for item in self.api_client.get(
                    f"/api/v2/projects/{project_id}/data-sources",
                )
            ]

    def update_data_source(
        self,
        project_id: str,
        data_source: SsbDataSource,
    ) -> SsbDataSource:
        """
        Update an existing data source in a SQL Stream Builder project.

        Args:
            project_id (str): The unique identifier of the project containing the data source.
            data_source (SsbDataSource): The data source object with updated properties.
                Must include the data source ID.

        Returns:
            SsbDataSource: The updated data source object with all current properties.
        """
        return from_dict(
            SsbDataSource,
            self.api_client.put(
                f"/api/v2/projects/{project_id}/data-sources/{data_source.id}",
                data=to_dict(data_source),
            ),
        )

    def delete_data_source(
        self,
        project_id: str,
        data_source_id: str,
        delete_dependents: bool = False,
    ) -> None:
        """
        Delete a specific data source by ID.

        Args:
            project_id (str): The ID of the project.
            data_source_id (str): The ID of the data source to delete.
            delete_dependents (bool): Whether to delete dependent resources. Defaults to False.
        """
        self.api_client.delete(
            f"/api/v2/projects/{project_id}/data-sources/{data_source_id}",
            params={"delete_dependents": delete_dependents},
            squelch={
                403: {},  # Data source not in project
                404: {},  # Data source not found
            },
        )

    def validate_data_source(
        self,
        project_id: str,
        data_source: SsbDataSourceSync,
    ) -> SsbDataSourceValidationResponse:
        """
        Validate a data source configuration without creating it.

        Args:
            project_id (str): The unique identifier of the project.
            data_source (SsbDataSourceSync): The data source configuration to validate.

        Returns:
            SsbDataSourceValidationResponse: The validation result from the API.
        """
        return from_dict(
            SsbDataSourceValidationResponse,
            self.api_client.post(
                f"/api/v2/projects/{project_id}/data-sources/validate",
                data=to_dict(data_source),
            ),
        )


@dataclass
class SsbTable:
    table_name: str
    type: str
    metadata: Dict[str, Any]
    id: Union[int, None, NULLABLE] = NULLABLE
    project_id: Union[str, None, NULLABLE] = NULLABLE
    transform_code_b64_encoded: Union[bool, None, NULLABLE] = NULLABLE
    transform_code: Union[str, None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE


class SsbTableClient:
    """Cloudera SSB Table API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client = api_client

    def create_table(
        self,
        project_id: str,
        table: SsbTable,
    ) -> SsbTable:
        return from_dict(
            SsbTable,
            self.api_client.post(
                f"/api/v2/projects/{project_id}/tables",
                data=to_dict(table),
            ),
        )

    def describe_table(
        self,
        project_id: str,
        table_id: int,
    ) -> Optional[SsbTable]:
        """
        Describe a specific table by ID.

        Args:
            project_id (str): The ID of the project.
            table_id (int): The ID of the table to describe.
        """

        return from_dict(
            SsbTable,
            self.api_client.get(
                f"/api/v2/projects/{project_id}/tables/{table_id}",
                squelch={
                    403: None,  # Table not in project
                    404: None,  # Table not found
                },
            ),
        )

    def list_tables(
        self,
        project_id: str,
    ) -> List[SsbTable]:
        """
        List all tables available to the current user for a project.

        Args:
            project_id (str): The ID of the project.
        """
        return [
            from_dict(SsbTable, item)
            for item in self.api_client.get(
                f"/api/v2/projects/{project_id}/tables",
            )
        ]

    def delete_table(
        self,
        project_id: str,
        table_id: int,
    ) -> None:
        """
        Delete a specific table by ID.

        Args:
            project_id (str): The ID of the project.
            table_id (int): The ID of the table to delete.
        """
        self.api_client.delete(
            f"/api/v2/projects/{project_id}/tables/{table_id}",
        )


@dataclass
class SsbEnvironmentSecuredProperty:
    value: str
    sensitive: Union[bool, None, NULLABLE] = NULLABLE


@dataclass
class SsbEnvironmentRequest:
    name: str
    properties: Dict[str, SsbEnvironmentSecuredProperty]


@dataclass
class SsbEnvironment:
    name: str
    secured_props: Dict[str, SsbEnvironmentSecuredProperty]
    id: Union[int, None, NULLABLE] = NULLABLE
    project: Union[str, None, NULLABLE] = NULLABLE
    created_at: Union[str, None, NULLABLE] = NULLABLE
    last_edited_at: Union[str, None, NULLABLE] = NULLABLE
    last_editor: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class SsbEnvironmentExportMetadata:
    project_name: Union[str, None, NULLABLE] = NULLABLE
    checksum: Union[str, None, NULLABLE] = NULLABLE
    exported_at: Union[str, None, NULLABLE] = NULLABLE
    last_edited_at: Union[str, None, NULLABLE] = NULLABLE
    exported_by: Union[str, None, NULLABLE] = NULLABLE
    last_edited_by: Union[str, None, NULLABLE] = NULLABLE
    csa_version: Union[str, None, NULLABLE] = NULLABLE


@dataclass
class SsbEnvironmentFile:
    name: str
    properties: Dict[str, SsbEnvironmentSecuredProperty]
    metadata: SsbEnvironmentExportMetadata


class SsbEnvironmentClient:
    """Cloudera SSB Project Environment API client."""

    def __init__(self, api_client: ServicesClient) -> None:
        """
        Initialize the SSB client with a ServicesClient instance.

        Args:
            api_client (ServicesClient): An instance of ServicesClient for making HTTP requests.
        """
        self.api_client = api_client

    def create_environment(
        self,
        project_id: str,
        environment: SsbEnvironmentRequest,
    ) -> SsbEnvironment:
        return from_dict(
            SsbEnvironment,
            self.api_client.post(
                f"/api/v2/projects/{project_id}/environments",
                data=to_dict(environment),
            ),
        )

    def describe_environment(
        self,
        project_id: str,
        environment_id: int,
    ) -> Optional[SsbEnvironment]:
        """
        Describe a specific environment by ID.

        Args:
            project_id (str): The ID of the project.
            environment_id (int): The ID of the environment to describe.
        """

        return from_dict(
            SsbEnvironment,
            self.api_client.get(
                f"/api/v2/projects/{project_id}/environments/{environment_id}",
                squelch={
                    403: None,  # Environment not in project
                    404: None,  # Environment not found
                },
            ),
        )

    def list_environments(
        self,
        project_id: str,
    ) -> List[SsbEnvironment]:
        """
        List all environments available to the current user for a project.

        Args:
            project_id (str): The ID of the project.
        """
        return [
            from_dict(SsbEnvironment, item)
            for item in self.api_client.get(
                f"/api/v2/projects/{project_id}/environments",
            )
        ]

    def update_environment(
        self,
        project_id: str,
        environment_id: int,
        environment: SsbEnvironmentRequest,
    ) -> SsbEnvironment:
        """
        Update an existing environment in a SQL Stream Builder project.

        Args:
            project_id (str): The unique identifier of the project containing the environment.
            environment_id (int): The unique identifier of the environment to update.
            environment (SsbEnvironmentRequest): The environment object with updated properties.
        """
        return from_dict(
            SsbEnvironment,
            self.api_client.put(
                f"/api/v2/projects/{project_id}/environments/{environment_id}",
                data=to_dict(environment),
            ),
        )

    def activate_environment(
        self,
        project_id: str,
        environment_id: int,
    ) -> None:
        """
        Activate a specific environment by ID.

        Args:
            project_id (str): The ID of the project.
            environment_id (int): The ID of the environment to activate.
        """
        self.api_client.post(
            f"/api/v2/projects/{project_id}/environments/{environment_id}/activate",
        )

    def deactivate_environment(
        self,
        project_id: str,
    ) -> None:
        """
        Deactivate any active environment.

        Args:
            project_id (str): The ID of the project.
        """
        self.api_client.post(
            f"/api/v2/projects/{project_id}/environments/deactivate",
        )

    def import_environment(
        self,
        project_id: str,
        environment_file: Optional[str] = None,
        environment_data: Optional[bytes] = None,
    ) -> SsbEnvironment:
        """
        Import a specific environment by file or data.

        Args:
            project_id (str): The ID of the project.
            environment_file (Optional[str]): The file path of the environment to import.
            environment_data (Optional[bytes]): The data of the environment to import.
        """
        if (environment_file is None) == (environment_data is None):
            raise ValueError(
                "Provide either environment_file or environment_data, not both.",
            )

        file_payload = {}

        if environment_file:
            file_payload.update(filename=environment_file)
        else:
            file_payload.update(content=environment_data)

        return from_dict(
            SsbEnvironment,
            self.api_client.post(
                f"/api/v2/projects/{project_id}/environments/file",
                data={
                    "file": file_payload,
                },
                format="multipart",
            ),
        )

    def export_environment(
        self,
        project_id: str,
        environment_id: int,
    ) -> SsbEnvironmentFile:
        """
        Export a specific environment by ID.

        Args:
            project_id (str): The ID of the project.
            environment_id (int): The ID of the environment to export.
        """
        return from_dict(
            SsbEnvironmentFile,
            self.api_client.get(
                f"/api/v2/projects/{project_id}/environments/file/{environment_id}",
            ),
        )

    def delete_environment(
        self,
        project_id: str,
        environment_id: int,
    ) -> None:
        """
        Delete a specific environment by ID.

        Args:
            project_id (str): The ID of the project.
            environment_id (int): The ID of the environment to delete.
        """
        self.api_client.delete(
            f"/api/v2/projects/{project_id}/environments/{environment_id}",
        )
