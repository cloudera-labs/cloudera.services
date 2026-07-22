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

from typing import Generator, Callable
from http.cookiejar import CookieJar
from kafka import KafkaAdminClient, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError
from pytest_mock import MockerFixture
from typing import Any, Callable, Dict, Generator, List
from unittest.mock import Mock

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.cloudera.services.plugins.module_utils.common import (
    AnsibleServicesClient,
)
from ansible_collections.cloudera.services.plugins.module_utils.ranger import (
    RangerPolicy,
    RangerPolicyClient,
    RangerPolicyResource,
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
from ansible_collections.cloudera.services.plugins.module_utils.ml import (
    CmlServicesClient,
    MlProject,
    MlProjectClient,
    MlJobClient,
    MlModelClient,
    MlApplicationClient,
    MlRuntimeClient,
    MlRuntimeAddonClient,
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
        "api_version_auto_timeout_ms": 30000,
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
def project_client(ssb_rest_client) -> SsbProjectClient:
    """Fixture to create an SSBProjectClient instance."""
    return SsbProjectClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_project(
    project_client,
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
            project_client.delete_project(project)
        except Exception as e:
            log.info(f"Failed to delete project {project.id} during cleanup: {str(e)}")


@pytest.fixture(scope="module")
def existing_project(request, project_client) -> Generator[SsbProject, None, None]:
    """Fixture to create a module-scoped test project and clean it up after the test."""
    project_name = request.node.name.lower().rstrip(".py")

    # Clean up any existing test project
    projects = project_client.list_projects()
    for project in projects:
        if project.name == project_name:
            project_client.delete_project(project)

    # Create the test project
    project = project_client.create_project(
        SsbProject(
            name=project_name,
            description="Existing project created by pytest",
        ),
    )

    yield project

    # Clean up after the test (module scope, cannot use purge_project fixture)
    try:
        project_client.delete_project(project)
    except Exception as e:
        log.info(f"Failed to delete project {project.id} during cleanup: {str(e)}")


@pytest.fixture()
def deletable_project(
    request,
    project_client,
    purge_project,
) -> Generator[SsbProject, None, None]:
    """Fixture to create a function-scoped test project and clean it up after the test if needed."""
    project_name = request.node.name.lower().rstrip(".py")

    # Clean up any existing test project
    projects = project_client.list_projects()
    for project in projects:
        if project.name == project_name:
            project_client.delete_project(project)

    # Create the test project
    project = project_client.create_project(
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
def table_client(ssb_rest_client) -> SsbTableClient:
    """Fixture to create an SSBTableClient instance."""
    return SsbTableClient(api_client=ssb_rest_client)


@pytest.fixture
def purge_table(table_client) -> Generator[Callable[[SsbTable], SsbTable], None, None]:
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
            table_client.delete_table(table.project_id, table.id)
        except Exception as e:
            log.info(f"Failed to delete table {table.id} during cleanup: {str(e)}")


@pytest.fixture
def existing_table_kafka(
    request,
    table_client,
    existing_project,
    purge_table,
    existing_data_source_kafka,
    existing_data_source_kafka_schema,
) -> Generator[SsbTable, None, None]:
    """Fixture to create and cleanup an existing table."""
    # Also is the name of the topic in Kafka via existing_data_source_kafka and smm_kafka_topic
    table_name = request.node.name.lower()

    # Clean up any existing test tables with the same name
    tables = table_client.list_tables(existing_project.id)
    for table in tables:
        if table.name == table_name:
            table_client.delete_table(table.project_id, table.id)

    table = table_client.create_table(
        project_id=existing_project.id,
        table=SsbTable(
            table_name=table_name,
            type="kafka",
            metadata={
                "endpoint": existing_data_source_kafka.id,
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
# Ranger Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ranger_rest_client(request) -> AnsibleServicesClient:
    """
    Fixture to create an AnsibleServicesClient instance for Ranger Admin.

    It checks for the following required environment variables set at the module
    and skips tests if any are missing:
    - RANGER_ADMIN_URL
    - RANGER_ADMIN_USERNAME
    - RANGER_ADMIN_PASSWORD
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
            "url": os.environ["RANGER_ADMIN_URL"],
            "url_username": os.environ["RANGER_ADMIN_USERNAME"],
            "url_password": os.environ["RANGER_ADMIN_PASSWORD"],
            "validate_certs": os.environ.get("RANGER_VALIDATE_CERTS", "false").lower()
            == "true",
            "force_basic_auth": True,
        },
    )

    # Create the AnsibleServicesClient instance
    return AnsibleServicesClient(
        module=module,
        cookies=CookieJar(),
    )


@pytest.fixture(scope="module")
def policy_client(ranger_rest_client) -> RangerPolicyClient:
    """Fixture to create a RangerPolicyClient instance."""
    return RangerPolicyClient(api_client=ranger_rest_client)


@pytest.fixture(scope="session")
def test_service():
    """Provide the name of a test Ranger service."""
    # Use an environment variable or default to a common service name
    return os.environ.get("RANGER_TEST_SERVICE", "cm_hdfs")


@pytest.fixture(scope="module")
def existing_policy(policy_client, test_service):
    """Get an existing policy from the Ranger Admin for read-only tests."""
    policies = policy_client.list_policies(service_name=test_service)

    if not policies:
        pytest.skip(
            f"No existing policies found in service '{test_service}'. "
            "Cannot run tests that require an existing policy.",
        )

    # Return the first policy found
    return policies[0]


@pytest.fixture
def deletable_policy(policy_client, test_service, purge_policy):
    """Create a policy that can be deleted/modified in tests."""
    policy = RangerPolicy(
        name=f"ansible-test-deletable-{os.getpid()}",
        service=test_service,
        description="Temporary policy for testing - safe to delete",
        resources={
            "path": RangerPolicyResource(
                values=[f"/tmp/ansible-test-{os.getpid()}"],
                is_excludes=False,
                is_recursive=False,
            ),
        },
    )

    created = policy_client.create_policy(policy)

    # Register for deletion after test
    purge_policy(created)

    yield created


@pytest.fixture
def purge_policy(
    policy_client,
) -> Generator[Callable[[RangerPolicy], RangerPolicy], None, None]:
    """Factory fixture to register policies for cleanup."""
    policies_to_delete = []

    def _register(policy: RangerPolicy) -> RangerPolicy:
        """Register a policy for cleanup."""
        if policy and hasattr(policy, "id") and policy.id:
            policies_to_delete.append(policy.id)
        return policy

    yield _register

    # Cleanup: Delete all registered policies
    for policy_id in policies_to_delete:
        try:
            policy_client.delete_policy_by_id(policy_id)
        except Exception as e:
            log.info(f"Failed to delete policy {policy_id} during cleanup: {str(e)}")


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
def ml_model_client(ml_rest_client) -> MlModelClient:
    """Fixture to create an MlModelClient instance."""
    return MlModelClient(api_client=ml_rest_client)


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

    # Clean up any existing test project with the same name
    for project in ml_project_client.list_projects():
        if project.name == project_name and isinstance(project.id, str):
            ml_project_client.delete_project(project.id)

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
