# %%

import numpy as np
import PyQt6.QtGui as pyqtg
import PyQt6.QtCore as pyqtc
import PyQt6.QtWidgets as pyqtw
from si_prefix import si_format, si_parse
import pyqtgraph.opengl as gl
import sys, copy

# TODO TMAT MISDEF FIX -> tmat[3, :3] (wrong) -> tmat[:3, 3] (RIGHT)
# TODO function / method attributes names uniformity check

def remove_repeated_spaces_from_string(string):
    string = ' '.join(string.split())
    return string


class AffineTransforms:
    """ Collection of affine transform function (Scale, Translate, Rotate)"""

    def scale_mat(self, scaling_ratio):
        """ Scale affine transformation matrix. """
        scale_mat = np.eye(4, dtype=float)
        if isinstance(scaling_ratio, int) or isinstance(scaling_ratio, float):
            scale_mat *= scaling_ratio
            scale_mat[-1, -1] = 1
        elif isinstance(scaling_ratio, np.ndarray):
            scale_mat[np.arange(3), np.arange(3)] = scaling_ratio
        return scale_mat
        
    def rot_mat(self, rot_axis='x', theta=0, angular_units='degrees'):
        """ Rotation affine transformation matrix. """
        rot_axis=rot_axis.lower(); angular_units=angular_units.lower() # Force args in lowercase

        # Convert to radians if necessary
        if angular_units=='degrees':
            theta=np.deg2rad(theta)
        elif angular_units=='radians':
            pass
        else:
            raise Exception('Unknown angular units.  Please use radians or degrees.')

        # Select appropriate basic homogenous matrix
        if rot_axis == 'x':
            rotmat = np.array([ [1, 0, 0, 0],
                                [0, np.cos(theta), -np.sin(theta), 0],
                                [0, np.sin(theta), np.cos(theta), 0],
                                [0, 0, 0, 1]])
        elif rot_axis == 'y':
            rotmat = np.array([ [np.cos(theta), 0, np.sin(theta), 0],
                                [0, 1, 0, 0],
                                [-np.sin(theta), 0, np.cos(theta), 0],
                                [0, 0, 0, 1]])
        elif rot_axis == 'z':
            rotmat = np.array([ [np.cos(theta), -np.sin(theta), 0, 0],
                                [np.sin(theta), np.cos(theta), 0, 0],
                                [0, 0, 1, 0],
                                [0, 0, 0, 1]])
        else:
            raise Exception('Unknown axis of rotation.  Please use x, y, or z.')
        return rotmat

    def translat_mat(self, translation_axis='x', translation_norm=1):
        """ Translation affine transformation matrix. """
        axii = 0 if translation_axis=='x' else 1 if translation_axis=='y' else 2 if translation_axis=='z' else None
        if axii is None:
            raise ValueError('translation_axis must contain x, y, or z characters')
        tmat = np.eye(4)
        tmat[axii, 3] = translation_norm
        return tmat

af_tr = AffineTransforms()

class AffineTransformsFromStr(AffineTransforms):

    """
    Supported string formats:
        -> Translate
            Tx50um (translate 50 micrometers along x)
        -> Rotate
            Rz12deg (12 degree rotation around z axis)
        -> Scale
            S.2 (apply a 0.2 scaling ratio in all directions)
            Sy30 (apply a 30 scaling ratio along y)
    
    Transform operations need to be sepated by a space
    """

    def str_trans2trans_mat(self, str_trans):
        try:
            trans_axis = str_trans[1]
            trans_dist = si_parse(str_trans[2:-1].replace('u', 'µ'))
            trans_mat = self.translat_mat(trans_axis, trans_dist)
        except:
            trans_mat = None
        return trans_mat

    def str_rot2rot_mat(self, str_rot):
        try:
            rot_axis = str_rot[1]
            rot_angle = si_parse(str_rot[2:-3])
            rot_mat = self.rot_mat(rot_axis, rot_angle)
        except:
            rot_mat = None
        return rot_mat
    
    def str_scale2scale_mat(self, str_scale):
        try:
            scale_axis = str_scale[1]
            if scale_axis in 'xyz':
                xyz_scale = np.array([1, 1, 1], dtype=float)
                scaling_ratio = si_parse(str_scale[2:])
                if scale_axis in 'x':
                    xyz_scale[0] = scaling_ratio
                elif scale_axis in 'y':
                    xyz_scale[1] = scaling_ratio
                elif scale_axis in 'z':
                    xyz_scale[2] = scaling_ratio
                scale_mat = self.scale_mat(xyz_scale)
            else:
                scaling_ratio = si_parse(str_scale[1:])
                scale_mat = self.scale_mat(scaling_ratio)
        except:
            scale_mat = None
        return scale_mat

    def transform_matrices_from_str(self, ef_tr_str):
        transform_matrices = []
        if ef_tr_str is None:
            return []
        for str_tr in ef_tr_str.split(' '):
            if str_tr.startswith('R') and str_tr.endswith('deg'):
                rot_mat = self.str_rot2rot_mat(str_tr)
                if rot_mat is not None:
                    transform_matrices.append(rot_mat)
            elif str_tr.startswith('T') and str_tr.endswith('m'):
                trans_mat = self.str_trans2trans_mat(str_tr)
                if trans_mat is not None:
                    transform_matrices.append(trans_mat)
            elif str_tr.startswith('S'):
                scale_mat = self.str_scale2scale_mat(str_tr)
                if scale_mat is not None:
                    transform_matrices.append(scale_mat)
        return transform_matrices
    
    def transform_matrix_from_str(self, ef_tr_str):
        tmat = np.eye(4)
        str_tmatrices = self.transform_matrices_from_str(ef_tr_str)
        for str_tmat in str_tmatrices:
            tmat = tmat @ str_tmat
        return tmat


