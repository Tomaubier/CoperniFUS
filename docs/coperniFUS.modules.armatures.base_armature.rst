Base ``Armature``
-----------------

Armature definition procedure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Armature are configured based on a Python dictionary object that can be modified in a dedicated editor included in the `Stereotaxic Frame module <coperniFUS.modules.stereotaxic_frame.rst>`_.

.. image:: /_static/armature_config_editor.png

The frame geometry is given as a series of `translation` and `rotation` transforms representative of each stereotaxic frame joints.

.. code-block:: python

   # Armature configuration definition example
   {
      '_armature_joints': {
         'Joint 1 (x translation only)': {
            'translation_0': {
               'args': ['x', 0.05],
               '_is_editable': False,
            }
         },
         'Joint 2 (z translation + z rotation + y translation)': {
            'translation_0': {
               'args': ['z', 0.01],
               '_is_editable': False
            },
            'rotation_0': {
               'args': ['z', 20.0, 'degrees'],
               '_is_editable': True,
               '_edit_increment': 1,
               '_unit': 'deg'
            },
            'translation_1': {
               'args': ['y', 0.07],
               '_is_editable': True,
               '_edit_increment': 0.0005,
               '_unit': 'm'
            }
         }
      }
   }

These dictionaries are constructed through carreful measurements of the stereotaxic frame geometry.

.. image:: /_static/stereatax_frame_constants.jpg

Joints with constant dimensions can reference values defined in a constant dictionary. These can be used as transformation arguments by providing a string that will be evaluated ``'args': ['x', "-csts['L2'] + csts['d1']/2"]`` when displaying the armature. Fixed joints can be hidden from the GUI editor by setting ``_is_editable`` to ``False``.

Armature definition validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Proper armature definition should results in simulated armature geometries matching their actual counterpart in a large range of configurations.

.. image:: /_static/armature_validation_no_angle.png
.. image:: /_static/armature_validation_dv1_angle.png
.. image:: /_static/armature_validation_dv0_angle.png

In this example, the stereotaxic frame has been defined as 3 dictinct armatures:
   #. `Bregma loc correction` → bridging the rodent head location, with the Arm origin.
   #. `Arm 2` → The main arm possessing 5 degrees of freedom (:math:`x`, :math:`y`, :math:`z` translations + :math:`x`, :math:`z` rotations)
   #. `Dummy probe` → a detachable probe holder which is in this case constitutes of a single rod with no attachments.

Configuration dictionaries for these armatures have been defined as follows:

* `Bregma loc correction` ``Armature``

.. code-block:: python

   # Armature configuration definition
   {
      '_armature_joints': {
         'AP Bregma': {
               'translation_0': {
                  'args': ['x', 0.0787],
                  '_is_editable': True,
                  '_edit_increment': 0.0005,
                  '_unit': 'm'
               }
         },
         'ML Bregma': {
               'translation_0': {
                  'args': ['y', 0.0938],
                  '_is_editable': True,
                  '_edit_increment': 0.0005,
                  '_unit': 'm'
               }
         },
         'DV Bregma': {
               'translation_0': {
                  'args': ['z', 0.0225],
                  '_is_editable': True,
                  '_edit_increment': 0.0005,
                  '_unit': 'm'
               }
         }
      }
   }

* `Arm 2` ``Armature``

.. code-block:: python

   # Armature constant definition
   {
      'L1': 0.0215,
      'L2': 0.135,
      'L3': 0.0483,
      'L4': 0.077,
      'L5': 0.0245,
      'L6': 0.1152,
      'L7': 0.013,
      'L8': 0.0303,
      'L9': 0.014,
      'L10': 0.0053,
      'L11': 0.0128,
      'L12': 0.136,
      'L13': 0.0245,
      'L14': 0.014,
      'd1': 0.0332,
      'd2': 0.0095,
      'd3': 0.0096,
      'd4': 0.008
   }

   # Armature configuration definition
   {
      '_armature_joints': {
         'ML0': {
               'translation_0': {
                  'args': ['y', "csts['L1']/2"],
                  '_is_editable': False
               }
         },
         'AP Knob': {
               'translation_0': {
                  'args': ['x', 0.0029],
                  '_is_editable': True,
                  '_force_gui_location_to': 0,
                  '_edit_increment': 0.0005,
                  '_color': 'x_RED',
                  '_unit': 'm'
               }
         },
         'AP0': {
               'translation_0': {
                  'args': ['x', "-csts['L2'] + csts['d1']/2"],
                  '_is_editable': False
               }
         },
         'DV0': {
               'translation_0': {
                  'args': ['z', "csts['L3'] - csts['d2']/2"],
                  '_is_editable': False
               },
               'rotation_0': {
                  'args': ['z', 20.0, 'degrees'],
                  '_is_editable': True,
                  '_edit_increment': 1,
                  '_unit': 'deg'
               }
         },
         'DV1': {
               'translation_0': {
                  'args': ['z', "csts['d2']/2 + csts['L4'] - csts['L5']"],
                  '_is_editable': False
               },
               'rotation_0': {
                  'args': ['x', 0.0, 'degrees'],
                  '_is_editable': True,
                  '_edit_increment': 1,
                  '_unit': 'deg'
               }
         },
         'DV Knob': {
               'translation_0': {
                  'args': ['z', 0.0128],
                  '_is_editable': True,
                  '_force_gui_location_to': 2,
                  '_color': 'z_BLUE',
                  '_edit_increment': 0.0005,
                  '_unit': 'm'
               }
         },
         'ML Knob': {
               'translation_0': {
                  'args': ['y', 0.013000000000000001],
                  '_is_editable': True,
                  '_force_gui_location_to': 1,
                  '_edit_increment': 0.0005,
                  '_color': 'y_GREEN',
                  '_unit': 'm'
               }
         },
         'AP2': {
               'translation_0': {
                  'args': ['x', "csts['d3']/2 - csts['L7'] + csts['L8'] - csts['L9'] - csts['L10'] - csts['d4']/2"],
                  '_is_editable': False
               }
         },
         'ML2': {
               'translation_0': {
                  'args': ['y', "-csts['d3']/2 + csts['L11'] - csts['L12'] + csts['d4']/2"],
                  '_is_editable': False
               }
         },
         'DV2': {
               'translation_0': {
                  'args': ['z', "csts['L13'] - csts['L14']"],
                  '_is_editable': False
               }
         }
      }
   }


* `Dummy probe attachment` ``Armature``

.. code-block:: python

   # Armature configuration definition
   {
      '_armature_joints': {
         'DummyProbe arm': {
               'translation_0': {
                  'args': ['z', -0.1465]
               }
         }
      }
   }

Base Armature API reference
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: coperniFUS.modules.armatures.base_armature
   :members:
   :undoc-members:
   :show-inheritance:
