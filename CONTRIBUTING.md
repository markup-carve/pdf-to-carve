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
a pushed `v*` tag. The publish job prefers a `PYPI_API_TOKEN` secret when one is
set and otherwise uploads through Trusted Publishing, which stores no
credential at all.

One-time setup, all of it outside this repository's files:

1. In the repository settings, create an environment named `pypi`. The publish
   job is bound to it, so restricting who may approve it also restricts who may
   release.
2. Give the first release a credential, either way round:
   - **Trusted Publishing, no secret.** On PyPI, add a *pending* publisher for
     the project name `pdf-to-carve`: owner `markup-carve`, repository
     `pdf-to-carve`, workflow `release.yml`, environment `pypi`. PyPI supports
     pending publishers precisely so a name that does not exist yet can be
     claimed this way.
   - **API token.** Set `PYPI_API_TOKEN` as a repository secret. A token for a
     project that does not exist yet has to be account-scoped, because
     project-scoped tokens cannot be minted before the project does. Treat that
     as a bootstrap credential: after the first upload, add a trusted publisher
     on the now-existing PyPI project and `gh secret delete PYPI_API_TOKEN`, so
     the broad credential stops living in the repository.

Trusted Publishing needs no token in either case; the token path exists only so
a first publish is not blocked on PyPI-side configuration.

Per release:

1. Move the entries under the version heading in `CHANGELOG.md` and set its
   date.
2. Set `project.version` in `pyproject.toml`. The workflow refuses to publish
   when the tag and that version disagree, so the two cannot drift.
3. Tag `vX.Y.Z` and push the tag.

