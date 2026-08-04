from coperniFUS import *


class TrimeshHandler:

    _DEFAULT_PARAMS = {
        'ignore_anatomical_landmarks_calibration': True,
        'ignore_plane_slicing': False,
        'gl_mesh_shader': 'viewNormalColor',
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_color': [.5, .5, .5, 1.],
        'gl_mesh_edgeColor': [.5, .5, .5, .7],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5,
    }
    """ Default configuration parameters used when a parameter value is not yet cached """

    def __init__(self, parent_viewer, **kwargs) -> None:
        self.parent_viewer = parent_viewer
        self.stl_item_name = None
        self._stl_item_tmat = None
        self._raw_stl_item_mesh = None
        self._stl_item_mesh_processed = None
        self._sliced_stl_item_mesh = None
        self._stl_item_mesh = None
        self.stl_glitem = None

    # --- Public attributes ---

    @property
    def stl_item_mesh_processed(self):
        """ Mesh object with affine transformation and boolean operations (if applicable) applied """
        if self._stl_item_mesh_processed is None:
            return None
        if np.all(self._stl_item_mesh_processed[0] == self.stl_item_tmat):
            return self._stl_item_mesh_processed[1] # Return mesh (or list of meshes) only
        else: # Reset if the boolean transform is no longer up to date
            self._stl_item_mesh_processed = None
            return None
    
    @stl_item_mesh_processed.setter
    def stl_item_mesh_processed(self, mesh):
        # Store mesh + current transform matrix (track tf change)
        self._stl_item_mesh_processed = (self.stl_item_tmat, mesh)

    @property
    def stl_item_mesh(self):
        """ Mesh object with affine transformation applied """
        def apply_tr(raw_mesh):
            mesh = copy.deepcopy(raw_mesh)
            mesh.apply_transform(self.stl_item_tmat.T)
            return mesh

        if self.stl_item_mesh_processed is not None:
            return self.stl_item_mesh_processed
        if self._stl_item_mesh is None:
            if isinstance(self.raw_stl_item_mesh, trimesh.Trimesh):
                self._stl_item_mesh = apply_tr(self.raw_stl_item_mesh)
            elif isinstance(self.raw_stl_item_mesh, list):
                self._stl_item_mesh = [apply_tr(mm) for mm in self.raw_stl_item_mesh]
        # Ignore if None
        return self._stl_item_mesh

    @stl_item_mesh.setter
    def stl_item_mesh(self, value):
        self._stl_item_mesh = value

    @property
    def raw_stl_item_mesh(self):
        """ Raw mesh object without any affine transformations or processing applied """
        if self._raw_stl_item_mesh is None:
            self.stl_item_mesh = None # Reset inheriting processed mesh
        return self._raw_stl_item_mesh

    @raw_stl_item_mesh.setter
    def raw_stl_item_mesh(self, value):
        self._raw_stl_item_mesh = value

    @property
    def stl_item_tmat(self):
        """ Holds the affine transformation matrix for the trimesh object """
        if self._stl_item_tmat is None:
            self._stl_item_tmat = np.eye(4) # No transform as default
        
        # Apply anatomical landmark calibration transformation if enabled
        if not self.get_user_param('ignore_anatomical_landmarks_calibration'):
            anatomically_calibrated_stl_item_tmat = self._stl_item_tmat @ self.parent_viewer.anat_calib.landmarks_calib_tmat
        else:
            anatomically_calibrated_stl_item_tmat = self._stl_item_tmat

        return anatomically_calibrated_stl_item_tmat
    
    @stl_item_tmat.setter
    def stl_item_tmat(self, value):
        if value is not None:
            if value.shape != (4, 4):
                raise ValueError('Transformation matrix should be of shape (4, 4)')
        self._stl_item_tmat = value
        self.stl_item_mesh = None # Reset processed stl mesh to apply transform
    
    # --- Required attributes for rendering ---

    def add_rendered_object(self):
        """ Called when populating the viewer with the module rendered objects """

        def handle_unavailable_shade_names(shader_name):
            if shader_name is not None and shader_name not in AVAILABLE_SHADER_NAMES:
                warnings.warn(f'{shader_name} does not exist. Please use one of these:\n\t{"\n\t".join(AVAILABLE_SHADER_NAMES)}.')
                shader_name = 'shaded'
            return shader_name

        def add_mesh_render(mesh):
            stl_item_gl_mesh_data = gl.MeshData(vertexes=mesh.vertices, faces=mesh.faces)

            self.stl_glitem.append(
                gl.GLMeshItem(
                    meshdata=stl_item_gl_mesh_data,
                    shader=handle_unavailable_shade_names(self.get_user_param('gl_mesh_shader')), # TODO get_user_param -> redondant -> transfer to stl dock
                    smooth=self.get_user_param('gl_mesh_smooth'),
                    color=self.get_user_param('gl_mesh_color'),
                    drawFaces=self.get_user_param('gl_mesh_drawFaces'),
                    drawEdges=self.get_user_param('gl_mesh_drawEdges'),
                    edgeColor=self.get_user_param('gl_mesh_edgeColor'),
                    edgeWidth=self.get_user_param('gl_mesh_edgeWidth'),
                    glOptions=self.get_user_param('gl_mesh_glOptions'),
            ))
            bool_mesh_index_str = f' {mesh.bool_mesh_index}' if hasattr(mesh, 'bool_mesh_index') else ''
            self.parent_viewer.gl_view.addItem(self.stl_glitem[-1], name=f'{self.stl_item_name}{bool_mesh_index_str} STL mesh')
            self.stl_glitem[-1].setDepthValue(-1)

        self.stl_glitem = []
        if isinstance(self.stl_item_mesh, trimesh.Trimesh):
            add_mesh_render(self.stl_item_mesh)
        elif isinstance(self.stl_item_mesh, list):
            for mm in self.stl_item_mesh:
                add_mesh_render(mm)
        # Ignore if None

    def update_rendered_object(self):
        """ Called on render view updates """
        def update_rendered_mesh(mesh, sub_mesh_index=0):
            if self.parent_viewer.slicing_plane_normal_vect is None or ignore_plane_slicing:
                stl_item_gl_mesh_data = gl.MeshData(vertexes=mesh.vertices, faces=mesh.faces)
            else:
                self._sliced_stl_item_mesh = mesh.slice_plane(
                    plane_origin=self.parent_viewer.slicing_plane_normal_vect[0],
                    plane_normal=self.parent_viewer.slicing_plane_normal_vect[1],
                    cap=True)
                stl_item_gl_mesh_data = gl.MeshData(vertexes=self._sliced_stl_item_mesh.vertices, faces=self._sliced_stl_item_mesh.faces)

            if sub_mesh_index < len(self.stl_glitem):
                self.stl_glitem[sub_mesh_index].setMeshData(meshdata=stl_item_gl_mesh_data)

        ignore_plane_slicing = self.get_user_param('ignore_plane_slicing')
        if not self.parent_viewer._postpone_slicing_plane_computation or ignore_plane_slicing:
            if self.stl_glitem is None:
                self.add_rendered_object()
            else:
                if isinstance(self.stl_item_mesh, trimesh.Trimesh):
                    update_rendered_mesh(self.stl_item_mesh)
                elif isinstance(self.stl_item_mesh, list):
                    for ii, mm in enumerate(self.stl_item_mesh):
                        update_rendered_mesh(mm, sub_mesh_index=ii)
            # Ignore if None

    def delete_rendered_object(self):
        """ Called on deletion of the module rendered objects """
        if self.stl_glitem is not None:
            if isinstance(self.stl_glitem, trimesh.Trimesh):
                self.parent_viewer.gl_view.removeItem(self.stl_glitem)
            elif isinstance(self.stl_glitem, list):
                for mm in self.stl_glitem:
                    self.parent_viewer.gl_view.removeItem(mm)
            self.raw_stl_item_mesh = None
            self.stl_item_mesh = None
            self.stl_glitem = None

    # --- cache wrapper for interface parameters ---

    def get_user_param(self, param_name, default_value=None):
        """ Get module configuration parameter stored in cache (or default values if non existant) """
        if default_value is None and param_name in self._DEFAULT_PARAMS:
            default_value = self._DEFAULT_PARAMS[param_name]
        if self.stl_item_name is not None:
            param_value = self.parent_viewer.cache.get_attr(
                ['mesh_handler', self.stl_item_name, param_name],
                default_value = default_value
            )
        else:
            param_value = default_value
        return param_value

    def set_user_param(self, param_name, param_value):
        """ Set module configuration parameter to cache """
        if self.stl_item_name is not None:
            self.parent_viewer.cache.set_attr(
                ['mesh_handler', self.stl_item_name, param_name],
                param_value
            )


