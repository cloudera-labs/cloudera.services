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
import sys
import time

from http.cookiejar import CookieJar
from kafka import KafkaAdminClient, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError
from pytest_mock import MockerFixture
from typing import Any, Callable, Dict, Generator, List, Optional
from unittest.mock import Mock

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    AnsibleServicesClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ssb import (
    SsbDataSource,
    SsbDataSourceClient,
    SsbEnvironment,
    SsbEnvironmentClient,
    SsbEnvironmentRequest,
    SsbEnvironmentSecuredProperty,
    SsbJob,
    SsbJobClient,
    SsbJobStop,
    SsbProject,
    SsbProjectClient,
    SsbTable,
    SsbTableClient,
    SsbUdf,
    SsbUdfClient,
    SsbUserClient,
    SsbUserKeytabClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
    RangerPolicyClient,
    RangerService,
    RangerServiceClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    CmlServicesClient,
    MlProject,
    MlProjectClient,
    MlJob,
    MlJobClient,
    MlJobRunClient,
    MlModel,
    MlModelClient,
    MlModelBuild,
    MlModelBuildClient,
    MlModelDeployment,
    MlModelDeploymentClient,
    MlApplication,
    MlApplicationClient,
    MlFile,
    MlProjectFileClient,
    MlRuntimeClient,
    MlRuntimeAddonClient,
    MlRuntimeRepo,
    MlRuntimeRepoClient,
)
from ansible_collections.cloudera.services.tests.unit import (
    AnsibleFailJson,
    AnsibleExitJson,
    TestServicesClient,
)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.ERROR,  # Global default
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("kafka").setLevel(logging.ERROR)

log = logging.getLogger("cloudera.services.conftest")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """
    Adds an 'all' alias to run all tests.
    Skips all tests if not running Python 3.6 or higher.
    Skips tests marked 'integration_api' if CDP_ACCESS_KEY_ID and CDP_PRIVATE_KEY
    are missing, and skips 'integration_token' if CDP_TOKEN is missing.
    """

    if sys.version_info < (3, 9):
        skip_python = pytest.mark.skip(
            reason=f"Skipping on Python {sys.version}. cloudera.services supports Python 3.9 and higher.",
        )
        for item in items:
            item.add_marker(skip_python)
        return

    marker_expr = config.getoption("-m")
    if marker_expr == "all":
        config.option.markexpr = ""


@pytest.fixture(scope="function")
def env_context(request) -> Dict[str, str]:
    """
    Validates and provides required environment variables for integration tests.

    Set REQUIRED_ENV_VARS at module, class, or function level to specify required variables.
    Variables from narrower scopes (function > class > module) are appended to broader scopes.

    Usage:
        # At module level
        REQUIRED_ENV_VARS = ["VAR1", "VAR2"]

        # At class level
        class TestClass:
            REQUIRED_ENV_VARS = ["VAR3"]  # Adds to module-level vars

        # At function level
        def test_func(env_context):
            pass
        test_func.REQUIRED_ENV_VARS = ["VAR4"]  # Adds to class and module-level vars

    Returns a dictionary of environment variable names to their values.
    """

    # Collect required vars from all scopes (module -> class -> function)
    required_vars = []

    # Module-level vars
    if hasattr(request.module, "REQUIRED_ENV_VARS"):
        required_vars.extend(request.module.REQUIRED_ENV_VARS)

    # Class-level vars (if test is in a class)
    if request.cls and hasattr(request.cls, "REQUIRED_ENV_VARS"):
        required_vars.extend(request.cls.REQUIRED_ENV_VARS)

    # Function-level vars
    if hasattr(request.function, "REQUIRED_ENV_VARS"):
        required_vars.extend(request.function.REQUIRED_ENV_VARS)

    # Remove duplicates while preserving order
    required_vars = list(dict.fromkeys(required_vars))

    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        pytest.skip(
            f"Skipping test {request.node.nodeid}: "
            f"Missing required env vars: {', '.join(missing)}",
        )

    return {var: os.environ[var] for var in required_vars}


@pytest.fixture
def module_args() -> Callable[[dict], None]:
    """Prepare module arguments"""

    def prep_args(args=dict()):
        args = json.dumps({"ANSIBLE_MODULE_ARGS": args})
        basic._ANSIBLE_ARGS = to_bytes(args)

    return prep_args


@pytest.fixture(autouse=True)
def patch_module(monkeypatch) -> None:
    """Patch AnsibleModule to raise exceptions on success and failure"""

    def exit_json(*args, **kwargs):
        if "changed" not in kwargs:
            kwargs["changed"] = False
        raise AnsibleExitJson(kwargs)

    def fail_json(*args, **kwargs):
        kwargs["failed"] = True
        raise AnsibleFailJson(kwargs)

    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", fail_json)


@pytest.fixture
def mock_ansible_module(mocker: MockerFixture) -> Mock:
    """Fixture for mock AnsibleModule."""
    module = mocker.Mock()
    module.params = {}
    module.fail_json = mocker.Mock(
        side_effect=AnsibleFailJson({"msg": "fail_json called"}),
    )
    module.exit_json = mocker.Mock(
        side_effect=AnsibleExitJson({"msg": "exit_json called"}),
    )
    return module


@pytest.fixture()
def ansible_services_client(
    module_creds: Dict[str, str],
    mock_ansible_module: Mock,
) -> AnsibleServicesClient:
    """Fixture for creating an AnsibleServicesClient instance."""

    return AnsibleServicesClient(
        module=mock_ansible_module,
        timeout=int(module_creds["timeout_seconds"]),
        default_page_size=int(module_creds["default_page_size"]),
        proxy_context_path=module_creds["proxy_context_path"],
    )


@pytest.fixture(scope="session")
def test_services_client() -> TestServicesClient:
    """
    Fixture for creating a TestServicesClient instance.

    Requires the following environment variables to be set:
    - DS_API_ENDPOINT
    - DS_API_PORT
    """
    return TestServicesClient(
        endpoint=os.getenv("DS_API_ENDPOINT", "https://not.set.cloudera.internal"),
        port=int(os.getenv("DS_API_PORT", "443")),
    )


