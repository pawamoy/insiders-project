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
- `insiders pypi`: Register names on PyPI.
- `insiders team`: Grant/revoke access to a private GitHub organization team to/from your sponsors.

More documentation will be added later, for now ask @pawamoy for details (see where I can be reached on my profile) 🙂
