from coperniFUS import *
from coperniFUS.modules.stereotaxic_frame import *

class Armature:

    _DEFAULT_PARAMS = {
        'visible': False,
        'tooltip_on_armature': False,
        'rgba_color': (0.6, 0.6, 0.6, 0.7),
        'glline_width': 5,
        'armature_config_csts': {
            'L1': 0.02,
            'L2': 0.04
        },
        'uneval_armature_config_dict': {
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
    }

    def __init__(self, armature_display_name, parent_viewer, stereotax_frame_instance, **kwargs) -> None:
        self.parent_viewer = parent_viewer
        self.armature_name = clean_string(armature_display_name)
        self.stereotax_frame_instance = stereotax_frame_instance
        self.armature_display_name = armature_display_name
        self.highlighted_in_render = False
        self.current_render_hash = None
        self.gl_object = None

        # # Reset aramatures configuration dicts with default ones
        # self.armature_config_csts = self._DEFAULT_PARAMS['armature_config_csts']
        # self.uneval_armature_config_dict = self._DEFAULT_PARAMS['uneval_armature_config_dict']
        self.tooltip_on_armature = False
        self.parent_transform_mat = None
        self._end_transform_mat = None
        self._armature_config_dict = None # armature_config_dict dictionary with evaluated args expressions

        self.params_editor_widget = ArmatureParamsEditorWidget(
            parent_viewer=self.parent_viewer,
            armature_object=self
        )

    # --- Armature specific cache wrapper ---

    def get_armature_user_param(self, param_name, default_value=None):
        """ Armature specific cache wrapper """
        if default_value is None and param_name in self._DEFAULT_PARAMS:
            default_value = self._DEFAULT_PARAMS[param_name]
        param_value = self.parent_viewer.cache.get_attr(
            ['armature', self.armature_name, param_name],
            default_value = default_value
        )
        return param_value

    def set_armature_user_param(self, param_name, param_value):
        """ Armature specific cache wrapper """
        self.parent_viewer.cache.set_attr(
            ['armature', self.armature_name, param_name],
            param_value
        )

    # --- Required armature attributes ---

    def add_render(self):
        armature_coords = self.compute_armature_coords()
        if self.gl_object != None or self.visible is False or len(armature_coords) < 2:
            self.delete_render()
        else:
            self.gl_object = gl.GLLinePlotItem(
                pos=armature_coords,
                width=self.glline_width,
                color=self.rgba_color,
                antialias=True,
                glOptions='translucent'
            )
            self.parent_viewer.gl_view.addItem(self.gl_object, name=f'{self.armature_display_name} armature')
            self._is_render_uptodate # Init hash

    def update_render(self, force_update=False):
        if not self._is_render_uptodate or force_update:
            armature_coords = self.compute_armature_coords()
            if self.visible is False or len(armature_coords) < 2:
                self.delete_render()
            else:
                if self.gl_object is None:
                    self.add_render()

                self.gl_object.setData(
                    pos=armature_coords,
                    color=((*self.rgba_color[:3], 1) if self.highlighted_in_render else self.rgba_color),
                    width=(self.glline_width+2 if self.highlighted_in_render else self.glline_width)
                )
        self._accept_render_update()
    
    def delete_render(self):
        if self.gl_object in self.parent_viewer.gl_view.items:
            self.parent_viewer.gl_view.removeItem(self.gl_object)
            self.gl_object = None

    # --- Optionnal armature methods ---

    def custom_armature_param_widgets(self, armature_params_rowcount, armature_params_colcount):
        custom_widgets = []
        return custom_widgets
    
    # --- Common methods ---

    @property
    def end_transform_mat(self):
        """ returns the transform matrix of the last joint in the armature """
        self.compute_armature_coords()
        self._end_transform_mat = list(self.armature_transf_mat.values())[-1]['transf_mat']
        if self._end_transform_mat is None:
            self._end_transform_mat = np.eye(4)
        return self._end_transform_mat

    @property
    def armature_tooltip_tmat(self):
        return self.end_transform_mat
    
    @property
    def _editable_params_values(self):
        _editable_params_values = {}

        editable_nested_keys = recursive_key_finder(self.armature_config_dict, target_key='_is_editable') # Editable params retrieval
        editable_nested_keys = [nkey[0] for nkey in editable_nested_keys if nkey[1] is True] # Discard params where _is_editable is set to False

        for nested_keys in editable_nested_keys:
            param_flat_dict = self.armature_config_dict
            for nested_key in nested_keys:
                param_flat_dict = param_flat_dict[nested_key]
                if 'args' in param_flat_dict:
                    _editable_params_values[nested_key] = param_flat_dict['args'][1]

        return _editable_params_values

    @property
    def _params_hash(self):
        phash = object_list_hash([ # attributes tracked change
            self.visible,
            self.armature_config_csts,
            self.armature_config_dict,
            self.parent_transform_mat,
            self.highlighted_in_render,
            self.parent_viewer.slicing_plane_normal_vect,
            self.parent_viewer.anat_calib.landmarks_calib_tmat
        ])
        return phash
    
    def _accept_render_update(self):
        # Call once the render has been updated
        self.current_render_hash = self._params_hash

    @property
    def _is_render_uptodate(self):
        _is_render_uptodate = False
        if self.current_render_hash == self._params_hash:
            _is_render_uptodate = True
        return _is_render_uptodate

    @property
    def visible(self):
        return self.get_armature_user_param('visible')

    @visible.setter
    def visible(self, value):
        self.set_armature_user_param('visible', value)

    @property
    def rgba_color(self):
        return self.get_armature_user_param('rgba_color')
    
    @property
    def glline_width(self):
        return self.get_armature_user_param('glline_width')

    @property
    def armature_config_csts(self):
        return self.get_armature_user_param('armature_config_csts')

    @armature_config_csts.setter
    def armature_config_csts(self, value):
        self.set_armature_user_param('armature_config_csts', value)

    @property
    def uneval_armature_config_dict(self):
        return self.get_armature_user_param('uneval_armature_config_dict')

    @uneval_armature_config_dict.setter
    def uneval_armature_config_dict(self, value):
        self.set_armature_user_param('uneval_armature_config_dict', value)

    def get_joints(self, armature_config_dict=None):
        if armature_config_dict is None:
            armature_config_dict = self.armature_config_dict
        if '_armature_joints' in armature_config_dict:
            armature_joint_names = [joint_name for joint_name in armature_config_dict['_armature_joints'].keys()]
        else:
            armature_joint_names = []
        return armature_joint_names

    def get_joint_transforms(self, joint_id, armature_config_dict=None):
        if armature_config_dict is None:
            armature_config_dict = self.armature_config_dict
        if '_armature_joints' in armature_config_dict:
            armature_joint_transforms = {kk: vv['args'] for (kk, vv) in armature_config_dict['_armature_joints'][joint_id].items()}
        else:
            armature_joint_transforms = {}
        return armature_joint_transforms
    
    def evaluate_armature_config_dict(self, uneval_armature_config_dict, armature_constants_dict, raise_errors=False): #LADEDAN
        evaluated_armature_config_dict = copy.deepcopy(uneval_armature_config_dict) # Deep copy for "inplace" str args evaluation
        args_nested_keys = recursive_key_finder(uneval_armature_config_dict, target_key='args') # Grab all 'args' keys from armature_config_dict

        for nested_keys, _ in args_nested_keys:
            param_flat_dict = evaluated_armature_config_dict
            for nested_key in nested_keys:
                param_flat_dict = param_flat_dict[nested_key]

            args = param_flat_dict['args']
            if isinstance(args, list) and len(args) >= 2: # if args contains 2 elements
                    
                if isinstance(args[1], str): # and is a str -> evaluate str
                    try:
                        evaluated_arg = eval(args[1], {'csts': armature_constants_dict, 'np': np})
                        args[1] = evaluated_arg
                    except Exception as e:
                        err_msg = f'Error in args expression in {self.armature_display_name} {"/".join(nested_keys)} -> {args}\n{type(e).__name__}: {str(e)}'
                        if raise_errors:
                            raise ValueError(err_msg)
                        else:
                            print(err_msg)

                else:
                    # Test validity of arg values (int or float are expected appart from string args for evaluation)
                    if not (isinstance(args[1], int) or isinstance(args[1], float)):
                        err_msg = f'Unsupported args expression in {self.armature_display_name} {"/".join(nested_keys)} -> {args}'
                        if raise_errors:
                            raise ValueError(err_msg)
                        else:
                            print(err_msg)
        return evaluated_armature_config_dict

    def _update_armature_dict_value(self, nested_keys, value):

        # --- uneval dict update ---
        uneval_armature_config_dict_copy = copy.deepcopy(self.uneval_armature_config_dict)
        # Recurse through the dict copy based on nested_keys
        param_flat_dict = uneval_armature_config_dict_copy
        for nested_key in nested_keys:
            param_flat_dict = param_flat_dict[nested_key]
        # Apply the value
        param_flat_dict['args'][1] = value
        # Update the actual dict
        self.uneval_armature_config_dict = uneval_armature_config_dict_copy

        # --- evaluated dict update ---
        armature_config_dict_copy = copy.deepcopy(self.armature_config_dict)
        # Recurse through the dict copy based on nested_keys
        param_flat_dict = armature_config_dict_copy
        for nested_key in nested_keys:
            param_flat_dict = param_flat_dict[nested_key]
        # Apply the value
        param_flat_dict['args'][1] = value
        # Update the actual dict
        self.armature_config_dict = armature_config_dict_copy
    
    @property
    def armature_config_dict(self): #LADEDAN
        if self._armature_config_dict is None:
            self._armature_config_dict = self.evaluate_armature_config_dict(self.uneval_armature_config_dict, self.armature_config_csts)
        return self._armature_config_dict

    @armature_config_dict.setter
    def armature_config_dict(self, value):
        self._armature_config_dict = value

    def compute_armature_coords(self):
        if self.parent_transform_mat is None:
            origin_transform_mat = np.eye(4) # (0, 0, 0) -> default if no parent armature
        else:
            origin_transform_mat = self.parent_transform_mat

        self.armature_transf_mat = {
            'Origin': {
                'transf_mat': origin_transform_mat,
                'link_end_loc': origin_transform_mat[3],
            }
        }

        parent_transf = origin_transform_mat
        for joint_id in self.get_joints():
            joint_transfmat = np.eye(4)
            for transform_id in self.get_joint_transforms(joint_id):
                transform_args = self.armature_config_dict['_armature_joints'][joint_id][transform_id]['args']
                if transform_id.startswith('translation'):
                    joint_transfmat = joint_transfmat @ af_tr.translat_mat(*transform_args)
                elif transform_id.startswith('rotation'):
                    joint_transfmat = joint_transfmat @ af_tr.rot_mat(*transform_args)

            compound_transf = joint_transfmat @ parent_transf
            self.armature_transf_mat[joint_id] = {
                'transf_mat': compound_transf,
                'link_end_loc': compound_transf[3],
            }
            parent_transf = compound_transf

            # DEGUG MODE
            # self.parent_viewer.add_debug_trihedra(self.armature_transf_mat[joint_id]['transf_mat'])

        frame_joints = np.array([transforms['link_end_loc'][:3] for _, transforms in self.armature_transf_mat.items()])

        return frame_joints