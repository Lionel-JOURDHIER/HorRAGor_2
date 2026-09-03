# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

project = 'HorRAGor'
copyright = '2026, simplon team'
author = 'simplon team'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "myst_parser",
    "sphinx.ext.graphviz",
    ]

templates_path = ['_templates']
exclude_patterns = []

language = 'fr'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"

html_title = "HorRAGor"

html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#7c3aed",
        "color-brand-content": "#6d28d9",
    },
    "dark_css_variables": {
        "color-brand-primary": "#a78bfa",
        "color-brand-content": "#c4b5fd",
    },
}

html_static_path = ['_static']
html_css_files = [
    "custom.css",
]