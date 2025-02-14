from coperniFUS import *
from coperniFUS.modules.armatures.mesh_armatures import STLMeshBooleanArmature
from coperniFUS.modules.armatures.base_armature import Armature
from coperniFUS.modules.interfaces.kwave_interfaces import *
from coperniFUS.modules.interfaces.trimesh_interfaces import *


class KwaveAShomogeneousSimulationArmature(Armature):

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (0.6, 0.6, 0.6, 0.7),
        'glline_width': 5,
        'armature_config_csts': {
            'p_max_viz': 100000.0,
            'kwave_AS_h5_dir': None
        },
        'uneval_armature_config_dict': {
            '_stl_mesh': {
                'file_path': 'None',
                'transform_str': None,
                'ignore_plane_slicing': True,
                'gl_mesh_shader': None,
                'gl_mesh_drawEdges': True,
                'gl_mesh_drawFaces': False,
                'gl_mesh_edgeColor': (0.82745098, 0.32941176, 0.0, 0.6),
                'gl_mesh_glOptions': 'opaque',
                'gl_mesh_smooth': False,
                'gl_mesh_edgeWidth': 5
            },
            '_kwave_sim': {
                'ignore_plane_slicing': True,
                '_axisym_domain_gl_options': {
                    'gl_mesh_shader': None,
                    'gl_mesh_drawEdges': True,
                    'gl_mesh_drawFaces': False,
                    'gl_mesh_edgeColor': (0.945, 0.768, 0.059, 1.0),
                    'gl_mesh_glOptions': 'opaque',
                    'gl_mesh_smooth': False,
                    'gl_mesh_edgeWidth': 2
                },
                '_axisymmetric_domain_boundary_trimesh_script': """

path_2d = trimesh.path.creation.circle(radius=AS_domain_r_size, segments=16)
extrusion = path_2d.extrude(AS_domain_z_size)
mesh = extrusion.to_mesh()
                    
                """,
                '_axisymmetric_domain_acoustic_params': {
                    'c_0': 1482.3,
                    'rho_0': 994.04,
                    'alpha_0': 0.0022,
                    'alpha_power_0': 1.0,
                    'c_tx_coupling_medium': 1482.3,
                    'rho_tx_coupling_medium': 994.04,
                    'source_f0': 1000000.0,
                    'source_roc': 0.015,
                    'source_diameter': 0.015,
                    'source_ac_pwr': 0.0249,
                    'source_phase': 0.0,
                    'AS_domain_z_size': 0.03,
                    'AS_domain_r_size': 0.01,
                    'ppw': 5,
                    'n_reflections': 2,
                    'record_periods': 1,
                    'cfl': 0.1,
                    'source_z_offset': 20,
                    'domain_z_extension': 20,
                    'bli_tolerance': 0.01,
                    'upsampling_rate': 10
                },
                '_sim_parameters': {
                    'source_f0': {
                        'args': ['f', 1000000.0],
                        '_is_editable': True,
                        '_edit_increment': 500000.0,
                        '_param_label': 'Source f0',
                        '_color': 'grey',
                        '_unit': 'Hz'
                    },
                    'AS_domain_z_size': {
                        'args': ['z', 0.03],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': 'Axisym. domain height',
                        '_color': 'grey',
                        '_unit': 'm'
                    },
                    'AS_domain_r_size': {
                        'args': ['r', 0.01],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': 'Axisym. domain radius',
                        '_color': 'grey',
                        '_unit': 'm'
                    }
                }
            }
        }
    }


    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        super().__init__(armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs)

        # Reset aramatures configuration dicts with default ones
        # self.armature_config_csts = self._DEFAULT_PARAMS['armature_config_csts']
        # self.uneval_armature_config_dict = self._DEFAULT_PARAMS['uneval_armature_config_dict']

        self._axisymm_p_field = None
        self.axisym_domain_mesh_handler = TrimeshHandler(parent_viewer)
        self._current_axisym_domain_mesh_params = None
        self._axisym_domain_mesh = None
        self._kwAS_success = False
        self.kwAS = None
        self.p_amp_AS_vol_tmat = None
        self.voxel_centers = {}

    @property
    def end_transform_mat(self):
        """ returns the transform matrix of the last joint in the armature """
        tx_bowl_depth = 2.01e-3
        if self.parent_transform_mat is None:
            self._end_transform_mat = np.eye(4) # (0, 0, 0) -> default if no parent armature
        else:
            self._end_transform_mat = self.parent_transform_mat
        self._end_transform_mat = af_tr.translat_mat('z', tx_bowl_depth) @ self._end_transform_mat
        self._end_transform_mat = af_tr.rot_mat('x', 180) @ self._end_transform_mat
        return self._end_transform_mat

    @property
    def axisym_domain_mesh(self):
        has_been_updated = False

        # Retreive boolean mask param values
        bool_mask_params = {mask_param: mask_param_value['args'][1] for (mask_param, mask_param_value) in self.armature_config_dict['_kwave_sim']['_sim_parameters'].items()}

        # Reset mesh if parameters have been updated
        if self._current_axisym_domain_mesh_params != bool_mask_params:
            self._axisym_domain_mesh = None

        if self._axisym_domain_mesh is None:
            accessible_globals_names = [
                'trimesh', 'np',
                'dict_to_path_patched'
            ]

            accessible_globals = {accessible_glob_name: globals()[accessible_glob_name] for accessible_glob_name in accessible_globals_names}
            accessible_globals = {**accessible_globals, **bool_mask_params}

            # run trimesh script
            try:
                exec(self.armature_config_dict['_kwave_sim']['_axisymmetric_domain_boundary_trimesh_script'], accessible_globals)
                self._axisym_domain_mesh = accessible_globals['mesh']
                self._current_axisym_domain_mesh_params = bool_mask_params
                has_been_updated = True
            except Exception as e:
                self._axisym_domain_mesh = None
                self._current_axisym_domain_mesh_params = None
                has_been_updated = False
                self.parent_viewer.show_error_popup(f"Error in {self.armature_display_name} _axisymmetric_domain_boundary_trimesh_script", f'{type(e).__name__}: {str(e)}')

        return (self._axisym_domain_mesh, has_been_updated)

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = super().custom_armature_param_widgets(armature_params_rowcount, armature_params_colcount)
        # AS simulation button
        as_sim_btn = pyqtw.QPushButton('Axisymmetric (AS) simulation')
        as_sim_btn.clicked.connect(self.run_AS_simulation)
        custom_widgets.append(
            (as_sim_btn, armature_params_rowcount+1, 0, 1, armature_params_colcount)
        )
        return custom_widgets

    def update_axisym_domain_transform_matrix(self):
        self.axisym_domain_mesh_handler.stl_item_tmat = self.end_transform_mat #bmask_tmat

    def update_AS_sim_parameters(self):
        # Overwrite default simulation parameters with those specified in the armature parameters dictionary under _kwave_sim and _axisymmetric_domain_acoustic_params
        armature_dict_sim_params = self.uneval_armature_config_dict['_kwave_sim']['_axisymmetric_domain_acoustic_params']
        for sim_param_key in armature_dict_sim_params.keys():
            self.kwAS.set_simulation_param(sim_param_key, armature_dict_sim_params[sim_param_key])

        # Overwrite default simulation parameters with editable values
        _editable_params_values = copy.deepcopy(self._editable_params_values)
        for sim_param_key in self.kwAS.simulation_params.keys():
            if sim_param_key in _editable_params_values:
                self.kwAS.set_simulation_param(sim_param_key, _editable_params_values[sim_param_key])

    def run_AS_simulation(self):

        self.kwAS = KwaveHomogeneousAxisymetricBowlSim()

        self.update_AS_sim_parameters()

        # kWave I/O h5 files location retreival
        if 'kwave_AS_h5_dir' in self.armature_config_csts:
            kwave_AS_h5_dir = self.armature_config_csts['kwave_AS_h5_dir']
        else:
            kwave_AS_h5_dir = None

        def run_simulation_threaded_wrapper(*args, **kwargs):
            # Run sim
            self._kwAS_success = self.kwAS.run_simulation(io_h5files_directory_path=kwave_AS_h5_dir)
            self.render_AS_pfield()

        self.threaded_kwave_sim = threading.Thread(
            target=run_simulation_threaded_wrapper,
            args=(kwave_AS_h5_dir,))
        self.threaded_kwave_sim.start()
        
    def render_AS_pfield(self):
        if self._kwAS_success:
            p_amp_AS_xyz, x_AS, y_AS, z_AS = self.kwAS.p_amp_xyz

            if np.any(np.isnan(p_amp_AS_xyz)):
                raise ValueError('kWave AS field contains NANs -> recompute sim with higher CFL and/or points per wavelength')

            # Pressure field render opacity
            if 'pressure_field_render_stride' in self.armature_config_csts:
                p_field_stride = self.armature_config_csts['pressure_field_render_stride']
            else:
                p_field_stride = 1

            p_amp_AS_xyz = p_amp_AS_xyz[p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride]
            x_AS = x_AS[p_field_stride//2::p_field_stride]
            y_AS = y_AS[p_field_stride//2::p_field_stride]
            z_AS = z_AS[p_field_stride//2::p_field_stride]

            z_mask = np.where(z_AS < np.abs(self.kwAS.simulation_params['AS_domain_z_size']))[0]
            p_amp_AS_xyz = p_amp_AS_xyz[:, :, z_mask]
            z_cart = z_AS[z_mask]

            if np.any(np.isnan(p_amp_AS_xyz)):
                raise ValueError('kWave AS field contains NANs -> recompute sim with higher CFL and/or points per wavelength')

            # Remove render if it already exists
            if hasattr(self, 'p_amp_AS_vol'):
                if self.p_amp_AS_vol in self.parent_viewer.gl_view.items:
                    self.parent_viewer.gl_view.removeItem(self.p_amp_AS_vol)

            # Colormap max
            if 'p_max_viz' in self.armature_config_csts:
                vmax = self.armature_config_csts['p_max_viz']
            else:
                vmax = p_amp_AS_xyz.max()

            # Pressure field render opacity
            if 'pressure_field_render_opacity' in self.armature_config_csts:
                p_amp_alpha = self.armature_config_csts['pressure_field_render_opacity']
            else:
                p_amp_alpha = 20

            p_amp_norm_func = plt.Normalize(vmin=0, vmax=vmax)
            self.p_amp_rgba = plt.cm.viridis(p_amp_norm_func(p_amp_AS_xyz)) * 255

            self.p_amp_rgba[:, :, :, 3] = (p_amp_alpha * p_amp_norm_func(p_amp_AS_xyz)).astype(int)
            self.p_amp_AS_vol = gl.GLVolumeItem(self.p_amp_rgba.astype(int), smooth=True, glOptions='additive')
            self.parent_viewer.gl_view.addItem(self.p_amp_AS_vol, name=f'k-Wave AS pressure field')
            self.p_amp_AS_vol.setDepthValue(2)

            self.p_amp_AS_vol_tmat = af_tr.scale_mat(self.kwAS.dx * p_field_stride)
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ af_tr.translat_mat('x', x_AS[0])
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ af_tr.translat_mat('y', y_AS[0])
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ af_tr.translat_mat('z', z_AS[0])
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ self.end_transform_mat

            self.p_amp_AS_vol.resetTransform()
            self.p_amp_AS_vol.applyTransform(pyqtg.QMatrix4x4(self.p_amp_AS_vol_tmat.T.ravel()), local=False)

    def add_render(self):
        super().add_render()
        if '_kwave_sim' in self.armature_config_dict:

            if self.axisym_domain_mesh is not None:
                self.axisym_domain_mesh_handler.stl_item_name = 'kwave_axisym_domain_mesh'
                self.axisym_domain_mesh_handler.raw_stl_item_mesh = self.axisym_domain_mesh[0]
                self._is_render_uptodate # Init hash
                
                self.update_axisym_domain_transform_matrix()

                # Set StlHandler gl parameters
                armature_dict_mesh_params = self.uneval_armature_config_dict['_kwave_sim']['_axisym_domain_gl_options']
                for mesh_param_key in self.axisym_domain_mesh_handler._DEFAULT_PARAMS.keys():
                    if mesh_param_key in armature_dict_mesh_params:
                        self.axisym_domain_mesh_handler.set_stl_user_param(mesh_param_key, armature_dict_mesh_params[mesh_param_key])

                if self.axisym_domain_mesh_handler.stl_glitem != None or self.visible is False:
                    self.axisym_domain_mesh_handler.delete_rendered_object()
                else:
                    self.axisym_domain_mesh_handler.add_rendered_object()

    def update_render(self, force_update=False):
        if not self._is_render_uptodate or force_update:
            super().update_render(force_update=True)
            # st_time = time.time()
            if self.visible is True:
                if self.axisym_domain_mesh_handler.stl_glitem is None:
                    self.add_render()

                self.update_axisym_domain_transform_matrix()

                if self.axisym_domain_mesh[1]: # Check if the mesh has been updated
                    self.axisym_domain_mesh_handler.raw_stl_item_mesh = self.axisym_domain_mesh[0]
                self.axisym_domain_mesh_handler.update_rendered_object()
            else:
                self.delete_render()
            # print(f' >> STLMeshBooleanArmature -> {self._is_render_uptodate} | {si_format(time.time() - st_time)}s')
    
    def delete_render(self):
        super().delete_render()
        self.axisym_domain_mesh_handler.delete_rendered_object()


class KWave3dSimulationArmature(STLMeshBooleanArmature):

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (0.6, 0.6, 0.6, 0.7),
        'glline_width': 5,
        'armature_config_csts': {
            'p_max_viz': 500000.0,
            'kwave_3D_h5_dir': None,
            'pressure_field_render_stride': 1
        },
        'uneval_armature_config_dict': {
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
                '_src_meshes': ['_stl_mesh'],
                '_boolean_operations': {
                    '1': ['intersection', ['Brain mesh (skull convex Hull)', '_boolean_mask']],
                    '2': ['intersection', ['Skull acoustic window', '_boolean_mask']]
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
    dict_to_path_patched(path_2d_dict)
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
                    'alpha_mode': None,
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
    }

    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        super().__init__(armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs)

        self._kw3D_success = False
        self.kw3D = None
        self.p_amp_3D_vol_tmat = None
        self.voxel_centers = {}

    @property
    def end_transform_mat(self):
        """ returns the transform matrix of the last joint in the armature """
        if self.parent_transform_mat is None:
            self._end_transform_mat = np.eye(4) # (0, 0, 0) -> default if no parent armature
        else:
            self._end_transform_mat = self.parent_transform_mat
        self._end_transform_mat = af_tr.rot_mat('x', 180) @ self._end_transform_mat
        return self._end_transform_mat

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = super().custom_armature_param_widgets(armature_params_rowcount, armature_params_colcount)

        # 3D simulation button
        as_sim_btn = pyqtw.QPushButton('3D simulation')
        as_sim_btn.clicked.connect(self.run_3D_simulation)
        custom_widgets.append(
            (as_sim_btn, armature_params_rowcount+2, 0, 1, armature_params_colcount)
        )
        return custom_widgets

    def update_3D_sim_parameters(self):
        # Overwrite default simulation parameters with those specified in the armature parameters dictionary under _kwave_sim and _3dcartesian_domain_acoustic_params
        armature_dict_sim_params = self.uneval_armature_config_dict['_kwave_sim']['_3dcartesian_domain_acoustic_params']
        for sim_param_key in armature_dict_sim_params.keys():
            self.kw3D.set_simulation_param(sim_param_key, armature_dict_sim_params[sim_param_key])

        # Overwrite default simulation parameters with editable values
        _editable_params_values = copy.deepcopy(self._editable_params_values)
        for sim_param_key in self.kw3D.simulation_params.keys():
            if sim_param_key in _editable_params_values:
                self.kw3D.set_simulation_param(sim_param_key, _editable_params_values[sim_param_key])

    def run_3D_simulation(self):

        self.kw3D = Kwave3D()

        self.update_3D_sim_parameters()

        # kWave I/O h5 files location retreival
        if 'kwave_3D_h5_dir' in self.armature_config_csts:
            kwave_3D_h5_dir = self.armature_config_csts['kwave_3D_h5_dir']
        else:
            kwave_3D_h5_dir = None

        # --- kWave complex medium setup ---

        # Skip medium definition if h5 result file already exists
        reload_sim_data_from_h5 = False
        if kwave_3D_h5_dir is not None:
            output_filepath = pathlib.Path(kwave_3D_h5_dir) / f'kwave_3D_output_{self.kw3D._simulation_hash}.h5'
            if output_filepath.exists():
                reload_sim_data_from_h5 = True

        if not reload_sim_data_from_h5:

            print('Starting kWave simulation..')

            # kWaveMedium init
            self.kw3D._medium = kWaveMedium(
                sound_speed=None,
                density=None,
                alpha_coeff=None,
                alpha_power=np.array([self.kw3D.kwave_alpha_power]), # stokes safe -> see kWave doc
                alpha_mode='stokes'
            )
            raveled_sound_speed = np.ones((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz), dtype=float).ravel()
            raveled_density = np.ones((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz), dtype=float).ravel()
            raveled_alpha = np.ones((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz), dtype=float).ravel()
            
            # Set base medium properties
            raveled_sound_speed *= self.kw3D.c(0)
            raveled_density *= self.kw3D.rho(0)
            raveled_alpha *= self.kw3D.alpha_corrected(0)

            def voxelize_domain_and_apply_mat_properties(mesh):
                material_index = mesh.bool_mesh_index # Retreive material index before deepcopy (will be deleted in that process)

                mesh = copy.deepcopy(mm)
                mesh.apply_transform(np.linalg.inv(self.end_transform_mat.T))

                # Voxelize mesh
                voxel_size = self.kw3D.dx
                voxelized = mesh.voxelized(pitch=voxel_size, max_iter=1000)
                voxelized = voxelized.fill()
                # voxelized.show() # Debug
                # KDTree for fast voxel lookup
                self.voxel_centers[material_index] = voxelized.points
                voxel_tree = cKDTree(self.voxel_centers[material_index])
                # self.render_voxelized_mesh_preview(material_index)
                # Only keep points that are within the voxel grid
                distance_threshold = voxel_size / 2.0  # Adjust based on voxel grid resolution
                distances, indices = voxel_tree.query(self.kw3D.kgrid_coords, distance_upper_bound=distance_threshold)
                valid_points_mask = distances != np.inf

                # Set medium properties on voxelized mesh
                raveled_sound_speed[valid_points_mask] = self.kw3D.c(material_index)
                raveled_density[valid_points_mask] = self.kw3D.rho(material_index)
                raveled_alpha[valid_points_mask] = self.kw3D.alpha_corrected(material_index)

            # Domain mesh material properties assignement
            if isinstance(self.mesh_handler.stl_item_mesh_processed, trimesh.Trimesh):
                voxelize_domain_and_apply_mat_properties(self.mesh_handler.stl_item_mesh_processed)
            elif isinstance(self.mesh_handler.stl_item_mesh_processed, list):
                for mm in self.mesh_handler.stl_item_mesh_processed:
                    voxelize_domain_and_apply_mat_properties(mm)

            self.kw3D._medium.sound_speed = raveled_sound_speed.reshape((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz))
            self.kw3D._medium.density = raveled_density.T.reshape((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz))
            self.kw3D._medium.alpha_coeff = raveled_alpha.T.reshape((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz))

            # Debug
            # viewer.add_image(self.kw3D._medium.sound_speed, name='Sound speed', rendering='attenuated_mip', translate=(-self.kw3D.Nx//2, -self.kw3D.Ny//2, -self.kw3D.simulation_params['source_z_offset']), opacity=.5)

        def run_simulation_threaded_wrapper(*args, **kwargs):
            # Run sim
            self._kw3D_success = self.kw3D.run_simulation(io_h5files_directory_path=kwave_3D_h5_dir)

            self.render_3D_pfield()

            # Debug
            # viewer.add_image(self.kw3D.p_amp_xyz[0], name='Pressure field', colormap='viridis', blending='additive', translate=(-self.kw3D.Nx//2, -self.kw3D.Ny//2, -self.kw3D.simulation_params['source_z_offset']))

        self.threaded_kwave_sim = threading.Thread(
            target=run_simulation_threaded_wrapper,
            args=(kwave_3D_h5_dir,))
        self.threaded_kwave_sim.start()
    
    def render_voxelized_mesh_preview(self, material_index=0):
        # Voxelized mesh gl preview
        if hasattr(self, f'voxelized_material_{material_index}'):
            vox_mat_glpts = getattr(self, f'voxelized_material_{material_index}')
            if vox_mat_glpts in self.parent_viewer.gl_view.items:
                self.parent_viewer.gl_view.removeItem(vox_mat_glpts)

        if self.voxel_centers is not None and material_index in self.voxel_centers:
            setattr(self, f'voxelized_material_{material_index}', gl.GLScatterPlotItem())
            vox_mat_glpts = getattr(self, f'voxelized_material_{material_index}')
            vox_mat_glpts.setData(
                pos=self.voxel_centers[material_index],
                color=(0. , 0.33, 0.26, .5)
            )
            self.parent_viewer.gl_view.addItem(vox_mat_glpts, name=f'k-Wave 3D voxelized material #{material_index}')

            voxmesh_tmat = af_tr.scale_mat(1)
            voxmesh_tmat = voxmesh_tmat @ self.end_transform_mat

            vox_mat_glpts.resetTransform()
            vox_mat_glpts.applyTransform(pyqtg.QMatrix4x4(voxmesh_tmat.T.ravel()), local=False)

    def render_3D_pfield(self):
        if self._kw3D_success:
            p_amp_3D_xyz, x_3D, y_3D, z_3D = self.kw3D.p_amp_xyz

            if np.any(np.isnan(p_amp_3D_xyz)):
                raise ValueError('kWave 3D field contains NANs -> recompute sim with higher CFL and/or points per wavelength')

            # Pressure field render opacity
            if 'pressure_field_render_stride' in self.armature_config_csts:
                p_field_stride = self.armature_config_csts['pressure_field_render_stride']
            else:
                p_field_stride = 1

            p_amp_3D_xyz = p_amp_3D_xyz[p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride]
            x_3D = x_3D[p_field_stride//2::p_field_stride]
            y_3D = y_3D[p_field_stride//2::p_field_stride]
            z_3D = z_3D[p_field_stride//2::p_field_stride]

            if hasattr(self, 'p_amp_3D_vol'):
                if self.p_amp_3D_vol in self.parent_viewer.gl_view.items:
                    self.parent_viewer.gl_view.removeItem(self.p_amp_3D_vol)

            # Colormap max
            if 'p_max_viz' in self.armature_config_csts:
                vmax = self.armature_config_csts['p_max_viz']
            else:
                vmax = p_amp_3D_xyz.max()

            # Pressure field render opacity
            if 'pressure_field_render_opacity' in self.armature_config_csts:
                p_amp_alpha = self.armature_config_csts['pressure_field_render_opacity']
            else:
                p_amp_alpha = 20

            p_amp_norm_func = plt.Normalize(vmin=0, vmax=vmax)
            self.p_amp_rgba = plt.cm.viridis(p_amp_norm_func(p_amp_3D_xyz)) * 255

            self.p_amp_rgba[:, :, :, 3] = (p_amp_alpha * p_amp_norm_func(p_amp_3D_xyz)).astype(int)
            self.p_amp_3D_vol = gl.GLVolumeItem(self.p_amp_rgba.astype(int), smooth=True, glOptions='additive')
            self.parent_viewer.gl_view.addItem(self.p_amp_3D_vol, name=f'k-Wave 3D pressure field')
            self.p_amp_3D_vol.setDepthValue(2)

            self.p_amp_3D_vol_tmat = af_tr.scale_mat(self.kw3D.dx * p_field_stride)
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ af_tr.translat_mat('x', x_3D[0])
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ af_tr.translat_mat('y', y_3D[0])
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ af_tr.translat_mat('z', z_3D[0])
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ self.end_transform_mat

            self.p_amp_3D_vol.resetTransform()
            self.p_amp_3D_vol.applyTransform(pyqtg.QMatrix4x4(self.p_amp_3D_vol_tmat.T.ravel()), local=False)


class KWaveAS3dSimulationArmature(STLMeshBooleanArmature):

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (0.6, 0.6, 0.6, 0.7),
        'glline_width': 5,
        'armature_config_csts': {
            'p_max_viz': 100000.0,
            'kwave_AS_h5_dir': None,
            'kwave_3D_h5_dir': None
        },
        'uneval_armature_config_dict': {
            '_stl_mesh': {
                'file_path': 'None',
                'transform_str': None,
                'ignore_plane_slicing': True,
                'gl_mesh_shader': None,
                'gl_mesh_drawEdges': True,
                'gl_mesh_drawFaces': False,
                'gl_mesh_edgeColor': (0.82745098, 0.32941176, 0.0, 0.6),
                'gl_mesh_glOptions': 'opaque',
                'gl_mesh_smooth': False,
                'gl_mesh_edgeWidth': 5
            },
            '_boolean_mask': {
                '_boolean_operations': {
                    1: ('intersection', ['Brain mesh (skull convex Hull)', '_boolean_mask']),
                    2: ('intersection', ['Skull acoustic window', '_boolean_mask'])
                },
                '_mask_preview_gl_options': {
                    'gl_mesh_shader': None,
                    'gl_mesh_drawEdges': True,
                    'gl_mesh_drawFaces': False,
                    'gl_mesh_edgeColor': (0.945, 0.768, 0.059, 1.0),
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
    dict_to_path_patched(path_2d_dict)
)

extrusion = path_2d_from_dict.extrude(threeD_domain_z_size)
mesh = extrusion.to_mesh()
z_translate_tmat = trimesh.transformations.compose_matrix(translate=[0, 0, AS_domain_z_size])
mesh.apply_transform(z_translate_tmat)
                    
                """,
                '_boolean_mask_coords': {
                    'AS_domain_z_size': {
                        'args': ['z', 0.006499999999999999],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': 'Axisym. domain height',
                        '_color': 'grey',
                        '_unit': 'm'
                    },
                    'AS_domain_r_size': {
                        'args': ['r', 0.01],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': 'Axisym. domain radius',
                        '_color': 'grey',
                        '_unit': 'm'
                    },
                    'threeD_domain_x_size': {
                        'args': ['x', 0.012],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': '3D ac. domain (x)',
                        '_color': 'x_RED',
                        '_unit': 'm'
                    },
                    'threeD_domain_y_size': {
                        'args': ['y', 0.01],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': '3D ac. domain (y)',
                        '_color': 'y_GREEN',
                        '_unit': 'm'
                    },
                    'threeD_domain_z_size': {
                        'args': ['x', 0.022],
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
                    'gl_mesh_edgeColor': (0.945, 0.768, 0.059, 1.0),
                    'gl_mesh_glOptions': 'opaque',
                    'gl_mesh_smooth': False,
                    'gl_mesh_edgeWidth': 2
                },
                '_axisymmetric_domain_boundary_trimesh_script': """

path_2d = trimesh.path.creation.circle(radius=AS_domain_r_size, segments=16)
extrusion = path_2d.extrude(AS_domain_z_size)
mesh = extrusion.to_mesh()
                    
                """,
                '_axisymmetric_domain_acoustic_params': {
                    'c_0': 1482.3,
                    'rho_0': 994.04,
                    'alpha_0': 0.0022,
                    'alpha_power_0': 1.0,
                    'c_tx_coupling_medium': 1482.3,
                    'rho_tx_coupling_medium': 994.04,
                    'source_f0': 1000000.0,
                    'source_roc': 0.015,
                    'source_diameter': 0.015,
                    'source_ac_pwr': 0.0249,
                    'source_phase': 0.0,
                    'AS_domain_z_size': 0.03,
                    'AS_domain_r_size': 0.01,
                    'ppw': 5,
                    'n_reflections': 2,
                    'record_periods': 1,
                    'cfl': 0.1,
                    'source_z_offset': 20,
                    'domain_z_extension': 20,
                    'bli_tolerance': 0.01,
                    'upsampling_rate': 10,
                    'cpp_engine': 'OMP',
                    'cpp_io_files_directory_path': 'cpp_files_path',
                    'run_through_external_cpp_solvers': True
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
                    'alpha_mode': None,
                    'source_f0': 1000000.0,
                    'source_roc': 0.015,
                    'source_diameter': 0.008,
                    'source_amp': 1000000.0,
                    'source_phase': 0.0,
                    'AS_domain_z_size': 0,
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
                        'args': ['f', 2000000.0],
                        '_is_editable': True,
                        '_edit_increment': 500000.0,
                        '_param_label': 'Source f0',
                        '_color': 'grey',
                        '_unit': 'Hz'
                    }
                }
            }
        }
    }


    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        super().__init__(armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs)

        # Reset aramatures configuration dicts with default ones
        # self.armature_config_csts = self._DEFAULT_PARAMS['armature_config_csts']
        # self.uneval_armature_config_dict = self._DEFAULT_PARAMS['uneval_armature_config_dict']

        self._axisymm_p_field = None
        self.axisym_domain_mesh_handler = TrimeshHandler(parent_viewer)
        self._current_axisym_domain_mesh_params = None
        self._axisym_domain_mesh = None
        self._kwAS_success = False
        self.kwAS = None
        self._kw3D_success = False
        self.kw3D = None
        self.p_amp_3D_vol_tmat = None
        self.p_amp_AS_vol_tmat = None
        self.voxel_centers = {}

    @property
    def end_transform_mat(self):
        """ returns the transform matrix of the last joint in the armature """
        tx_bowl_depth = 2.01e-3
        if self.parent_transform_mat is None:
            self._end_transform_mat = np.eye(4) # (0, 0, 0) -> default if no parent armature
        else:
            self._end_transform_mat = self.parent_transform_mat
        self._end_transform_mat = af_tr.translat_mat('z', tx_bowl_depth) @ self._end_transform_mat
        self._end_transform_mat = af_tr.rot_mat('x', 180) @ self._end_transform_mat
        return self._end_transform_mat

    @property
    def axisym_domain_mesh(self):
        has_been_updated = False

        # Retreive boolean mask param values
        bool_mask_params = {mask_param: mask_param_value['args'][1] for (mask_param, mask_param_value) in self.armature_config_dict['_boolean_mask']['_boolean_mask_coords'].items()}

        # Reset mesh if parameters have been updated
        if self._current_axisym_domain_mesh_params != bool_mask_params:
            self._axisym_domain_mesh = None

        if self._axisym_domain_mesh is None:
            accessible_globals_names = [
                'trimesh', 'np',
                'dict_to_path_patched'
            ]

            accessible_globals = {accessible_glob_name: globals()[accessible_glob_name] for accessible_glob_name in accessible_globals_names}
            accessible_globals = {**accessible_globals, **bool_mask_params}

            # run trimesh script
            try:
                exec(self.armature_config_dict['_kwave_sim']['_axisymmetric_domain_boundary_trimesh_script'], accessible_globals)
                self._axisym_domain_mesh = accessible_globals['mesh']
                self._current_axisym_domain_mesh_params = bool_mask_params
                has_been_updated = True
            except Exception as e:
                self._axisym_domain_mesh = None
                self._current_axisym_domain_mesh_params = None
                has_been_updated = False
                self.parent_viewer.show_error_popup(f"Error in {self.armature_display_name} _axisymmetric_domain_boundary_trimesh_script", f'{type(e).__name__}: {str(e)}')

        return (self._axisym_domain_mesh, has_been_updated)

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = super().custom_armature_param_widgets(armature_params_rowcount, armature_params_colcount)
        # AS simulation button
        as_sim_btn = pyqtw.QPushButton('Axisymmetric (AS) simulation')
        as_sim_btn.clicked.connect(self.run_AS_simulation)
        custom_widgets.append(
            (as_sim_btn, armature_params_rowcount+1, 0, 1, armature_params_colcount)
        )
        # 3D simulation button
        as_sim_btn = pyqtw.QPushButton('Coupled AS-3D simulation')
        as_sim_btn.clicked.connect(self.run_AS3D_simulation)
        custom_widgets.append(
            (as_sim_btn, armature_params_rowcount+2, 0, 1, armature_params_colcount)
        )
        return custom_widgets
    
    def update_axisym_domain_transform_matrix(self):
        self.axisym_domain_mesh_handler.stl_item_tmat = self.end_transform_mat #bmask_tmat

    def update_AS_sim_parameters(self):
        # Overwrite default simulation parameters with those specified in the armature parameters dictionary under _kwave_sim and _axisymmetric_domain_acoustic_params
        armature_dict_sim_params = self.uneval_armature_config_dict['_kwave_sim']['_axisymmetric_domain_acoustic_params']
        for sim_param_key in armature_dict_sim_params.keys():
            self.kwAS.set_simulation_param(sim_param_key, armature_dict_sim_params[sim_param_key])

        # Overwrite default simulation parameters with editable values
        _editable_params_values = copy.deepcopy(self._editable_params_values)
        for sim_param_key in self.kwAS.simulation_params.keys():
            if sim_param_key in _editable_params_values:
                self.kwAS.set_simulation_param(sim_param_key, _editable_params_values[sim_param_key])

    def update_3D_sim_parameters(self):
        # Overwrite default simulation parameters with those specified in the armature parameters dictionary under _kwave_sim and _3dcartesian_domain_acoustic_params
        armature_dict_sim_params = self.uneval_armature_config_dict['_kwave_sim']['_3dcartesian_domain_acoustic_params']
        for sim_param_key in armature_dict_sim_params.keys():
            self.kw3D.set_simulation_param(sim_param_key, armature_dict_sim_params[sim_param_key])

        # Overwrite default simulation parameters with editable values
        _editable_params_values = copy.deepcopy(self._editable_params_values)
        for sim_param_key in self.kw3D.simulation_params.keys():
            if sim_param_key in _editable_params_values:
                self.kw3D.set_simulation_param(sim_param_key, _editable_params_values[sim_param_key])

    def run_AS_simulation(self):

        self.kwAS = KwaveHomogeneousAxisymetricBowlSim()

        self.update_AS_sim_parameters()

        # kWave I/O h5 files location retreival
        if 'kwave_AS_h5_dir' in self.armature_config_csts:
            kwave_AS_h5_dir = self.armature_config_csts['kwave_AS_h5_dir']
        else:
            kwave_AS_h5_dir = None

        def run_simulation_threaded_wrapper(*args, **kwargs):
            # Run sim
            self._kwAS_success = self.kwAS.run_simulation(io_h5files_directory_path=kwave_AS_h5_dir)
            self.render_AS_pfield()

        self.threaded_kwave_sim = threading.Thread(
            target=run_simulation_threaded_wrapper,
            args=(kwave_AS_h5_dir,))
        self.threaded_kwave_sim.start()
        
    def render_AS_pfield(self):
        if self._kwAS_success:
            p_amp_AS_xyz, x_AS, y_AS, z_AS = self.kwAS.p_amp_xyz

            if np.any(np.isnan(p_amp_AS_xyz)):
                raise ValueError('kWave 3D field contains NANs -> recompute sim with higher CFL and/or points per wavelength')

            # Pressure field render opacity
            if 'pressure_field_render_stride' in self.armature_config_csts:
                p_field_stride = self.armature_config_csts['pressure_field_render_stride']
            else:
                p_field_stride = 1

            p_amp_AS_xyz = p_amp_AS_xyz[p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride]
            x_AS = x_AS[p_field_stride//2::p_field_stride]
            y_AS = y_AS[p_field_stride//2::p_field_stride]
            z_AS = z_AS[p_field_stride//2::p_field_stride]

            z_mask = np.where(z_AS < np.abs(self.kwAS.simulation_params['AS_domain_z_size']))[0]
            p_amp_AS_xyz = p_amp_AS_xyz[:, :, z_mask]
            z_cart = z_AS[z_mask]

            if np.any(np.isnan(p_amp_AS_xyz)):
                raise ValueError('kWave AS field contains NANs -> recompute sim with higher CFL and/or points per wavelength')

            # Remove render if it already exists
            if hasattr(self, 'p_amp_AS_vol'):
                if self.p_amp_AS_vol in self.parent_viewer.gl_view.items:
                    self.parent_viewer.gl_view.removeItem(self.p_amp_AS_vol)

            # Colormap max
            if 'p_max_viz' in self.armature_config_csts:
                vmax = self.armature_config_csts['p_max_viz']
            else:
                vmax = p_amp_AS_xyz.max()

            # Pressure field render opacity
            if 'pressure_field_render_opacity' in self.armature_config_csts:
                p_amp_alpha = self.armature_config_csts['pressure_field_render_opacity']
            else:
                p_amp_alpha = 20

            p_amp_norm_func = plt.Normalize(vmin=0, vmax=vmax)
            self.p_amp_rgba = plt.cm.viridis(p_amp_norm_func(p_amp_AS_xyz)) * 255

            self.p_amp_rgba[:, :, :, 3] = (p_amp_alpha * p_amp_norm_func(p_amp_AS_xyz)).astype(int)
            self.p_amp_AS_vol = gl.GLVolumeItem(self.p_amp_rgba.astype(int), smooth=True, glOptions='additive')
            self.parent_viewer.gl_view.addItem(self.p_amp_AS_vol, name=f'k-Wave AS pressure field')
            self.p_amp_AS_vol.setDepthValue(2)

            self.p_amp_AS_vol_tmat = af_tr.scale_mat(self.kwAS.dx * p_field_stride)
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ af_tr.translat_mat('x', x_AS[0])
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ af_tr.translat_mat('y', y_AS[0])
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ af_tr.translat_mat('z', z_AS[0])
            self.p_amp_AS_vol_tmat = self.p_amp_AS_vol_tmat @ self.end_transform_mat

            self.p_amp_AS_vol.resetTransform()
            self.p_amp_AS_vol.applyTransform(pyqtg.QMatrix4x4(self.p_amp_AS_vol_tmat.T.ravel()), local=False)

    def run_AS3D_simulation(self):

        if not self._kwAS_success:
            warnings.warn('Please run the AS simulation first to perform AS-3D coupling')
        else:
            self.kw3D = Kwave3D()

            self.update_3D_sim_parameters()

            # kWave I/O h5 files location retreival
            if 'kwave_3D_h5_dir' in self.armature_config_csts:
                kwave_3D_h5_dir = self.armature_config_csts['kwave_3D_h5_dir']
            else:
                kwave_3D_h5_dir = None

            # --- kWave complex medium setup ---

            # Skip medium definition if h5 result file already exists
            reload_sim_data_from_h5 = False
            if kwave_3D_h5_dir is not None:
                output_filepath = pathlib.Path(kwave_3D_h5_dir) / f'kwave_3D_output_{self.kw3D._simulation_hash}.h5'
                if output_filepath.exists():
                    reload_sim_data_from_h5 = True

            if not reload_sim_data_from_h5:

                # kWaveMedium init
                self.kw3D._medium = kWaveMedium(
                    sound_speed=None,
                    density=None,
                    alpha_coeff=None,
                    alpha_power=np.array([self.kw3D.kwave_alpha_power]), # stokes safe -> see kWave doc
                    alpha_mode='stokes'
                )
                raveled_sound_speed = np.ones((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz), dtype=float).ravel()
                raveled_density = np.ones((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz), dtype=float).ravel()
                raveled_alpha = np.ones((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz), dtype=float).ravel()
                
                # Set base medium properties
                raveled_sound_speed *= self.kw3D.c(0)
                raveled_density *= self.kw3D.rho(0)
                raveled_alpha *= self.kw3D.alpha_corrected(0)

                def voxelize_domain_and_apply_mat_properties(mesh):
                    material_index = mesh.bool_mesh_index # Retreive material index before deepcopy (will be deleted in that process)

                    mesh = copy.deepcopy(mm)
                    mesh.apply_transform(np.linalg.inv(self.end_transform_mat.T))

                    # Voxelize mesh
                    voxel_size = self.kw3D.dx
                    voxelized = mesh.voxelized(pitch=voxel_size, max_iter=1000)
                    voxelized = voxelized.fill()
                    # voxelized.show() # Debug
                    # KDTree for fast voxel lookup
                    self.voxel_centers[material_index] = voxelized.points
                    voxel_tree = cKDTree(self.voxel_centers[material_index])
                    # self.render_voxelized_mesh_preview(material_index)
                    # Only keep points that are within the voxel grid
                    distance_threshold = voxel_size / 2.0  # Adjust based on voxel grid resolution
                    distances, indices = voxel_tree.query(self.kw3D.kgrid_coords, distance_upper_bound=distance_threshold)
                    valid_points_mask = distances != np.inf

                    # Set medium properties on voxelized mesh
                    raveled_sound_speed[valid_points_mask] = self.kw3D.c(material_index)
                    raveled_density[valid_points_mask] = self.kw3D.rho(material_index)
                    raveled_alpha[valid_points_mask] = self.kw3D.alpha_corrected(material_index)

                # Domain mesh material properties assignement
                if isinstance(self.mesh_handler.stl_item_mesh_processed, trimesh.Trimesh):
                    voxelize_domain_and_apply_mat_properties(self.mesh_handler.stl_item_mesh_processed)
                elif isinstance(self.mesh_handler.stl_item_mesh_processed, list):
                    for mm in self.mesh_handler.stl_item_mesh_processed:
                        voxelize_domain_and_apply_mat_properties(mm)

                self.kw3D._medium.sound_speed = raveled_sound_speed.reshape((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz))
                self.kw3D._medium.density = raveled_density.T.reshape((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz))
                self.kw3D._medium.alpha_coeff = raveled_alpha.T.reshape((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz))

                # Debug
                # viewer.add_image(self.kw3D._medium.sound_speed, name='Sound speed', rendering='attenuated_mip', translate=(-self.kw3D.Nx//2, -self.kw3D.Ny//2, -self.kw3D.simulation_params['source_z_offset'] + self.kw3D.simulation_params['AS_domain_z_size']/self.kw3D.dx), opacity=.5)

                # --- kWave source setup -> AS - 3D domain coupling ---

                self.kw3D._source = kSource()

                pseudo_src_zloc_index = self.kw3D.simulation_params['source_z_offset']
                pseudo_src_zloc = self.kw3D.kgrid.z_vec[pseudo_src_zloc_index].item()

                self.kw3D._source.p_mask = np.zeros((self.kw3D.Nx, self.kw3D.Ny, self.kw3D.Nz), dtype=bool)
                self.kw3D._source.p_mask[:, :, pseudo_src_zloc_index] = True

                # Debug
                # viewer.add_image(self.kw3D._source.p_mask, name='Sound speed', rendering='attenuated_mip', translate=(-self.kw3D.Nx//2, -self.kw3D.Ny//2, -self.kw3D.simulation_params['source_z_offset'] + self.kw3D.simulation_params['AS_domain_z_size']/self.kw3D.dx), opacity=.5, colormap='red')

                # kWave grid XY coordinates
                x_grid, y_grid, z_grid = np.meshgrid(
                    np.squeeze(self.kw3D.kgrid.x_vec),
                    np.squeeze(self.kw3D.kgrid.y_vec),
                    pseudo_src_zloc - self.kw3D.kgrid.z_vec[0] + self.kw3D.simulation_params['AS_domain_z_size'] - self.kw3D.simulation_params['source_z_offset'] * self.kw3D.dx
                )

                # Convert the Cartesian grid to cylindrical coordinates
                r_grid = np.sqrt(x_grid**2 + y_grid**2)

                # Create a 2D interpolator for the pressure and phase fields
                p_amp_zr, phase_zr, f0, z_as, r_as = self.kwAS.pamp_phase_freq_zr
                interp_pmag = scipy.interpolate.RegularGridInterpolator((r_as, z_as), p_amp_zr.T, bounds_error=False, fill_value=0)
                interp_phase = scipy.interpolate.RegularGridInterpolator((r_as, z_as), np.unwrap(phase_zr - np.pi/2).T, bounds_error=False, fill_value=0) # TODO check -np.pi/2 in unwrap

                # Interpolate the AS field onto the 3D kgrid
                points = np.array([r_grid.flatten(), z_grid.flatten()]).T
                pseudo_src_pmag = interp_pmag(points).reshape(r_grid.shape)
                pseudo_src_phase = interp_phase(points).reshape(r_grid.shape)

                # Populate 3D grid with interpolated AS pressures
                t_vec = np.squeeze(self.kw3D.kgrid.t_array)
                self.kw3D._source.p = np.zeros((pseudo_src_pmag.size, t_vec.size))
                for ii, (amp, phase) in enumerate(zip(tqdm(pseudo_src_pmag.ravel()), pseudo_src_phase.ravel())):
                    self.kw3D._source.p[ii] = create_cw_signals(t_vec, f0, np.array([amp]), np.array([phase]))

            def run_simulation_threaded_wrapper(*args, **kwargs):
                # Run sim
                self._kw3D_success = self.kw3D.run_simulation(io_h5files_directory_path=kwave_3D_h5_dir)

                self.render_3D_pfield()

                # Debug
                # viewer.add_image(self.kw3D.p_amp_xyz[0], name='Pressure field', colormap='viridis', blending='additive', translate=(-self.kw3D.Nx//2, -self.kw3D.Ny//2, -self.kw3D.simulation_params['source_z_offset'] + self.kw3D.simulation_params['AS_domain_z_size']/self.kw3D.dx))

            self.threaded_kwave_sim = threading.Thread(
                target=run_simulation_threaded_wrapper,
                args=(kwave_3D_h5_dir,))
            self.threaded_kwave_sim.start()

    
    def render_voxelized_mesh_preview(self, material_index=0):
        # Voxelized mesh gl preview
        if hasattr(self, f'voxelized_material_{material_index}'):
            vox_mat_glpts = getattr(self, f'voxelized_material_{material_index}')
            if vox_mat_glpts in self.parent_viewer.gl_view.items:
                self.parent_viewer.gl_view.removeItem(vox_mat_glpts)

        if self.voxel_centers is not None and material_index in self.voxel_centers:
            setattr(self, f'voxelized_material_{material_index}', gl.GLScatterPlotItem())
            vox_mat_glpts = getattr(self, f'voxelized_material_{material_index}')
            vox_mat_glpts.setData(
                pos=self.voxel_centers[material_index],
                color=(0. , 0.33, 0.26, .5)
            )
            self.parent_viewer.gl_view.addItem(vox_mat_glpts, name=f'k-Wave AS-3D voxelized material #{material_index}')

            voxmesh_tmat = af_tr.scale_mat(1)
            voxmesh_tmat = voxmesh_tmat @ self.end_transform_mat

            vox_mat_glpts.resetTransform()
            vox_mat_glpts.applyTransform(pyqtg.QMatrix4x4(voxmesh_tmat.T.ravel()), local=False)


    def render_3D_pfield(self):
        if self._kw3D_success:
            p_amp_3D_xyz, x_3D, y_3D, z_3D = self.kw3D.p_amp_xyz

            if np.any(np.isnan(p_amp_3D_xyz)):
                raise ValueError('kWave 3D field contains NANs -> recompute sim with higher CFL and/or points per wavelength')

            # Pressure field render opacity
            if 'pressure_field_render_stride' in self.armature_config_csts:
                p_field_stride = self.armature_config_csts['pressure_field_render_stride']
            else:
                p_field_stride = 1

            p_amp_3D_xyz = p_amp_3D_xyz[p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride, p_field_stride//2::p_field_stride]
            x_3D = x_3D[p_field_stride//2::p_field_stride]
            y_3D = y_3D[p_field_stride//2::p_field_stride]
            z_3D = z_3D[p_field_stride//2::p_field_stride]

            if hasattr(self, 'p_amp_3D_vol'):
                if self.p_amp_3D_vol in self.parent_viewer.gl_view.items:
                    self.parent_viewer.gl_view.removeItem(self.p_amp_3D_vol)

            # Colormap max
            if 'p_max_viz' in self.armature_config_csts:
                vmax = self.armature_config_csts['p_max_viz']
            else:
                vmax = p_amp_3D_xyz.max()

            # Pressure field render opacity
            if 'pressure_field_render_opacity' in self.armature_config_csts:
                p_amp_alpha = self.armature_config_csts['pressure_field_render_opacity']
            else:
                p_amp_alpha = 20

            p_amp_norm_func = plt.Normalize(vmin=0, vmax=vmax)
            self.p_amp_rgba = plt.cm.viridis(p_amp_norm_func(p_amp_3D_xyz)) * 255

            self.p_amp_rgba[:, :, :, 3] = (p_amp_alpha * p_amp_norm_func(p_amp_3D_xyz)).astype(int)
            self.p_amp_3D_vol = gl.GLVolumeItem(self.p_amp_rgba.astype(int), smooth=True, glOptions='additive')
            self.parent_viewer.gl_view.addItem(self.p_amp_3D_vol, name=f'k-Wave AS-3D pressure field')
            self.p_amp_3D_vol.setDepthValue(2)

            self.p_amp_3D_vol_tmat = af_tr.scale_mat(self.kw3D.dx * p_field_stride)
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ af_tr.translat_mat('x', x_3D[0])
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ af_tr.translat_mat('y', y_3D[0])
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ af_tr.translat_mat('z', z_3D[0])
            self.p_amp_3D_vol_tmat = self.p_amp_3D_vol_tmat @ self.end_transform_mat

            self.p_amp_3D_vol.resetTransform()
            self.p_amp_3D_vol.applyTransform(pyqtg.QMatrix4x4(self.p_amp_3D_vol_tmat.T.ravel()), local=False)

    def add_render(self):
        super().add_render()
        if '_kwave_sim' in self.armature_config_dict:

            if self.axisym_domain_mesh is not None:
                self.axisym_domain_mesh_handler.stl_item_name = 'kwave_axisym_domain_mesh'
                self.axisym_domain_mesh_handler.raw_stl_item_mesh = self.axisym_domain_mesh[0]
                self._is_render_uptodate # Init hash
                
                self.update_axisym_domain_transform_matrix()

                # Set StlHandler gl parameters
                armature_dict_mesh_params = self.uneval_armature_config_dict['_kwave_sim']['_axisym_domain_gl_options']
                for mesh_param_key in self.axisym_domain_mesh_handler._DEFAULT_PARAMS.keys():
                    if mesh_param_key in armature_dict_mesh_params:
                        self.axisym_domain_mesh_handler.set_stl_user_param(mesh_param_key, armature_dict_mesh_params[mesh_param_key])

                if self.axisym_domain_mesh_handler.stl_glitem != None or self.visible is False:
                    self.axisym_domain_mesh_handler.delete_rendered_object()
                else:
                    self.axisym_domain_mesh_handler.add_rendered_object()

    def update_render(self, force_update=False):
        if not self._is_render_uptodate or force_update:
            super().update_render(force_update=True)
            # st_time = time.time()
            if self.visible is True:
                if self.axisym_domain_mesh_handler.stl_glitem is None:
                    self.add_render()

                self.update_axisym_domain_transform_matrix()

                if self.axisym_domain_mesh[1]: # Check if the mesh has been updated
                    self.axisym_domain_mesh_handler.raw_stl_item_mesh = self.axisym_domain_mesh[0]
                self.axisym_domain_mesh_handler.update_rendered_object()
            else:
                self.delete_render()
            # print(f' >> STLMeshBooleanArmature -> {self._is_render_uptodate} | {si_format(time.time() - st_time)}s')
    
    def delete_render(self):
        super().delete_render()
        self.axisym_domain_mesh_handler.delete_rendered_object()

