.. CoperniFUS documentation master file, created by
   sphinx-quickstart on Mon Jan 13 14:51:15 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

========================
CoperniFUS documentation
========================

*CoperniFUS: A flexible Python-based GUI for stereotaxic experiment planning.*

In the quest for a better control and understanding of the mechanisms of ultrasound neuromodulation and neurostimulation, the planning of experiments, evaluation of acoustic parameters via simulations, and post-processing of results often rely on distinct software programs with their own coordinate systems, which greatly complicates the integration, analysis, and interpretation of key information.

Designed around a unified coordinate system architecture, `CoperniFUS` is built to address this challenge by offering a versatile software platform for planning stereotaxic focused ultrasound (FUS) procedures.

.. warning::
   Like any other numerical modeling technique, the quality of the results produced by CoperniFUS depends entirely on the choice of input parameters. This software, developed in the context of my PhD, is also subject to bugs. It is therefore of the responsibility of the user to design and perform careful assessments of the results validity.  If you identify any issues, please report them `in GitHub's dedicated section <https://github.com/Tomaubier/CoperniFUS/issues>`_.

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
   contributing.md
   contents/usage
   contents/tutorial
   contents/api_reference
   contents/related_projects
   Github <https://github.com/Tomaubier/CoperniFUS>
