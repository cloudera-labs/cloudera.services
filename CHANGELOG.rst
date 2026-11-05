===============================
cloudera.services Release Notes
===============================

.. contents:: Topics

v1.1.0
======

Minor Changes
-------------

- Add Atlas module utilities, fixtures, and atlas_enum_def and atlas_typedef_info modules (https://github.com/cloudera-labs/cloudera.services/pull/20)
- Add Ranger Policy modules (https://github.com/cloudera-labs/cloudera.services/pull/17)
- Add Ranger Role modules (https://github.com/cloudera-labs/cloudera.services/pull/18)
- Add Ranger policy and role modules to action groups (https://github.com/cloudera-labs/cloudera.services/pull/26)
- Add Ranger service modules (https://github.com/cloudera-labs/cloudera.services/pull/15)
- Add SSB action groups (https://github.com/cloudera-labs/cloudera.services/pull/27)
- Add atlas_business_metadata_def module and unit and integration tests (https://github.com/cloudera-labs/cloudera.services/pull/25)
- Add atlas_classification_def module (https://github.com/cloudera-labs/cloudera.services/pull/21)
- Add atlas_entity_business_metadata module and unit and integration tests (https://github.com/cloudera-labs/cloudera.services/pull/42)
- Add atlas_entity_def module and unit and integration tests (https://github.com/cloudera-labs/cloudera.services/pull/22)
- Add atlas_entity_info module and unit and integration tests (https://github.com/cloudera-labs/cloudera.services/pull/36)
- Add atlas_entity_label module and unit and integration tests (https://github.com/cloudera-labs/cloudera.services/pull/39)
- Add atlas_relationship_def module and unit and integration tests (https://github.com/cloudera-labs/cloudera.services/pull/24)
- Add atlas_struct_def module and unit and integration tests (https://github.com/cloudera-labs/cloudera.services/pull/23)
- Add integration tests for Atlas entity label module utility functions (https://github.com/cloudera-labs/cloudera.services/pull/43)
- Add smm_kafka_topic modules (https://github.com/cloudera-labs/cloudera.services/pull/37)
- Consolidate Atlas TypeDef module utilities (https://github.com/cloudera-labs/cloudera.services/pull/32)
- Consolidate Atlas TypeDef testing utilities (https://github.com/cloudera-labs/cloudera.services/pull/33)
- Refactor Atlas EnumDef and ClassificationDef bundle extraction (https://github.com/cloudera-labs/cloudera.services/pull/31)
- Update Atlas documentation for consolidated TypeDef functions and test utilities (https://github.com/cloudera-labs/cloudera.services/pull/34)
- Update ML action groups (https://github.com/cloudera-labs/cloudera.services/pull/28)
- Update ServicesClient data parameter annotations (https://github.com/cloudera-labs/cloudera.services/pull/35)
- Update environment payload handling in ML project (https://github.com/cloudera-labs/cloudera.services/pull/19)
- Update replica and ISR descriptions to use RV notation in smm_kafka_topic  modules (https://github.com/cloudera-labs/cloudera.services/pull/38)
- Update ssb_job module with 'wait' parameter (https://github.com/cloudera-labs/cloudera.services/pull/40)

New Modules
-----------

- cloudera.services.atlas_business_metadata_def - Manage business metadata type definitions in Apache Atlas.
- cloudera.services.atlas_classification_def - Manage classification type definitions in Apache Atlas.
- cloudera.services.atlas_entity_business_metadata - Manage business metadata on an Apache Atlas entity.
- cloudera.services.atlas_entity_def - Manage entity type definitions in Apache Atlas.
- cloudera.services.atlas_entity_info - Retrieve an entity from Apache Atlas.
- cloudera.services.atlas_entity_label - Manage the labels of an Apache Atlas entity.
- cloudera.services.atlas_enum_def - Manage enum type definitions in Apache Atlas.
- cloudera.services.atlas_relationship_def - Manage relationship type definitions in Apache Atlas.
- cloudera.services.atlas_struct_def - Manage struct type definitions in Apache Atlas.
- cloudera.services.atlas_typedef_info - Retrieve type definitions from Apache Atlas.
- cloudera.services.ranger_policy - Manage policies in Apache Ranger.
- cloudera.services.ranger_policy_info - Retrieve policy details from Apache Ranger.
- cloudera.services.ranger_role - Manage roles in Apache Ranger.
- cloudera.services.ranger_role_info - Retrieve role details from Apache Ranger.
- cloudera.services.ranger_service - Manage services in Apache Ranger.
- cloudera.services.ranger_service_info - Retrieve service details from Apache Ranger.
- cloudera.services.smm_kafka_topic - Manage Kafka topics in Streams Messaging Manager.
- cloudera.services.smm_kafka_topic_info - Retrieve Kafka topic details from Streams Messaging Manager.

v1.0.0
======

New Modules
-----------

- cloudera.services.ml_project - Create and delete Cloudera Machine Learning (CML) projects.
- cloudera.services.ml_project_application - Manage a Cloudera Machine Learning (CML) project application.
- cloudera.services.ml_project_application_info - Retrieve information about Cloudera Machine Learning (CML) project applications.
- cloudera.services.ml_project_file - Manage a file within a Cloudera Machine Learning (CML) project.
- cloudera.services.ml_project_file_info - Retrieve information about files within a Cloudera Machine Learning (CML) project.
- cloudera.services.ml_project_info - Retrieve information about Cloudera Machine Learning (CML) projects.
- cloudera.services.ml_project_job - Manage a Cloudera Machine Learning (CML) project job.
- cloudera.services.ml_project_job_info - Retrieve information about Cloudera Machine Learning (CML) project jobs.
- cloudera.services.ml_project_job_run - Start or stop a Cloudera Machine Learning (CML) project job run.
- cloudera.services.ml_project_job_run_info - Retrieve information about Cloudera Machine Learning (CML) project job runs.
- cloudera.services.ml_project_model - Manage a Cloudera Machine Learning (CML) project model.
- cloudera.services.ml_project_model_build - Manage a Cloudera Machine Learning (CML) project model build.
- cloudera.services.ml_project_model_build_info - Retrieve information about Cloudera Machine Learning (CML) project model builds.
- cloudera.services.ml_project_model_deployment - Manage a Cloudera Machine Learning (CML) project model deployment.
- cloudera.services.ml_project_model_deployment_info - Retrieve information about Cloudera Machine Learning (CML) project model deployments.
- cloudera.services.ml_project_model_info - Retrieve information about Cloudera Machine Learning (CML) project models.
- cloudera.services.ml_runtime - Register or set the status of a Cloudera Machine Learning (CML) runtime.
- cloudera.services.ml_runtime_addon - Manage the status of Cloudera Machine Learning (CML) runtime addons.
- cloudera.services.ml_runtime_addon_info - Retrieve information about Cloudera Machine Learning (CML) runtime addons.
- cloudera.services.ml_runtime_info - Retrieve information about Cloudera Machine Learning (CML) runtimes.
- cloudera.services.ml_runtime_repo - Manage a Cloudera Machine Learning (CML) runtime repository.
- cloudera.services.ml_runtime_repo_info - Retrieve information about Cloudera Machine Learning (CML) runtime repositories.
- cloudera.services.ssb_data_source - Manage SSB project data sources.
- cloudera.services.ssb_data_source_info - Retrieve information about SSB project data sources.
- cloudera.services.ssb_environment - Manage SSB project environments.
- cloudera.services.ssb_environment_info - Retrieve information about SSB project environments.
- cloudera.services.ssb_job - Manage SSB jobs.
- cloudera.services.ssb_job_info - Retrieve information about SSB jobs.
- cloudera.services.ssb_project - Manage SSB projects.
- cloudera.services.ssb_project_info - Retrieve information about SSB projects.
- cloudera.services.ssb_table - Manage SSB project tables.
- cloudera.services.ssb_table_info - Retrieve information about SSB project tables.
- cloudera.services.ssb_udf - Manage SSB User Defined Functions (UDFs).
- cloudera.services.ssb_udf_info - Retrieve information about SSB project User Defined Functions (UDFs).
- cloudera.services.ssb_user - Manage the current SSB user's settings.
- cloudera.services.ssb_user_info - Retrieve information about the current SSB user.
- cloudera.services.ssb_user_keytab - Set the user keytab in SSB.
