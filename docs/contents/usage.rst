Usage
-----

As a standalone software
^^^^^^^^^^^^^^^^^^^^^^^^
After activation of the ``coperniFUS_env`` environment, a standalone ``coperniFUS`` instance can be lauched by typing ``coperniFUS`` in a terminal (for macOS and linux) or command prompt in Windows.

Assets (such as ``.stl`` mesh files) loaded by armatures need to be located in a single directory. By default, example data will be loaded from ``coperniFUS/examples/assets`` however this behaviour can be changed by providing an ``--assets_dir_path`` argument.

.. code-block:: bash

   coperniFUS --assets_dir_path 'path/to/your/armature/assets'

Interactively in a ``notebook``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. nbgallery::

   interactive_example.ipynb

General Application Structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``CoperniFUS`` is architectured around three main components:
 - the ``Viewer`` hosting the 3D viewport and all UI elements
 - ``Modules`` which allow the manipulation of data displayed in the viewport
 - and ``Armatures`` which are submodules lying in the *Stereotaxic Frame* module and allow the user to conduct operations in the spatial coordinate frames of a stereotaxic aparatus.

.. image:: /_static/CoperniFUS_ui_breakdown.png

Description of data fields can be obtained by hovering gui elements.

.. image:: /_static/pointer_tooltip_doc.png

.. _transformation_strings_syntax:

Affine transformations from strings syntax
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Throughtout the sofware - in the GUI or configuration dictionaries - transformations of 3D objects can be defined by the user as ``strings``.

The syntax supports:

* Translation
    * ``Tx50um`` (translate 50 micrometers along :math:`x`)
* Rotate:
    * ``Rz12deg`` (12 degree rotation around :math:`z` axis)
* Scale
    * ``S0.2`` (apply a 0.2 scaling ratio in all directions)
    * ``Sy30`` (apply a 30 scaling ratio along :math:`y`)

Detailed information of the app structure can be found in `the API reference page <api_reference.rst>`_