@pytest.fixture
def smm_kafka_topic(
    env_context,
) -> Generator[
    Callable[[str, int], Callable[[List[Dict[str, Any]]], None]],
    None,
    None,
]:
    """
    A fixture factory that provisions, seeds, and deprovisions a SSM Kafka topic.

    Requires the following environment variables to be set:
    - SMM_KAFKA_BROKERS
    - SMM_KAFKA_USERNAME
    - SMM_KAFKA_PASSWORD
    - SMM_KAFKA_SSL_CAFILE

    Typically, the username and password are the CDP workload credentials, while
    the SSL CA file is the CDP Environment (FreeIPA) certificate.

    The topic can be seeded with data by passing a list of dictionaries to the factory function.
    Each dictionary represents a record to be sent to the topic, and will be serialized as JSON.
    """

    SECURITY_CONFIG = {
        "client_id": "ansible-smm-test-client",
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "PLAIN",
        "sasl_plain_username": env_context["SMM_KAFKA_USERNAME"],
        "sasl_plain_password": env_context["SMM_KAFKA_PASSWORD"],
        "ssl_cafile": env_context["SMM_KAFKA_SSL_CAFILE"],
        # "api_version_auto_timeout_ms": 30000,
    }

    admin_client = KafkaAdminClient(
        bootstrap_servers=[
            broker.strip() for broker in env_context["SMM_KAFKA_BROKERS"].split(",")
        ],
        **SECURITY_CONFIG,
    )

    producer = KafkaProducer(
        bootstrap_servers=[
            broker.strip() for broker in env_context["SMM_KAFKA_BROKERS"].split(",")
        ],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        **SECURITY_CONFIG,
    )

    created_topics = []
    log = logging.getLogger("kafka")

    def _factory(topic_name: str, partitions: int = 1):
        topic_list = [
            NewTopic(name=topic_name, num_partitions=partitions, replication_factor=1),
        ]
        try:
            admin_client.create_topics(new_topics=topic_list, validate_only=False)
        except TopicAlreadyExistsError:
            log.info(f"Topic '{topic_name}' already exists. Appending data...")

        created_topics.append(topic_name)

        def _seed(seed_data: List[Dict[str, Any]]):
            for record in seed_data:
                producer.send(topic_name, record)
            producer.flush()

        return _seed

    yield _factory

    if created_topics:
        try:
            admin_client.delete_topics(topics=created_topics)
            # Wait briefly for controller to propagate deletion
            time.sleep(2)
        except UnknownTopicOrPartitionError:
            pass  # Already gone
        except Exception as e:
            pytest.fail(f"Teardown failed: {e}")

    admin_client.close()
    producer.close()


@pytest.fixture(scope="module")
def ssb_rest_client(request) -> AnsibleServicesClient:
    """
    Fixture to create an AnsibleServicesClient instance with a mock AnsibleModule.
    This fixture's Ansible module is used for set up and teardown of SSB test
    resources (module-scope).

    It checks for the following required environment variables set at the module
    and skips tests if any are missing.
    - SSB_SSE_API_URL
    - SSB_SSE_API_USERNAME
    - SSB_SSE_API_PASSWORD
    """
    required_vars = getattr(request.module, "REQUIRED_ENV_VARS", [])
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")

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
            "url": os.environ["SSB_SSE_API_URL"],
            "url_username": os.environ["SSB_SSE_API_USERNAME"],
            "url_password": os.environ["SSB_SSE_API_PASSWORD"],
        },
    )

    # Create the AnsibleServicesClient instance
    return AnsibleServicesClient(
        module=module,
        cookies=CookieJar(),
    )


