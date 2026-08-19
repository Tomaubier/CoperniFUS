
# %%

""" Script designed to setup CoperniFUS in the tutorial configuration in a programatic way.
    See 
"""

steretaxic_frame_buider_dict = {}

# %% --- Bregma to Stereotaxic Frame Origin (Armature) ---

armature_name = 'Bregma to Stereotaxic Frame Origin'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {}
steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'AP Bregma': {
            'translation_0': {
                'args': ['x', 0.0784],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_color': 'x_RED',
                '_unit': 'm'
            }
        },
        'ML Bregma': {
            'translation_0': {
                'args': ['y', 0.0948],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_color': 'y_GREEN',
                '_unit': 'm'
            }
        },
        'DV Bregma': {
            'translation_0': {
                'args': ['z', 0.013],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_color': 'z_BLUE',
                '_unit': 'm'
            }
        }
    }
}

# --- Skull Mesh (STLMeshArmature) ---

armature_name = 'Skull Mesh'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'STLMeshArmature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {}
steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_stl_mesh': {
        'file_path': 'Pohl2013_coarse.stl',
        'transform_str': 'Rz90deg Tz-0.292m Tx0.415m Ry4.2deg S.09',
        'ignore_plane_slicing': False,
        'ignore_anatomical_landmarks_calibration': False,
        'gl_mesh_shader': 'softShade',
        'gl_mesh_color': [0.972, 0.76, 0.568, 1.],
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_edgeColor': [0.9, 0.9, 0.9, 0.7],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 2
    }
}

# --- Brain Mesh (STLMeshConvexHull) ---

armature_name = 'Brain Mesh'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'STLMeshConvexHull'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {}
steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
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
        '_src_mesh': 'Skull Mesh',
        '_mask_preview_gl_options': {
            'ignore_plane_slicing': True,
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

# %% ======== Coordinates Registration Probe Arm (Armature) ========

armature_name = 'Coordinates Registration Probe Arm'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
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

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'ML0': {
            'translation_0': {
                'args': ['y', "csts['L1']/2"],
                '_is_editable': False
            }
        },
        'AP Knob': {
            'translation_0': {
                'args': ['x', 0.051],
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
                'args': ['z', 0.0, 'degrees'],
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
                'args': ['z', 0.0258],
                '_is_editable': True,
                '_force_gui_location_to': 2,
                '_color': 'z_BLUE',
                '_edit_increment': 0.0005,
                '_unit': 'm'
            }
        },
        'ML Knob': {
            'translation_0': {
                'args': ['y', 0.0185],
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

# --- Coords Registration Probe Shaft (Armature) ---

armature_name = 'Coords Registration Probe Shaft'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
    'registration_shaft_len': 0.1337,
}

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'Registration probe shaft': {
            'translation_0': {
                'args': ['z', "- csts['registration_shaft_len']"],
                '_is_editable': False
            },
            'rotation_0': {
                'args': ['z', 0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            },
            'rotation_1': {
                'args': ['x', 0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            }
        }
    }
}

# --- Coords Registration Probe Tip (Armature)

armature_name = 'Coords Registration Probe Tip'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
    'registration_tip_x_offset': 0.0183,
    'registration_tip_z_height': 0.0164
}

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'Registration probe tip offset': {
            'translation_0': {
                'args': ['x', "- csts['registration_tip_x_offset']"],
                '_is_editable': False
            }
        },
        'Registration probe tip length': {
            'translation_0': {
                'args': ['z', "- csts['registration_tip_z_height']"],
                '_is_editable': False
            }
        }
    }
}


# %% ======== FUS Transducer Arm (Armature) ========

