Application structure & API reference
-------------------------------------

``CoperniFUS`` is architectured around three main components:
 - a **Viewer** hosting the 3D viewport and all UI elements
 - **Modules** allowing manipulation of data displayed in the viewport
 - **Armatures** which are submodules lying in the *Stereotaxic Frame* module and allow the user to conduct operations in the spatial coordinate frames of a stereotaxic aparatus.

.. image:: /_static/CoperniFUS_ui_breakdown.png

API reference
^^^^^^^^^^^^^
.. toctree::
    :maxdepth: 5
    :titlesonly:

    ../coperniFUS.viewer
    ../coperniFUS.modules
    ../coperniFUS.interfaces