@pytest.fixture(scope="module")
def ssb_project_client(ssb_rest_client) -> SsbProjectClient:
    """Fixture to create an SSBProjectClient instance."""
    return SsbProjectClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_project(
    ssb_project_client,
) -> Generator[Callable[[SsbProject], SsbProject], None, None]:
    """Fixture to purge a test project after the test."""
    projects = []

    def _add_project(project: SsbProject):
        projects.append(project)
        return project

    yield _add_project

    # Clean up after the test
    for project in projects:
        try:
            ssb_project_client.delete_project(project)
        except Exception as e:
            log.info(f"Failed to delete project {project.id} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def existing_project(request, ssb_project_client) -> Generator[SsbProject, None, None]:
    """Fixture to create a module-scoped test project and clean it up after the test."""
    project_name = request.node.name.lower().rstrip(".py")

    # Clean up any existing test project
    projects = ssb_project_client.list_projects()
    for project in projects:
        if project.name == project_name:
            ssb_project_client.delete_project(project)

    # Create the test project
    project = ssb_project_client.create_project(
        SsbProject(
            name=project_name,
            description="Existing project created by pytest",
        ),
    )

    yield project

    # Clean up after the test (module scope, cannot use purge_project fixture)
    try:
        ssb_project_client.delete_project(project)
    except Exception as e:
        log.info(f"Failed to delete project {project.id} during cleanup: {str(e)}")


@pytest.fixture()
def deletable_project(
    request,
    ssb_project_client,
    purge_project,
) -> Generator[SsbProject, None, None]:
    """Fixture to create a function-scoped test project and clean it up after the test if needed."""
    project_name = request.node.name.lower().rstrip(".py")

    # Clean up any existing test project
    projects = ssb_project_client.list_projects()
    for project in projects:
        if project.name == project_name:
            ssb_project_client.delete_project(project)

    # Create the test project
    project = ssb_project_client.create_project(
        SsbProject(
            name=project_name,
            description="Deletable project created by pytest",
        ),
    )

    # Register for deletion after test
    purge_project(project)

    yield project


@pytest.fixture(scope="module")
def data_source_client(ssb_rest_client) -> SsbDataSourceClient:
    """Fixture to create an SSBDataSourceClient instance."""
    return SsbDataSourceClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_data_source(
    data_source_client,
) -> Generator[Callable[[SsbDataSource], SsbDataSource], None, None]:
    """Fixture to purge a test job after the test."""
    sources: List[SsbDataSource] = []

    def _add_source(job: SsbDataSource) -> SsbDataSource:
        sources.insert(
            0,
            job,
        )  # Needs to be a First-In-Last-Out list to handle dependencies (vs. using delete_dependents)
        return job

    yield _add_source

    # Clean up after the test
    for source in sources:
        try:
            data_source_client.delete_data_source(
                project_id=source.project_id,
                data_source_id=source.id,
                delete_dependents=False,
            )
        except Exception as e:
            log.info(
                f"Failed to delete data source {source.id} during cleanup: {str(e)}",
            )


@pytest.fixture
def existing_data_source_kafka_data() -> List[Dict[str, Any]]:
    """Fixture to provide sample data for Kafka data source tests."""
    return [
        {"id": 1, "status": "PENDING", "amount": 100.50},
        {"id": 2, "status": "SHIPPED", "amount": 25.00},
    ]


@pytest.fixture
def existing_data_source_kafka_schema() -> Dict[str, Any]:
    """Fixture to provide a sample schema for Kafka data source tests."""
    return {
        "type": "record",
        "name": "test_record",
        "fields": [
            {
                "name": "id",
                "type": "long",
            },
            {
                "name": "status",
                "type": "string",
            },
            {
                "name": "amount",
                "type": "double",
            },
        ],
    }


@pytest.fixture
def existing_data_source_kafka(
    request,
    data_source_client,
    env_context,
    existing_project,
    existing_data_source_kafka_data,
    purge_data_source,
    smm_kafka_topic,
) -> Generator[SsbDataSource, None, None]:
    """Fixture to create a test SSB data source (Kafka) and clean it up after the test."""
    source_name = request.node.name.lower() + "_kafka"

    # Create the test Kafka topic and seed it with data
    topic = smm_kafka_topic(source_name)
    topic(existing_data_source_kafka_data)

    # Clean up any existing test data sources with the same name
    sources = data_source_client.list_data_sources(existing_project.id)
    for source in sources:
        if source.name == source_name:
            data_source_client.delete_data_source(
                source.project_id,
                source.data_source_id,
            )

    source = data_source_client.create_data_source(
        project_id=existing_project.id,
        data_source=SsbDataSource(
            name=source_name,
            type="kafka",
            properties={
                "brokers": env_context["SMM_KAFKA_BROKERS"],
                "protocol": "sasl",
                "mechanism": "KERBEROS",
            },
            custom_truststore=False,
        ),
    )

    # Register the data source for cleanup
    purge_data_source(source)

    yield source


@pytest.fixture
def existing_data_source_hive(
    request,
    data_source_client,
    existing_project,
    purge_data_source,
) -> Generator[SsbDataSource, None, None]:
    """Fixture to create a test SSB data source (Hive) and clean it up after the test."""
    source_name = request.node.name.lower() + "_hive"

    # Clean up any existing test data sources with the same name
    sources = data_source_client.list_data_sources(existing_project.id)
    for source in sources:
        if source.name == source_name:
            data_source_client.delete_data_source(
                source.project_id,
                source.data_source_id,
            )

    source = data_source_client.create_data_source(
        project_id=existing_project.id,
        data_source=SsbDataSource(
            name=source_name,
            type="catalog",
            properties={
                "table_filters": [],
                "catalog_type": "hive",
            },
            custom_truststore=False,
        ),
    )

    # Register the data source for cleanup
    purge_data_source(source)

    yield source


@pytest.fixture(scope="module")
def job_client(ssb_rest_client) -> SsbJobClient:
    """Fixture to create an SSBJobClient instance."""
    return SsbJobClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_job(job_client) -> Generator[Callable[[SsbJob], SsbJob], None, None]:
    """Fixture to purge a test job after the test."""
    jobs: List[SsbJob] = []

    def _add_job(job: SsbJob) -> SsbJob:
        jobs.append(job)
        return job

    yield _add_job

    # Clean up after the test
    for job in jobs:
        try:
            job_status = job_client.get_job_state(job.project_id, job.job_id)
            if job_status.state in SsbJobClient.READY_STATES:
                job_client.stop_job(
                    project_id=job.project_id,
                    job_id=job.job_id,
                    config=SsbJobStop(),
                )
            job_client.delete_job(job.project_id, job.job_id)
        except Exception as e:
            log.info(f"Failed to delete job {job.job_id} during cleanup: {str(e)}")


@pytest.fixture
def udf_client(ssb_rest_client) -> SsbUdfClient:
    """Fixture to create an SsbUdfClient instance."""
    return SsbUdfClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_udf(udf_client) -> Generator[Callable[[SsbUdf], SsbUdf], None, None]:
    """Fixture to purge a test UDF after the test."""
    udfs = []

    def _add_udf(udf: SsbUdf) -> SsbUdf:
        udfs.append(udf)
        return udf

    yield _add_udf

    # Clean up after the test
    for udf in udfs:
        try:
            udf_client.delete_udf(udf.project_id, udf.id)
        except Exception as e:
            log.info(f"Failed to delete UDF {udf.id} during cleanup: {str(e)}")


@pytest.fixture
def existing_udf(
    request,
    ssb_rest_client,
    existing_project,
    purge_udf,
) -> Generator[SsbUdf, None, None]:
    """Fixture to create a test UDF and clean it up after the test."""
    udf_name = request.node.name.lower() + "_udf"

    client = SsbUdfClient(api_client=ssb_rest_client)

    # Clean up any existing test UDF
    udfs = client.list_udfs(existing_project.id)
    for udf in udfs:
        if udf.name == udf_name and isinstance(udf.id, int):
            client.delete_udf(existing_project.id, udf.id)

    # Create the test UDF
    udf = client.create_udf(
        udf=SsbUdf(
            name=udf_name,
            project_id=existing_project.id,
            output_type="PYTHON_INFERRED",
            language="PYTHON",
            code="def test_func(str):\n    return str.upper()",
            input_types=["STRING"],
            description="Test UDF for integration tests",
        ),
    )

    purge_udf(udf)

    yield udf


@pytest.fixture()
def user_client(ssb_rest_client) -> SsbUserClient:
    """Fixture to create an SSBUserClient instance."""
    return SsbUserClient(api_client=ssb_rest_client)


@pytest.fixture
def user_keytab_client(ssb_rest_client) -> SsbUserKeytabClient:
    """Fixture to create an SSBUserKeytabClient instance."""
    return SsbUserKeytabClient(api_client=ssb_rest_client)


@pytest.fixture
def clear_keytab(user_keytab_client) -> Generator[None, None, None]:
    """Fixture to clear the keytab before and after tests."""
    # Ensure keytab is deleted before test
    user_keytab_client.delete_keytab()

    yield

    # Ensure keytab is deleted after test
    user_keytab_client.delete_keytab()


@pytest.fixture
def set_keytab(user_keytab_client, env_context) -> Generator[None, None, None]:
    """Fixture to create a keytab before and clear after tests."""
    # Ensure keytab is deleted before test
    user_keytab_client.delete_keytab()
    user_keytab_client.generate_keytab(
        principal=env_context["SSB_SSE_API_USERNAME"],
        password=env_context["SSB_SSE_API_PASSWORD"],
    )

    yield

    # Ensure keytab is deleted after test
    user_keytab_client.delete_keytab()


@pytest.fixture(scope="module")
def ssb_table_client(ssb_rest_client) -> SsbTableClient:
    """Fixture to create an SSBTableClient instance."""
    return SsbTableClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_table(
    ssb_table_client,
) -> Generator[Callable[[SsbTable], SsbTable], None, None]:
    """Fixture to purge a test job after the test."""
    tables: List[SsbTable] = []

    def _add_table(table: SsbTable) -> SsbTable:
        tables.insert(
            0,
            table,
        )  # Needs to be a First-In-Last-Out list to handle dependencies
        return table

    yield _add_table

    # Clean up after the test
    for table in tables:
        try:
            ssb_table_client.delete_table(table.project_id, table.id)
        except Exception as e:
            log.info(f"Failed to delete table {table.id} during cleanup: {str(e)}")


@pytest.fixture
def existing_table_kafka(
    request,
    ssb_table_client,
    existing_project,
    purge_table,
    existing_data_source_kafka,
    existing_data_source_kafka_schema,
) -> Generator[SsbTable, None, None]:
    """Fixture to create and cleanup an existing table."""
    # Also is the name of the topic in Kafka via existing_data_source_kafka and smm_kafka_topic
    table_name = request.node.name.lower()

    # Clean up any existing test tables with the same name
    tables = ssb_table_client.list_tables(existing_project.id)
    for table in tables:
        if table.table_name == table_name:
            ssb_table_client.delete_table(table.project_id, table.id)

    table = ssb_table_client.create_table(
        project_id=existing_project.id,
        table=SsbTable(
            table_name=table_name,
            type="kafka",
            metadata={
                "kafka_source_name": existing_data_source_kafka.name,
                "format": "JSON",
                "schema": json.dumps(existing_data_source_kafka_schema),
                "topic": table_name,
            },
        ),
    )

    # Register the table for cleanup
    purge_table(table)

    yield table


@pytest.fixture(scope="module")
def environment_client(ssb_rest_client) -> SsbEnvironmentClient:
    """Fixture to create an SSBEnvironmentClient instance."""
    return SsbEnvironmentClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_environment(
    environment_client,
) -> Generator[Callable[[str, SsbEnvironment], SsbEnvironment], None, None]:
    """Fixture to purge a test environment after the test."""
    environments: List[tuple[str, SsbEnvironment]] = []

    def _add_environment(
        project_id: str,
        environment: SsbEnvironment,
    ) -> SsbEnvironment:
        environments.append((project_id, environment))
        return environment

    yield _add_environment

    # Clean up after the test
    for project_id, environment in environments:
        try:
            environment_client.deactivate_environment(project_id)
            environment_client.delete_environment(project_id, environment.id)
        except Exception as e:
            log.info(
                f"Failed to delete environment {environment.id} during cleanup: {str(e)}",
            )


@pytest.fixture(scope="module")
def existing_environment(
    request,
    existing_project,
    environment_client,
) -> Generator[SsbEnvironment, None, None]:
    """Fixture to create a module-scoped test environment and clean it up after the test."""
    environment_name = request.node.name.lower().rstrip(".py")

    # Clean up any existing test environment
    environments = environment_client.list_environments(existing_project.id)
    for environment in environments:
        if environment.name == environment_name:
            environment_client.delete_environment(existing_project.id, environment.id)

    # Create the test environment
    environment = environment_client.create_environment(
        existing_project.id,
        SsbEnvironmentRequest(
            name=environment_name,
            properties={
                "test_key": SsbEnvironmentSecuredProperty(
                    value="test_value",
                    sensitive=False,
                ),
            },
        ),
    )

    yield environment

    # Clean up after the test (module scope, cannot use purge_environment fixture)
    try:
        environment_client.deactivate_environment(existing_project.id)
        environment_client.delete_environment(existing_project.id, environment.id)
    except Exception as e:
        log.info(
            f"Failed to delete environment {environment.id} during cleanup: {str(e)}",
        )


@pytest.fixture()
def deletable_environment(
    request,
    existing_project,
    environment_client,
    purge_environment,
) -> Generator[SsbEnvironment, None, None]:
    """Fixture to create a function-scoped test environment and clean it up after the test if needed."""
    environment_name = request.node.name.lower().rstrip(".py")

    # Clean up any existing test environment
    environments = environment_client.list_environments(existing_project.id)
    for environment in environments:
        if environment.name == environment_name:
            environment_client.delete_environment(existing_project.id, environment.id)

    # Create the test environment
    environment = environment_client.create_environment(
        existing_project.id,
        SsbEnvironmentRequest(
            name=environment_name,
            properties={
                "test_key": SsbEnvironmentSecuredProperty(
                    value="deletable_value",
                    sensitive=False,
                ),
            },
        ),
    )

    # Register for deletion after test
    purge_environment(existing_project.id, environment)

    yield environment


@pytest.fixture
def activated_environment(ssb_rest_client, existing_project, existing_environment):
    """Fixture that ensures an environment is activated on the project."""
    SsbEnvironmentClient(ssb_rest_client).activate_environment(
        existing_project.id,
        existing_environment.id,
    )
    return existing_environment


@pytest.fixture
def activated_deletable_environment(
    ssb_rest_client,
    existing_project,
    deletable_environment,
):
    """Fixture that ensures an environment is activated on the project."""
    SsbEnvironmentClient(ssb_rest_client).activate_environment(
        existing_project.id,
        deletable_environment.id,
    )
    return deletable_environment


# ---------------------------------------------------------------------------
# Cloudera Machine Learning (CML) Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ml_rest_client(request) -> CmlServicesClient:
    """
    Fixture to create a CmlServicesClient instance authenticated with a bearer token.

    It checks for the following required environment variables set at the module
    and skips tests if any are missing:
    - CML_ENDPOINT
    - CML_API_KEY

    Optionally honors CML_VALIDATE_CERTS (default "true").
    """
    required_vars = getattr(request.module, "REQUIRED_ENV_VARS", [])
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")

    module = Mock()
    module.params = {}
    module.fail_json = Mock(side_effect=AnsibleFailJson({"msg": "fail_json called"}))
    module.exit_json = Mock(side_effect=AnsibleExitJson({"msg": "exit_json called"}))

    module.params.update(
        {
            "url": os.environ["CML_ENDPOINT"],
            "api_key": os.environ["CML_API_KEY"],
            "validate_certs": os.environ.get("CML_VALIDATE_CERTS", "true").lower()
            == "true",
        },
    )

    return CmlServicesClient(module=module, cookies=CookieJar())


@pytest.fixture(scope="module")
def ml_project_client(ml_rest_client) -> MlProjectClient:
    """Fixture to create an MlProjectClient instance."""
    return MlProjectClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_job_client(ml_rest_client) -> MlJobClient:
    """Fixture to create an MlJobClient instance."""
    return MlJobClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_job_run_client(ml_rest_client) -> MlJobRunClient:
    """Fixture to create an MlJobRunClient instance."""
    return MlJobRunClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_model_client(ml_rest_client) -> MlModelClient:
    """Fixture to create an MlModelClient instance."""
    return MlModelClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_model_build_client(ml_rest_client) -> MlModelBuildClient:
    """Fixture to create an MlModelBuildClient instance."""
    return MlModelBuildClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_model_deployment_client(ml_rest_client) -> MlModelDeploymentClient:
    """Fixture to create an MlModelDeploymentClient instance."""
    return MlModelDeploymentClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_runtime_repo_client(ml_rest_client) -> MlRuntimeRepoClient:
    """Fixture to create an MlRuntimeRepoClient instance."""
    return MlRuntimeRepoClient(api_client=ml_rest_client)


@pytest.fixture
def purge_ml_runtime_repo(
    ml_runtime_repo_client,
) -> Generator[Callable[[MlRuntimeRepo], MlRuntimeRepo], None, None]:
    """Factory fixture to register CML runtime repos for cleanup after the test."""
    repos: List[MlRuntimeRepo] = []

    def _add_repo(repo: MlRuntimeRepo) -> MlRuntimeRepo:
        repos.append(repo)
        return repo

    yield _add_repo

    for repo in repos:
        try:
            if isinstance(repo.id, int):
                ml_runtime_repo_client.delete_runtime_repo(repo.id)
        except Exception as e:
            log.info(
                f"Failed to delete runtime repo {repo.id} during cleanup: {str(e)}",
            )


@pytest.fixture(scope="module")
def ml_application_client(ml_rest_client) -> MlApplicationClient:
    """Fixture to create an MlApplicationClient instance."""
    return MlApplicationClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_runtime_client(ml_rest_client) -> MlRuntimeClient:
    """Fixture to create an MlRuntimeClient instance."""
    return MlRuntimeClient(api_client=ml_rest_client)


@pytest.fixture(scope="module")
def ml_runtime_addon_client(ml_rest_client) -> MlRuntimeAddonClient:
    """Fixture to create an MlRuntimeAddonClient instance."""
    return MlRuntimeAddonClient(api_client=ml_rest_client)


@pytest.fixture
def purge_ml_project(
    ml_project_client,
) -> Generator[Callable[[MlProject], MlProject], None, None]:
    """Factory fixture to register CML projects for cleanup after the test."""
    projects: List[MlProject] = []

    def _add_project(project: MlProject) -> MlProject:
        projects.append(project)
        return project

    yield _add_project

    # Clean up after the test
    for project in projects:
        try:
            if isinstance(project.id, str):
                ml_project_client.delete_project(project.id)
        except Exception as e:
            log.info(f"Failed to delete project {project.id} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def existing_ml_project(request, ml_project_client) -> Generator[MlProject, None, None]:
    """Fixture to create a module-scoped CML project and clean it up afterwards."""
    project_name = request.path.stem

    # Clean up any existing test project with the same name. CML can 500 on
    # project deletion during filesystem (VFS) cleanup, so tolerate leftovers
    # rather than poisoning the run.
    for project in ml_project_client.list_projects():
        if project.name == project_name and isinstance(project.id, str):
            try:
                ml_project_client.delete_project(project.id)
            except Exception as e:
                log.info(
                    f"Failed to delete pre-existing project {project.id}: {str(e)}",
                )

    project = ml_project_client.create_project(
        MlProject(
            name=project_name,
            description="Existing project created by pytest",
            template="blank",
        ),
    )

    yield project

    # Clean up after the test (module scope, cannot use purge_ml_project fixture)
    try:
        if isinstance(project.id, str):
            ml_project_client.delete_project(project.id)
    except Exception as e:
        log.info(f"Failed to delete project {project.id} during cleanup: {str(e)}")


@pytest.fixture()
def deletable_ml_project(
    request,
    ml_project_client,
    purge_ml_project,
) -> Generator[MlProject, None, None]:
    """Fixture to create a function-scoped CML project and clean it up if needed."""
    project_name = f"ansible-ml-int-{request.node.name.lower()}"[:100]

    # Clean up any existing test project with the same name
    for project in ml_project_client.list_projects():
        if project.name == project_name and isinstance(project.id, str):
            ml_project_client.delete_project(project.id)

    project = ml_project_client.create_project(
        MlProject(
            name=project_name,
            description="Deletable project created by pytest",
            template="blank",
        ),
    )

    # Register for deletion after test
    purge_ml_project(project)

    yield project


def _ml_subdomain(value: str) -> str:
    """Build a valid CML application subdomain from an arbitrary string."""
    out = "".join(c if c.isalnum() else "-" for c in value.lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:63].strip("-") or "app"


@pytest.fixture(scope="module")
def ml_runtime_identifier(ml_runtime_client) -> str:
    """Fixture to discover an available CML runtime image identifier."""
    runtimes = ml_runtime_client.list_runtimes()
    for runtime in runtimes:
        if isinstance(runtime.image_identifier, str):
            return runtime.image_identifier
    pytest.skip("No CML runtime image identifier available")


@pytest.fixture(scope="module")
def ml_model_runtime_identifier(ml_runtime_client) -> str:
    """Discover a model-serving-capable CML runtime image identifier.

    Model builds require a PBJ Workbench Python runtime; JupyterLab/notebook
    runtimes are not deployable as models and cause the build to fail.
    """
    runtimes = ml_runtime_client.list_runtimes()

    def _pick(predicate) -> Optional[str]:
        for r in runtimes:
            if isinstance(r.image_identifier, str) and predicate(r):
                return r.image_identifier
        return None

    identifier = _pick(
        lambda r: r.editor == "PBJ Workbench"
        and r.edition == "Standard"
        and "Python" in str(r.kernel or ""),
    ) or _pick(
        lambda r: r.editor == "PBJ Workbench" and "Python" in str(r.kernel or ""),
    )
    if identifier is None:
        pytest.skip("No PBJ Workbench Python runtime available for model builds")
    return identifier


@pytest.fixture
def purge_ml_application(
    ml_application_client,
) -> Generator[Callable[[str, MlApplication], MlApplication], None, None]:
    """Factory fixture to register CML applications for cleanup after the test."""
    applications: List[tuple] = []

    def _add_application(project_id: str, application: MlApplication) -> MlApplication:
        applications.append((project_id, application))
        return application

    yield _add_application

    # Clean up after the test
    for project_id, application in applications:
        try:
            if isinstance(application.id, str):
                ml_application_client.delete_application(project_id, application.id)
        except Exception as e:
            log.info(
                f"Failed to delete application {application.id} during cleanup: {str(e)}",
            )


@pytest.fixture(scope="module")
def existing_ml_application(
    existing_ml_project,
    ml_application_client,
    ml_runtime_identifier,
    ml_project_script,
) -> Generator[MlApplication, None, None]:
    """Fixture to create a module-scoped CML application and clean it up afterwards."""
    name = "existing-app"
    # Subdomains are unique across the workspace, so derive from the per-run
    # project id to avoid colliding with leftovers from earlier runs.
    subdomain = _ml_subdomain(f"existing-{existing_ml_project.id}")

    # Clean up any existing test application with the same name
    for app in ml_application_client.list_applications(existing_ml_project.id):
        if app.name == name and isinstance(app.id, str):
            ml_application_client.delete_application(existing_ml_project.id, app.id)

    application = ml_application_client.create_application(
        existing_ml_project.id,
        MlApplication(
            name=name,
            subdomain=subdomain,
            script=ml_project_script,
            runtime_identifier=ml_runtime_identifier,
        ),
    )

    yield application

    # Clean up after the test (module scope, cannot use purge_ml_application fixture)
    try:
        if isinstance(application.id, str):
            ml_application_client.delete_application(
                existing_ml_project.id,
                application.id,
            )
    except Exception as e:
        log.info(
            f"Failed to delete application {application.id} during cleanup: {str(e)}",
        )


@pytest.fixture()
def deletable_ml_application(
    request,
    existing_ml_project,
    ml_application_client,
    ml_runtime_identifier,
    ml_project_script,
    purge_ml_application,
) -> Generator[MlApplication, None, None]:
    """Fixture to create a function-scoped CML application and clean it up if needed."""
    name = f"del-{request.node.name.lower()}"[:100]
    # Subdomains are unique across the workspace; include the per-run project id.
    subdomain = _ml_subdomain(f"{request.node.name}-{existing_ml_project.id}")

    # Clean up any existing test application with the same name
    for app in ml_application_client.list_applications(existing_ml_project.id):
        if app.name == name and isinstance(app.id, str):
            ml_application_client.delete_application(existing_ml_project.id, app.id)

    application = ml_application_client.create_application(
        existing_ml_project.id,
        MlApplication(
            name=name,
            subdomain=subdomain,
            script=ml_project_script,
            runtime_identifier=ml_runtime_identifier,
        ),
    )

    # Register for deletion after test
    purge_ml_application(existing_ml_project.id, application)

    yield application


@pytest.fixture
def purge_ml_job(
    ml_job_client,
) -> Generator[Callable[[str, MlJob], MlJob], None, None]:
    """Factory fixture to register CML jobs for cleanup after the test."""
    jobs: List[tuple] = []

    def _add_job(project_id: str, job: MlJob) -> MlJob:
        jobs.append((project_id, job))
        return job

    yield _add_job

    # Clean up after the test
    for project_id, job in jobs:
        try:
            if isinstance(job.id, str):
                ml_job_client.delete_job(project_id, job.id)
        except Exception as e:
            log.info(f"Failed to delete job {job.id} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def existing_ml_job(
    existing_ml_project,
    ml_job_client,
    ml_runtime_identifier,
    ml_project_script,
) -> Generator[MlJob, None, None]:
    """Fixture to create a module-scoped CML job and clean it up afterwards."""
    name = "existing-job"

    # Clean up any existing test job with the same name
    for job in ml_job_client.list_jobs(existing_ml_project.id):
        if job.name == name and isinstance(job.id, str):
            ml_job_client.delete_job(existing_ml_project.id, job.id)

    job = ml_job_client.create_job(
        existing_ml_project.id,
        MlJob(
            name=name,
            script=ml_project_script,
            runtime_identifier=ml_runtime_identifier,
        ),
    )

    yield job

    # Clean up after the test (module scope, cannot use purge_ml_job fixture)
    try:
        if isinstance(job.id, str):
            ml_job_client.delete_job(existing_ml_project.id, job.id)
    except Exception as e:
        log.info(f"Failed to delete job {job.id} during cleanup: {str(e)}")


@pytest.fixture()
def deletable_ml_job(
    request,
    existing_ml_project,
    ml_job_client,
    ml_runtime_identifier,
    ml_project_script,
    purge_ml_job,
) -> Generator[MlJob, None, None]:
    """Fixture to create a function-scoped CML job and clean it up if needed."""
    name = f"del-{request.node.name.lower()}"[:100]

    # Clean up any existing test job with the same name
    for job in ml_job_client.list_jobs(existing_ml_project.id):
        if job.name == name and isinstance(job.id, str):
            ml_job_client.delete_job(existing_ml_project.id, job.id)

    job = ml_job_client.create_job(
        existing_ml_project.id,
        MlJob(
            name=name,
            script=ml_project_script,
            runtime_identifier=ml_runtime_identifier,
        ),
    )

    # Register for deletion after test
    purge_ml_job(existing_ml_project.id, job)

    yield job


@pytest.fixture
def purge_ml_model(
    ml_model_client,
) -> Generator[Callable[[str, MlModel], MlModel], None, None]:
    """Factory fixture to register CML models for cleanup after the test."""
    models: List[tuple] = []

    def _add_model(project_id: str, model: MlModel) -> MlModel:
        models.append((project_id, model))
        return model

    yield _add_model

    # Clean up after the test
    for project_id, model in models:
        try:
            if isinstance(model.id, str):
                ml_model_client.delete_model(project_id, model.id)
        except Exception as e:
            log.info(f"Failed to delete model {model.id} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def existing_ml_model(
    existing_ml_project,
    ml_model_client,
) -> Generator[MlModel, None, None]:
    """Fixture to create a module-scoped CML model and clean it up afterwards."""
    name = "existing-model"

    # Clean up any existing test model with the same name
    for model in ml_model_client.list_models(existing_ml_project.id):
        if model.name == name and isinstance(model.id, str):
            ml_model_client.delete_model(existing_ml_project.id, model.id)

    model = ml_model_client.create_model(
        existing_ml_project.id,
        MlModel(
            name=name,
            description="An existing model for integration tests.",
        ),
    )

    yield model

    # Clean up after the test (module scope, cannot use purge_ml_model fixture)
    try:
        if isinstance(model.id, str):
            ml_model_client.delete_model(existing_ml_project.id, model.id)
    except Exception as e:
        log.info(f"Failed to delete model {model.id} during cleanup: {str(e)}")


@pytest.fixture()
def deletable_ml_model(
    request,
    existing_ml_project,
    ml_model_client,
    purge_ml_model,
) -> Generator[MlModel, None, None]:
    """Fixture to create a function-scoped CML model and clean it up if needed."""
    name = f"del-{request.node.name.lower()}"[:100]

    # Clean up any existing test model with the same name
    for model in ml_model_client.list_models(existing_ml_project.id):
        if model.name == name and isinstance(model.id, str):
            ml_model_client.delete_model(existing_ml_project.id, model.id)

    model = ml_model_client.create_model(
        existing_ml_project.id,
        MlModel(
            name=name,
            description="A deletable model for integration tests.",
        ),
    )

    # Register for deletion after test
    purge_ml_model(existing_ml_project.id, model)

    yield model


@pytest.fixture
def purge_ml_model_build(
    ml_model_build_client,
) -> Generator[Callable[[str, str, MlModelBuild], MlModelBuild], None, None]:
    """Factory fixture to register CML model builds for cleanup after the test."""
    builds: List[tuple] = []

    def _add_build(project_id: str, model_id: str, build: MlModelBuild) -> MlModelBuild:
        builds.append((project_id, model_id, build))
        return build

    yield _add_build

    # Clean up after the test
    for project_id, model_id, build in builds:
        try:
            if isinstance(build.id, str):
                ml_model_build_client.delete_build(project_id, model_id, build.id)
        except Exception as e:
            log.info(f"Failed to delete build {build.id} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def existing_ml_model_build(
    existing_ml_project,
    existing_ml_model,
    ml_model_build_client,
    ml_runtime_identifier,
    ml_project_script,
) -> Generator[MlModelBuild, None, None]:
    """Fixture to create a module-scoped CML model build and clean it up afterwards."""
    build = ml_model_build_client.create_build(
        existing_ml_project.id,
        existing_ml_model.id,
        MlModelBuild(
            file_path=ml_project_script,
            function_name="predict",
            runtime_identifier=ml_runtime_identifier,
            comment="existing-build",
        ),
    )

    yield build

    # Clean up after the test (module scope, cannot use purge_ml_model_build fixture)
    try:
        if isinstance(build.id, str):
            ml_model_build_client.delete_build(
                existing_ml_project.id,
                existing_ml_model.id,
                build.id,
            )
    except Exception as e:
        log.info(f"Failed to delete build {build.id} during cleanup: {str(e)}")


@pytest.fixture()
def deletable_ml_model_build(
    existing_ml_project,
    existing_ml_model,
    ml_model_build_client,
    ml_runtime_identifier,
    ml_project_script,
    purge_ml_model_build,
) -> Generator[MlModelBuild, None, None]:
    """Fixture to create a function-scoped CML model build and clean it up if needed."""
    build = ml_model_build_client.create_build(
        existing_ml_project.id,
        existing_ml_model.id,
        MlModelBuild(
            file_path=ml_project_script,
            function_name="predict",
            runtime_identifier=ml_runtime_identifier,
            comment="deletable-build",
        ),
    )

    # Register for deletion after test
    purge_ml_model_build(existing_ml_project.id, existing_ml_model.id, build)

    yield build


@pytest.fixture(scope="module")
def ml_project_file_client(ml_rest_client) -> MlProjectFileClient:
    """Fixture to create an MlProjectFileClient instance."""
    return MlProjectFileClient(api_client=ml_rest_client)


@pytest.fixture
def purge_ml_file(
    ml_project_file_client,
) -> Generator[Callable[[str, str], str], None, None]:
    """Factory fixture to register CML project files for cleanup after the test."""
    files: List[tuple] = []

    def _add_file(project_id: str, path: str) -> str:
        files.append((project_id, path))
        return path

    yield _add_file

    # Clean up after the test
    for project_id, path in files:
        try:
            ml_project_file_client.delete_file(project_id, path)
        except Exception as e:
            log.info(f"Failed to delete file {path} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def existing_ml_file(
    existing_ml_project,
    ml_project_file_client,
) -> Generator[MlFile, None, None]:
    """Fixture to upload a module-scoped project file and clean it up afterwards."""
    path = "pytest-existing.py"
    ml_project_file_client.upload_file(
        existing_ml_project.id,
        path,
        content="# created by pytest\nprint('existing')\n",
    )

    yield MlFile(path=path)

    try:
        ml_project_file_client.delete_file(existing_ml_project.id, path)
    except Exception as e:
        log.info(f"Failed to delete file {path} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def ml_project_script(
    existing_ml_project,
    ml_project_file_client,
) -> Generator[str, None, None]:
    """Fixture ensuring an entrypoint script exists in the project for applications.

    CML rejects application creation when the entrypoint script is not a real
    file within the project, so applications must seed this first. The file is
    removed on teardown (before the enclosing project is deleted) to keep the
    project filesystem clean for deletion.
    """
    path = "app.py"
    ml_project_file_client.upload_file(
        existing_ml_project.id,
        path,
        content="# created by pytest\nprint('app')\n",
    )

    yield path

    try:
        ml_project_file_client.delete_file(existing_ml_project.id, path)
    except Exception as e:
        log.info(f"Failed to delete script {path} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def ml_model_script(
    existing_ml_project,
    ml_project_file_client,
) -> Generator[str, None, None]:
    """Fixture seeding a servable model script (with a ``predict`` function).

    A model build compiles this file into a servable artifact, so the entrypoint
    function must exist for the build to succeed and be deployable.
    """
    path = "model.py"
    ml_project_file_client.upload_file(
        existing_ml_project.id,
        path,
        content=(
            "# created by pytest\n"
            "def predict(args):\n"
            "    return {'result': args}\n"
        ),
    )

    yield path

    try:
        ml_project_file_client.delete_file(existing_ml_project.id, path)
    except Exception as e:
        log.info(f"Failed to delete script {path} during cleanup: {str(e)}")


# Terminal CML model build statuses.
_ML_BUILD_SUCCESS = {"built", "succeeded"}
_ML_BUILD_FAILURE = {"build failed", "timedout", "unknown"}


@pytest.fixture(scope="module")
def built_ml_model_build(
    existing_ml_project,
    existing_ml_model,
    ml_model_build_client,
    ml_model_runtime_identifier,
    ml_model_script,
) -> Generator[MlModelBuild, None, None]:
    """Create a model build and block until it finishes building.

    Model builds compile and push a container image asynchronously (the
    C(pushing) phase alone can take several minutes), so tests that need a
    deployable build must wait for a terminal status. Tune the poll ceiling with
    the C(CML_BUILD_TIMEOUT) env var (seconds; default 1200). Marked implicitly
    slow via the consuming test.
    """
    build = ml_model_build_client.create_build(
        existing_ml_project.id,
        existing_ml_model.id,
        MlModelBuild(
            file_path=ml_model_script,
            function_name="predict",
            runtime_identifier=ml_model_runtime_identifier,
            comment="built-build",
        ),
    )

    timeout = int(os.getenv("CML_BUILD_TIMEOUT", "1200"))
    interval = int(os.getenv("CML_BUILD_POLL_INTERVAL", "15"))
    deadline = time.monotonic() + timeout
    status = build.status
    while time.monotonic() < deadline:
        current = ml_model_build_client.describe_build(
            existing_ml_project.id,
            existing_ml_model.id,
            build.id,
        )
        status = current.status if current else status
        if status in _ML_BUILD_SUCCESS:
            build = current
            break
        if status in _ML_BUILD_FAILURE:
            pytest.fail(f"Model build {build.id} ended in status '{status}'")
        time.sleep(interval)
    else:
        pytest.fail(
            f"Model build {build.id} did not finish within {timeout}s "
            f"(last status '{status}')",
        )

    yield build

    try:
        if isinstance(build.id, str):
            ml_model_build_client.delete_build(
                existing_ml_project.id,
                existing_ml_model.id,
                build.id,
            )
    except Exception as e:
        log.info(f"Failed to delete build {build.id} during cleanup: {str(e)}")


@pytest.fixture
def purge_ml_model_deployment(
    ml_model_deployment_client,
) -> Generator[
    Callable[[str, str, str, MlModelDeployment], MlModelDeployment],
    None,
    None,
]:
    """Factory fixture to register CML model deployments for cleanup after the test."""
    deployments: List[tuple] = []

    def _add_deployment(
        project_id: str,
        model_id: str,
        build_id: str,
        deployment: MlModelDeployment,
    ) -> MlModelDeployment:
        deployments.append((project_id, model_id, build_id, deployment))
        return deployment

    yield _add_deployment

    # Clean up after the test: stop then delete (best effort).
    for project_id, model_id, build_id, deployment in deployments:
        if not isinstance(deployment.id, str):
            continue
        for action in (
            ml_model_deployment_client.stop_deployment,
            ml_model_deployment_client.delete_deployment,
        ):
            try:
                action(project_id, model_id, build_id, deployment.id)
            except Exception as e:
                log.info(
                    f"Failed to {action.__name__} {deployment.id} during cleanup: {str(e)}",
                )


# ---------------------------------------------------------------------------
# Ranger Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ranger_rest_client(request) -> AnsibleServicesClient:
    """
    Fixture to create an AnsibleServicesClient instance for the Ranger Admin
    endpoint. This fixture's Ansible module is used for set up and teardown of
    Ranger test resources (module-scope).

    Ranger authenticates with HTTP basic auth, which fetch_url performs natively
    from the url_username / url_password / force_basic_auth module parameters.

    It checks for the following required environment variables set at the module
    and skips tests if any are missing:
    - RANGER_API_URL
    - RANGER_API_USERNAME
    - RANGER_API_PASSWORD
    """
    required_vars = getattr(request.module, "REQUIRED_ENV_VARS", [])
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")

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
            "url": os.environ["RANGER_API_URL"],
            "url_username": os.environ["RANGER_API_USERNAME"],
            "url_password": os.environ["RANGER_API_PASSWORD"],
            "validate_certs": os.environ.get("RANGER_VALIDATE_CERTS", "false").lower()
            == "true",
        },
    )

    # Create the AnsibleServicesClient instance
    return AnsibleServicesClient(
        module=module,
        cookies=CookieJar(),
    )


