"""Sphinx configuration for http-ping documentation."""

from importlib.metadata import version as pkg_version

# -- Project information ------------------------------------------------------

project = "http-ping"
author = "Derafu"
release = pkg_version("http-ping")

# -- General configuration ----------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",     # Pull docstrings from source code.
    "sphinx.ext.viewcode",    # Add links to highlighted source code.
    "sphinx.ext.napoleon",    # Support Google/NumPy docstring styles.
]

# -- HTML output --------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_extra_path = ["CNAME"]   # Copied as-is to the build output.
