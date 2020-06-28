# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

import os
import re
import sys

# this adds the equivalent of "../../" to the python path
PACKAGEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PACKAGEDIR)


# -- Project information -----------------------------------------------------

project = "pytorch-widedeep"
copyright = "2020, Javier Rodriguez Zaurin"
author = "Javier Rodriguez Zaurin"

# # The full version, including alpha/beta/rc tags
# def get_version():
#     r"""

#     Get the current version number for the library
#     Returns
#     -------
#     String
#         Of the form "<major>.<minor>.<micro>", in which "major", "minor" and "micro" are numbers

# 	"""
#     with open("../pytorch_widedeep/VERSION") as f:
#         return f.read().strip()
# release = get_version()

with open(os.path.join(PACKAGEDIR, "pytorch_widedeep", "version.py")) as f:
    version = re.search(r"__version__ \= \"(\d+\.\d+\.\d+)\"", f.read())
    assert version is not None, "can't parse __version__ from __init__.py"
    version = version.groups()[0]
    assert len(version.split(".")) == 3, "bad version spec"
    release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    'sphinx_autodoc_typehints',
    "numpydoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
]


# need to do this otherwise won't find numpy autodocs (yes, it's a shame)
numpydoc_class_members_toctree = False
numpydoc_show_class_members = True
add_module_names = False
autosummary_generate = True

autoclass_content = "init"

autodoc_default_flags = ['members', 'inherited-members']
# autodoc_default_flags = ["show-inheritance"]
autodoc_default_options = {'special-members': '__call__'}
# autodoc_member_order = 'alphabetical'
autodoc_member_order = "bysource"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames. You can specify multiple suffix as a list of string: `source_suffix = ['.rst', '.md']`
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation for a list of supported languages. This is also used
# if you do content translation via gettext catalogs. Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
# html_theme_path = ['_themes']

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# options for
html_theme_options = {
    "canonical_url": "",
    # 'analytics_id': 'UA-XXXXXXX-1',  #  Provided by Google in your dashboard
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    # Toc options
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

modindex_common_prefix = ["pytorch_widedeep."]

# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "pytorch_widedeepdoc"


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        "pytorch_widedeep.tex",
        "pytorch_widedeep Documentation",
        "Javier Rodriguez Zaurin",
        "manual",
    ),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, "pytorch_widedeep", "pytorch_widedeep Documentation", [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "pytorch_widedeep",
        "pytorch_widedeep Documentation",
        author,
        "pytorch_widedeep",
        "One line description of project.",
        "Miscellaneous",
    ),
]


# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# add custom css and javascript
def setup(app):
    app.add_css_file("custom.css")
    # app.add_javascript('js/custom.js')