af_tr = AffineTransforms()
af_tr_from_str = AffineTransformsFromStr()

# ====

# translation

def get_pick_ray(view: gl.GLViewWidget, screen_x, screen_y):
    w, h = view.width(), view.height()
    ndc_x = (screen_x / w) * 2.0 - 1.0
    ndc_y = 1.0 - (screen_y / h) * 2.0

    region = (0, 0, w, h)
    proj = view.projectionMatrix(region, region)
    view_mat = view.viewMatrix()
    mvp = proj * view_mat

    inv_mvp, ok = mvp.inverted()
    if not ok:
        raise RuntimeError("MVP not invertible")

    near = inv_mvp.map(pyqtg.QVector3D(ndc_x, ndc_y, -1.0))
    far  = inv_mvp.map(pyqtg.QVector3D(ndc_x, ndc_y,  1.0))

    o = np.array([near.x(), near.y(), near.z()])
    f = np.array([far.x(),  far.y(),  far.z()])
    d = f - o
    d /= np.linalg.norm(d)
    return o, d

def closest_param_on_line(line_point, line_dir, ray_origin, ray_dir):
    d1 = line_dir / np.linalg.norm(line_dir)
    d2 = ray_dir  # already normalized
    r = line_point - ray_origin
    b = np.dot(d1, d2)
    dd = np.dot(d1, r)
    e = np.dot(d2, r)
    denom = 1.0 - b * b
    if abs(denom) < 1e-8:
        return None  # drag axis nearly parallel to view direction — degenerate
    return (b * e - dd) / denom

# rotation

def ray_plane_intersection(ray_origin, ray_dir, plane_point, plane_normal):
    denom = np.dot(ray_dir, plane_normal)
    if abs(denom) < 1e-8:
        return None  # ray parallel to plane (looking edge-on at rotation plane)
    t = np.dot(plane_point - ray_origin, plane_normal) / denom
    if t < 0:
        return None  # plane is behind the camera
    return ray_origin + t * ray_dir

def make_plane_basis(axis):
    axis = axis / np.linalg.norm(axis)
    # pick a helper vector not parallel to axis
    helper = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(helper, axis)) > 0.9:
        helper = np.array([0.0, 1.0, 0.0])
    u = np.cross(axis, helper)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)  # already unit length since axis, u are orthonormal
    return u, v

def angle_on_plane(point, pivot, u, v):
    rel = point - pivot
    x = np.dot(rel, u)
    y = np.dot(rel, v)
    return np.arctan2(y, x)

# Scale

def project_to_screen(view: gl.GLViewWidget, world_point):
    w, h = view.width(), view.height()
    region = (0, 0, w, h)
    proj = view.projectionMatrix(region, region)
    view_mat = view.viewMatrix()
    mvp = proj * view_mat

    p = pyqtg.QVector3D(*world_point)
    clip = mvp.map(p)  # QMatrix4x4.map on QVector3D does perspective divide

    screen_x = (clip.x() * 0.5 + 0.5) * w
    screen_y = (1.0 - (clip.y() * 0.5 + 0.5)) * h  # flip y back to Qt coords
    return np.array([screen_x, screen_y])


class DescriptiveQLineEdit(pyqtw.QLineEdit):

    def __init__(self, default_text, description_text, **kwargs):
        super().__init__(default_text, **kwargs)

        # Description prefix label
        prefix_label = pyqtw.QLabel(description_text)
        prefix_label.setStyleSheet("padding-left: 2px; padding-right: 0px; color: gray;")

        # Eval description width to avoid trucation
        font_metrics = pyqtg.QFontMetrics(prefix_label.font())
        text_width = font_metrics.horizontalAdvance(description_text)
        prefix_label.setFixedWidth(text_width + font_metrics.averageCharWidth())

        # Description label embeding into QLineEdit
        prefix_action = pyqtw.QWidgetAction(self)
        prefix_action.setDefaultWidget(prefix_label)
        self.addAction(prefix_action, pyqtw.QLineEdit.ActionPosition.LeadingPosition)
        self.setTextMargins(text_width - font_metrics.averageCharWidth(), 0, 0, 0)


