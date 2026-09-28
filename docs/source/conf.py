# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Sphinx configuration for RitterRadar."""

import sys
import tomllib
from pathlib import Path

import fastapi  # noqa: F401 — import runtime before autodoc examines type stubs

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

project = "RitterRadar"
author = "Marcel Petrick"
package = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())
release = package["project"]["version"]
copyright = "2026, Marcel Petrick"  # noqa: A001

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = []

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
