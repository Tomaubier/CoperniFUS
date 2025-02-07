# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os, sys
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("../"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'CoperniFUS'
copyright = '2025, Tom Aubier'
author = 'Tom Aubier'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',  # For Google/NumPy-style docstrings
    'sphinx.ext.autosummary',  # Optional: for summaries
    'sphinx_autodoc_typehints',  # If using type hints
    "sphinx_mdinclude",
    "nbsphinx" # Import notebook
]

# Napoleon settings (for Google or NumPy-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
autodoc_member_order = 'bysource' # Class attributes ordering

source_suffix = [".rst", ".md"]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
exclude_patterns = ["README.md", "_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']