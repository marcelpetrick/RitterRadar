# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Sphinx configuration for RitterRadar."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

project = "RitterRadar"
author  = "Marcel Petrick"
release = "0.0.18"
copyright = "2026, Marcel Petrick"  # noqa: A001

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

autodoc_default_options = {
    "members":          True,
    "undoc-members":    True,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring  = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = []

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
