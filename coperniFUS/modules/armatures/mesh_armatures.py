from coperniFUS import *
from coperniFUS.modules.interfaces.trimesh_interfaces import StlHandler, TrimeshHandler
from coperniFUS.modules.armatures.base_armature import Armature


class STLMeshArmature(Armature):

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (.6, .6, .6, .7),
        'glline_width': 5,

        'armature_config_csts': {},
        'uneval_armature_config_dict': {
            '_armature_joints': {
                'udialysis FUS holder': {
                    'translation_0': {
                        'args': ['x', -18e-3],
                        '_is_editable': False},
                    'translation_1': {
                        'args': ['z', -10e-3],
                        '_is_editable': False},
                }
            },
            '_stl_mesh': {
                'file_path': 'None',
                'transform_str': None,
                'ignore_plane_slicing': True,
                'ignore_anatomical_landmarks_calibration': True,
                'gl_mesh_shader': None,
                'gl_mesh_drawEdges': True,
                'gl_mesh_drawFaces': False,
                'gl_mesh_edgeColor': (.9, .9, .9, 1),
                'gl_mesh_glOptions': 'opaque',
                'gl_mesh_smooth': False,
                'gl_mesh_edgeWidth': 5,
            },
        },
    }

    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        super().__init__(armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs)

        # Reset aramatures configuration dicts with default ones
        # self.armature_config_csts = self._DEFAULT_PARAMS['armature_config_csts']
        # self.uneval_armature_config_dict = self._DEFAULT_PARAMS['uneval_armature_config_dict']

        self.mesh_handler = StlHandler(parent_viewer)

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = super().custom_armature_param_widgets(armature_params_rowcount, armature_params_colcount)
        # # Some widget
        # apply_boolean_operation_btn = pyqtw.QPushButton('Apply boolean operation')
        # apply_boolean_operation_btn.clicked.connect(self.compute_boolean_operation)
        # custom_widgets.append(
        #     (apply_boolean_operation_btn, armature_params_rowcount, 0, 1, armature_params_colcount)
        # )
        return custom_widgets

    def update_stl_item_transform_matrix(self):
        if 'transform_str' in self.armature_config_dict['_stl_mesh'] and self.armature_config_dict['_stl_mesh']['transform_str'] is not None:
            transforms_matrices = af_tr_from_str.transform_matrices_from_str(self.armature_config_dict['_stl_mesh']['transform_str'])
        else:
            transforms_matrices = [np.eye(4)]

        stl_item_tmat = np.eye(4)
        for tr_mat in transforms_matrices:
                stl_item_tmat = stl_item_tmat @ tr_mat
        stl_item_tmat = stl_item_tmat @ self.end_transform_mat

        self.mesh_handler.stl_item_tmat = stl_item_tmat

    def add_render(self):
        super().add_render()

        if '_stl_mesh' in self.armature_config_dict and self.armature_config_dict['_stl_mesh']['file_path'] is not None:

            if self.parent_viewer.assets_dir_path is not None:
                stl_fpath = self.parent_viewer.assets_dir_path / self.armature_config_dict['_stl_mesh']['file_path']
            else:
                stl_fpath = self.armature_config_dict['_stl_mesh']['file_path']

            if pathlib.Path(stl_fpath).exists():
                self._is_render_uptodate # Init hash
                self.mesh_handler.stl_item_name = pathlib.Path(stl_fpath).stem
                self.mesh_handler.set_stl_user_param('file_path', str(stl_fpath))
                
            # Set StlHandler gl parameters
            armature_dict_stl_params = self.uneval_armature_config_dict['_stl_mesh']
            for stl_param_key in self.mesh_handler._DEFAULT_PARAMS.keys():
                if stl_param_key in armature_dict_stl_params and stl_param_key != 'file_path':
                    self.mesh_handler.set_stl_user_param(stl_param_key, armature_dict_stl_params[stl_param_key])

            self.update_stl_item_transform_matrix()

            if self.mesh_handler.stl_glitem != None or self.visible is False:
                self.mesh_handler.delete_rendered_object()
            else:
                self.mesh_handler.add_rendered_object()

    def update_render(self, force_update=False):
        if not self._is_render_uptodate or force_update:
            super().update_render(force_update=True)
            if self.visible is True:
                if self.mesh_handler.stl_glitem is None:
                    self.add_render()
                self.update_stl_item_transform_matrix()
                self.mesh_handler.update_rendered_object() #ignore_plane_slicing=True)
            else:
                self.delete_render()
    
    def delete_render(self):
        super().delete_render()
        self.mesh_handler.delete_rendered_object()


