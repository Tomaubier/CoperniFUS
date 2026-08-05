import pytest
import PyQt6.QtCore as pyqtc
from PyQt6.QtTest import QTest

import trimesh, copy, pathlib
import numpy as np
from coperniFUS.viewer import Window
import coperniFUS

reference_test_assets_dir_path = pathlib.Path(coperniFUS.__file__).parent.parent / 'tests' / 'reference_test_assets'

# ===== Viewer =====

@pytest.fixture(scope="session")
def viewer_window(qapp):
    """ Fixture to create CoperniFUS viewer window. """
    window = Window(app=qapp, disable_threaded_wrappers=True)
    window.switch_cached_settings_file('Test config', force_create_new=True)
    yield window
    window.close()

# ==== Misc ====

# --- object hash eval ---
from coperniFUS import object_list_hash, get_nparray_shorthash

def test_object_list_hash():
    expected_hash = 'e1d36c5b7f9bf54785c6c6ba5f0237aeecefee0f7ab228ea49e8a68253ebbcd8'
    test_object_list = [True, 12, "bla"]
    assert object_list_hash(test_object_list) == expected_hash

def test_ndarray_hash():
    expected_hash = 'AoZjNH'
    test_nparray = np.array([29.2, 1], dtype=np.float64)
    assert get_nparray_shorthash(test_nparray) == expected_hash

# --- Affine transformation matrices contructor ---

from coperniFUS import AffineTransformsFromStr

def test_str_tmat():
    expected_hash = 'IXvDnZ'
    af_tr_from_str = AffineTransformsFromStr()
    str_tmat = af_tr_from_str.transform_matrix_from_str('Rx30deg Tz1mm S2')
    assert get_nparray_shorthash(str_tmat) == expected_hash

# --- json shelve cache handler ---
# Test value conservation for all jsonable types used in CoperniFUS

from coperniFUS import CachedDataHandler

@pytest.fixture
def cache_handler():
    """ Fixture to create CoperniFUS viewer window. """
    cdh = CachedDataHandler(cache_dir_name='.cacheHandlerTestDir')
    return cdh

def test_int_caching(cache_handler):
    test_value = 456
    cache_handler.set_attr('new_int_attribute_id', test_value)
    assert cache_handler.get_attr('new_int_attribute_id') == test_value

def test_float_caching(cache_handler):
    test_value = 376438648.4746577654
    cache_handler.set_attr('new_float_attribute_id', test_value)
    assert cache_handler.get_attr('new_float_attribute_id') == test_value

def test_str_caching(cache_handler):
    test_value = "Hello world"
    cache_handler.set_attr('new_str_attribute_id', test_value)
    assert cache_handler.get_attr('new_str_attribute_id') == test_value

def test_bool_caching(cache_handler):
    test_value = True
    cache_handler.set_attr('new_bool_attribute_id', test_value)
    assert cache_handler.get_attr('new_bool_attribute_id') == test_value

def test_list_caching(cache_handler):
    test_value = [12, "bla", 978.6]
    cache_handler.set_attr('new_list_attribute_id', test_value)
    assert cache_handler.get_attr('new_list_attribute_id') == test_value

def test_dict_caching(cache_handler):
    test_value = {
        'a_key': 3456,
        'b_key': {
            'ba_key': True,
            'bb_key': [12, "bla", 978.6],
        }
    }
    cache_handler.set_attr('new_dict_attribute_id', test_value)
    assert cache_handler.get_attr('new_dict_attribute_id') == test_value

# --- internal console ---

def test_internal_console_print(viewer_window):
    msg = 'This is a message that should end up in the console'
    console_module = viewer_window.get_module_object_from_name('InternalConsoleModule')
    console_module.append_console(msg)
    assert msg in console_module.console_widget.toPlainText()

def test_internal_console_clearing(viewer_window):
    console_module = viewer_window.get_module_object_from_name('InternalConsoleModule')
    console_module.clear_console()
    assert console_module.console_widget.toPlainText() == ''


# ===== Interfaces =====


