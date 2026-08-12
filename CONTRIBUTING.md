# Contributing

Use Python 3.10 or newer and install the development environment with
`uv sync --extra dev`. Before submitting a change, run the lint, formatting,
test, and build commands from the README.

Extraction JSON is an external contract. Add validation, serialization, and
round-trip tests when changing it. Provider-specific response shapes must stay
behind the provider boundary; deterministic conversion must remain usable
without credentials or network access.

## Releasing

Releases are published to PyPI by `.github/workflows/release.yml`, which runs on
a pushed `v*` tag and uploads through Trusted Publishing - no API token is
stored in the repository.

One-time setup, both maintainer actions outside this repository's files:

1. On PyPI, add a *pending* publisher for the project name `pdf-to-carve`:
   owner `markup-carve`, repository `pdf-to-carve`, workflow `release.yml`,
   environment `pypi`.
2. In the repository settings, create an environment named `pypi`. The publish
   job is bound to it, so restricting who may approve it also restricts who may
   release.

Per release:

1. Move the entries under the version heading in `CHANGELOG.md` and set its
   date.
2. Set `project.version` in `pyproject.toml`. The workflow refuses to publish
   when the tag and that version disagree, so the two cannot drift.
3. Tag `vX.Y.Z` and push the tag.

