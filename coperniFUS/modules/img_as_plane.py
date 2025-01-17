from coperniFUS import *
from coperniFUS.modules.module_base import Module


class RefImageAsPlane(Module):

    _DEFAULT_PARAMS = {
        'file_path': 'None',
        'ignore_anatomical_landmarks_calibration': False,
        'plane': 'X',
        'alpha': .6,
        'px_size': 1e-5, # [m]
        'origin_px_xloc': 0, # [px]
        'origin_px_yloc': 0, # [px]
    }

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, 'ref_image_as_plane_params', **kwargs)

        self.ref_image_glitem = None
        self._ref_image_tmat = None
        self.ref_image_name = None
        self.ref_image = None
    
    # --- Atlas specific cache wrapper ---
    
    def get_user_param(self, param_name, default_value=None):
        if self.ref_image_name is not None:
            param_value = super().get_user_param(
                param_name,
                additional_identifiers=[self.ref_image_name],
                default_value=default_value)
        else:
            param_value = self._DEFAULT_PARAMS[param_name]
        return param_value

    def set_user_param(self, param_name, param_value):
        if self.ref_image_name is not None:
            super().set_user_param(
                param_name,
                additional_identifiers=[self.ref_image_name],
                param_value=param_value)

    # --- Required module attributes ---

    def init_dock(self):
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Reference Image As Plane', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Import button
        self.select_ref_img_btn = pyqtw.QPushButton('Select Image')
        self.select_ref_img_btn.clicked.connect(self._import_image)
        self.dock_layout.addWidget(self.select_ref_img_btn, 0, 0, 1, 3) # Y, X, w, h

        # Pixel size setter
        unit = 'm'
        self.px_size_editor = pyqtw.QLineEdit(si_format(
            self.get_user_param('px_size'), format_str='{value} {prefix}' + unit))
        self.px_size_editor.editingFinished.connect(functools.partial(self._parse_editor, self.px_size_editor, 'px_size', unit))
        self.dock_layout.addWidget(self.px_size_editor, 1, 0, 1, 1) # Y, X, w, h
        self.px_size_editor.setToolTip('Size of image pixels in meters')

        # Origin setter
        unit = 'px'
        self.origin_px_xloc_editor = pyqtw.QLineEdit(si_format(
            self.get_user_param('origin_px_xloc'), format_str='{value} {prefix}' + unit))
        self.origin_px_xloc_editor.editingFinished.connect(
            functools.partial(self._parse_editor, self.origin_px_xloc_editor, 'origin_px_xloc', unit))
        self.dock_layout.addWidget(self.origin_px_xloc_editor, 1, 1, 1, 1) # Y, X, w, h
        self.origin_px_xloc_editor.setToolTip('Origin X coordinate in pixels')
        
        self.origin_px_yloc_editor = pyqtw.QLineEdit(si_format(
            self.get_user_param('origin_px_yloc'), format_str='{value} {prefix}' + unit))
        self.origin_px_yloc_editor.editingFinished.connect(
            functools.partial(self._parse_editor, self.origin_px_yloc_editor, 'origin_px_yloc', unit))
        self.dock_layout.addWidget(self.origin_px_yloc_editor, 1, 2, 1, 1) # Y, X, w, h
        self.origin_px_xloc_editor.setToolTip('Origin Y coordinate in pixels')

        # Select plane button
        self.ref_img_plane_selector_btns = {
            'X': pyqtw.QPushButton('X'),
            'Y': pyqtw.QPushButton('Y'),
            'Z': pyqtw.QPushButton('Z'),
        }
        for ii, (normal_axis, btn) in enumerate(self.ref_img_plane_selector_btns.items()):
            btn.clicked.connect(functools.partial(self._set_img_plane, normal_axis))
            self.dock_layout.addWidget(btn, 2, ii, 1, 1) # Y, X, w, h
            btn.setToolTip(f'Plane normal axis')

        self._enable_disable_editors(False)

    def delete_rendered_object(self):
        if self.ref_image_glitem is not None:
            self.parent_viewer.gl_view.removeItem(self.ref_image_glitem)
            self.parent_viewer.cache.set_attr(['ref_image_as_plane_params', 'last_used_img_name'], None)
        self.select_ref_img_btn.setText('Select Image')
        self.select_ref_img_btn.clicked.disconnect()
        self.select_ref_img_btn.clicked.connect(self._import_image)

    def add_rendered_object(self):
        try: # Load previous ref image if valid path
            self.ref_image_name = self.parent_viewer.cache.get_attr(
                ['ref_image_as_plane_params', 'last_used_img_name'])
            if self.ref_image_name is not None:
                last_used_ref_img_path = self.get_user_param('file_path')
                self._load_img(last_used_ref_img_path)
        except:
            pass

    def update_rendered_object(self):
        if self.ref_image_glitem is not None:
            self.ref_image_glitem.resetTransform()
            self.ref_image_glitem.applyTransform(pyqtg.QMatrix4x4(self.ref_image_tmat.T.ravel()), local=False)
    
    # --- Module specific attributes ---

    def _parse_editor(self, src_editor, param_name, unit):
        edited_text = src_editor.text().replace(' ', '') # remove spaces
        edited_text_nounit = edited_text[:-len(unit)]
        edited_value = si_parse(edited_text_nounit.replace('u', 'µ'))
        self.set_user_param(param_name, edited_value)
        self.update_img_transform()

    def _update_editors(self):
        self.px_size_editor.setText(si_format(
            self.get_user_param('px_size'), format_str='{value} {prefix}' + 'm'))
        self.origin_px_xloc_editor.setText(si_format(
            self.get_user_param('origin_px_xloc'), format_str='{value} {prefix}' + 'px'))
        self.origin_px_yloc_editor.setText(si_format(
            self.get_user_param('origin_px_yloc'), format_str='{value} {prefix}' + 'px'))
        
        # Plane buttons
        normal_axis = self.get_user_param('plane')
        if '-' in normal_axis:
            self._update_plane_button_ui(normal_axis.replace('-', ''), reverse=True)
        else:
            self._update_plane_button_ui(normal_axis)
    
    def _enable_disable_editors(self, enable=True):
        for ii, (normal_axis, btn) in enumerate(self.ref_img_plane_selector_btns.items()):
            btn.setEnabled(enable)
        self.px_size_editor.setEnabled(enable)
        self.origin_px_xloc_editor.setEnabled(enable)
        self.origin_px_yloc_editor.setEnabled(enable)

    def _import_image(self):
        import_path = pyqtw.QFileDialog.getOpenFileName(parent=self.parent_viewer, caption=self.parent_viewer.tr("Select an image"), filter=self.parent_viewer.tr('Image (*.png)'))

        if import_path[0] == '':
            self.parent_viewer.statusBar().showMessage('Invalid file path', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)
        else:
            if self._load_img(import_path[0]):
                self.ref_image_name = pathlib.Path(import_path[0]).stem
                self.parent_viewer.cache.set_attr(
                    ['ref_image_as_plane_params', 'last_used_img_name'],
                    self.ref_image_name
                )
                self.set_user_param('file_path', import_path[0])
            
    def _load_img(self, img_path):
        success = False
        if pathlib.Path(img_path).exists():
            self.ref_image = Image.open(img_path)

            self.select_ref_img_btn.setText('Remove Image')
            self.select_ref_img_btn.clicked.disconnect()
            self.select_ref_img_btn.clicked.connect(self.delete_rendered_object)
            self._show_image()
            success = True
        else:
            self.parent_viewer.statusBar().showMessage('Ref img file not found', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)
        return success

    def _show_image(self):
        ref_image_asarray = np.array(self.ref_image)
        if ref_image_asarray.shape[2] == 3: # Turn RGB array to RGBA
            ref_image_asarray_rgba = np.ones((*ref_image_asarray.shape[:2], 4))
            ref_image_asarray_rgba[:, :, :3] = ref_image_asarray
            ref_image_asarray = ref_image_asarray_rgba
            del ref_image_asarray_rgba
        elif ref_image_asarray.shape[2] != 4:
            raise ValueError('Unsupported png channels numbers')
            
        alpha = self.get_user_param('alpha')
        ref_image_asarray[:, :, 3] = int(alpha * 255) # Transparent img

        self.ref_image_glitem = gl.GLImageItem(ref_image_asarray)
        self.parent_viewer.gl_view.addItem(self.ref_image_glitem, name=f'Ref. image {self.ref_image_name}')
        self.ref_image_glitem.setDepthValue(-1) # GL images -> render tree background
        self._enable_disable_editors(True)
        self.update_img_transform()
        self._update_editors()

    @property
    def ref_image_tmat(self):
        if self._ref_image_tmat is None:
            px_size = self.get_user_param('px_size')
            self._ref_image_tmat = af_tr.scale_mat(px_size)

            self._ref_image_tmat = self._ref_image_tmat @ af_tr.translat_mat('x', -self.get_user_param('origin_px_xloc') * px_size)
            self._ref_image_tmat = self._ref_image_tmat @ af_tr.translat_mat('y', -self.get_user_param('origin_px_yloc') * px_size)

            if self.get_user_param('plane') == 'X':
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('y', 90)
            if self.get_user_param('plane') == '-X':
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('y', 90)
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('z', 180)
            if self.get_user_param('plane') == 'Y':
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('y', 90)
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('z', 90)
            if self.get_user_param('plane') == '-Y':
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('y', 90)
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('z', 90)
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('z', 180)
            if self.get_user_param('plane') == '-Z':
                self._ref_image_tmat = self._ref_image_tmat @ af_tr.rot_mat('x', 180)
        
        # Apply anatomical landmark calibration transformation if enabled
        if not self.get_user_param('ignore_anatomical_landmarks_calibration'):
            anatomically_calibrated_img_tmat = self._ref_image_tmat @ self.parent_viewer.anat_calib.landmarks_calib_tmat
        else:
            anatomically_calibrated_img_tmat = self._ref_image_tmat

        return anatomically_calibrated_img_tmat
    
    @ref_image_tmat.setter
    def ref_image_tmat(self, value):
        self._ref_image_tmat = value

    def update_img_transform(self):
        self.ref_image_tmat = None # Reset
        self.update_rendered_object()

    def _update_plane_button_ui(self, normal_axis, reverse=False):
        self.ref_img_plane_selector_btns['X'].setDown(False)
        self.ref_img_plane_selector_btns['Y'].setDown(False)
        self.ref_img_plane_selector_btns['Z'].setDown(False)
        self.ref_img_plane_selector_btns[normal_axis].setDown(True)

        btn_text = normal_axis if not reverse else f'-{normal_axis}'
        self.ref_img_plane_selector_btns[normal_axis].setText(btn_text)

    def _set_img_plane(self, btn_normal_axis):
        # Reverse axis if button is pushed twice
        if self.get_user_param('plane') == btn_normal_axis:
            normal_axis = f'-{btn_normal_axis}'
            reverse = True
        else:
            normal_axis = btn_normal_axis
            reverse = False
        self._update_plane_button_ui(btn_normal_axis, reverse)

        self.set_user_param('plane', normal_axis)
        self.update_img_transform()
