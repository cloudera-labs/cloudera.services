# cloudera.services - Cloudera Data Platform (CDP) for Public and Private Cloud data and compute services

[![API documentation](https://github.com/cloudera-labs/cloudera.services/actions/workflows/publish_docs.yml/badge.svg?branch=main&event=push)](https://github.com/cloudera-labs/cloudera.services/actions/workflows/publish_docs.yml)
[![FOSSA Status](https://app.fossa.com/api/projects/custom%2B449%2Fgit%40github.com%3Acloudera-labs%2Fcloudera.services.git.svg?type=shield&issueType=license)](https://app.fossa.com/projects/custom%2B449%2Fgit%40github.com%3Acloudera-labs%2Fcloudera.services.git?ref=badge_shield&issueType=license)

`cloudera.services` is an Ansible collection that lets you use and manage your **[Cloudera Data Platform (CDP)](https://www.cloudera.com/products/cloudera-data-platform.html) Public and Private Cloud** execution services and resources for both data and compute. With this collection, you can:

* Create and manage [Shared Data Experience (SDX)](https://www.cloudera.com/products/cloudera-data-platform/sdx.html) assets, including:
  * Manage Atlas groups and entities
  * Manage Ranger roles and policies
* Execute your [Cloudera Machine Learning (CML)](https://www.cloudera.com/products/machine-learning.html) projects and resources, including:
  * Run jobs
  * Build and deploy models
  * Install and run [Accelerators for ML Projects (AMPs)](https://cloudera.github.io/Applied-ML-Prototypes/#/)
  * Construct DataViz applications
* Manage and orchestrate [Cloudera DataFlow (CDF)](https://www.cloudera.com/products/dataflow.html) NiFi flows
* Manage and control [Cloudera Stream Processing (CSP)](https://www.cloudera.com/products/stream-processing.html) assets, including
  * Configure SQL Stream Builder (SSB) catalogs and data sources and run jobs
  * Create and manage Streams Messaging Manager (SSM) Kafka topics

and more!

If you have any questions, want to chat about the collection's capabilities and usage, need help using the collection, or just want to stay updated, join us at our [Discussions](https://github.com/cloudera-labs/cloudera.services/discussions).

## Quickstart

1. [Install the collection](#installation)
1. [Use the collection](#using-the-collection)

## API

See the [API documentation](https://cloudera-labs.github.io/cloudera.services/) for details for each plugin and role within the collection.

## Installation

The preferred method is to install via Ansible Galaxy; in your `requirements.yml` file, add the following:

```yaml
collections:
  - name: cloudera.services
```

If you want to install from GitHub, add to your `requirements.yml` file the following:

```yaml
collections:
  - name: https://github.com/cloudera-labs/cloudera.services.git
    type: git
    version: main
```

And then run in your project:

```bash
ansible-galaxy collection install -r requirements.yml
```

You can also install the collection directly:

```bash
# From Ansible Galaxy
ansible-galaxy collection install cloudera.services
```

```bash
# From GitHub
ansible-galaxy collection install git+https://github.com/cloudera-labs/cloudera.services.git@main
```

`ansible-builder` can discover and install all Python dependencies - current collection and dependencies - if you wish to use that application to construct your environment. Otherwise, you will need to read each collection and role dependency and follow its installation instructions.

See the [Collection Metadata](https://ansible.readthedocs.io/projects/builder/en/latest/collection_metadata/) section for further details on how to install (and manage) collection dependencies.

You may wish to use a _virtual environment_ to manage the Python dependencies.

## Using the Collection

Once installed, reference the collection in your playbooks and roles.

For example, here we use the
[`cloudera.services.ssb_project_info` module](https://cloudera-labs.github.io/cloudera.services/ssb_project_info_module.html) to discover details regarding available SQL Stream Builder (SSB) projects:

```yaml
- hosts: localhost
  connection: local
  gather_facts: no
  tasks:
    - name: List all SSB projects
      cloudera.services.ssb_project_list:
        endpoint: "https://example.cldr.com/ssb_endpoint"
```

## Building the API Documentation

To create a local copy of the API documentation, first make sure the collection is in your `ANSIBLE_COLLECTIONS_PATH`.

```bash
hatch run docs:build
```

Your local documentation will be found at `docsbuild/build/html`.

You can also lint the documentation with the following command:

```bash
hatch run lint
```

## Preparing a New Version

To prepare a version release, first set the following variables for `antsichaut`:

```bash
export GITHUB_TOKEN=some_gh_token_value # Read-only scope
```

Update the collection version using [`hatch version`](https://hatch.pypa.io/latest/version/). For example, to increment to the next _minor_ release:

```bash
hatch version minor
```

Then update the changelog to query the pull requests since the last release.

```bash
hatch run docs:changelog
```

You can then examine (and update if needed) the resulting `changelog.yaml` and `CHANGELOG.rst` files before committing to the release branch.

## Roadmap

If you want to see what we are working on or have pending, check out:

*  the [Milestones](https://github.com/cloudera-labs/cloudera.services/milestones) and [active issues](https://github.com/cloudera-labs/cloudera.services/issues?q=is%3Aissue+is%3Aopen+milestone%3A*) to see our current activity,
* the [issue backlog](https://github.com/cloudera-labs/cloudera.services/issues?q=is%3Aopen+is%3Aissue+no%3Amilestone) to see what work is pending or under consideration, and
* read up on the [Ideas](https://github.com/cloudera-labs/cloudera.services/discussions/categories/ideas) we have in mind.

Are we missing something? Let us know by [creating a new issue](https://github.com/cloudera-labs/cloudera.services/issues/new) or [posting a new idea](https://github.com/cloudera-labs/cloudera.services/discussions/new?category=ideas)!

## Contribute

For more information on how to get involved with the `cloudera.services` Ansible collection, head over to [CONTRIBUTING.md](CONTRIBUTING.md).

## License and Copyright

Copyright 2026, Cloudera, Inc.

```
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
