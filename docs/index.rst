.. CoperniFUS documentation master file, created by
   sphinx-quickstart on Mon Jan 13 14:51:15 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

========================
CoperniFUS documentation
========================
CoperniFUS: A flexible Python-based GUI for stereotaxic experiment planning.

.. image:: /_static/CoperniFUS_screenshot.png

.. include:: contents/key_features.rst

General Application Structure
-----------------------------

``CoperniFUS`` is architectured around three main components:
 - the ``Viewer`` hosting the 3D viewport and all UI elements
 - ``Modules`` which allow the manipulation of data displayed in the viewport
 - and ``Armatures`` which are submodules lying in the *Stereotaxic Frame* module and allow the user to conduct operations in the spatial coordinate frames of a stereotaxic aparatus.

.. image:: /_static/CoperniFUS_ui_breakdown.png

Detailed information of the app structure can be found in `the API reference page <contents/api_reference.rst>`_. 

.. include:: contents/related_projects.rst

Documentation Structure
-----------------------

.. toctree::
   :titlesonly:

   contents/key_features
   contents/installation
   contents/usage
   contents/api_reference
   contents/related_projects
   Github <https://github.com/Tomaubier/CoperniFUS>
