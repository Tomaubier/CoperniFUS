from coperniFUS import *


class TrimeshHandler:

    _DEFAULT_PARAMS = {
        'ignore_anatomical_landmarks_calibration': True,
        'ignore_plane_slicing': False,
        'gl_mesh_shader': 'viewNormalColor',
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_edgeColor': (.9, .9, .9, 1),
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5,
    }

    def __init__(self, parent_viewer, **kwargs) -> None:
        self.parent_viewer = parent_viewer
        self.stl_item_name = None
        self._stl_item_tmat = None
        self._raw_stl_item_mesh = None
        self._stl_item_mesh_processed = None
        self._sliced_stl_item_mesh = None
        self._stl_item_mesh = None
        self.stl_glitem = None

    # Img specific cache wrapper
    def get_stl_user_param(self, param_name, default_value=None):
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

    # Img specific cache wrapper
    def set_stl_user_param(self, param_name, param_value):
        if self.stl_item_name is not None:
            self.parent_viewer.cache.set_attr(
                ['mesh_handler', self.stl_item_name, param_name],
                param_value
            )

    @property
    def stl_item_tmat(self):
        if self._stl_item_tmat is None:
            self._stl_item_tmat = np.eye(4) # No transform as default
        
        # Apply anatomical landmark calibration transformation if enabled
        if not self.get_stl_user_param('ignore_anatomical_landmarks_calibration'):
            anatomically_calibrated_stl_item_tmat = self._stl_item_tmat @ self.parent_viewer.anat_calib.landmarks_calib_tmat
        else:
            anatomically_calibrated_stl_item_tmat = self._stl_item_tmat

        return anatomically_calibrated_stl_item_tmat
    
    @stl_item_tmat.setter
    def stl_item_tmat(self, value):
        self._stl_item_tmat = value
        self.stl_item_mesh = None # Reset processed stl mesh to apply transform
    
    @property
    def stl_item_mesh_processed(self):
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
    def raw_stl_item_mesh(self):
        if self._raw_stl_item_mesh is None:
            self.stl_item_mesh = None # Reset inheriting processed mesh
        return self._raw_stl_item_mesh

    @raw_stl_item_mesh.setter
    def raw_stl_item_mesh(self, value):
        self._raw_stl_item_mesh = value

    @property
    def stl_item_mesh(self):
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

    def delete_rendered_object(self):
        if self.stl_glitem is not None:
            if isinstance(self.stl_glitem, trimesh.Trimesh):
                self.parent_viewer.gl_view.removeItem(self.stl_glitem)
            elif isinstance(self.stl_glitem, list):
                for mm in self.stl_glitem:
                    self.parent_viewer.gl_view.removeItem(mm)
            self.raw_stl_item_mesh = None
            self.stl_item_mesh = None
            self.stl_glitem = None

    def add_rendered_object(self):

        def add_mesh_render(mesh):
            stl_item_gl_mesh_data = gl.MeshData(vertexes=mesh.vertices, faces=mesh.faces)
            self.stl_glitem.append(
                gl.GLMeshItem(
                    meshdata=stl_item_gl_mesh_data,
                    shader=self.get_stl_user_param('gl_mesh_shader'), # TODO get_stl_user_param -> redondant -> transfer to stl dock
                    smooth=self.get_stl_user_param('gl_mesh_smooth'),
                    drawFaces=self.get_stl_user_param('gl_mesh_drawFaces'),
                    drawEdges=self.get_stl_user_param('gl_mesh_drawEdges'),
                    edgeColor=self.get_stl_user_param('gl_mesh_edgeColor'),
                    edgeWidth=self.get_stl_user_param('gl_mesh_edgeWidth'),
                    glOptions=self.get_stl_user_param('gl_mesh_glOptions'),
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

        ignore_plane_slicing = self.get_stl_user_param('ignore_plane_slicing')
        if not self.parent_viewer.postpone_slicing_plane_computation or ignore_plane_slicing:
            if self.stl_glitem is None:
                self.add_rendered_object()
            else:
                if isinstance(self.stl_item_mesh, trimesh.Trimesh):
                    update_rendered_mesh(self.stl_item_mesh)
                elif isinstance(self.stl_item_mesh, list):
                    for ii, mm in enumerate(self.stl_item_mesh):
                        update_rendered_mesh(mm, sub_mesh_index=ii)
            # Ignore if None


class StlHandler(TrimeshHandler):

    _DEFAULT_PARAMS = {
        'file_path': 'None',
        'ignore_anatomical_landmarks_calibration': True,
        'ignore_plane_slicing': False,
        'gl_mesh_shader': 'viewNormalColor',
        'gl_mesh_drawEdges': False,
        'gl_mesh_drawFaces': True,
        'gl_mesh_edgeColor': (.9, .9, .9, 1),
        'gl_mesh_glOptions': 'opaque',
        'gl_mesh_smooth': False,
        'gl_mesh_edgeWidth': 5,
    }

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, **kwargs)

    @property
    def raw_stl_item_mesh(self): # Override mesh import for stl
        if self._raw_stl_item_mesh is None:
            self.stl_item_mesh = None # Reset inheriting processed mesh
            stl_file_path = self.get_stl_user_param('file_path')
            if pathlib.Path(stl_file_path).exists():
                self._raw_stl_item_mesh = trimesh.load(stl_file_path)
        return self._raw_stl_item_mesh
    
    @raw_stl_item_mesh.setter
    def raw_stl_item_mesh(self, value):
        # self.stl_item_mesh = None # Reset inheriting processed mesh
        self._raw_stl_item_mesh = value