class StrTransformDescriptiveQLineEdit(DescriptiveQLineEdit):

    def __init__(self, default_text, description_text, **kwargs):
        super().__init__(default_text, description_text, **kwargs)

    def get_transforms_strs_before_text_caret(self):
        """ returns (str transforms before carret, trim index) """

        tr_str, caret_location = self.text(), self.cursorPosition()
        spaces_locations = np.array([i for i, c in enumerate(tr_str) if c.isspace()])
        carret2space_distance = spaces_locations - caret_location
        positive_carret2space_distance = carret2space_distance >= 0
        if any(positive_carret2space_distance):
            tr_str_trim_index = caret_location + np.min(carret2space_distance[positive_carret2space_distance])
        else:
            tr_str_trim_index = None # keep full transform str

        return (tr_str[:tr_str_trim_index], tr_str_trim_index)

    def insert_tr_str(self, tr_str_insert, insertion_index=None):
        tmat_str = self.text()
        if insertion_index is not None:
            new_tmat_str = tmat_str[:insertion_index] + ' ' + tr_str_insert + ' ' + tmat_str[insertion_index:]
        else: # insert at the end of str
            new_tmat_str = tmat_str[:insertion_index] + ' ' + tr_str_insert
        new_tmat_str = remove_repeated_spaces_from_string(new_tmat_str) # cleanup string
        self.setText(new_tmat_str)

    def eval_tmat_before_text_carret(self):
        tr_str_before_text_carret, tr_str_trim_index = self.get_transforms_strs_before_text_caret()
        tmat_before_text_carret = af_tr_from_str.transform_matrix_from_str(
            tr_str_before_text_carret
        )

        print('eval_tmat_before_text_carret: ', tr_str_before_text_carret, tr_str_trim_index)

        return (tmat_before_text_carret, tr_str_trim_index)

    def eval_tmat(self):
        tmat = af_tr_from_str.transform_matrix_from_str(
            self.text()
        )
        return tmat


class MWEWindow(pyqtw.QMainWindow):
    """ Main class for CoperniFUS. """

    x_RED = '#e74c3c'
    """ Defaut x axis color (red) """
    y_GREEN = '#7fd169'
    """ Defaut y axis color (green) """
    z_BLUE = '#497ccc'
    """ Defaut z axis color (blue) """

    ATLAS_SPACE_CONVENTION = ['Anterior', 'Left', 'Superior']
    """ Atlas space convention defined according to `the brainglobe-space <https://brainglobe.info/documentation/brainglobe-space/index.html>`_ """

    _STATUS_BAR_MSG_TIMEOUT = 5000

    def __init__(self, app, **kwargs) -> None:
        
        self.app_kwargs = kwargs
        self.app = app
        self.app.setStyle('Fusion')
        super().__init__()

        self.setGeometry(100, 100, 1500, 1000)

        self._init_gui()
        self._show_axes()
        self.show()

    def _init_gui(self):

        # Window layout setup
        self.viewer_widget = pyqtw.QWidget()
        self.viewer_layout = pyqtw.QGridLayout()
        self.viewer_widget.setLayout(self.viewer_layout)
        self.viewer_widget.setContentsMargins(0, 0, 0, 0)
        self.viewer_layout.setContentsMargins(0, 0, 0, 0)

        # GLview setup
        self.gl_view = DragAxisGLView(parent_viewer=self)
        self.gl_view.opts['distance'] = 20
        self.gl_view.opts['fov'] = 1

        # Add to layout
        self.viewer_layout.addWidget(self.gl_view, 0, 0, 1, 1) # row, col
        self.setCentralWidget(self.viewer_widget)

        self.tooltip_transform_editor = StrTransformDescriptiveQLineEdit(
            'S0.03 Rz30deg Tx12mm Ty4mm', 'Default Tooltip transform'
        )
        self.statusBar().addPermanentWidget(self.tooltip_transform_editor)

        # --- 3D viewer axes ---
    
    def _show_axes(self, axes_len=2e-2):
        x_glaxis = gl.GLLinePlotItem(pos=[[0,0,0], [axes_len,0,0]], width=8, color=self.x_RED, antialias=True, glOptions='translucent')
        y_glaxis = gl.GLLinePlotItem(pos=[[0,0,0], [0,axes_len,0]], width=8, color=self.y_GREEN, antialias=True, glOptions='translucent')
        z_glaxis = gl.GLLinePlotItem(pos=[[0,0,0], [0,0,axes_len]], width=8, color=self.z_BLUE, antialias=True, glOptions='translucent')

        self.gl_view.addItem(x_glaxis, name='X axis')
        self.gl_view.addItem(y_glaxis, name='Y axis')
        self.gl_view.addItem(z_glaxis, name='Z axis')

        x_glaxis.setDepthValue(-1) # Axis -> render tree background
        y_glaxis.setDepthValue(-1) # Axis -> render tree background
        z_glaxis.setDepthValue(-1) # Axis -> render tree background