armature_name = 'FUS Transducer Arm'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
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

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'ML0': {
            'translation_0': {
                'args': ['y', "csts['L1']/2"],
                '_is_editable': False
            }
        },
        'AP Knob': {
            'translation_0': {
                'args': ['x', 0.0177],
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
                'args': ['z', 0.0, 'degrees'],
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
                'args': ['z', 0.0213],
                '_is_editable': True,
                '_force_gui_location_to': 2,
                '_color': 'z_BLUE',
                '_edit_increment': 0.0005,
                '_unit': 'm'
            }
        },
        'ML Knob': {
            'translation_0': {
                'args': ['y', 0.0153],
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

# --- FUS Transducer Shaft (Armature) ---

armature_name = 'FUS Transducer Shaft'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
    'shaft_len': 0.1142,
    '3d_printed_joint_len': 0.018037
}

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'FUS Tx Shaft': {
            'translation_0': {
                'args': ['z', "-(csts['shaft_len'] + csts['3d_printed_joint_len'])"],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_unit': 'm'
            },
            'rotation_0': {
                'args': ['z', 186.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            },
            'rotation_1': {
                'args': ['x', 0.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            }
        },
        'FUS Tx holder joint angle': {
            'rotation_0': {
                'args': ['y', 1.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            }
        }
    }
}

# --- FUS Transducer Holder Mesh (STLMeshArmature) ---

armature_name = 'FUS Transducer Holder Mesh'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'STLMeshArmature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
    '3d_printed_FUS_holder_x_offset': -0.018,
    '3d_printed_FUS_holder_z_offset': -0.01
}

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'FUS holder': {
            'translation_0': {
                'args': ['x', "csts['3d_printed_FUS_holder_x_offset']"],
                '_is_editable': False
            },
            'translation_1': {
                'args': ['z', "csts['3d_printed_FUS_holder_z_offset']"],
                '_is_editable': False
            }
        }
    },
    '_stl_mesh': {
        'file_path': 'simple_transducer_holder.stl',
        'ignore_plane_slicing': True,
        'ignore_anatomical_landmarks_calibration': True,
        'gl_mesh_shader': 'softShade',
        'gl_mesh_color': [0.7, 0.7, 0.7, 1.0],
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_edgeColor': [0.9, 0.9, 0.9, 0.7],
        'gl_mesh_glOptions': 'translucent',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 3
    }
}

# --- Theoretical FUS focal spot preview (TrimeshScriptArmature) ---

armature_name = 'Theoretical FUS focal spot preview'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'TrimeshScriptArmature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {}
steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_stl_mesh': {
        'file_path': 'None',
        'transform_str': None,
        'ignore_plane_slicing': True,
        'ignore_anatomical_landmarks_calibration': True,
        'gl_mesh_shader': None,
        'gl_mesh_drawEdges': True,
        'gl_mesh_drawFaces': False,
        'gl_mesh_edgeColor': [0.88, 0.69, 0.17, 1],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5
    },
    '_trimesh_script': """


c0 = 1500
lambd = c0 / tx_freq        
len_focus = 7*lambd * (F_tx/D_tx)**2
width_focus = (lambd * F_tx) / D_tx
fspot_est_zloc = np.sqrt(F_tx**2 - (D_tx / 2)**2)
mesh = trimesh.creation.icosphere(radius=1, subsivisions=1)
mesh.apply_scale((width_focus, width_focus, len_focus))
mesh.apply_translation((0, 0, -fspot_est_zloc))

    
    """,
    '_trimesh_script_coords': {
        'F_tx': {
            'args': ['z', 0.015],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Tx radius of curvature',
            '_color': 'grey',
            '_unit': 'm'
        },
        'D_tx': {
            'args': ['z', 0.015],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Tx aperture',
            '_color': 'grey',
            '_unit': 'm'
        },
        'tx_freq': {
            'args': ['z', 2000000.0],
            '_is_editable': True,
            '_edit_increment': 10000.0,
            '_param_label': 'Tx central frequency',
            '_color': 'grey',
            '_unit': 'Hz'
        }
    }
}

# --- kWave 3D Simulation (KWave3dSimulationArmature) ---

