Anatomical landmarks calibration ``Module``
-------------------------------------------

Calibration of coordinates systems based on anatomical measurements is currently implemented for sets of anatomical landmarks constituted of a pair of points. This calibration algorithm was developped for correction of rodent head sizes and orientations based on the registration of stereotaxic coordinates of the `Lambda` and `Bregma` skull structures.

.. image:: /_static/3_anatomical_calib_demo.gif

Calibration of brain atlases and assets are performed by registering `uncalibrated` and `calibrated` sets of anatomical landmark locations. `Uncalibrated` coordinates correspond to the locations of landmarks on ``CoperniFUS``'s assets. Cross registration of assets (such as brain atlases and skull meshes) can be assisted through the use of `reference images loaded as planes <coperniFUS.modules.img_as_plane.rst>`_. `Calibrated` coordinates on the other hand correspond to the actual locations of landmarks on the animal subject. During experiments - `assuming well defined armatures <coperniFUS.modules.armatures.base_armature.rst>`_ - regitration of these coordinates can be done using a reference needle probe attachment aligned with the targetted landmark.

.. automodule:: coperniFUS.modules.anatomical_landmarks_calibration_helper
   :members:
   :undoc-members:
   :show-inheritance:
