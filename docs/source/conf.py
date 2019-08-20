# Configuration file for the Sphinx documentation builder.
# Documentation:
# http://www.sphinx-doc.org/en/master/config

import os
import sys
import subprocess

# -- Path setup --------------------------------------------------------------
_ROOT = os.path.join('..', '..')

sys.path.append(os.path.abspath(os.path.join(_ROOT, 'src')))

# -- Project information -----------------------------------------------------

project = 'GOG Galaxy Integrations API'
copyright = '2019, GOG.com'

_author, _version = subprocess.check_output(
    ['python', os.path.join(_ROOT, 'setup.py'), '--author', '--version'],
    universal_newlines=True).strip().split('\n')

author = _author
version = _version
release = _version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinxcontrib.asyncio',
    'sphinx_autodoc_typehints',
    'm2r'  # mdinclude directive for makrdown files
]
autodoc_member_order = 'bysource'
autodoc_inherit_docstrings = False
autodoc_mock_imports = ["galaxy.http"]

set_type_checking_flag = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [] # type: ignore


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    # 'canonical_url': '',  # main page to be serach in google with trailing slash
    'display_version': True,
    'style_external_links': True,
    # Toc options
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

master_doc = 'index'
