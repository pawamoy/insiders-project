# insiders

[![ci](https://github.com/pawamoy/insiders-project/workflows/ci/badge.svg)](https://github.com/pawamoy/insiders-project/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-mkdocs-708FCC.svg?style=flat)](https://pawamoy.github.io/insiders-project/)
[![pypi version](https://img.shields.io/pypi/v/insiders.svg)](https://pypi.org/project/insiders/)
[![gitter](https://badges.gitter.im/join%20chat.svg)](https://app.gitter.im/#/room/#insiders-project:gitter.im)

Manage your Insiders projects.

## Installation

```bash
pip install insiders
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install insiders
```

## Usage

The `insiders` tool provides several commands that will help you manage projects based on a sponsorware strategy.

- `insiders backlog`: Print a backlog of issues, ordered using your own defined criteria
- `insiders index`: Serve a PyPI-like index locally, and upload private Insiders packages to it.
- `insiders project`: Bootstrap public/insiders project pairs on GitHub.
- `insiders sponsors`: Manage your sponsors (grant/revoke access to private team, etc.).

Run `insiders -h` to see where the configuration file is found. Example configuration:

```toml
# --------------------------------------------------------------------------- #
# Backlog configuration.                                                      #
# --------------------------------------------------------------------------- #
# The `backlog` command prints a list of issues from GitHub repositories.
# It is used to keep track of what needs to be done, and to prioritize tasks.
# It integrates with sponsorships and issue boosts to let your sponsors
# influence the priority of issues.
[backlog]

# GitHub namespaces (user accounts / organizations) from which to fetch issues.
namespaces = ["pawamoy", "mkdocstrings"]

# How many issues to display when showing the backlog.
limit = 30

# Sorting criteria, in order of importance.
# TODO: Document syntax and available options.
sort = [
    "label('bug')",
    "label('unconfirmed')",
    "label('docs')",
    "label('refactor')",
    "min_sponsorships(50)",
    "min_pledge(30)",
    "min_upvotes(2)",
    "label('insiders')",
    "repository('mkdocstrings/*')",
    "created",
]

# A shell command to get your GitHub token.
github-token-command = "pass show tokens/insiders/github"

# The backlog supports issue "boosts" (funding) via Polar.
# If you have a Polar account and enabled Issue Funding,
# you can configure it here.
polar-token-command = "pass show tokens/insiders/polar"

# A map of labels to emojis, for shorter display in the backlog.
[backlog.issue-labels]
bug = "🐞"
docs = "📘"
feature = "✨"
insiders = "🔒"
unconfirmed = "❔"

# --------------------------------------------------------------------------- #
# Index configuration.                                                        #
# --------------------------------------------------------------------------- #
# The `index` command lets you serve a PyPI-like index locally,
# and upload Insiders versions of projects to it,
# so that you can install them transparently as dependencies.
# You can configure a remote index too, instead of a locally-served one.
[index]

# The URL of the index, local or remote.
url = "http://localhost:31411"

# Whether to start the index server in the background (when serving locally).
start-in-background = true

# The path to the log file of the index server (when serving locally).
log-path = "/tmp/insiders-index.log"

# --------------------------------------------------------------------------- #
# Projects configuration.                                                     #
# --------------------------------------------------------------------------- #
# The `project` command lets you create public and private projects on GitHub.
# It supports Copier templates to generate the initial project structure.
# It can also register projects on PyPI, and run post-creation commands.
# Created projects will be cloned in the specified directories.
[project]

# If your Insiders organization is named "your-username-insiders",
# you can specify your GitHub username instead of both the public
# and insiders namespaces in which projects will be created.
github-username = "pawamoy"

# Explicitly specify the public and insiders namespaces.
namespace = "pawamoy"
insiders-namespace = "pawamoy-insiders"

# Where to clone the created projects (Git repositories).
directory = "~/data/dev"
insiders-directory = "~/data/dev/insiders"

# Whether to register projects on PyPI.
register-on-pypi = false
pypi-username = "pawamoy"

# Post-creation commands to run after creating a project.
# The command only runs in the public project, not the private one.
post-creation-command = [
    "python",
    "scripts/make",
    "setup",
    "changelog",
    "release",
    "version=0.1.0",
]

# A Copier template to generate new projects from.
copier-template = "gh:pawamoy/copier-uv"

# A mapping of template questions to answers.
# TODO: Document syntax and available options.
[project.copier-template-answers]
project_name = "{public_name}"
project_description = "{description}"
author_username = "pawamoy"
repository_namespace = "{public_namespace}"
repository_name = "{public_name}"
insiders = true
insiders_repository_name = "{insiders_name}"

# --------------------------------------------------------------------------- #
# Sponsors configuration.                                                     #
# --------------------------------------------------------------------------- #
# The `sponsors` command lets you list sponsors from different platforms,
# show detailed information about a user,
# and synchronize your sponsors' access to a GitHub team,
# where your private projects are made available.
[sponsors]

# Your GitHub account receiving sponsorships.
github-sponsored-account = "pawamoy"

# A shell command to get your GitHub token.
github-token-command = "pass show tokens/insiders/github"

# Your Polar account receiving sponsorships.
polar-sponsored-account = "pawamoy"

# A shell command to get your Polar token.
polar-token-command = "pass show tokens/insiders/polar"

# The minimum amount a sponsor must pledge to be considered an insider,
# granting them access to your private projects.
minimum-amount = 10

# The GitHub team to which insiders are invited.
insiders-team = "pawamoy-insiders/insiders"

# A list of users to always include into the insiders team.
include-users = [
    "pawamoy",  # Myself.
]

# A list of users to always exclude from the insiders team.
exclude-users = []

# A map of GitHub sponsors to their beneficiaries.
# Beneficiaries are users/organizations who get voting power
# and are optionally granted access to your Insiders team.
# TODO: Document supported values.
[sponsors.github-beneficiaries]
some-github-account = [
    "some-github-user",
    "&some-github-org",
]

# A map of Polar sponsors to their beneficiaries.
# Beneficiaries are users/organizations who get voting power
# and are optionally granted access to your Insiders team.
# TODO: Document supported values.
[sponsors.polar-beneficiaries]
```

More documentation will be added later, for now ask @pawamoy for details (see where I can be reached on my profile) 🙂