class TrimeshScriptArmature(Armature):

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (.6, .6, .6, .7),
        'glline_width': 5,
        'armature_config_csts': {},
        'uneval_armature_config_dict': {
            '_stl_mesh': {
                'file_path': 'None',
                'transform_str': None,
                'ignore_plane_slicing': True,
                'ignore_anatomical_landmarks_calibration': True,
                'gl_mesh_shader': None,
                'gl_mesh_drawEdges': True,
                'gl_mesh_drawFaces': False,
                'gl_mesh_edgeColor': (.9, .9, .9, 1),
                'gl_mesh_glOptions': 'opaque',
                'gl_mesh_smooth': False,
                'gl_mesh_edgeWidth': 5,
            },
            '_trimesh_script': """
path_2d = trimesh.path.creation.circle(radius=cylinder_diameter/2, segments=64)
extrusion = path_2d.extrude(z)
mesh = extrusion.to_mesh()
z_translate_tmat = trimesh.transformations.compose_matrix(translate=[0, 0, z_offset])
mesh.apply_transform(z_translate_tmat)
        """,
            '_trimesh_script_coords': {
                'cylinder_diameter': {
                    'args': [
                        'diameter',
                        0.015
                    ],
                    '_is_editable': True,
                    '_edit_increment': 0.0005,
                    '_param_label': 'Ac. domain diameter',
                    '_color': 'grey',
                    '_unit': 'm'
                },
                'z': {
                    'args': [
                        'x',
                        -0.012500000000000002
                    ],
                    '_is_editable': True,
                    '_edit_increment': 0.0005,
                    '_param_label': 'Ac. domain (z)',
                    '_color': 'z_BLUE',
                    '_unit': 'm'
                },
                'z_offset': {
                    'args': [
                        'z',
                        0.0
                    ],
                    '_is_editable': True,
                    '_edit_increment': 0.0005,
                    '_param_label': 'Axisym. domain height',
                    '_color': 'grey',
                    '_unit': 'm'
                },
            },
        },
    }


    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        super().__init__(armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs)

        # Reset aramatures configuration dicts with default ones
        # self.armature_config_csts = self._DEFAULT_PARAMS['armature_config_csts']
        # self.uneval_armature_config_dict = self._DEFAULT_PARAMS['uneval_armature_config_dict']

        self._scripted_mesh = None
        self._current_mesh_params = None
        self.mesh_handler = StlHandler(parent_viewer)

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = super().custom_armature_param_widgets(armature_params_rowcount, armature_params_colcount)
        # # Some widget
        # apply_boolean_operation_btn = pyqtw.QPushButton('Apply boolean operation')
        # apply_boolean_operation_btn.clicked.connect(self.compute_boolean_operation)
        # custom_widgets.append(
        #     (apply_boolean_operation_btn, armature_params_rowcount, 0, 1, armature_params_colcount)
        # )
        return custom_widgets
    
    @property
    def scripted_mesh(self):
        has_been_updated = False

        if '_trimesh_script' in self.armature_config_dict:

            # Retreive scripted mesh param values
            if '_trimesh_script_coords' in self.armature_config_dict:
                mesh_params = {mask_param: mask_param_value['args'][1] for (mask_param, mask_param_value) in self.armature_config_dict['_trimesh_script_coords'].items()}
            else:
                mesh_params = {}
            
            # Reset mesh if parameters have been updated
            if self._current_mesh_params != mesh_params:
                self._scripted_mesh = None

            if self._scripted_mesh is None:
                accessible_globals_names = [
                    'trimesh', 'np',
                    'dict_to_path_patched'
                ]

                accessible_globals = {accessible_glob_name: globals()[accessible_glob_name] for accessible_glob_name in accessible_globals_names}
                accessible_globals = {**accessible_globals, **mesh_params}

                # run trimesh script
                try:
                    exec(self.armature_config_dict['_trimesh_script'], accessible_globals)
                    self._scripted_mesh = accessible_globals['mesh']
                    self._current_mesh_bmask_params = mesh_params
                    has_been_updated = True
                except Exception as e:
                    self._scripted_mesh = None
                    self._current_mesh_bmask_params = None
                    has_been_updated = False
                    self.parent_viewer.show_error_popup("Error in {self.armature_display_name} _trimesh_script", f'{type(e).__name__}: {str(e)}')

        else:
            self._scripted_mesh = None

        return (self._scripted_mesh, has_been_updated)

    def update_stl_item_transform_matrix(self):
        if 'transform_str' in self.armature_config_dict['_stl_mesh'] and self.armature_config_dict['_stl_mesh']['transform_str'] is not None:
            transforms_matrices = af_tr_from_str.transform_matrices_from_str(self.armature_config_dict['_stl_mesh']['transform_str'])
        else:
            transforms_matrices = [np.eye(4)]

        stl_item_tmat = np.eye(4)
        for tr_mat in transforms_matrices:
                stl_item_tmat = stl_item_tmat @ tr_mat
        stl_item_tmat = stl_item_tmat @ self.end_transform_mat

        self.mesh_handler.stl_item_tmat = stl_item_tmat

    def add_render(self):
        super().add_render()
        if '_trimesh_script' in self.armature_config_dict:

            if self.scripted_mesh is not None:
                self.mesh_handler.stl_item_name = 'trimesh_scripted_mesh'
                self.mesh_handler.raw_stl_item_mesh = self.scripted_mesh[0]
                self._is_render_uptodate # Init hash
                
                self.update_stl_item_transform_matrix()

                # Set StlHandler gl parameters
                armature_dict_stl_params = self.uneval_armature_config_dict['_stl_mesh']
                for stl_param_key in self.mesh_handler._DEFAULT_PARAMS.keys():
                    if stl_param_key in armature_dict_stl_params:
                        self.mesh_handler.set_stl_user_param(stl_param_key, armature_dict_stl_params[stl_param_key])

                if self.mesh_handler.stl_glitem != None or self.visible is False:
                    self.mesh_handler.delete_rendered_object()
                else:
                    self.mesh_handler.add_rendered_object()

    def update_render(self, force_update=False):
        if not self._is_render_uptodate or force_update:
            super().update_render(force_update=True)
            if self.visible is True:
                if self.mesh_handler.stl_glitem is None:
                    self.add_render()

                self.update_stl_item_transform_matrix()

                if self.scripted_mesh[1]: # Check if the mesh has been updated
                    self.mesh_handler.raw_stl_item_mesh = self.scripted_mesh[0]
                self.mesh_handler.update_rendered_object()
            else:
                self.delete_render()
    
    def delete_render(self):
        super().delete_render()
        self.mesh_handler.delete_rendered_object()