class GLViewWidgetWithCamMoveSignal(gl.GLViewWidget):

    VIEWPORT_SPATIAL_UNIT = 'm'
    SCALEBAR_TARGET_PX_LENGTH = 120
    SCALEBAR_PX_PADDING = 20
    SCALEBAR_PX_WIDTH = 4

    camera_changed_signal = pyqtc.pyqtSignal()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_changed_signal.connect(self.on_camera_change)

    def on_camera_change(self):
        pass # to be overriden in subclasses

    def wheelEvent(self, ev):
        super().wheelEvent(ev)
        self.camera_changed_signal.emit()

    def mouseMoveEvent(self, ev):
        super().mouseMoveEvent(ev)
        self.camera_changed_signal.emit()

    def setCameraPosition(self, pos=None, distance=None, elevation=None, azimuth=None, rotation=None):
        super().setCameraPosition(
            pos=pos, distance=distance, elevation=elevation,
            azimuth=azimuth, rotation=rotation
        )
        self.camera_changed_signal.emit()


class GLViewWidgetWithScaleBar(GLViewWidgetWithCamMoveSignal):

    VIEWPORT_SPATIAL_UNIT = 'm'
    SCALEBAR_TARGET_PX_LENGTH = 120
    SCALEBAR_PX_PADDING = 20
    SCALEBAR_PX_WIDTH = 4

    def paintEvent(self, event):
        super().paintEvent(event) # draws the normal 3D scene

        # add scale bar overlay
        painter = pyqtg.QPainter(self)
        painter.setRenderHint(pyqtg.QPainter.RenderHint.Antialiasing)
        self._draw_scale_bar(painter)
        painter.end()

    def _pick_nice_scalebar_length(self, target_px_length):
        """ returns (world_coord_length, px_length) """

        # eval px size in the center if the world
        center = self.opts['center']
        px_size = self.pixelSize(center) # world units per pixel

        world_coord_length = self._round_scalebar_value(target_px_length * px_size)
        px_length = world_coord_length / px_size

        return world_coord_length, px_length

    def _draw_scale_bar(self, painter):
        world_coord_length, px_length = self._pick_nice_scalebar_length(self.SCALEBAR_TARGET_PX_LENGTH)

        # eval scalebar position in bottom-left corner
        y = self.height() - self.SCALEBAR_PX_PADDING
        x0 = self.SCALEBAR_PX_PADDING
        x1 = x0 + px_length

        pen = pyqtg.QPen(pyqtc.Qt.GlobalColor.white, self.SCALEBAR_PX_WIDTH)
        painter.setPen(pen)
        painter.drawLine(int(x0), int(y), int(x1), int(y))

        painter.drawText(int(x0), int(y) - 10, self._scalebar_value_formatter(world_coord_length))

    def _scalebar_value_formatter(self, scalebar_value):
        formatted_value = si_format(
            scalebar_value,
            format_str='{value} {prefix}' + self.VIEWPORT_SPATIAL_UNIT,
            precision=0
        )
        return formatted_value

    def _round_scalebar_value(self, scalebar_value):
        """ Round to a visually clean 1/2/5 * 10^n value """

        if scalebar_value <= 0:
            return 1.0
        exp = np.floor(np.log10(scalebar_value))
        frac = scalebar_value / 10**exp
        if frac < 1.5:
            clean_value = 1
        elif frac < 3.5:
            clean_value = 2
        elif frac < 7.5:
            clean_value = 5
        else:
            clean_value = 10
        
        return clean_value * 10**exp


class NamedGLViewWidget(GLViewWidgetWithScaleBar):

    def __init__(self, parent_viewer, **kwargs):
        self.parent_viewer = parent_viewer
        super().__init__(**kwargs)
        # self.gl_items_toggler = GlItemsToggler(parent_viewer=parent_viewer, gl_view=self)

    def get_safe_gl_item_name(self, name, existing_names):
        safe_name = copy.deepcopy(name)

        # Increment suffix until an unused name is found
        suffix_index = 1
        while safe_name in existing_names:
            safe_name = f'{copy.deepcopy(name)} {suffix_index}'
            suffix_index += 1

        return safe_name

    def addItem(self, item, name=None, double_click_event_func=None):
        """ addItem overloaded with the handling of a gl_item name attribute + GlItemsToggler """
        existing_names = self.gl_items_names

        if name is None:
            name = f'{item.__class__.__name__}_{id(item)}'
        item.name = self.get_safe_gl_item_name(name, existing_names)

        # Connect double-click event
        if callable(double_click_event_func):
            item.double_click_event_func = double_click_event_func
        else:
            item.double_click_event_func = None
        
        super().addItem(item)
        # self.gl_items_toggler.update_list_view()

    def removeItem(self, item):
        super().removeItem(item)
        # self.gl_items_toggler.update_list_view()

    @property
    def gl_items_names(self):
        return [gl_item.name for gl_item in self.items]
    
    @property
    def gl_items_named_dict(self):
        return {gl_item.name: gl_item for gl_item in self.items}

    @property
    def gl_items_names2double_click_events_dict(self):
        return {gl_item.name: gl_item.double_click_event_func for gl_item in self.items}
    
    def get_gl_item_from_name(self, gl_item_name):
        name2item_dict = self.gl_items_named_dict
        if gl_item_name in name2item_dict:
            return name2item_dict[gl_item_name]
        else:
            return None


