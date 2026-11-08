"""Sphinx configuration for the Deadcode documentation."""

project = 'Deadcode'
author = 'Albertas Gimbutas'

extensions = ['myst_parser']
source_suffix = {
    '.md': 'markdown',
    '.rst': 'restructuredtext',
}
master_doc = 'index'
exclude_patterns = ['_build']

myst_heading_anchors = 3
suppress_warnings = ['myst.header']

html_theme = 'sphinx_rtd_theme'
html_title = 'Deadcode documentation'
html_static_path = ['_static']
html_css_files = ['custom.css']