armature_name = 'kWave 3D Simulation'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'KWave3dSimulationArmature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
    'p_max_viz': 500000.0,
    'kwave_3D_h5_dir': None,
    'pressure_field_render_stride': 1
}

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
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
            '1': ['intersection', ['Brain Mesh', '_boolean_mask']],
            '2': ['intersection', ['Skull Mesh', '_boolean_mask']]
        },
        '_mask_preview_gl_options': {
            'gl_mesh_shader': None,
            'gl_mesh_drawEdges': True,
            'gl_mesh_drawFaces': False,
            'gl_mesh_edgeColor': [0.945, 0.768, 0.059, 1.0],
            'gl_mesh_glOptions': 'opaque',
            'gl_mesh_smooth': False,
            'gl_mesh_edgeWidth': 2,
            'transform_str': None,
            'ignore_plane_slicing': True,
        },
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
                'args': ['x', 0.025],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_param_label': '3D ac. domain (z)',
                '_color': 'z_BLUE',
                '_unit': 'm'
            }
        }
    },
    '_kwave_sim': {
        '_axisym_domain_gl_options': {
            'ignore_plane_slicing': True,
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
                'args': ['f', 1000000.0],
                '_is_editable': True,
                '_edit_increment': 500000.0,
                '_param_label': 'Source f0',
                '_color': 'grey',
                '_unit': 'Hz'
            }
        }
    }
}



# %% ======== Recording Electrode Arm (Armature) ========

# --- Stereotaxic Frame Rails Distance (Armature) ---

armature_name = 'Stereotaxic Frame Rails Distance'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
    'rails_distance': 0.19
}

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'Rails_spacing': {
            'translation_0': {
                'args': ['y', "-csts['rails_distance']"],
                '_is_editable': False
            }
        }
    }
}

# --- Recording Electrode Arm (Armature) ---