class STLMeshBooleanArmature(STLMeshArmature):

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (.6, .6, .6, .7),
        'glline_width': 5,

        'armature_config_csts': {},
        'uneval_armature_config_dict': {
            '_stl_mesh': {
                'file_path': 'Pohl2013_coarse.stl',
                'transform_str': 'S.11 Rz90deg Tz-31.9mm Tx46mm Ry3.7deg',
                'ignore_plane_slicing': False,
                'ignore_anatomical_landmarks_calibration': False,
                'gl_mesh_shader': 'boneShader',
                'gl_mesh_drawEdges': False,
                'gl_mesh_drawFaces': True,
                'gl_mesh_edgeColor': (0.9, 0.9, 0.9, 0.7),
                'gl_mesh_glOptions': 'opaque',
                'gl_mesh_smooth': False,
                'gl_mesh_edgeWidth': 2
            },
            '_boolean_mask': {
                'transform_str': 'Tz2mm',
                'ignore_plane_slicing': True,
                '_boolean_operations': ['difference', ['_stl_mesh', '_boolean_mask']],
                '_mask_preview_gl_options': {
                    'gl_mesh_shader': None,
                    'gl_mesh_drawEdges': True,
                    'gl_mesh_drawFaces': False,
                    'gl_mesh_edgeColor': (0.5, 0, 0, 1),
                    'gl_mesh_glOptions': 'opaque',
                    'gl_mesh_smooth': False,
                    'gl_mesh_edgeWidth': 5
                },
                '_boolean_mask_trimesh_script': """

a_AP_bregref = a_AP - bregma_AP
b_ML_bregref = b_ML - bregma_ML
c_AP_bregref = c_AP - bregma_AP
d_ML_bregref = d_ML - bregma_ML

mid_ML = (b_ML_bregref + d_ML_bregref) / 2
corner_radius = abs(b_ML_bregref - d_ML_bregref) / 2

trimesh.path.entities.Arc(points=[0, 1, 2], closed=False)

path_2d_dict = {
    'entities': [
        {'type': 'Arc', 'points': [0, 1, 2], 'closed': False},
        {'type': 'Line', 'points': [2, 3], 'closed': False},
        {'type': 'Arc', 'points': [3, 4, 5], 'closed': False},
        {'type': 'Arc', 'points': [5, 6, 7], 'closed': False},
        {'type': 'Line', 'points': [7, 8], 'closed': False},
        {'type': 'Arc', 'points': [8, 9, 0], 'closed': False}
        ],
    'vertices': [
        [a_AP_bregref, mid_ML],
        [a_AP_bregref - corner_radius * (1 - np.cos(np.pi/4)), mid_ML + corner_radius * np.cos(np.pi/4)],
        [a_AP_bregref - corner_radius, d_ML_bregref],
        [c_AP_bregref + corner_radius, d_ML_bregref],
        [c_AP_bregref + corner_radius * (1 - np.cos(np.pi/4)), mid_ML + corner_radius * np.cos(np.pi/4)],
        [c_AP_bregref, mid_ML],
        [c_AP_bregref + corner_radius * (1 - np.cos(np.pi/4)), mid_ML - corner_radius * np.cos(np.pi/4)],
        [c_AP_bregref + corner_radius, b_ML_bregref],
        [a_AP_bregref - corner_radius, b_ML_bregref],
        [a_AP_bregref - corner_radius * (1 - np.cos(np.pi/4)), mid_ML - corner_radius * np.cos(np.pi/4)],
    ]
}

path_2d_from_dict = trimesh.path.exchange.load.load_path(
    dict_to_path_patched(path_2d_dict)
)

extrusion = path_2d_from_dict.extrude(extrude_length)
mesh = extrusion.to_mesh()
                """,
                '_boolean_mask_coords': {
                    'bregma_AP': {
                        'args': ['x', 0.0684],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': 'Bregma AP',
                        '_color': 'grey',
                        '_unit': 'm'
                    },
                    'bregma_ML': {
                        'args': ['x', 0.019100000000000002],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': 'Bregma ML',
                        '_color': 'grey',
                        '_unit': 'm'
                    },
                    'a_AP': {
                        'args': ['x', 0.0673],
                        '_is_editable': True,
                        '_edit_increment': 0.0001,
                        '_param_label': 'Ac. window (a)',
                        '_color': 'x_RED',
                        '_unit': 'm'
                    },
                    'b_ML': {
                        'args': ['y', 0.014400000000000001],
                        '_is_editable': True,
                        '_edit_increment': 0.0001,
                        '_param_label': 'Ac. window (b)',
                        '_color': 'y_GREEN',
                        '_unit': 'm'
                    },
                    'c_AP': {
                        'args': ['x', 0.06],
                        '_is_editable': True,
                        '_edit_increment': 0.0001,
                        '_param_label': 'Ac. window (c)',
                        '_color': 'x_RED',
                        '_unit': 'm'
                    },
                    'd_ML': {
                        'args': ['y', 0.0185],
                        '_is_editable': True,
                        '_edit_increment': 0.0001,
                        '_param_label': 'Ac. window (d)',
                        '_color': 'y_GREEN',
                        '_unit': 'm'
                    },
                    'extrude_length': {
                        'args': ['x', -0.004],
                        '_is_editable': True,
                        '_edit_increment': 0.0005,
                        '_param_label': 'Ac. window extrude length',
                        '_color': 'grey',
                        '_unit': 'm'
                    }
                }
            }
        },
    }

    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        super().__init__(armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs)

        # Reset aramatures configuration dicts with default ones
        # self.armature_config_csts = self._DEFAULT_PARAMS['armature_config_csts']
        # self.uneval_armature_config_dict = self._DEFAULT_PARAMS['uneval_armature_config_dict']

        self.bool_mask_mesh_handler = TrimeshHandler(parent_viewer)
        self._bmask_mesh = None
        self._current_mesh_bmask_params = None

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = super().custom_armature_param_widgets(armature_params_rowcount, armature_params_colcount)

        # Boolean operation button
        apply_boolean_operation_btn = pyqtw.QPushButton('Apply boolean operation')
        apply_boolean_operation_btn.clicked.connect(self.compute_boolean_operation)

        custom_widgets.append(
            (apply_boolean_operation_btn, armature_params_rowcount, 0, 1, armature_params_colcount)
        )
        return custom_widgets

    def compute_boolean_operation(self):
        """ Supported boolean operations:
                - difference
                - intersection
                - union
        """

        def compute_b_operation(boperator_str, boolean_meshes_names, bool_mesh_index):
            b_mesh = None
            b_meshes = []
            for b_mesh_name in boolean_meshes_names:
                if b_mesh_name == '_stl_mesh':
                    self.mesh_handler.stl_item_mesh_processed = None # Reset boolean operations
                    b_mesh = self.mesh_handler.stl_item_mesh
                elif b_mesh_name == '_boolean_mask':
                    self.bool_mask_mesh_handler.stl_item_mesh_processed = None # Reset boolean operations
                    b_mesh = self.bool_mask_mesh_handler.stl_item_mesh
                elif b_mesh_name in self.stereotax_frame_instance._armatures_objects:
                    arma_obj = self.stereotax_frame_instance._armatures_objects[b_mesh_name]
                    if '_stl_mesh' in arma_obj.armature_config_dict:
                        b_mesh = copy.deepcopy(arma_obj.mesh_handler.stl_item_mesh)
                    else:
                        raise ValueError(f'Unsupported boolean mesh from armature -> {b_mesh_name}')
                else:
                    raise ValueError(f'Unsupported boolean mesh -> {b_mesh_name}')
                
                if b_mesh is not None:
                    b_meshes.append(b_mesh)
                else:
                    available_stl_armatures_formated = "\n\t".join([arma_obj_name for arma_obj_name, arma_obj in self.stereotax_frame_instance._armatures_objects.items() if '_stl_mesh' in arma_obj.armature_config_dict])
                    warnings.warn(f'Skipping {b_mesh_name} as it does not exist -> Please make sure that the mesh has been succesfully loaded or computed in the case of trimesh operations.\nAvaiblable meshes are:\n\t_stl_mesh\n\t_boolean_mask{available_stl_armatures_formated}')

            if boperator_str in b_operators:
                boolean_computed_mesh = b_operators[boperator_str](b_meshes)
                boolean_computed_mesh.bool_mesh_index = bool_mesh_index # Add index attribute (acoustic simulations material assignement)
            else:
                raise ValueError('Invalid boolean operator')
            
            return boolean_computed_mesh

        print('Applying boolean operation...')

        b_operators = {
            'difference': trimesh.boolean.difference,
            'intersection': trimesh.boolean.intersection,
            'union': trimesh.boolean.union
        }

        boolean_operations = self.armature_config_dict['_boolean_mask']['_boolean_operations']

        if isinstance(boolean_operations, list) and len(boolean_operations) == 2:
            boperator_str, boolean_meshes_names = boolean_operations
            boolean_computed_meshes = compute_b_operation(boperator_str, boolean_meshes_names, bool_mesh_index=0)
        elif isinstance(boolean_operations, dict):
            boolean_computed_meshes = []
            for op_ii, (boperator_str, boolean_meshes_names) in boolean_operations.items():
                boolean_computed_meshes.append(compute_b_operation(boperator_str, boolean_meshes_names, bool_mesh_index=op_ii))
        else:
            raise ValueError('Invalid boolean operation instruction')
        
        # Add mesh(es) to viewer
        if self.mesh_handler.stl_item_name is None: # If mesh_handler did not exist
            # Assign available mesh_handler name
            mesh_item_index = 0
            mesh_item_name_formater = lambda ii: f'boolean_op_result_mesh_{ii}'
            mesh_handler_child_attributes = [child_att for child_att in self.parent_viewer.cache.get_attr_unique_childs('mesh_handler') if 'boolean_op_result_mesh' in child_att]
            while mesh_item_name_formater(mesh_item_index) in mesh_handler_child_attributes:
                mesh_item_index += 1
            self.mesh_handler.stl_item_name = mesh_item_name_formater(mesh_item_index)

            # Set StlHandler gl parameters
            armature_dict_stl_params = self.uneval_armature_config_dict['_stl_mesh']
            for stl_param_key in self.mesh_handler._DEFAULT_PARAMS.keys():
                if stl_param_key in armature_dict_stl_params:
                    self.mesh_handler.set_stl_user_param(stl_param_key, armature_dict_stl_params[stl_param_key])

            self.mesh_handler.stl_item_mesh_processed = boolean_computed_meshes
            self.mesh_handler.add_rendered_object()

        else:
            self.mesh_handler.stl_item_mesh_processed = boolean_computed_meshes
            self.mesh_handler.update_rendered_object()
        
        print('Done')

    @property
    def bmask_mesh(self):
        has_been_updated = False

        if '_boolean_mask' in self.armature_config_dict and '_boolean_mask_trimesh_script' in self.armature_config_dict['_boolean_mask']:

            # Retreive boolean mask param values
            if '_boolean_mask_coords' in self.armature_config_dict['_boolean_mask']:
                bool_mask_params = {mask_param: mask_param_value['args'][1] for (mask_param, mask_param_value) in self.armature_config_dict['_boolean_mask']['_boolean_mask_coords'].items()}
            else:
                bool_mask_params = {}
            
            # Reset mesh if parameters have been updated
            if self._current_mesh_bmask_params != bool_mask_params:
                self._bmask_mesh = None

            if self._bmask_mesh is None:
                accessible_globals_names = [
                    'trimesh', 'np',
                    'dict_to_path_patched'
                ]

                accessible_globals = {accessible_glob_name: globals()[accessible_glob_name] for accessible_glob_name in accessible_globals_names}
                accessible_globals = {**accessible_globals, **bool_mask_params}

                # run trimesh script
                try:
                    exec(self.armature_config_dict['_boolean_mask']['_boolean_mask_trimesh_script'], accessible_globals)
                    self._bmask_mesh = accessible_globals['mesh']
                    self._current_mesh_bmask_params = bool_mask_params
                    has_been_updated = True
                except Exception as e:
                    self._bmask_mesh = None
                    self._current_mesh_bmask_params = None
                    has_been_updated = False
                    self.parent_viewer.show_error_popup(f"Error in {self.armature_display_name} _boolean_mask_trimesh_script", f'{type(e).__name__}: {str(e)}')

        else:
            self._bmask_mesh = None

        return (self._bmask_mesh, has_been_updated)

    def update_boolean_mask_transform_matrix(self):
        if ('_boolean_mask' in self.armature_config_dict) and ('transform_str' in self.armature_config_dict['_boolean_mask']) and (self.armature_config_dict['_boolean_mask']['transform_str'] is not None):
            transforms_matrices = af_tr_from_str.transform_matrices_from_str(self.armature_config_dict['_boolean_mask']['transform_str'])
        else:
            transforms_matrices = [np.eye(4)]

        bmask_tmat = self.end_transform_mat
        for tr_mat in transforms_matrices:
                bmask_tmat = bmask_tmat @ tr_mat

        self.bool_mask_mesh_handler.stl_item_tmat = bmask_tmat

    def add_render(self):
        super().add_render()
        if '_boolean_mask' in self.armature_config_dict:

            if self.bmask_mesh is not None:
                self.bool_mask_mesh_handler.stl_item_name = 'boolean_mask_mesh'
                self.bool_mask_mesh_handler.raw_stl_item_mesh = self.bmask_mesh[0]
                self._is_render_uptodate # Init hash
                
                self.update_boolean_mask_transform_matrix()

                # Set StlHandler gl parameters
                armature_dict_bmask_params = self.uneval_armature_config_dict['_boolean_mask']['_mask_preview_gl_options']
                for bmask_param_key in self.bool_mask_mesh_handler._DEFAULT_PARAMS.keys():
                    if bmask_param_key in armature_dict_bmask_params:
                        self.bool_mask_mesh_handler.set_stl_user_param(bmask_param_key, armature_dict_bmask_params[bmask_param_key])

                if self.bool_mask_mesh_handler.stl_glitem != None or self.visible is False:
                    self.bool_mask_mesh_handler.delete_rendered_object()
                else:
                    self.bool_mask_mesh_handler.add_rendered_object()

    def update_render(self, force_update=False):
        if not self._is_render_uptodate or force_update:
            super().update_render(force_update=True)
            # st_time = time.time()
            if self.visible is True:
                if self.bool_mask_mesh_handler.stl_glitem is None:
                    self.add_render()

                self.update_boolean_mask_transform_matrix()

                if self.bmask_mesh[1]: # Check if the mesh has been updated
                    self.bool_mask_mesh_handler.raw_stl_item_mesh = self.bmask_mesh[0]
                self.bool_mask_mesh_handler.update_rendered_object() #ignore_plane_slicing=True)
            else:
                self.delete_render()
            # print(f' >> STLMeshBooleanArmature -> {self._is_render_uptodate} | {si_format(time.time() - st_time)}s')
    
    def delete_render(self):
        super().delete_render()
        self.bool_mask_mesh_handler.delete_rendered_object()


