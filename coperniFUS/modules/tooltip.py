from coperniFUS import *
from coperniFUS.modules.module_base import Module


class Tooltip(Module):

    _DEFAULT_PARAMS = {
        'tooltip_transforms_str' : 'Rx0deg Tz0um',
        'axes_length': 1e-3
    }

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, 'tooltip', **kwargs)

        self._tooltip_tmat = None
        self.x_glaxis = None
        self.y_glaxis = None
        self.z_glaxis = None

    # --- Required module attributes ---

    def add_rendered_object(self):
        self.x_glaxis = gl.GLLinePlotItem(pos=[[0,0,0], [self.get_user_param('axes_length'),0,0]], width=6, color=self.parent_viewer.x_RED, antialias=True, glOptions='additive')
        self.y_glaxis = gl.GLLinePlotItem(pos=[[0,0,0], [0,self.get_user_param('axes_length'),0]], width=6, color=self.parent_viewer.y_GREEN, antialias=True, glOptions='additive')
        self.z_glaxis = gl.GLLinePlotItem(pos=[[0,0,0], [0,0,self.get_user_param('axes_length')]], width=6, color=self.parent_viewer.z_BLUE, antialias=True, glOptions='additive')

        self.parent_viewer.gl_view.addItem(self.x_glaxis, name='Tooltip X axis')
        self.parent_viewer.gl_view.addItem(self.y_glaxis, name='Tooltip Y axis')
        self.parent_viewer.gl_view.addItem(self.z_glaxis, name='Tooltip Z axis')

        self.x_glaxis.setDepthValue(10) # Tooltip -> render tree foreground
        self.y_glaxis.setDepthValue(10) # Tooltip -> render tree foreground
        self.z_glaxis.setDepthValue(10) # Tooltip -> render tree foreground

        self._update_transform()

    def update_rendered_object(self):
        if self.x_glaxis is not None:
            self._update_transform()

    def delete_rendered_object(self):
        if self.x_glaxis in self.parent_viewer.gl_view.items:
            self.parent_viewer.gl_view.removeItem(self.x_glaxis)
            self.x_glaxis = None
        if self.y_glaxis in self.parent_viewer.gl_view.items:
            self.parent_viewer.gl_view.removeItem(self.y_glaxis)
            self.y_glaxis = None
        if self.z_glaxis in self.parent_viewer.gl_view.items:
            self.parent_viewer.gl_view.removeItem(self.z_glaxis)
            self.z_glaxis = None
    
    def _init_status_bar_widget(self):
        seperator_ui_label = pyqtw.QLabel(' |')
        self.parent_viewer.statusBar().addPermanentWidget(seperator_ui_label)

        default_tooltip_tf_ui_label = pyqtw.QLabel('Default tooltip transform')
        self.parent_viewer.statusBar().addPermanentWidget(default_tooltip_tf_ui_label)

        self.tooltip_transform_editor = pyqtw.QLineEdit(str(self.get_user_param('tooltip_transforms_str')))
        self.tooltip_transform_editor.editingFinished.connect(functools.partial(self._parse_editor, self.tooltip_transform_editor, 'tooltip_transforms_str', '', 'str'))
        self.parent_viewer.statusBar().addPermanentWidget(self.tooltip_transform_editor)
        self.tooltip_transform_editor.setFixedWidth(400)
        self.tooltip_transform_editor.setToolTip('STL mesh transformations<br> - S0.5: Apply a 0.5 scaling factor (Use Sx to scale along x)<br> - Ty1mm: 1mm translation along y<br> - Rz90deg: Rotate by 90 degrees around z axis')
    
    def _on_editor_parsed(self, param_name, edited_value):
        self.set_user_param(param_name, edited_value)
        self.parent_viewer.update_rendered_view()

    def _parse_editor(self, src_editor, param_name, unit='', param_type='float'): # TODO move to MOdule
        if param_type == 'int':
            edited_value = int(src_editor.text())
        elif param_type == 'float':
            edited_text = src_editor.text().replace(' ', '') # remove spaces
            edited_text_nounit = edited_text[:-len(unit)]
            edited_value = si_parse(edited_text_nounit.replace('u', 'µ'))
        else: # raw str
            edited_value = src_editor.text()
        self._on_editor_parsed(param_name, edited_value)
    
    # --- Module specific attributes ---

    @property
    def tooltip_tmat(self):
        if self._tooltip_tmat is None:
            # Compute tooltip transform matrix from tooltip_transforms_str (status bar qedit)
            transforms_matrices = af_tr_from_str.transform_matrices_from_str(
                self.get_user_param('tooltip_transforms_str')
            )
            self._tooltip_tmat = af_tr.scale_mat(1)
            for tr_mat in transforms_matrices:
                self._tooltip_tmat = self._tooltip_tmat @ tr_mat
        return self._tooltip_tmat
    
    @tooltip_tmat.setter
    def tooltip_tmat(self, value):
        self._tooltip_tmat = value
    
    def _update_transform(self):
        self.x_glaxis.resetTransform()
        self.x_glaxis.applyTransform(pyqtg.QMatrix4x4(self.tooltip_tmat.T.ravel()), local=False)
        self.y_glaxis.resetTransform()
        self.y_glaxis.applyTransform(pyqtg.QMatrix4x4(self.tooltip_tmat.T.ravel()), local=False)
        self.z_glaxis.resetTransform()
        self.z_glaxis.applyTransform(pyqtg.QMatrix4x4(self.tooltip_tmat.T.ravel()), local=False)