class StlHandler(TrimeshHandler):

    _DEFAULT_PARAMS = {
        'file_path': 'None',
        'ignore_anatomical_landmarks_calibration': True,
        'ignore_plane_slicing': False,
        'gl_mesh_shader': 'viewNormalColor',
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_color': [.5, .5, .5, 1.],
        'gl_mesh_edgeColor': [.5, .5, .5, .7],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5,
    }
    """ Default configuration parameters used when a parameter value is not yet cached """

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, **kwargs)

    @property
    def raw_stl_item_mesh(self): # Override mesh import for stl
        """ Raw mesh object without any affine transformations or processing applied """
        if self._raw_stl_item_mesh is None:
            self.stl_item_mesh = None # Reset inheriting processed mesh
            stl_file_path = self.get_user_param('file_path')
            if stl_file_path is not None and pathlib.Path(stl_file_path).exists():
                self._raw_stl_item_mesh = trimesh.load(stl_file_path)
        return self._raw_stl_item_mesh
    
    @raw_stl_item_mesh.setter
    def raw_stl_item_mesh(self, value):
        self._raw_stl_item_mesh = value


class TrimeshScriptHandler(TrimeshHandler):

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, **kwargs)
        self._eval_scripted_mesh = None
        self._trimesh_script = None
        self._trimesh_script_constants_dict = None

    @property
    def trimesh_script(self): # Override mesh import for stl
        """ Script to be used to construct the trimesh mesh. Uppon execution, the script should define a 'mesh' object. """
        if self._trimesh_script is None:
            self._trimesh_script = """"""
        return self._trimesh_script
    
    @trimesh_script.setter
    def trimesh_script(self, value):
        if value is None or isinstance(value, str):
            self._trimesh_script = value
        else:
            raise ValueError('trimesh_script should be a string (or None).')
    
    @property
    def trimesh_script_constants_dict(self): # Override mesh import for stl
        """ Constants to be provided uppon evaluation of the trimesh_script. Constants keys in trimesh_script_constants_dict can be referenced trimesh_script """
        if self._trimesh_script_constants_dict is None:
            self._trimesh_script_constants_dict = {}
        return self._trimesh_script_constants_dict
    
    @trimesh_script_constants_dict.setter
    def trimesh_script_constants_dict(self, value):
        if value is None or isinstance(value, dict):
            self._trimesh_script_constants_dict = value
        else:
            raise ValueError('trimesh_script_constants_dict should be a dict (or None).')

    def eval_scripted_mesh(self):
        """ Trimesh mesh object constructed from trimesh_script attriute. Uppon execution, the script should define a 'mesh' object. """

        current_param_hash = ''
        if self._eval_scripted_mesh is not None and isinstance(self._eval_scripted_mesh, tuple):
            current_param_hash = self._eval_scripted_mesh[1]

        if self.trimesh_script is not None and (self._eval_scripted_mesh is None or current_param_hash != object_list_hash([self.trimesh_script, self.trimesh_script_constants_dict])):

            accessible_globals_names = [
                'trimesh', 'np',
                'dict_to_path_patched'  # Depricated in v0.1.1
            ]
            accessible_globals = {
                accessible_glob_name: globals()[accessible_glob_name]
                for accessible_glob_name in accessible_globals_names
            }
            accessible_globals = {
                **accessible_globals, **self.trimesh_script_constants_dict,
                'dict_to_path': trimesh.path.exchange.misc.dict_to_path
            }

            # run trimesh script
            self._eval_scripted_mesh = (None, '') # mesh, param_hash
            try:
                exec(self.trimesh_script, accessible_globals)
                if 'mesh' in accessible_globals:
                    scripted_mesh = accessible_globals['mesh']
                    scripted_mesh = ensure_mesh_is_a_volume_manifold(scripted_mesh) # Cleanup mesh
                    param_hash = object_list_hash([self.trimesh_script, self.trimesh_script_constants_dict])
                    self._eval_scripted_mesh =  (scripted_mesh, param_hash)
            except Exception as e:
                raise ValueError(f'{type(e).__name__} in trimesh_script evaluation: {str(e)}')

        return self._eval_scripted_mesh[0]

    @property
    def raw_stl_item_mesh(self): # Override mesh import for stl
        """ Raw mesh object without any affine transformations or processing applied """
        if self._raw_stl_item_mesh is None:
            self.stl_item_mesh = None # Reset inheriting processed mesh
            self._raw_stl_item_mesh = self.eval_scripted_mesh()
        return self._raw_stl_item_mesh
    
    @raw_stl_item_mesh.setter
    def raw_stl_item_mesh(self, value):
        self._raw_stl_item_mesh = value


class StlHandler(TrimeshHandler):

    _DEFAULT_PARAMS = {
        'file_path': 'None',
        'ignore_anatomical_landmarks_calibration': True,
        'ignore_plane_slicing': False,
        'gl_mesh_shader': 'viewNormalColor',
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_color': [.5, .5, .5, 1.],
        'gl_mesh_edgeColor': [.5, .5, .5, .7],
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5,
    }
    """ Default configuration parameters used when a parameter value is not yet cached """

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, **kwargs)

    @property
    def raw_stl_item_mesh(self): # Override mesh import for stl
        """ Raw mesh object without any affine transformations or processing applied """
        if self._raw_stl_item_mesh is None:
            self.stl_item_mesh = None # Reset inheriting processed mesh
            stl_file_path = self.get_user_param('file_path')
            if stl_file_path is not None and pathlib.Path(stl_file_path).exists():
                self._raw_stl_item_mesh = trimesh.load(stl_file_path)
        return self._raw_stl_item_mesh
    
    @raw_stl_item_mesh.setter
    def raw_stl_item_mesh(self, value):
        self._raw_stl_item_mesh = value