class STLMeshConvexHull(STLMeshArmature): # Armature

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (.6, .6, .6, .7),
        'glline_width': 5,

        'armature_config_csts': {},
        'uneval_armature_config_dict': {
            '_stl_mesh': {
                'file_path': 'None',
                'transform_str': 'S1 Rx0deg Tz0mm',
                'ignore_plane_slicing': False,
                'gl_mesh_shader': None,
                'gl_mesh_drawEdges': True,
                'gl_mesh_drawFaces': False,
                'gl_mesh_edgeColor': (0.9, 0.9, 0.9, 1),
                'gl_mesh_glOptions': 'opaque',
                'gl_mesh_smooth': False,
                'gl_mesh_edgeWidth': 5},
            '_convex_hull': {
                '_src_mesh': 'Skull acoustic window',
                'ignore_plane_slicing': True,
                '_mask_preview_gl_options': {
                    'gl_mesh_shader': None,
                    'gl_mesh_drawEdges': True,
                    'gl_mesh_drawFaces': False,
                    'gl_mesh_edgeColor': (.5, 0, 0, 1),
                    'gl_mesh_glOptions': 'opaque',
                    'gl_mesh_smooth': False,
                    'gl_mesh_edgeWidth': 5,
                },
            }
        },
    }

    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        super().__init__(armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs)

        # Reset aramatures configuration dicts with default ones
        # self.armature_config_csts = self._DEFAULT_PARAMS['armature_config_csts']
        # self.uneval_armature_config_dict = self._DEFAULT_PARAMS['uneval_armature_config_dict']

        self._hull_mesh_handler = TrimeshHandler(parent_viewer)
        self._hull_mesh = None

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = super().custom_armature_param_widgets(armature_params_rowcount, armature_params_colcount)

        # Compute convex hull operation button
        compute_convex_hull_btn = pyqtw.QPushButton('Compute convex hull')
        compute_convex_hull_btn.clicked.connect(self.compute_convex_hull)

        custom_widgets.append(
            (compute_convex_hull_btn, armature_params_rowcount, 0, 1, armature_params_colcount)
        )
        return custom_widgets

    def compute_convex_hull(self):
        """ Implementaion of https://trimesh.org/trimesh.base.html#trimesh.base.Trimesh.convex_hull """
        
        convex_hull_src_mesh_name = self.armature_config_dict['_convex_hull']['_src_mesh']

        scr_mesh = None
        if convex_hull_src_mesh_name == '_stl_mesh':
            self.mesh_handler.stl_item_mesh_processed = None # Reset previous trimesh operations
            scr_mesh = self.mesh_handler.stl_item_mesh
        elif convex_hull_src_mesh_name in self.stereotax_frame_instance._armatures_objects:
            arma_obj = self.stereotax_frame_instance._armatures_objects[convex_hull_src_mesh_name]
            if '_stl_mesh' in arma_obj.armature_config_dict:
                scr_mesh = copy.deepcopy(arma_obj.mesh_handler.stl_item_mesh)
            else:
                raise ValueError(f'Convex Hull: Unsupported mesh from armature -> {convex_hull_src_mesh_name}')
        else:
            raise ValueError(f'Convex Hull: Unsupported mesh -> {convex_hull_src_mesh_name}')

        if scr_mesh is not None:
            convex_hull_mesh = scr_mesh.convex_hull
        else:
            raise ValueError(f'Convex Hull: Unsupported mesh -> {convex_hull_src_mesh_name}')
        
        # Add mesh to viewer

        if self.mesh_handler.stl_item_name is None: # If mesh_handler did not exist
            # Assign available mesh_handler name
            mesh_item_index = 0
            mesh_item_name_formater = lambda ii: f'convex_hull_result_mesh_{ii}'
            mesh_handler_child_attributes = [child_att for child_att in self.parent_viewer.cache.get_attr_unique_childs('mesh_handler') if 'convex_hull_result_mesh' in child_att]
            while mesh_item_name_formater(mesh_item_index) in mesh_handler_child_attributes:
                mesh_item_index += 1
            self.mesh_handler.stl_item_name = mesh_item_name_formater(mesh_item_index)

            # Set StlHandler gl parameters
            armature_dict_stl_params = self.uneval_armature_config_dict['_stl_mesh']
            for stl_param_key in self.mesh_handler._DEFAULT_PARAMS.keys():
                if stl_param_key in armature_dict_stl_params:
                    self.mesh_handler.set_stl_user_param(stl_param_key, armature_dict_stl_params[stl_param_key])

            self.mesh_handler.stl_item_mesh_processed = convex_hull_mesh
            self.mesh_handler.add_rendered_object()

        else:
            self.mesh_handler.stl_item_mesh_processed = convex_hull_mesh
            self.mesh_handler.update_rendered_object()
