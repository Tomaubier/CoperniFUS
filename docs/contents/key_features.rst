Key features
------------

BrainGlobe + Structure highlighting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Supports a large range of Brain Atlases and associated structures thanks to `BrainGlobe Atlas API <https://brainglobe.info/documentation/brainglobe-atlasapi/index.html>`_.

.. image:: /_static/readme_imgs/1_atlas_demo.gif

Stereotaxic frame module - Armature inheritance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Arbitrary stereotaxic frames can be easily modelled using a flexible dictionary-based editor.

.. image:: /_static/readme_imgs/armature_config_editor.png

Stereotaxic frame elements (referred to as ``Armatures``) can be associated in a hierarchical tree structure, allowing operations such as mesh boolean operations or acoustic simulations in any spatial reference frame.

.. image:: /_static/readme_imgs/2_arm_heritance_demo.gif

Anatomical calibration module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
3D objects can inherit from a anatomically calibrated coordinate frame whose scale and orientation can be simply matched to experimental conditions using anatomical landmarks such as Lambda and Bregma for rodents.

.. image:: /_static/readme_imgs/3_anatomical_calib_demo.gif

Trimesh boolean operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Integration with the Python library `trimesh <https://trimesh.org>`_ allows for the manipulation of meshes. This feature greatly simplifies the definition of complex domains in the context of acoustic simulations.

.. image:: /_static/readme_imgs/4_boolean_operations_demo.gif

k-Wave acoustic simulation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Supports axisymmetric simulations in homogeneous domains and 3D simulations in complex mediums derived from mesh objects.

.. image:: /_static/readme_imgs/5_kwave_demo.gif