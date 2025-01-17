Stereotaxic Frame ``Module``
----------------------------

coperniFUS's ``Stereotaxic Frame Module`` can be populated with ``Armature`` objects which at their core can model coordinates transformations of arbitrary stereotaxic frame structures. The ``Stereotaxic Frame Module`` allows the nesting of ``Armature`` objects, which facilitates the modeling of complex frame configurations.

.. image:: /_static/CoperniFUS_ui_breakdown_armatures.png

Specialized armatures can be derived from the base ``Armature`` object, which allows operations to be carried out within the frame coordinates. Currently, specilized armature are implemented to handle the manipulation of mesh objects and perform acoustic simulations

Available Armatures
^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 2

   coperniFUS.modules.armatures.base_armature
   coperniFUS.modules.armatures.mesh_armatures
   coperniFUS.modules.armatures.kwave_armatures

To interact with data from armatures, ``Armature`` objects can be grabbed using ``stereotaxic_frame`` module ``armatures_objects`` attribute.

.. code-block:: python

   In [1]: from coperniFUS.viewer import coperniFUSviewer
      Lauching CoperniFUS
   In [2]: cfv = coperniFUSviewer()
   In [3]: cfv.stereotaxic_frame.armatures_objects
      {
         'Skull acoustic window': <coperniFUS.modules.armatures.mesh_armatures.STLMeshBooleanArmature at 0x317446900>,
         'Brain mesh (skull convex Hull)': <coperniFUS.modules.armatures.mesh_armatures.STLMeshConvexHull at 0x317446840>,
         'kWave 3D simulation': <coperniFUS.modules.armatures.kwave_armatures.KWave3dSimulationArmature at 0x317446780>,
         'Main frame': <coperniFUS.modules.armatures.base_armature.Armature at 0x317446750>
      }

Stereotaxic Frame ``Module`` class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: coperniFUS.modules.stereotaxic_frame
   :members:
   :undoc-members:
   :show-inheritance: