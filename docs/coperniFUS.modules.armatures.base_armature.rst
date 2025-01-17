Base ``Armature``
-----------------

.. code-block:: python

   {
      '_armature_joints': {
         'ML_offset_1': {
            'translation_0': {
               'args': ['y', "csts['L1']*2"],
               '_is_editable': False
            }
         },
         'AP knob': {
            'translation_0': {
               'args': ['x', -0.005],
               '_is_editable': True,
               '_force_gui_location_to': 0,
               '_edit_increment': 0.0005,
               '_param_label': 'AP knob',
               '_color': 'x_RED',
               '_unit': 'm'
            },
            'rotation_0': {
               'args': ['x', 4.0, 'degrees'],
               '_is_editable': True,
               '_edit_increment': 1,
               '_param_label': 'AP tilt',
               '_unit': 'deg'
            }
         },
         'DV knob': {
            'translation_0': {
               'args': ['z', 0.05],
               '_is_editable': True,
               '_force_gui_location_to': 1,
               '_edit_increment': 0.0005,
               '_param_label': 'DV knob',
               '_color': 'z_BLUE',
               '_unit': 'm'
            },
            'rotation_0': {
               'args': ['z', 0.0, 'degrees'],
               '_is_editable': True,
               '_edit_increment': 1,
               '_param_label': 'DV tilt',
               '_unit': 'deg'
            }
         },
         'ML knob': {
            'translation_0': {
               'args': ['y', -0.043],
               '_is_editable': True,
               '_force_gui_location_to': 2,
               '_edit_increment': 0.0005,
               '_param_label': 'ML knob',
               '_color': 'y_GREEN',
               '_unit': 'm'
            }
         },
         'holder_rod': {
            'translation_0': {
               'args': ['z', "-csts['L2']"],
               '_is_editable': False
            }
         }
      }
   }


.. automodule:: coperniFUS.modules.armatures.base_armature
   :members:
   :undoc-members:
   :show-inheritance:
