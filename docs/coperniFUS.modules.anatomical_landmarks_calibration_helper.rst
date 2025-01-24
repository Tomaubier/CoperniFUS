Anatomical landmarks calibration ``Module``
--------------------------------------------------

Calibration of coordinates systems based on anatomical measurement is currently implemented for sets of anatomical landmarks constituted of a pair of coordinates. This correction algorithm was developped for the correction of rodent head sizes and orientations based on the acquisition of stereotaxic coordinates for `Lambda` and `Bregma` skull structures.

.. image:: /_static/3_anatomical_calib_demo.gif

Calibration of brain atlases and assets are performed by registering `uncalibrated` and `calibrated` sets of anatomical landmark locations. `Uncalibrated` coordinates correspond to the locations of landmarks on the ``CoperniFUS``'s assets. Cross registration of assets (such as brain atlases and skull meshes) can be assisted through the use of reference images loaded as planes. `Calibrated` coordinates on the other hand correspond to the actual locations of landmarks on the animal. During experiments - `assuming well defined armatures <coperniFUS.modules.stereotaxic_frame.rst>`_ - regitration of these coordinates can be done using a reference needle probe attachment aligned with the targetted landmark.

Matching the settings of the stereotaxic frame modelled within CoperniFUS with its real counterpart will . Placing the `tooltip <coperniFUS.modules.tooltip.rst>`_ on the 

Coordinates of anatomical landmarks are specify to the Anatomical landmarks calibration module by setting the tooltip to the a  `Set landmark to tooltip`


To define the transformation matrix :math:`T` for the new 3D Cartesian coordinate system whose origin lies at :math:`A`, with its :math:`x`-axis aligned with the vector :math:`\mathbf{AB}` and its :math:`z`-axis orthogonal to the global :math:`y`-axis, follow these steps:

1. **Compute Basis Vectors**

   a. **Compute the :math:`x`-axis of the local system (:math:`\mathbf{x}_{\text{local}}`):**

      The :math:`x`-axis aligns with the vector :math:`\mathbf{AB}`, so:

      .. math::

         \mathbf{x}_{\text{local}} = \frac{\mathbf{AB}}{\|\mathbf{AB}\|}, \quad \text{where } \mathbf{AB} = \mathbf{B} - \mathbf{A}.

   b. **Compute the :math:`z`-axis of the local system (:math:`\mathbf{z}_{\text{local}}`):**

      The :math:`z`-axis must be orthogonal to the global :math:`y`-axis (:math:`\mathbf{y}_{\text{global}}`) and :math:`\mathbf{x}_{\text{local}}`. Compute it as:

      .. math::

         \mathbf{z}_{\text{local}} = \frac{\mathbf{x}_{\text{local}} \times \mathbf{y}_{\text{global}}}{\|\mathbf{x}_{\text{local}} \times \mathbf{y}_{\text{global}}\|}.

   c. **Compute the :math:`y`-axis of the local system (:math:`\mathbf{y}_{\text{local}}`):**

      The :math:`y`-axis is orthogonal to both :math:`\mathbf{x}_{\text{local}}` and :math:`\mathbf{z}_{\text{local}}`. Compute it using the cross product:

      .. math::

         \mathbf{y}_{\text{local}} = \mathbf{z}_{\text{local}} \times \mathbf{x}_{\text{local}}.

      Now, you have the orthonormal basis vectors :math:`\mathbf{x}_{\text{local}}, \mathbf{y}_{\text{local}}, \mathbf{z}_{\text{local}}`.

2. **Construct the Rotation Matrix**

   The rotation matrix :math:`R` to transform from the global coordinate system to the local coordinate system is:

   .. math::

      R = \begin{bmatrix}
      \mathbf{x}_{\text{local}} & \mathbf{y}_{\text{local}} & \mathbf{z}_{\text{local}}
      \end{bmatrix}^\top,

   where each column of :math:`R` is one of the local basis vectors in terms of the global frame:

   .. math::

      R = \begin{bmatrix}
      x_{\text{local},1} & y_{\text{local},1} & z_{\text{local},1} \\
      x_{\text{local},2} & y_{\text{local},2} & z_{\text{local},2} \\
      x_{\text{local},3} & y_{\text{local},3} & z_{\text{local},3}
      \end{bmatrix}.

3. **Add the Translation**

   The translation vector :math:`\mathbf{t}` is the vector :math:`\mathbf{A}`, the origin of the local frame in the global coordinate system.

   The transformation matrix :math:`T` is:

   .. math::

      T = \begin{bmatrix}
      R & \mathbf{t} \\
      0 & 1
      \end{bmatrix},

   where :math:`\mathbf{t} = \begin{bmatrix} A_x \\ A_y \\ A_z \end{bmatrix}`.

4. **Final Expression**

   In homogeneous coordinates, :math:`T` becomes:

   .. math::

      T = \begin{bmatrix}
      x_{\text{local},1} & y_{\text{local},1} & z_{\text{local},1} & A_x \\
      x_{\text{local},2} & y_{\text{local},2} & z_{\text{local},2} & A_y \\
      x_{\text{local},3} & y_{\text{local},3} & z_{\text{local},3} & A_z \\
      0 & 0 & 0 & 1
      \end{bmatrix}.


.. automodule:: coperniFUS.modules.anatomical_landmarks_calibration_helper
   :members:
   :undoc-members:
   :show-inheritance:
