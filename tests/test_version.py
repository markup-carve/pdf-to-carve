"""Keep the package version aligned with build metadata."""

from importlib.metadata import version

from pdf_to_carve import __version__


def test_package_version_matches_distribution() -> None:
    assert __version__ == version("pdf-to-carve")