@pytest.fixture(scope="module")
def ranger_service_client(ranger_rest_client) -> RangerServiceClient:
    """Fixture to create a RangerServiceClient instance."""
    return RangerServiceClient(api_client=ranger_rest_client)


@pytest.fixture(scope="session")
def ranger_service_type() -> str:
    """Provide the Ranger service type used to create test services.

    Defaults to ``tag``, a built-in Ranger service definition that has no
    required connection configs, so test services can be created without any
    external backend. Override with RANGER_TEST_SERVICE_TYPE (e.g. ``hdfs``).
    """
    return os.environ.get("RANGER_TEST_SERVICE_TYPE", "tag")


@pytest.fixture
def purge_ranger_service(
    ranger_service_client,
) -> Generator[Callable[[RangerService], RangerService], None, None]:
    """Factory fixture to register services for cleanup after the test."""
    service_ids: List[int] = []

    def _register(service: RangerService) -> RangerService:
        if service and getattr(service, "id", None):
            service_ids.append(service.id)
        return service

    yield _register

    # Clean up after the test
    for service_id in service_ids:
        try:
            ranger_service_client.delete_service_by_id(service_id)
        except Exception as e:
            log.info(
                f"Failed to delete service {service_id} during cleanup: {str(e)}",
            )


@pytest.fixture(scope="module")
def existing_ranger_service(
    request,
    ranger_service_client,
    ranger_service_type,
) -> Generator[RangerService, None, None]:
    """Fixture to create a module-scoped test service for read-only tests."""
    service_name = f"ansible-test-existing-{request.node.name.lower().rstrip('.py')}"

    # Clean up any existing test service with the same name
    stale = ranger_service_client.get_service_by_name(service_name)
    if stale is not None:
        ranger_service_client.delete_service_by_id(stale.id)

    service = ranger_service_client.create_service(
        RangerService(
            name=service_name,
            type=ranger_service_type,
            description="Existing service created by pytest",
        ),
    )

    yield service

    # Clean up after the test (module scope, cannot use purge_ranger_service fixture)
    try:
        ranger_service_client.delete_service_by_id(service.id)
    except Exception as e:
        log.info(f"Failed to delete service {service.id} during cleanup: {str(e)}")


