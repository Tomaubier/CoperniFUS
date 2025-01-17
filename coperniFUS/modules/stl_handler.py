from coperniFUS import *
from coperniFUS.modules.interfaces.trimesh_interfaces import StlHandler


class StlHandlerGUI(StlHandler): # TODO Subclass Module

    _DEFAULT_PARAMS = {
        'file_path': 'None',
        'ignore_anatomical_landmarks_calibration': True,
        'ignore_plane_slicing': False,
        'stl_item_transforms_str' : 'S1 Rx0deg Tz0um',
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

    # --- Required module attributes ---

    def init_dock(self):
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('STL Handler', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Import button
        self.select_stl_file_btn = pyqtw.QPushButton('Select STL file')
        self.select_stl_file_btn.clicked.connect(self._import_stl)
        self.dock_layout.addWidget(self.select_stl_file_btn, 0, 0, 1, 1) # Y, X, w, h

        # Transform matrix str editor
        self.stl_item_transform_editor = pyqtw.QLineEdit(str(self.get_stl_user_param('stl_item_transforms_str')))
        self.stl_item_transform_editor.editingFinished.connect(functools.partial(self.parse_editor, self.stl_item_transform_editor, 'stl_item_transforms_str', '', 'str'))
        self.stl_item_transform_editor.editingFinished.connect(self.reset_stl_item_tmat)
        self.stl_item_transform_editor.setEnabled(False)
        self.dock_layout.addWidget(self.stl_item_transform_editor, 1, 0, 1, 1) # Y, X, w, h
        self.stl_item_transform_editor.setToolTip('STL mesh transformations<br> - S0.5: Apply a 0.5 scaling factor (Use Sx to scale along x)<br> - Ty1mm: 1mm translation along y<br> - Rz90deg: Rotate by 90 degrees around z axis')

    def add_rendered_object(self,):
        if self.stl_item_name is None:
            self.stl_item_name = self.parent_viewer.cache.get_attr(['mesh_handler', 'last_used_stl_item_name'])
        super().add_rendered_object()
        if isinstance(self.stl_glitem, pg.opengl.items.GLMeshItem.GLMeshItem) or (isinstance(self.stl_glitem, list) and len(self.stl_glitem) > 0):
            self._update_item_transform_editor()
            self.stl_item_transform_editor.setEnabled(True)

            # Setup dock button for image deletion
            self.select_stl_file_btn.setText('Remove STL')
            self.select_stl_file_btn.clicked.disconnect()
            self.select_stl_file_btn.clicked.connect(self.delete_rendered_object)

    def delete_rendered_object(self):
        if self.stl_glitem is not None:
            self.parent_viewer.cache.set_attr(['mesh_handler', 'last_used_stl_item_name'], None)
        super().delete_rendered_object()
        self.select_stl_file_btn.setText('Select STL file')
        self.select_stl_file_btn.clicked.disconnect()
        self.select_stl_file_btn.clicked.connect(self._import_stl)

        self.stl_item_transform_editor.setText(str(self._DEFAULT_PARAMS['stl_item_transforms_str']))
        self.stl_item_transform_editor.setEnabled(False)

    # --- Module specific attributes ---

    def parse_editor(self, src_editor, param_name, unit='', param_type='float'): # TODO move to Module
        if param_type == 'int':
            edited_value = int(src_editor.text())
        elif param_type == 'float':
            edited_text = src_editor.text().replace(' ', '') # remove spaces
            edited_text_nounit = edited_text[:-len(unit)]
            edited_value = si_parse(edited_text_nounit.replace('u', 'µ'))
        else: # raw str
            edited_value = src_editor.text()
        self.set_stl_user_param(param_name, edited_value)
        self.parent_viewer.update_rendered_view()

    @property
    def stl_item_tmat(self):
        if self._stl_item_tmat is None:
            # Compute transform matrix from transforms str
            transforms_matrices = af_tr_from_str.transform_matrices_from_str(
                self.get_stl_user_param('stl_item_transforms_str')
            )
            self._stl_item_tmat = af_tr.scale_mat(1)
            for tr_mat in transforms_matrices:
                self._stl_item_tmat = self._stl_item_tmat @ tr_mat

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

    def reset_stl_item_tmat(self):
        self.stl_item_tmat = None

    def _update_item_transform_editor(self):
        self.stl_item_transform_editor.setText(str(self.get_stl_user_param('stl_item_transforms_str')))

    def _import_stl(self):
        import_path = pyqtw.QFileDialog.getOpenFileName(parent=self.parent_viewer, caption=self.parent_viewer.tr("Select an STL"), filter=self.parent_viewer.tr('STL file (*.stl)'))

        if import_path[0] == '':
            self.parent_viewer.statusBar().showMessage('Invalid STL file path', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)
        else:
            self.raw_stl_item_mesh = None # Reset before reload
            self.stl_item_name = pathlib.Path(import_path[0]).stem
            self.set_stl_user_param('file_path', import_path[0])
            if self.raw_stl_item_mesh is None: # If import has failed
                self.parent_viewer.statusBar().showMessage('STL file import fail', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)
                self.set_stl_user_param('file_path') # Reset to default
                self.stl_item_name = None
            else: # On success -> save for future use
                self.add_rendered_object()
                self.parent_viewer.cache.set_attr(
                    ['mesh_handler', 'last_used_stl_item_name'],
                    self.stl_item_name)