# --- trimesh ---

from coperniFUS.modules.interfaces import trimesh_interfaces

def test_trimesh_interface(viewer_window, qtbot):
    trmsh = trimesh_interfaces.TrimeshHandler(parent_viewer=viewer_window)
    trmsh.raw_stl_item_mesh = trimesh.primitives.Sphere()
    assert np.isclose(trmsh.raw_stl_item_mesh.volume, 4.188, atol=1e-3) # Check raw shepre mesh volume

    # Test affine transformation application 
    af_tr_from_str = AffineTransformsFromStr()
    trmsh.stl_item_tmat = af_tr_from_str.transform_matrix_from_str('Rx30deg Tz1mm S2')
    assert np.isclose(trmsh.stl_item_mesh.volume, 33.510, atol=1e-3) # Check raw shepre mesh volume

# --- k-wave ---

from coperniFUS.modules.interfaces import kwave_interfaces

def test_kwave_3D_interface():

    ref_pmag_xmidplane_fpath = reference_test_assets_dir_path / 'test_kwave_3D_interface_pmag_xmidplane.npy'
    assert ref_pmag_xmidplane_fpath.exists()
    ref_pmag_xmidplane = np.load(ref_pmag_xmidplane_fpath)

    kw3D = kwave_interfaces.Kwave3D()
    
    kw3D.DEFAULT_SIM_PARAMS = {
        'c_0': 1482.3,
        'rho_0': 994.04,
        'alpha_0': 0.0022,
        'alpha_power_0': 1.0,
        'c_1': 2400,
        'rho_1': 1850,
        'alpha_1': 2.693,
        'alpha_power_1': 1.18,
        # 'alpha_mode': 'stokes',
        'source_f0': 1000000.0,
        'source_roc': 0.015,
        'source_diameter': 0.008,
        'source_amp': 1000000.0,
        'source_phase': 0.0,
        'AS_domain_z_size': 0,
        'threeD_domain_x_size': 0.01,
        'threeD_domain_y_size': 0.01,
        'threeD_domain_z_size': 0.02,
        'ppw': 4,
        't_end': 4e-05,
        'record_periods': 1,
        'cfl': 0.3,
        'source_z_offset': 10,
        'bli_tolerance': 0.01,
        'upsampling_rate': 10,
        'verbose_level': 1,
        'cpp_engine': 'OMP',
        'cpp_io_files_directory_path': None,
        'run_through_external_cpp_solvers': False,
        'use_gpu': False
    }

    kw3D.set_simulation_param('source_f0', 500000.0)
    kw3D.run_simulation()
    pmag_xmidplane_test_outome = kw3D.p_amp_xyz[0][14//2]

    print(f'test_kwave_3D_interface error {(pmag_xmidplane_test_outome - ref_pmag_xmidplane).max()}')
    assert (pmag_xmidplane_test_outome - ref_pmag_xmidplane).max() < 1 # tolerance in the pascal range

# TOIMPLEMENT once kave bug has been fixed test_kwave_AS -> does not run on macOS -> https://github.com/waltsims/k-wave-python/issues/470
# def test_kwave_AS():
#     expected_pmag_array_hash = ''

#     kwAS = kwave_interfaces.KwaveHomogeneousAxisymetricBowlSim()
#     kwAS.DEFAULT_SIM_PARAMS = {
#         'c_0': 1482.3,
#         'rho_0': 994.04,
#         'alpha_0': 0.0022,
#         'alpha_power_0': 1.0,
#         'alpha_mode': 'stokes',
#         'c_tx_coupling_medium': 1482.3,
#         'rho_tx_coupling_medium': 994.04,
#         'source_f0': 1000000.0,
#         'source_roc': 0.015,
#         'source_diameter': 0.015,
#         'source_ac_pwr': 0.0249,
#         'source_phase': 0.0,
#         'AS_domain_z_size': 0.03,
#         'AS_domain_r_size': 0.01,
#         'ppw': 5,
#         'n_reflections': 2,
#         'record_periods': 1,
#         'cfl': 0.1,
#         'source_z_offset': 20,
#         'domain_z_extension': 20,
#         'bli_tolerance': 0.01,
#         'upsampling_rate': 10,
#         'cpp_engine': 'OMP',
#         'cpp_io_files_directory_path': None,
#         'run_through_external_cpp_solvers': False
#     }

#     kwAS.set_simulation_param('source_f0', 500000.0)
#     kwAS.run_simulation()
#     p_mag = kwAS.p_amp_zr[0]

#     assert get_nparray_shorthash(p_mag) == expected_pmag_array_hash


# ===== Built-in Modules =====


# --- Tooltip ---

def test_tooltip(viewer_window, qtbot):
    # Get QTextEdit tooltip transform editor reference
    tooltip_module = viewer_window.get_module_object_from_name('Tooltip')
    tooltip_module.release_from_modules() # Make sure its location is not tied to any modules
    tr_editor = tooltip_module.tooltip_transform_editor

    assert tr_editor is not None

    # Focus on editor and type transformation str
    tr_editor.setFocus()
    # Clear field
    QTest.keyClick(tr_editor, pyqtc.Qt.Key.Key_A, pyqtc.Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(tr_editor, pyqtc.Qt.Key.Key_Delete)
    # Enter value
    QTest.keyClicks(tr_editor, "Rz30deg Tx2mm Tz5um")
    QTest.keyClick(tr_editor, pyqtc.Qt.Key.Key_Enter)
    
    # Check tooltip loc
    assert np.isclose(tooltip_module.tooltip_coordinates, np.array([2.000e-03, 0.000e+00, 5.000e-06]), rtol=1e-3).all()

# --- AnatLandmarksCalib ---

def test_2landmarks_anatcalib(viewer_window, qtbot):
    expected_calib_tmat = np.array([
        [1.556e+00, -3.333e-01, -1.667e-01, 0.000e+00],
        [3.314e-01, 1.564e+00, -3.551e-02, 0.000e+00],
        [1.704e-01, 0.000e+00, 1.590e+00, 0.000e+00],
        [3.556e-03, -3.333e-04, 3.333e-04, 1.000e+00]
    ])

    anatcalib_module = viewer_window.get_module_object_from_name('AnatLandmarksCalib')

    landmark_test_dict = {
        'uncal_anatomical_landmarks_coords': {'LM1': [-1e-3, 0, 0], 'LM2': [-1e-2, 0, 0]},
        'cal_anatomical_landmarks_coords': {'LM1': [2e-3, 0, 500e-6], 'LM2': [-1.2e-2, 3e-3, 2e-3]}
    }
    anatcalib_module._populate_treeview_from_dict(landmark_test_dict)
    anatcalib_module._on_treeview_edit()

    qtbot.mouseClick(anatcalib_module.apply_calibration_tmat_btn, pyqtc.Qt.MouseButton.LeftButton) # Apply calib
    assert np.isclose(anatcalib_module.landmarks_calib_tmat, expected_calib_tmat, rtol=1e-3).all()
    
    qtbot.mouseClick(anatcalib_module.apply_calibration_tmat_btn, pyqtc.Qt.MouseButton.LeftButton) # Disable calib
    assert np.isclose(anatcalib_module.landmarks_calib_tmat, np.eye(4), rtol=1e-3).all()

# --- StereotaxicFrame ---

def test_stereotaxicframe_module(viewer_window, qtbot):
    steframe_module = viewer_window.get_module_object_from_name('StereotaxicFrame')
    steframe_module.update_armature_inheritance()

    # Add / remove armature
    steframe_module.add_armature('Armature', 'Test Armature')
    steframe_module.delete_armature('Test Armature')

    assert steframe_module.armatures_objects is not None

# ===== StereotaxicFrame Armatures =====

def clear_all_armatures(steframe_module):
    for armature_name in copy.deepcopy(list(steframe_module.armatures_objects.keys())):
        steframe_module.delete_armature(armature_name)

# --- Base ---

base_armature_test_config_csts = {
    'L1': 0.015,
    'L2': 0.02
}

base_armature_test_config_dict = {
    '_armature_joints': {
        'ML_offset_1': {
            'translation_0': {
                'args': ['y', "csts['L1']*2"],
                '_is_editable': False
            }
        },
        'AP knob': {
            'translation_0': {
                'args': ['x', -0.02],
                '_is_editable': True,
                '_force_gui_location_to': 0,
                '_edit_increment': 0.0005,
                '_param_label': 'AP knob',
                '_color': 'x_RED',
                '_unit': 'm'
            },
            'rotation_0': {
                'args': ['x', 5.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_param_label': 'AP tilt',
                '_unit': 'deg'
            }
        },
        'DV knob': {
            'translation_0': {
                'args': ['z', 0.0365],
                '_is_editable': True,
                '_force_gui_location_to': 1,
                '_edit_increment': 0.0005,
                '_param_label': 'DV knob',
                '_color': 'z_BLUE',
                '_unit': 'm'
            },
            'rotation_0': {
                'args': ['z', 30.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_param_label': 'DV tilt',
                '_unit': 'deg'
            }
        },
        'ML knob': {
            'translation_0': {
                'args': ['y', -0.0375],
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

def test_base_armature(viewer_window, qtbot):
    steframe_module = viewer_window.get_module_object_from_name('StereotaxicFrame')
    clear_all_armatures(steframe_module)
    
    # Add base armature
    steframe_module.add_armature('Armature', 'Test Armature 1')
    base_armature_1 = steframe_module.armatures_objects['Test Armature 1']
    steframe_module.add_armature('Armature', 'Test Armature 2')
    base_armature_2 = steframe_module.armatures_objects['Test Armature 2']

    # Apply test config to 'Test Armature 1'
    base_armature_1.armature_config_dict = None
    base_armature_1.armature_config_csts = base_armature_test_config_csts
    base_armature_1.uneval_armature_config_dict = base_armature_test_config_dict
    steframe_module._update_armature_parameters_widgets_on_configuration_change(base_armature_1)
    base_armature_1.update_render()

    # Apply test config to 'Test Armature 2'
    base_armature_2.armature_config_dict = None
    base_armature_2.armature_config_csts = base_armature_test_config_csts
    base_armature_2.uneval_armature_config_dict = base_armature_test_config_dict
    steframe_module._update_armature_parameters_widgets_on_configuration_change(base_armature_2)
    base_armature_2.update_render()

    expected_root_end_transform_mat = np.array([
        [8.660e-01, 4.981e-01, 4.358e-02, 0.000e+00],
        [-5.000e-01, 8.627e-01, 7.548e-02, 0.000e+00],
        [0.000e+00, -8.716e-02, 9.962e-01, 0.000e+00],
        [-1.250e-03, -3.790e-03, 1.361e-02, 1.000e+00]
    ])

    assert np.isclose(base_armature_1.end_transform_mat, expected_root_end_transform_mat, rtol=1e-3).all()
    assert np.isclose(base_armature_2.end_transform_mat, expected_root_end_transform_mat, rtol=1e-3).all()

    # Architecture inheritance test

    expected_inherited_end_transform_mat = np.array([
        [5.010e-01, 8.573e-01, 1.187e-01, 0.000e+00],
        [-8.644e-01, 4.887e-01, 1.185e-01, 0.000e+00],
        [4.358e-02, -1.620e-01, 9.858e-01, 0.000e+00],
        [-4.373e-04, -8.869e-03, 2.682e-02, 1.000e+00]
    ])

    steframe_module.update_armature_inheritance(steframe_arch_dict={
        'Test Armature 1': {'Test Armature 2': None}
    })
    assert np.isclose(base_armature_2.end_transform_mat, expected_inherited_end_transform_mat, rtol=1e-3).all()

    steframe_module.delete_armature('Test Armature 2')
    # Keep Test Armature 1 for later use in kwave_test

# --- trimesh ---

fake_skull_armature_test_config_dict = {
    '_stl_mesh': {
        'file_path': None,
        'transform_str': 'Rx90deg Rz90deg',
        'ignore_plane_slicing': True,
        'ignore_anatomical_landmarks_calibration': False,
        'gl_mesh_shader': 'softShade',
        'gl_mesh_color': [0.7, 0.7, 0.7, 1],
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_edgeColor': [0.9, 0.9, 0.9, 1],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5
    },
    '_trimesh_script': """

outer_circle = trimesh.path.creation.circle(radius=tube_diameter/2, segments=64)
inner_circle = trimesh.path.creation.circle(radius=tube_diameter/2 - tube_thickness, segments=64)
path_2d = outer_circle + inner_circle
extrusion = path_2d.extrude(tube_length)
mesh = extrusion.to_mesh()
tmat = trimesh.transformations.compose_matrix(translate=[0, 0, z_offset])
mesh.apply_transform(tmat)

    """,
    '_trimesh_script_coords': {
        'tube_diameter': {
            'args': ['diameter', 0.02],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Tube diameter',
            '_color': 'grey',
            '_unit': 'm'
        },
        'tube_thickness': {
            'args': ['diameter', 0.001],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Tube thickness',
            '_color': 'grey',
            '_unit': 'm'
        },
        'tube_length': {
            'args': ['x', 0.02],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Tube length',
            '_color': 'z_BLUE',
            '_unit': 'm'
        },
        'z_offset': {
            'args': ['z', -0.01],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Tube offset',
            '_color': 'grey',
            '_unit': 'm'
        }
    }
}

fake_brain_tissues_armature_test_config_dict = {
    '_stl_mesh': {
        'file_path': 'None',
        'transform_str': 'S1 Rx0deg Tz0mm',
        'ignore_plane_slicing': False,
        'ignore_anatomical_landmarks_calibration': True,
        'gl_mesh_shader': None,
        'gl_mesh_drawEdges': True,
        'gl_mesh_drawFaces': False,
        'gl_mesh_edgeColor': [0.9, 0.9, 0.9, 1],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5
    },
    '_convex_hull': {
        '_src_mesh': 'Fake Skull Mesh',
        'ignore_plane_slicing': True,
        '_mask_preview_gl_options': {
            'gl_mesh_shader': None,
            'gl_mesh_drawEdges': True,
            'gl_mesh_drawFaces': False,
            'gl_mesh_edgeColor': [0.5, 0, 0, 1],
            'gl_mesh_glOptions': 'opaque',
            'gl_mesh_smooth': False,
            'gl_mesh_edgeWidth': 5
        }
    }
}

def test_mesh_armature(viewer_window, qtbot):
    steframe_module = viewer_window.get_module_object_from_name('StereotaxicFrame')

    # Add trimesh armature
    steframe_module.add_armature('TrimeshScriptArmature', 'Fake Skull Mesh')
    fake_skull_armature = steframe_module.armatures_objects['Fake Skull Mesh']

    # Apply fake skull test config to 'Fake Skull Mesh'
    fake_skull_armature.armature_config_dict = None
    fake_skull_armature.armature_config_csts = {}
    fake_skull_armature.uneval_armature_config_dict = fake_skull_armature_test_config_dict
    fake_skull_armature.visible = True
    steframe_module._update_armature_parameters_widgets_on_configuration_change(fake_skull_armature)
    fake_skull_armature.update_render()

    print(fake_skull_armature.mesh_handler.stl_item_mesh is None)

    assert np.isclose(fake_skull_armature.mesh_handler.stl_item_mesh.volume, 1.192e-06, rtol=1e-3)

    # -- Test convex hull armature --
    
    steframe_module.add_armature('STLMeshConvexHull', 'Fake Brain Tissues Mesh')
    fake_brain_armature = steframe_module.armatures_objects['Fake Brain Tissues Mesh']

    # Apply fake skull test config to 'Fake Brain Tissues Mesh'
    fake_brain_armature.armature_config_dict = None
    fake_brain_armature.armature_config_csts = {}
    fake_brain_armature.visible = True
    fake_brain_armature.uneval_armature_config_dict = fake_brain_tissues_armature_test_config_dict
    steframe_module._update_armature_parameters_widgets_on_configuration_change(fake_brain_armature)
    fake_brain_armature.update_render()
    
    fake_brain_armature.compute_convex_hull()

    assert np.isclose(fake_brain_armature.mesh_handler.stl_item_mesh.volume, 6.276e-06, rtol=1e-3)

# --- k-wave ---

kwave_armature_test_config_csts = {
    'p_max_viz': 300000.0,
    'kwave_3D_h5_dir': None,
    'pressure_field_render_stride': 1
}

kwave_armature_test_config_dict = {
    '_armature_joints': {
        'source_offset': {
            'translation_0': {
                'args': ['z', 0],
                '_is_editable': False
            },
            'rotation_0': {
                'args': ['x', 180],
                '_is_editable': False
            }
        }
    },
    '_stl_mesh': {
        'file_path': 'None',
        'transform_str': None,
        'ignore_plane_slicing': True,
        'gl_mesh_shader': None,
        'gl_mesh_drawEdges': True,
        'gl_mesh_drawFaces': False,
        'gl_mesh_edgeColor': [0.82745098, 0.32941176, 0.0, 0.6],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5
    },
    '_boolean_mask': {
        '_boolean_operations': {
            '1': ['intersection', ['Fake Brain Tissues Mesh', '_boolean_mask']],
            '2': ['intersection', ['Fake Skull Mesh', '_boolean_mask']]
        },
        '_mask_preview_gl_options': {
            'gl_mesh_shader': None,
            'gl_mesh_drawEdges': True,
            'gl_mesh_drawFaces': False,
            'gl_mesh_edgeColor': [0.945, 0.768, 0.059, 1.0],
            'gl_mesh_glOptions': 'opaque',
            'gl_mesh_smooth': False,
            'gl_mesh_edgeWidth': 2
        },
        'transform_str': None,
        'ignore_plane_slicing': True,
        '_boolean_mask_trimesh_script': """


path_2d_dict = {
    'entities': [
        {'type': 'Line', 'points': [0, 1, 2, 3, 0], 'closed': False},
        ],
    'vertices': [
        [-threeD_domain_x_size/2, threeD_domain_y_size/2],
        [threeD_domain_x_size/2, threeD_domain_y_size/2],
        [threeD_domain_x_size/2, -threeD_domain_y_size/2],
        [-threeD_domain_x_size/2, -threeD_domain_y_size/2],
    ]
}

path_2d_from_dict = trimesh.path.exchange.load.load_path(
    dict_to_path(path_2d_dict)
)

extrusion = path_2d_from_dict.extrude(threeD_domain_z_size)
mesh = extrusion.to_mesh()

        
        """,
        '_boolean_mask_coords': {
            'threeD_domain_x_size': {
                'args': ['x', 0.02],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_param_label': '3D ac. domain (x)',
                '_color': 'x_RED',
                '_unit': 'm'
            },
            'threeD_domain_y_size': {
                'args': ['y', 0.02],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_param_label': '3D ac. domain (y)',
                '_color': 'y_GREEN',
                '_unit': 'm'
            },
            'threeD_domain_z_size': {
                'args': ['x', 0.03],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_param_label': '3D ac. domain (z)',
                '_color': 'z_BLUE',
                '_unit': 'm'
            }
        }
    },
    '_kwave_sim': {
        'ignore_plane_slicing': True,
        '_axisym_domain_gl_options': {
            'gl_mesh_shader': None,
            'gl_mesh_drawEdges': True,
            'gl_mesh_drawFaces': False,
            'gl_mesh_edgeColor': [0.945, 0.768, 0.059, 1.0],
            'gl_mesh_glOptions': 'opaque',
            'gl_mesh_smooth': False,
            'gl_mesh_edgeWidth': 2
        },
        '_3dcartesian_domain_acoustic_params': {
            'c_0': 1482.3,
            'rho_0': 994.04,
            'alpha_0': 0.0022,
            'alpha_power_0': 1.0,
            'c_1': 1546,
            'rho_1': 1045,
            'alpha_1': 0.208,
            'alpha_power_1': 1.3,
            'c_2': 2400,
            'rho_2': 1850,
            'alpha_2': 2.693,
            'alpha_power_2': 1.18,
            # 'alpha_mode': None,
            'source_f0': 1000000.0,
            'source_roc': 0.015,
            'source_diameter': 0.015,
            'source_amp': 100000.0,
            'source_phase': 0.0,
            'threeD_domain_x_size': 0.01,
            'threeD_domain_y_size': 0.01,
            'threeD_domain_z_size': 0.02,
            'ppw': 5,
            't_end': 4e-05,
            'record_periods': 1,
            'cfl': 0.1,
            'source_z_offset': 10,
            'bli_tolerance': 0.01,
            'upsampling_rate': 10,
            'verbose_level': 1,
            'cpp_engine': 'CUDA',
            'cpp_io_files_directory_path': 'cpp_files_path',
            'run_through_external_cpp_solvers': False
        },
        '_sim_parameters': {
            'source_f0': {
                'args': ['f', 400000.0],
                '_is_editable': True,
                '_edit_increment': 500000.0,
                '_param_label': 'Source f0',
                '_color': 'grey',
                '_unit': 'Hz'
            }
        }
    }
}

def test_kwave_armature(viewer_window, qtbot):
    """ Ensure that Test Armature 1, Fake Skull Mesh, Fake Brain Tissues Mesh from test_base_armature and test_mesh_armature are still loaded """

    ref_pmag_xmidplane_fpath = reference_test_assets_dir_path / 'test_kwave_armature_pmag_xmidplane.npy'
    assert ref_pmag_xmidplane_fpath.exists()
    ref_pmag_xmidplane = np.load(ref_pmag_xmidplane_fpath)

    steframe_module = viewer_window.get_module_object_from_name('StereotaxicFrame')

    # Add trimesh armature
    steframe_module.add_armature('KWave3dSimulationArmature', 'Test 3D FUS simulation')
    kwave_armature = steframe_module.armatures_objects['Test 3D FUS simulation']

    # Apply fake skull test config to 'Test 3D FUS simulation'
    kwave_armature.armature_config_dict = None
    kwave_armature.armature_config_csts = kwave_armature_test_config_csts
    kwave_armature.uneval_armature_config_dict = kwave_armature_test_config_dict
    kwave_armature.visible = True
    steframe_module._update_armature_parameters_widgets_on_configuration_change(kwave_armature)
    kwave_armature.update_render()

    # Set Test 3D FUS simulation armature as Test Armature 1 child
    steframe_module.update_armature_inheritance(steframe_arch_dict={
        'Test Armature 1': {
            'Test 3D FUS simulation': None
        },
        'Fake Skull Mesh': None,
        'Fake Brain Tissues Mesh': None,
    })

    kwave_armature.compute_boolean_operation()
    kwave_armature.run_3D_simulation()

    pmag_xmidplane_test_outome = kwave_armature.kw3D.p_amp_xyz[0][26//2]
    print(f'test_kwave_armature error {(pmag_xmidplane_test_outome - ref_pmag_xmidplane).max()}')
    assert (pmag_xmidplane_test_outome - ref_pmag_xmidplane).max() < 1e3 # tolerance in the kPa range (TODO refine -> 25Pa discrapencies observed between macOS & linux runs)


# ===== Optionnal Modules =====


# --- BrainAtlas ---

def test_brain_atlas(viewer_window, qtbot):
    """ Test that the example mouse atlas + CH structure layer can be loaded."""
    batlas_module = viewer_window.get_module_object_from_name('BrainAtlas') # Get BrainAtlasModule handle
    batlas_module.add_reference_atlas('example_mouse_100um') # Loading demo atlas
    batlas_module.add_structure_layer(structure='Cerebrum (CH)', hemisphere='Left Hemisphere') # Loading a brain structure
    assert len(batlas_module.layers) == 2