@pytest.fixture
def deletable_ranger_service(
    request,
    ranger_service_client,
    ranger_service_type,
    purge_ranger_service,
) -> Generator[RangerService, None, None]:
    """Fixture to create a function-scoped test service that can be modified or deleted."""
    service_name = f"ansible-test-deletable-{request.node.name.lower()}"

    # Clean up any existing test service with the same name
    stale = ranger_service_client.get_service_by_name(service_name)
    if stale is not None:
        ranger_service_client.delete_service_by_id(stale.id)

    service = ranger_service_client.create_service(
        RangerService(
            name=service_name,
            type=ranger_service_type,
            description="Deletable service created by pytest - safe to delete",
        ),
    )

    # Register for deletion after test
    purge_ranger_service(service)

    yield service


# ---------------------------------------------------------------------------
# Ranger Policy Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ranger_policy_client(ranger_rest_client) -> RangerPolicyClient:
    """Fixture to create a RangerPolicyClient instance."""
    return RangerPolicyClient(api_client=ranger_rest_client)


def _policy_test_resource(suffix: str = "default") -> Dict[str, Any]:
    """Resource block for test policies, matching the default ``tag`` service type.

    Override the base tag value with RANGER_TEST_POLICY_TAG. If
    RANGER_TEST_SERVICE_TYPE is set to something other than ``tag``, supply
    matching resources in the test.

    A unique ``suffix`` keeps each policy's resource distinct: Ranger rejects two
    policies that share the same resource within a single service.
    """
    base_tag = os.environ.get("RANGER_TEST_POLICY_TAG", "ansible-test-tag")
    return {"tag": {"values": [f"{base_tag}-{suffix}"]}}


@pytest.fixture(scope="module")
def ranger_policy_test_service(
    request,
    ranger_service_client,
    ranger_service_type,
) -> Generator[RangerService, None, None]:
    """Create a module-scoped Ranger service to host test policies."""
    service_name = f"ansible-test-policy-svc-{request.node.name.lower().rstrip('.py')}"

    # Clean up any stale service with the same name.
    stale = ranger_service_client.get_service_by_name(service_name)
    if stale is not None:
        ranger_service_client.delete_service_by_id(stale.id)

    service = ranger_service_client.create_service(
        RangerService(
            name=service_name,
            type=ranger_service_type,
            description="Service hosting pytest policies",
        ),
    )

    yield service

    # Deleting the service removes any policies still attached to it.
    try:
        ranger_service_client.delete_service_by_id(service.id)
    except Exception as e:
        log.info(f"Failed to delete policy test service {service.id}: {str(e)}")


@pytest.fixture
def ranger_purge_policy(
    ranger_policy_client,
) -> Generator[Callable[[RangerPolicy], RangerPolicy], None, None]:
    """Factory fixture to register policies for cleanup after the test."""
    policy_ids: List[int] = []

    def _register(policy: RangerPolicy) -> RangerPolicy:
        if policy and getattr(policy, "id", None):
            policy_ids.append(policy.id)
        return policy

    yield _register

    # Clean up after the test.
    for policy_id in policy_ids:
        try:
            ranger_policy_client.delete_policy_by_id(policy_id)
        except Exception as e:
            log.info(f"Failed to delete policy {policy_id} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def ranger_existing_policy(
    request,
    ranger_policy_client,
    ranger_policy_test_service,
) -> Generator[RangerPolicy, None, None]:
    """Fixture to create a module-scoped test policy for read-only tests."""
    node_name = request.node.name.lower().rstrip(".py")
    policy_name = f"ansible-test-existing-policy-{node_name}"

    # Clean up any stale policy with the same name.
    stale = ranger_policy_client.get_policy_by_name(
        service_name=ranger_policy_test_service.name,
        policy_name=policy_name,
    )
    if stale is not None:
        ranger_policy_client.delete_policy_by_id(stale.id)

    policy = ranger_policy_client.create_policy(
        RangerPolicy(
            name=policy_name,
            service=ranger_policy_test_service.name,
            description="Existing policy created by pytest",
            resources=_policy_test_resource(f"existing-{node_name}"),
        ),
    )

    yield policy

    # Clean up after the test (module scope, cannot use ranger_purge_policy fixture).
    try:
        ranger_policy_client.delete_policy_by_id(policy.id)
    except Exception as e:
        log.info(f"Failed to delete policy {policy.id} during cleanup: {str(e)}")


@pytest.fixture
def ranger_deletable_policy(
    request,
    ranger_policy_client,
    ranger_policy_test_service,
    ranger_purge_policy,
) -> Generator[RangerPolicy, None, None]:
    """Fixture to create a function-scoped test policy that can be modified or deleted."""
    policy_name = f"ansible-test-deletable-policy-{request.node.name.lower()}"

    # Clean up any stale policy with the same name.
    stale = ranger_policy_client.get_policy_by_name(
        service_name=ranger_policy_test_service.name,
        policy_name=policy_name,
    )
    if stale is not None:
        ranger_policy_client.delete_policy_by_id(stale.id)

    policy = ranger_policy_client.create_policy(
        RangerPolicy(
            name=policy_name,
            service=ranger_policy_test_service.name,
            description="Deletable policy created by pytest - safe to delete",
            resources=_policy_test_resource(f"deletable-{request.node.name.lower()}"),
        ),
    )

    # Register for deletion after test.
    ranger_purge_policy(policy)

    yield policy