armature_name = 'Recording Electrode Arm'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {
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

steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'ML0': {
            'translation_0': {
                'args': ['y', "-csts['L1']/2"],
                '_is_editable': False
            }
        },
        'AP Knob': {
            'translation_0': {
                'args': ['x', 0.051],
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
                'args': ['z', 0.0, 'degrees'],
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
                'args': ['z', 0.0043],
                '_is_editable': True,
                '_force_gui_location_to': 2,
                '_color': 'z_BLUE',
                '_edit_increment': 0.0005,
                '_unit': 'm'
            }
        },
        'ML Knob': {
            'translation_0': {
                'args': ['y', -0.0188],
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
                'args': ['y', "csts['d3']/2 - csts['L11'] + csts['L12'] - csts['d4']/2"],
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

# --- Recording Electrode Shaft (Armature) ---

armature_name = 'Electrode Electrode Shaft'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'Armature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {}
steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'Electrode Probe Shaft': {
            'translation_0': {
                'args': ['z', -0.115],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_unit': 'm'
            },
            'rotation_0': {
                'args': ['z', 190.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            },
            'rotation_1': {
                'args': ['x', 0.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            }
        },
        'Electrode Probe joint angle': {
            'rotation_0': {
                'args': ['y', 162.0, 'degrees'],
                '_is_editable': True,
                '_edit_increment': 1,
                '_unit': 'deg'
            }
        }
    }
}

# --- Recording Electrode Body (TrimeshScriptArmature)

armature_name = 'Recording Electrode Body'
steretaxic_frame_buider_dict[armature_name] = {}
steretaxic_frame_buider_dict[armature_name]['armature_type'] = 'TrimeshScriptArmature'

steretaxic_frame_buider_dict[armature_name]['constants_dict'] = {}
steretaxic_frame_buider_dict[armature_name]['configuration_dict'] = {
    '_armature_joints': {
        'Electrode Probe Length': {
            'translation_0': {
                'args': ['z', 0.025],
                '_is_editable': True,
                '_edit_increment': 0.0005,
                '_unit': 'm'
            }
        }
    },
    '_stl_mesh': {
        'file_path': 'None',
        'transform_str': None,
        'ignore_plane_slicing': True,
        'gl_mesh_shader': 'softShade',
        'gl_mesh_color': [0.7, 0.7, 0.7, 1.0],
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_edgeColor': [0.9, 0.9, 0.9, 1],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5
    },
    '_trimesh_script': """

path_2d = trimesh.path.creation.circle(radius=probe_diameter/2, segments=8)
extrusion = path_2d.extrude(-probe_length)
mesh = extrusion.to_mesh()

    """,
    '_trimesh_script_coords': {
        'probe_diameter': {
            'args': ['diameter', 0.0009],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Probe Mesh diameter',
            '_color': 'grey',
            '_unit': 'm'
        },
        'probe_length': {
            'args': ['length', 0.022],
            '_is_editable': True,
            '_edit_increment': 0.0005,
            '_param_label': 'Probe Mesh length',
            '_color': 'grey',
            '_unit': 'm'
        }
    }
}

# %% Armatures definition

from coperniFUS.viewer import coperniFUSviewer
from coperniFUS import *
np.set_printoptions(formatter={'float':lambda x: f'{x:.3e}'}) # ndarray print option for transformation matrices

cfv = coperniFUSviewer(
    disable_internal_console=True, # prevent messages to be forwarded to the internal console -> useful in interactive mode
)

cfv.switch_cached_settings_file('Dual arms FUS + rec electrode rat tutorial config', force_create_new=True)

def add_armature_with_config(steframe_module_handle, armature_name, armature_type, config_dict, config_csts):
    # Add armature to stereotaxic frame module
    steframe_module_handle.add_armature(armature_type, armature_name)
    armature_handle = steframe_module.armatures_objects[armature_name]

    # Apply config to armature
    armature_handle.armature_config_dict = None
    armature_handle.armature_config_csts = config_csts
    armature_handle.uneval_armature_config_dict = config_dict
    armature_handle.visible = True
    steframe_module._update_armature_parameters_widgets_on_configuration_change(armature_handle)
    armature_handle.update_render()


steframe_module = cfv.get_module_object_from_name('StereotaxicFrame')

for armature_name, armature_attr in steretaxic_frame_buider_dict.items():
    add_armature_with_config(
        steframe_module,
        armature_name,
        armature_attr['armature_type'],
        armature_attr['configuration_dict'],
        armature_attr['constants_dict']
    )

# %% Setup armatures architecture

steframe_module.update_armature_inheritance(steframe_arch_dict={
    'Skull Mesh': None,
    'Brain Mesh': None,
    'Bregma to Stereotaxic Frame Origin': {
        'Stereotaxic Frame Rails Distance': {
            'Recording Electrode Arm': {
                'Electrode Electrode Shaft': {
                    'Recording Electrode Body': None
                }
            }
        },
        'FUS Transducer Arm': {
            'FUS Transducer Shaft': {
                'FUS Transducer Holder Mesh': {
                    'Theoretical FUS focal spot preview': None,
                    'kWave 3D Simulation': None
                }
            }
        },
        'Coordinates Registration Probe Arm': {
            'Coords Registration Probe Shaft': {
                'Coords Registration Probe Tip': None
            }
        }
    }
})

# %% Add Atlas

batlas_module = cfv.get_module_object_from_name('BrainAtlas') # Get BrainAtlasModule handle
batlas_module.add_reference_atlas('whs_sd_rat_39um') # Loading atlas
batlas_module.add_structure_layer(structure='Ventral tegmental area (VTA)', hemisphere='Right Hemisphere')
batlas_module.add_structure_layer(structure='Nucleus accumbens (NAc)', hemisphere='Right Hemisphere')

batlas_module.set_user_param('atlas_transform_str', 'Rx0.7deg Ry-6.6deg Ty-0.5mm Tx-4.5mm Tz-8mm')
batlas_module._update_atlas_user_params_editors()
batlas_module.update_rendered_object()

# %% Set Anatomical calibration landmarks

anatcalib_module = cfv.get_module_object_from_name('AnatLandmarksCalib')

anat_landmarks_dict = {
    'uncal_anatomical_landmarks_coords': {
        'Lambda': [-0.0075, 0.0, 0.0], 'Bregma': [0.0, 0.0, 0.0]},
    'cal_anatomical_landmarks_coords': {
        'Lambda': [-0.0085, 5e-05, -3.465e-18], 'Bregma': [0.0, 0.0, 0.0]}
}

anatcalib_module._populate_treeview_from_dict(anat_landmarks_dict)
anatcalib_module._on_treeview_edit()