class DragAxisGLView(NamedGLViewWidget):

    TRS_MODE_TRIHEDRA_TARGET_PX_LENGTH = 200
    TRS_MODE_TRIHEDRA_LINEWIDTHS = (3, 10) # (inactive axis, active axis)

    def __init__(self, parent_viewer, **kwargs):
        self.parent_viewer = parent_viewer
        super().__init__(parent_viewer, **kwargs)

        # --- trs mode -> translate rotate scale ---
        self._trs_mode = None
        self._trs_mode_axis = ''
        self._trs_mode_original_tmat = None
        self._trs_mode_trihedras_tmat = None
        self._nice_TRS_trihedra_scale_factor = None
        self._trs_mode_tr_str_trim_index = None
        self._trs_focussed_widget = None
        self._trs_preview_trihedras = []
        self._pressed_spacebar = False

        self.trs_mode_translation_distance = 0
        self.trs_mode_rotation_angle = 0
        self.trs_mode_scale_factor = 1
        self._trs_mode_translation_start_distance = 0
        self._trs_mode_rotation_start_angle = 0
        self._trs_mode_scale_start_factor = 1

        # Receive keyboard events regardless of which widget has focus
        # pyqtw.QApplication.instance().installEventFilter(self)
        self.parent_viewer.app.installEventFilter(self)

    # --- TRS transforms computation methods ---

    def begin_axis_drag(self, origin, direction):
        self.drag_origin = np.asarray(origin, dtype=float)
        self.drag_dir = np.asarray(direction, dtype=float)
        self.drag_dir /= np.linalg.norm(self.drag_dir)
        self._s0 = None

    def begin_axis_rotate(self, pivot, axis):
        self.rot_pivot = np.asarray(pivot, dtype=float)
        self.rot_axis = np.asarray(axis, dtype=float)
        self.rot_axis /= np.linalg.norm(self.rot_axis)
        self.rot_u, self.rot_v = make_plane_basis(self.rot_axis)
        self._theta0 = None

    def begin_scale(self, pivot, min_distance=5.):
        self.scale_pivot = np.asarray(pivot, dtype=float)
        self._scale_min_dist = min_distance  # px; guards against div-by-~0 near pivot
        self._d0 = None

    # --- 

    def on_camera_change(self):
        super().on_camera_change()

        if self._trs_mode is not None: # update TRS mode trihedra scale
            self.update_TRS_preview_trihedra()

    @property
    def trs_mode_original_tmat(self):
        if self._trs_mode_original_tmat is None:
            self._trs_mode_original_tmat = np.eye(4)
        return self._trs_mode_original_tmat

    @trs_mode_original_tmat.setter
    def trs_mode_original_tmat(self, value):
        if value is not None:
            if value.shape != (4, 4):
                raise ValueError('Transformation matrix should be of shape (4, 4)')
        self._trs_mode_original_tmat = value

    def eventFilter(self, obj, event): # TODO update tmat
        if event.type() == pyqtc.QEvent.Type.KeyPress:
            pressed_key = event.key()

            # Escape TRS mode without saving
            if self._trs_mode is not None and pressed_key == pyqtc.Qt.Key.Key_Escape:
                self.trs_mode_switcher(save_tr=False)
                event.accept()
                return True

            # Save translation and exit TRS mode
            elif self._trs_mode is not None and pressed_key in [pyqtc.Qt.Key.Key_Enter, pyqtc.Qt.Key.Key_Return] and self.underMouse():
                self.trs_mode_switcher()
                event.accept()
                return True

            # Pause TRS mode
            elif self._trs_mode is not None and pressed_key == pyqtc.Qt.Key.Key_Space and self.underMouse():
                self._pressed_spacebar = True
                event.accept() # Prevent Space from being typed into QLineEdit
                return True

            # Set TRS axis
            elif self._trs_mode in ['T', 'R'] and self.underMouse() and pressed_key in [
                pyqtc.Qt.Key.Key_X,
                pyqtc.Qt.Key.Key_Y,
                pyqtc.Qt.Key.Key_Z
            ]:
                self.trs_mode_switcher(target_transformation_axis=pressed_key)

                event.accept() # Prevent x y z from being typed into QLineEdit
                return True

            # Init TRS mode
            elif pressed_key in [
                pyqtc.Qt.Key.Key_T,
                pyqtc.Qt.Key.Key_R,
                pyqtc.Qt.Key.Key_S
            ]:
                if self._trs_focussed_widget is None:
                    self._trs_focussed_widget = self.parent_viewer.focusWidget()

                # Only activate if transform str editor is focused mouse is currently over this GL widget
                if isinstance(self._trs_focussed_widget, StrTransformDescriptiveQLineEdit) and self.underMouse(): 
                    if not event.isAutoRepeat():
                        self.trs_mode_switcher(target_mode=pressed_key)

                    # Prevent T / R / S from being typed into QLineEdit
                    event.accept()
                    return True

                else:
                    self._trs_focussed_widget = None

        if event.type() == pyqtc.QEvent.Type.KeyRelease:
            released_key = event.key()

            # End TRS Pause
            if self._trs_mode is not None and released_key == pyqtc.Qt.Key.Key_Space:
                self._pressed_spacebar = False

        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):

        if self._pressed_spacebar is False and self._trs_mode == 'T' and self._trs_mode_axis in ['x', 'y', 'z']:

            # self._trs_mode_tr_start_tmat = copy.deepcopy(self._trs_mode_trihedras_tmat)
            self._trs_mode_translation_start_distance = self.trs_mode_translation_distance
            transform_origin = self._trs_mode_trihedras_tmat[:3, 3]
            transform_axis = transform_origin + self._trs_mode_trihedras_tmat[
                :3, ['x', 'y', 'z'].index(self._trs_mode_axis)
            ]
            self.begin_axis_drag(transform_origin, transform_axis)

            pos = event.position()
            o, d = get_pick_ray(self, pos.x(), pos.y())
            self._s0 = closest_param_on_line(self.drag_origin, self.drag_dir, o, d) or 0.0 # TODO rename self._s0

            event.accept()

        elif self._pressed_spacebar is False and self._trs_mode == 'R' and self._trs_mode_axis in ['x', 'y', 'z']:

            # self._trs_mode_tr_start_tmat = copy.deepcopy(self._trs_mode_trihedras_tmat)
            self._trs_mode_rotation_start_angle = self.trs_mode_rotation_angle
            transform_origin = self._trs_mode_trihedras_tmat[:3, 3]
            transform_axis = transform_origin + self._trs_mode_trihedras_tmat[
                :3, ['x', 'y', 'z'].index(self._trs_mode_axis)
            ]
            self.begin_axis_rotate(transform_origin, transform_axis)

            pos = event.position()
            o, d = get_pick_ray(self, pos.x(), pos.y())
            hit = ray_plane_intersection(o, d, self.rot_pivot, self.rot_axis)
            if hit is not None:
                self._theta0 = angle_on_plane(hit, self.rot_pivot, self.rot_u, self.rot_v)
            else:
                self._theta0 = 0.0

            event.accept()

        elif self._pressed_spacebar is False and self._trs_mode == 'S' and self._trs_mode_axis == 'xyz':

            # self._trs_mode_tr_start_tmat = copy.deepcopy(self._trs_mode_trihedras_tmat)
            self._trs_mode_scale_start_factor = self.trs_mode_scale_factor
            transform_origin = self._trs_mode_trihedras_tmat[:3, 3]
            self.begin_scale(transform_origin)

            pos = event.position()
            mouse_loc_xy = np.array([pos.x(), pos.y()])
            pivot_screen = project_to_screen(self, self.scale_pivot)
            self._d0 = max(np.linalg.norm(mouse_loc_xy - pivot_screen), self._scale_min_dist)

            event.accept()

        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if self._pressed_spacebar is False and self._trs_mode == 'T' and self._trs_mode_axis in ['x', 'y', 'z']:

            pos = event.position()
            o, d = get_pick_ray(self, pos.x(), pos.y())
            s = closest_param_on_line(self.drag_origin, self.drag_dir, o, d)
            if s is not None:
                self.trs_mode_translation_distance = self._trs_mode_translation_start_distance + (s - self._s0)

                # Update TRS mode transform preview trihedra
                self._trs_mode_trihedras_tmat = self._trs_mode_original_tmat @ af_tr.translat_mat(
                    self._trs_mode_axis, self.trs_mode_translation_distance)

            self.update_TRS_preview_trihedra()
            event.accept()

        elif self._pressed_spacebar is False and self._trs_mode == 'R' and self._trs_mode_axis in ['x', 'y', 'z']:

            pos = event.position()
            o, d = get_pick_ray(self, pos.x(), pos.y())
            hit = ray_plane_intersection(o, d, self.rot_pivot, self.rot_axis)
            if hit is not None:
                theta = angle_on_plane(hit, self.rot_pivot, self.rot_u, self.rot_v)
                self.trs_mode_rotation_angle = self._trs_mode_rotation_start_angle + np.rad2deg(theta - self._theta0)

                # Update TRS mode transform preview trihedra
                self._trs_mode_trihedras_tmat = self._trs_mode_original_tmat @ af_tr.rot_mat(
                    self._trs_mode_axis, self.trs_mode_rotation_angle)

            self.update_TRS_preview_trihedra()
            event.accept()

        elif self._pressed_spacebar is False and self._trs_mode == 'S' and self._trs_mode_axis == 'xyz':

            pos = event.position()
            mouse = np.array([pos.x(), pos.y()])
            pivot_screen = project_to_screen(self, self.scale_pivot)
            d = max(np.linalg.norm(mouse - pivot_screen), self._scale_min_dist)
            self.trs_mode_scale_factor = self._trs_mode_scale_start_factor * (d / self._d0)

            # Update TRS mode transform preview trihedra
            self._trs_mode_trihedras_tmat = self._trs_mode_original_tmat @ af_tr.scale_mat(
                self.trs_mode_scale_factor)

            self.update_TRS_preview_trihedra()
            event.accept()

        else: # Normal GLViewWidget mouse handling
            super().mouseMoveEvent(event)

    def trs_mode_switcher(self, target_mode=None, target_transformation_axis=None, save_tr=True):
        """ target mode: T / R / S 
            perserve_current_mode: bool -> set to True to keep current mode when switching T/R axis
            save_tr: bool -> set to False when escaping from TRS mode
        """

        # Save trs transform before switching
        if save_tr and self._trs_mode is not None:
            self.save_trs_mode_transform()
    
        # Register targetted TRS mode
        if target_mode == 'T' or target_mode == pyqtc.Qt.Key.Key_T:
            new_mode = 'T'
        elif target_mode == 'R' or target_mode == pyqtc.Qt.Key.Key_R:
            new_mode = 'R'
        elif target_mode == 'S' or target_mode == pyqtc.Qt.Key.Key_S:
            new_mode = 'S'
        else:
            new_mode = None

        # Register targetted transformation axis
        if target_transformation_axis == 'x' or target_transformation_axis == pyqtc.Qt.Key.Key_X:
            new_transformation_axis = 'x'
        elif target_transformation_axis == 'y' or target_transformation_axis == pyqtc.Qt.Key.Key_Y:
            new_transformation_axis = 'y'
        elif target_transformation_axis == 'z' or target_transformation_axis == pyqtc.Qt.Key.Key_Z:
            new_transformation_axis = 'z'
        else:
            new_transformation_axis = ''

        # Switch mode / axis
        if target_transformation_axis is not None: # Update TRS mode (new transformation axis)
            self.trs_mode_original_tmat, self._trs_mode_tr_str_trim_index = self._trs_focussed_widget.eval_tmat_before_text_carret()
            self._trs_mode_trihedras_tmat = copy.deepcopy(self.trs_mode_original_tmat)

        elif new_mode is None or self._trs_mode == new_mode: # Exit TRS mode
            self._trs_mode = None
            self._trs_focussed_widget = None

        else: # Enter TRS mode
            self._trs_mode = new_mode
            self.trs_mode_original_tmat, self._trs_mode_tr_str_trim_index = self._trs_focussed_widget.eval_tmat_before_text_carret()
            self._trs_mode_trihedras_tmat = copy.deepcopy(self.trs_mode_original_tmat)

        # Tnit TRS mode attributes
        self.trs_mode_translation_distance = 0
        self.trs_mode_rotation_angle = 0
        self.trs_mode_scale_factor = 1
        self._pressed_spacebar = False
        if self._trs_mode == 'S':
            new_transformation_axis = 'xyz'
        self._trs_mode_axis = new_transformation_axis

        # Update trihedra
        self.update_TRS_preview_trihedra()

    def save_trs_mode_transform(self):
        formatted_transform_value = None
        if self._trs_mode == 'T' and self.trs_mode_translation_distance != 0:
            transform_prefix = f'{self._trs_mode}{self._trs_mode_axis}'
            formatted_transform_value = si_format(self.trs_mode_translation_distance, format_str='{value}{prefix}'+'m')
        elif self._trs_mode == 'R' and self.trs_mode_rotation_angle != 0:
            transform_prefix = f'{self._trs_mode}{self._trs_mode_axis}'
            formatted_transform_value = si_format(self.trs_mode_rotation_angle, format_str='{value}{prefix}'+'deg')
        elif self._trs_mode == 'S' and self.trs_mode_scale_factor != 1:
            transform_prefix = self._trs_mode
            formatted_transform_value = f'{self.trs_mode_scale_factor:.3g}'
        else:
            return None

        if formatted_transform_value is not None:
            self._trs_focussed_widget.insert_tr_str(
                f'{transform_prefix}{formatted_transform_value}',
                self._trs_mode_tr_str_trim_index
            )
            # self._trs_mode_tr_str_trim_index += len(formatted_transform_value) # shift trim index to allow the insertion of multiple transforms # TODO save trs_mode_original_tmat for TRS mode insertion sequences??

    def add_scale_accurate_TRS_trihedra(self):
        """ Render an axes trihedra corresponding to a given transform_matrix. Axes length correspond to their actual scale. """

        self.delete_scale_accurate_TRS_trihedra()

        x_glaxis = gl.GLLinePlotItem(
            width=self.TRS_MODE_TRIHEDRA_LINEWIDTHS[int('x' in self._trs_mode_axis)], # active / inactive
            color=self.parent_viewer.x_RED,
            glOptions='translucent',
            antialias=True)
        y_glaxis = gl.GLLinePlotItem(
            width=self.TRS_MODE_TRIHEDRA_LINEWIDTHS[int('y' in self._trs_mode_axis)], # active / inactive
            color=self.parent_viewer.y_GREEN,
            glOptions='translucent',
            antialias=True)
        z_glaxis = gl.GLLinePlotItem(
            width=self.TRS_MODE_TRIHEDRA_LINEWIDTHS[int('z' in self._trs_mode_axis)], # active / inactive
            color=self.parent_viewer.z_BLUE,
            glOptions='translucent',
            antialias=True)

        scale_gltext = gl.GLTextItem(
            text='',
            alignment=pyqtc.Qt.AlignmentFlag.AlignCenter
        )

        self._trs_preview_trihedras = [x_glaxis, y_glaxis, z_glaxis, scale_gltext]

        self.addItem(x_glaxis, name='_trs trihedra ogsc x axis')
        self.addItem(y_glaxis, name='_trs trihedra ogsc y axis')
        self.addItem(z_glaxis, name='_trs trihedra ogsc z axis')
        self.addItem(scale_gltext, name='_trs trihedra ogsc scale text')

    def update_TRS_preview_trihedra(self):
        # if self._trs_mode_trihedras_tmat is not None:
        if self._trs_mode is None:
            self.delete_scale_accurate_TRS_trihedra()
        else:
            if len(self._trs_preview_trihedras) != 4:
                self.add_scale_accurate_TRS_trihedra()

            # pick trihedra scale so that it fits in the viewport
            if self._trs_mode != 'S' or self._nice_TRS_trihedra_scale_factor is None: # freeze trihedra scale ajustement during TRS mode scale
                trihedras_scale_world_coords, _ = self._pick_nice_scalebar_length(self.TRS_MODE_TRIHEDRA_TARGET_PX_LENGTH)
                original_tmat_scale = np.linalg.norm(self._trs_mode_trihedras_tmat[:3, 0]) # x vec norm -> assumes uniform scale accross x, y, z
                self._nice_TRS_trihedra_scale_factor = trihedras_scale_world_coords / original_tmat_scale

            nicely_scaled_trihedras_tmat = self._trs_mode_trihedras_tmat @ af_tr.scale_mat(self._nice_TRS_trihedra_scale_factor)
            x_vec = nicely_scaled_trihedras_tmat[:3, 0]
            y_vec = nicely_scaled_trihedras_tmat[:3, 1]
            z_vec = nicely_scaled_trihedras_tmat[:3, 2]
            origin = nicely_scaled_trihedras_tmat[:3, 3]

            # Scale loc
            text_offset_tmat = np.eye(4)
            text_offset_tmat[0, 3] = np.linalg.norm(nicely_scaled_trihedras_tmat[:3, 0]) # translate scale label along xyz
            text_pos = (nicely_scaled_trihedras_tmat @ np.array([1/3, 1/3, 1/3, 1]))[:3]

            self._trs_preview_trihedras[0].setData(
                pos=np.array([origin, origin+x_vec]),
                width=self.TRS_MODE_TRIHEDRA_LINEWIDTHS[int('x' in self._trs_mode_axis)]) # active / inactive
            self._trs_preview_trihedras[1].setData(
                pos=np.array([origin, origin+y_vec]),
                width=self.TRS_MODE_TRIHEDRA_LINEWIDTHS[int('y' in self._trs_mode_axis)]) # active / inactive
            self._trs_preview_trihedras[2].setData(
                pos=np.array([origin, origin+z_vec]),
                width=self.TRS_MODE_TRIHEDRA_LINEWIDTHS[int('z' in self._trs_mode_axis)]) # active / inactive
            self._trs_preview_trihedras[3].setData(
                pos=text_pos,
                text=f'1: {1/self._nice_TRS_trihedra_scale_factor:.3g}'
            )

    def delete_scale_accurate_TRS_trihedra(self):
        """ Remove all debug trihedras """
        for trihedra_gl_obj in self._trs_preview_trihedras:
            self.removeItem(trihedra_gl_obj)
        self._trs_preview_trihedras = []


%gui qt

app = pyqtw.QApplication(sys.argv)
mwe_viewer = MWEWindow(app)

# %%
