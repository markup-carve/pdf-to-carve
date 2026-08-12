# Contributing

Use Python 3.10 or newer and install the development environment with
`uv sync --extra dev`. Before submitting a change, run the lint, formatting,
test, and build commands from the README.

Extraction JSON is an external contract. Add validation, serialization, and
round-trip tests when changing it. Provider-specific response shapes must stay
behind the provider boundary; deterministic conversion must remain usable
without credentials or network access.

