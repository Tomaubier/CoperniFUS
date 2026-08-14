# %%
from importlib.metadata import version

print(f"Launching CoperniFUS v{version('coperniFUS')}")

import sys, pathlib, trimesh, pymeshfix, copy, hashlib, base64, warnings, re
import PyQt6.QtGui as pyqtg
import PyQt6.QtCore as pyqtc
import PyQt6.QtWidgets as pyqtw
from si_prefix import si_format, si_parse
import pyqtgraph.opengl as gl
import numpy as np

# Handle multiple GLview instances
pyqtc.QCoreApplication.setAttribute(pyqtc.Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

from coperniFUS.modules import _jsonshelve

import coperniFUS
coperniFUS_location = coperniFUS.__file__

def clean_string(string):
    clean_string = ''.join(filter(str.isalnum, string))
    return clean_string

def remove_repeated_spaces_from_string(string):
    string = ' '.join(string.split())
    return string

class CachedDataHandler:

    def __init__(self, cache_dir_name='.cachedDir', cached_settings_fname=None):
        self.cache_dir = pathlib.Path.home() / cache_dir_name
        
        # Make cache dir if it does not exists
        self.cache_dir.mkdir(exist_ok=True)

        # Default -> new untitled config
        self.cached_settings_fname = 'Untitled Configuration.json'

        # If name not specified bug some config files exist in cache_dir -> set first available file name by default
        if cached_settings_fname is None:
            db_cached_fpaths = list(self.cache_dir.glob("*.json"))
            if len(db_cached_fpaths) > 0:
                self.cached_settings_fname = db_cached_fpaths[0].name

        # If name specified -> set cache name
        else:
            self.cached_settings_fname = f'{cached_settings_fname.split(".")[0]}.json'
        
        # Try loading cached_settings_fname
        successful_loading = False
        if self.cached_settings_fname is not None:
            try:
                cached_db = _jsonshelve.FlatShelf(self.cached_settings_fpath)
                with cached_db:
                    _ = dict(cached_db)
                cached_db.close()
                successful_loading = True
            except Exception as e:
                print(f'\nFailed to load .json cached settings file\n{self.cached_settings_fname}\n{type(e).__name__}: {str(e)}')

        # If unsuccesful loading -> fallback to new untitled config
        if not successful_loading:
            self.cached_settings_fname = 'Untitled Configuration.json'

        print(f'\n> Info: Cached configuration file location: {self.cached_settings_fpath}')

    def is_cached_filename_already_defined(self, cache_fname):
        """ Checks the availibility of a cache_fname (regardless of the file extension). """
        directory_path = pathlib.Path(self.cache_dir)
        cache_fname_without_ext = cache_fname.split(".")[0]
        for file in directory_path.iterdir():
            if file.is_file() and file.stem == cache_fname_without_ext:
                return True
        return False

    @property
    def cached_settings_fpath(self):
        """ FIle path of the cached file. """
        return self.cache_dir / self.cached_settings_fname

    def _attribute_str_id(self, attribute_id):
        if isinstance(attribute_id, str):
            attribute_str_id = attribute_id
        elif isinstance(attribute_id, list):
            attribute_str_id = '.'.join(attribute_id)
        return attribute_str_id

    def set_attr(self, attribute_id, value):
        """ Set the value of an attribute. """
        attribute_str_id = self._attribute_str_id(attribute_id)

        cached_db = _jsonshelve.FlatShelf(self.cached_settings_fpath)
        with cached_db:
            cached_db[attribute_str_id] = value
        cached_db.close()

    def get_attr(self, attribute_id, default_value=None):
        """ Get the value of an attribute. default_value will be returned if the attribute does not exist in cache. """
        attribute_str_id = self._attribute_str_id(attribute_id)

        cached_db = _jsonshelve.FlatShelf(self.cached_settings_fpath)
        with cached_db:
            if attribute_str_id in cached_db:
                value = cached_db[attribute_str_id]
            else:
                cached_db[attribute_str_id] = default_value
                value = default_value
        cached_db.close()
        return value
            
    def get_attr_unique_childs(self, attribute_prefix):
        """ Garanties attribute name unicity. """
        cached_db = _jsonshelve.FlatShelf(self.cached_settings_fpath)
        with cached_db:
            attributes_keys = list(cached_db.keys())
            attkeys_with_prefix = [attk.replace(attribute_prefix, '') for attk in attributes_keys if attk.startswith(attribute_prefix)]
            attkeys_with_prefix_splitted = [[k for k in attk.split('.') if len(k)>0] for attk in attkeys_with_prefix if len(attk)>0]
        cached_db.close()

        unique_child_names = np.unique([attk[0] for attk in attkeys_with_prefix_splitted])
        return unique_child_names


class NewConfigNamePopup(pyqtw.QDialog):

    def __init__(self, parent_viewer):
        self.parent_viewer = parent_viewer
        super().__init__(self.parent_viewer)

        # Layout for the dialog
        self.setWindowTitle("New CoperniFUS Configuration")
        self.popup_layout = pyqtw.QGridLayout()
        self.setLayout(self.popup_layout)
        self.setMinimumSize(400, 10)

        # Armature name editor
        self.config_name_editor = pyqtw.QLineEdit('Untitled Configuration')
        self.popup_layout.addWidget(self.config_name_editor, 1, 0, 1, 1) # Y, X, w, h

        # Set up the button box
        self.button_box = pyqtw.QDialogButtonBox(pyqtw.QDialogButtonBox.StandardButton.Cancel | pyqtw.QDialogButtonBox.StandardButton.Ok)
        self.popup_layout.addWidget(self.button_box, 2, 0, 1, 1) # Y, X, w, h
        # Connect buttons to actions
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.on_accept)

    def _is_valid_filename(self, filename):
        # Windows forbidden characters
        forbidden_chars = r'<>:"/\\|?*'
        # Reserved names in Windows
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }

        name = pathlib.Path(filename).name
        if any(char in name for char in forbidden_chars):
            return False
        if name.split('.')[0].upper() in reserved_names:
            return False
        if name in (".", "..") or len(name.strip()) == 0:
            return False
        return True
    
    def on_accept(self):

        is_name_valid = True

        if not self._is_valid_filename(self.new_config_name):
            is_name_valid = False
            self.parent_viewer.show_error_popup("Invalid configuration name", "This name is not suitable for use as a filename, please choose a different one.")

        if self.parent_viewer.cache.is_cached_filename_already_defined(self.new_config_name):
            is_name_valid = False
            self.parent_viewer.show_error_popup("Invalid configuration name", "This name already exists, please choose a different one.")

        if is_name_valid:
            self.accept()

    @property
    def new_config_name(self):
        return self.config_name_editor.text()



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
                                [0, 0, 0, 1]]).T
        elif rot_axis == 'y':
            rotmat = np.array([ [np.cos(theta), 0, np.sin(theta), 0],
                                [0, 1, 0, 0],
                                [-np.sin(theta), 0, np.cos(theta), 0],
                                [0, 0, 0, 1]]).T
        elif rot_axis == 'z':
            rotmat = np.array([ [np.cos(theta), -np.sin(theta), 0, 0],
                                [np.sin(theta), np.cos(theta), 0, 0],
                                [0, 0, 1, 0],
                                [0, 0, 0, 1]]).T
        else:
            raise Exception('Unknown axis of rotation.  Please use x, y, or z.')
        return rotmat

    def translat_mat(self, translation_axis='x', translation_norm=1):
        """ Translation affine transformation matrix. """
        axii = 0 if translation_axis=='x' else 1 if translation_axis=='y' else 2 if translation_axis=='z' else None
        if axii is None:
            raise ValueError('translation_axis must contain x, y, or z characters')
        tmat = np.eye(4)
        tmat[3, axii] = translation_norm
        return tmat


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

def constrain_scaling_along_local_axis(tmat, scale, scaling_axis_index):
    """
    Constrain a 3D affine transformation matrix to apply a specific scaling along the local x/y/z axis.
    Parameters:
        tmat (np.array): 4x4 affine transformation matrix.
        scale (float): The desired scaling factor along the local x-axis.
        scaling_axis_index (int): 0: x 1:y 2:z
    Returns:
        np.array: A new 4x4 transformation matrix with the constrained scaling along the local axis.
    """
    
    # Extract the local x-axis direction from the first column of the matrix (ignoring translation)
    local_x_axis = tmat[:3, 0]
    # Normalize the local x-axis direction
    norm_local_x_axis = local_x_axis / np.linalg.norm(local_x_axis)
    # Apply the desired scaling
    scaled_x_axis = scale * norm_local_x_axis
    # Construct the new transformation matrix with the scaled local x-axis
    constrained_tmat = np.copy(tmat)
    # Replace the first column (local x-axis) with the scaled x-axis
    constrained_tmat[:3, 0] = scaled_x_axis
    return constrained_tmat

# ----- QT misc classes and functions ------

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

    def eval_tmat_before_text_carret(self):
        tr_str_before_text_carret, tr_str_trim_index = self.get_transforms_strs_before_text_caret()
        tmat_before_text_carret = af_tr_from_str.transform_matrix_from_str(
            tr_str_before_text_carret
        )
        return (tmat_before_text_carret, tr_str_trim_index)

    def eval_tmat(self):
        tmat = af_tr_from_str.transform_matrix_from_str(
            self.text()
        )
        return tmat

class AcceptRejectDialog(pyqtw.QDialog):
    def __init__(self, parent=None, title='Title', msg='Msg'):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setGeometry(100 + 1500//2, 100 + 1000//2, 300, 100)

        self.layout = pyqtw.QVBoxLayout()
        self.label = pyqtw.QLabel(msg)
        self.layout.addWidget(self.label)

        # Create a QDialogButtonBox with StandardButtons
        self.buttonBox = pyqtw.QDialogButtonBox(pyqtw.QDialogButtonBox.StandardButton.Ok | pyqtw.QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)  # Connect the accepted signal to the accept slot
        self.buttonBox.rejected.connect(self.reject)  # Connect the rejected signal to the reject slot

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class DynamicallyResizableTreeView(pyqtw.QTreeView):

    resized = pyqtc.pyqtSignal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit() # Emit signal on resize


def uncheck_all_checkboxes_in_qtree_column(model, checkbox_column=0, parent_index=None):
    if parent_index is None:
        parent_index = model.invisibleRootItem()

    row_count = parent_index.rowCount()
    for row in range(row_count):
        item = parent_index.child(row, checkbox_column)
        if item is not None:
            if item.isCheckable():
                item.setCheckState(pyqtc.Qt.CheckState.Unchecked)
        # Recurse into children
        child = parent_index.child(row)
        if child:
            uncheck_all_checkboxes_in_qtree_column(model, checkbox_column, child)


# ----- misc helper functions -----


def recursive_key_finder(nested_dict, target_key='_is_editable'):
    def recursive_search(d, parent_keys=None):
        if parent_keys is None:
            parent_keys = []
        
        found_keys = []
        
        for key, value in d.items():
            current_keys = parent_keys + [key]
            
            if isinstance(value, dict):
                found_keys.extend(recursive_search(value, current_keys))
            
            if key == target_key:
                found_keys.append((parent_keys, d[key])) # returns (nested_keys, value)
        
        return found_keys
    
    return recursive_search(nested_dict)


def get_flipped_atlas_space_convention(space_convention):
    """ Returns a flipped version of space_convention according to https://brainglobe.info/documentation/brainglobe-space/index.html
    space_convention can be
        - a list of axes directions (eg. ['Posterior', 'Left', 'Superior'])
        - a string containing abreviations (eg. 'pls')
    """
    flipped_space_convention = [None]*len(space_convention) # create empty list
    for ii, ax in enumerate(space_convention):

        if ax == "Right" or ax.lower() == 'r':
            flipped_space_convention[ii] = "Left"
        elif ax == "Left" or ax.lower() == 'l':
            flipped_space_convention[ii] = "Right"
        
        elif ax == "Superior" or ax.lower() == 's':
            flipped_space_convention[ii] = "Inferior"
        elif ax == "Inferior" or ax.lower() == 'i':
            flipped_space_convention[ii] = "Superior"
        
        elif ax == "Anterior" or ax.lower() == 'a':
            flipped_space_convention[ii] = "Posterior"
        elif ax == "Posterior" or ax.lower() == 'p':
            flipped_space_convention[ii] = "Anterior"
        
        else:
            raise ValueError(f'{ax} is not a valid space convention axis. See https://brainglobe.info/documentation/brainglobe-space/index.html')
        
    return flipped_space_convention


def object_list_hash(obj_list):
    # Enforce list type
    if not isinstance(obj_list, list):
        obj_list = [obj_list]

    hash_object = hashlib.sha256()
    for obj in obj_list:
        # Convert objects to bytes before hashing
        if isinstance(obj, np.ndarray):
            obj_bytes = obj.tobytes()
        else:
            obj_bytes = str(obj).encode('utf-8')
        # Update hash with bytes
        hash_object.update(obj_bytes)
    # Get the hexadecimal representation of the hash
    hash_value = hash_object.hexdigest()
    return hash_value


def get_nparray_shorthash(nparray):
    if isinstance(nparray, np.ndarray):
        fullhash = hashlib.md5(nparray.tobytes()).digest()
        shorthash = base64.urlsafe_b64encode(fullhash)[:6].decode("utf-8")
        return shorthash
    else:
        return None


def dict_to_path_patched(as_dict):
    """
    --- DEPRICATED in v0.1.1 with trimesh 4.6.12 ---
    See https://github.com/mikedh/trimesh/issues/2303

    TEMPORARY FIX for trimesh < v4.6.12

    Turn a pure dict into a dict containing entity objects that
    can be sent directly to a Path constructor.

    Parameters
    ------------
    as_dict : dict
      Has keys: 'vertices', 'entities'

    Returns
    ------------
    kwargs : dict
      Has keys: 'vertices', 'entities'
    """
    
    # # start kwargs with initial value
    # result = as_dict.copy()
    # # map of constructors
    # loaders = {"Arc": trimesh.path.entities.Arc, "Line": trimesh.path.entities.Line}
    # # pre- allocate entity array
    # entities = [None] * len(as_dict["entities"])
    # # run constructor for dict kwargs
    # for entity_index, entity in enumerate(as_dict["entities"]):
    #     if entity["type"] == 'Line':
    #         entities[entity_index] = loaders[entity["type"]](
    #             points=entity["points"]
    #         )
    #     else:
    #         entities[entity_index] = loaders[entity["type"]](
    #             points=entity["points"], closed=entity["closed"]
    #         )
    # result["entities"] = entities

    warnings.warn('dict_to_path_patched was depricated in v0.1.1, please transition to trimesh\'s built-in dict_to_path (trimesh.path.exchange.misc.dict_to_path).')

    result = trimesh.path.exchange.misc.dict_to_path(as_dict)
    return result


def ensure_mesh_is_a_volume_manifold(mesh):
    """ Ensures that the mesh  """
    is_mesh_valid = lambda mesh: mesh.is_watertight and mesh.is_volume

    if not is_mesh_valid(mesh): # Attempt with trimesh built-in functions first
        mesh_charac_dimension = mesh.bounding_box.extents.max()
        mesh.update_faces(mesh.nondegenerate_faces(height=mesh_charac_dimension * 1e-5))
        mesh.update_faces(mesh.unique_faces())
        mesh.fill_holes()

    if not is_mesh_valid(mesh): # Run meshfix on your mesh if needed
        warnings.warn('Mesh is not valid for boolean operations (not a volume manifold) -> Attempting automatic repair..')
        meshfix = pymeshfix.MeshFix(mesh.vertices, mesh.faces)
        meshfix.repair()
        mesh = trimesh.Trimesh(vertices=meshfix.v, faces=meshfix.f)

        if is_mesh_valid(mesh):
            warnings.warn('Mesh succesfully repaired!')
        else:
            raise ValueError('Mesh could not be automatically repaired')
    
    return mesh


def limit_line_breaks(text):
    """
    Limit consecutive line breaks in multiline strings.
    """
    # Replace sequences of line breaks (with optional spaces) with exactly two line breaks
    return re.sub(r'(\n\s*){3,}', '\n', text)


def nested_dict_formatter(d, indent=0):
    formatted_result = ""

    if isinstance(d, dict):
        formatted_result += '{\n'
        indent += 4
        for i, (key, value) in enumerate(d.items()):
            formatted_result += ' ' * indent + repr(key) + ": "  # Use repr to preserve quotes
            if isinstance(value, (dict, list)):
                formatted_result += nested_dict_formatter(value, indent)  # Recurse for nested structures
            elif isinstance(value, str) and '\n' in value:  # Detect multiline strings
                # Apply the limit_line_breaks function to multiline strings
                limited_value = limit_line_breaks(value)
                formatted_result += '"""\n' + limited_value + '\n' + ' ' * indent + '"""'  # Wrap in triple quotes
            else:
                formatted_result += repr(value)  # Preserve Python types and quotes
            if i < len(d) - 1:
                formatted_result += ','  # Add commas between items
            formatted_result += '\n'
        indent -= 4
        formatted_result += ' ' * indent + '}'

    else:
        formatted_result += repr(d)  # Use repr for simple types

    return formatted_result


# ----- GLviewer overloaded classes + item toggler widget ------

class GlItemsToggler:

    def __init__(self, parent_viewer, gl_view, **kwargs) -> None:
        self.parent_viewer = parent_viewer
        self.gl_view = gl_view
        
        self.model = pyqtg.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Item Name"])

    # --- Required module attributes ---

    def init_dock(self):
        """ Called on GUI setup to add a module dock """
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Viewer Layers', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Set up the list view
        self.gl_layers_editor = pyqtw.QListView()
        self.gl_layers_editor.setSelectionMode(pyqtw.QListView.SelectionMode.NoSelection)
        self.gl_layers_editor.setEditTriggers(pyqtw.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.gl_layers_editor.setModel(self.model)
        self.gl_layers_editor.doubleClicked.connect(self._on_item_double_clicked)
        self.update_list_view()
        self.dock_layout.addWidget(self.gl_layers_editor, 0, 0, 1, 1) # Y, X, w, h
        self.model.itemChanged.connect(self._on_item_changed)

    # --- Module specific attributes ---

    def update_list_view(self):
        """ Updates the list of objects rendered in the viewer """
        self.model.clear()
        for gl_item_name, gl_item in self.gl_view.gl_items_named_dict.items():
            if not gl_item_name.startswith('_'): # Do not show in tree list if starting with underscore
                list_view_item = pyqtg.QStandardItem(gl_item_name)
                list_view_item.setCheckable(True)
                if gl_item.visible():
                    list_view_item.setCheckState(pyqtc.Qt.CheckState.Checked)
                else:
                    list_view_item.setCheckState(pyqtc.Qt.CheckState.Unchecked)

                # Set name to bold if double-clickable item
                if callable(gl_item.double_click_event_func):
                    font = list_view_item.font()
                    font.setBold(True)
                    list_view_item.setFont(font)
                self.model.appendRow(list_view_item)

    def _on_item_changed(self, list_view_item):
        edited_gl_item = self.gl_view.get_gl_item_from_name(list_view_item.text())
        if list_view_item.checkState() == pyqtc.Qt.CheckState.Checked:
            edited_gl_item.show()
        else:
            edited_gl_item.hide()

    def _on_item_double_clicked(self, index):
        item = self.model.itemFromIndex(index)
        glitem_name = item.text()
        if glitem_name in self.gl_view.gl_items_names2double_click_events_dict:
            if self.gl_view.gl_items_names2double_click_events_dict[glitem_name] is not None:
                print(self.gl_view.gl_items_names2double_click_events_dict[glitem_name])
                try:
                    self.gl_view.gl_items_names2double_click_events_dict[glitem_name]()
                except Exception as e:
                    warnings.warn(f'Double click function ({glitem_name}) returned an error:\n\t-> {str(e)}.')


class NamedGLViewWidget(gl.GLViewWidget):

    def __init__(self, parent_viewer, **kwargs):
        self.parent_viewer = parent_viewer
        super().__init__(**kwargs)
        self.gl_items_toggler = GlItemsToggler(parent_viewer=parent_viewer, gl_view=self)

        # --- trs mode -> translate rotate scale ---
        self._trs_mode = None
        self._trs_focussed_widget = None
        self._trs_ogsc_trihedras = []
        self._pressed_spacebar = False

        # Receive keyboard events regardless of which widget has focus
        pyqtw.QApplication.instance().installEventFilter(self)

    # --- translate / rotate / scale modifier keys ---

    def trs_mode_switcher(self, target_mode):
        # Translate
        if target_mode == 'T' or target_mode == pyqtc.Qt.Key.Key_T:
            if self._trs_mode == 'T':
                self._trs_mode = None # reset
            else:
                self._trs_mode = 'T'
        # Rotate
        if target_mode == 'R' or target_mode == pyqtc.Qt.Key.Key_R:
            if self._trs_mode == 'R':
                self._trs_mode = None # reset
            else:
                self._trs_mode = 'R'
        # Scale
        if target_mode == 'S' or target_mode == pyqtc.Qt.Key.Key_S:
            if self._trs_mode == 'S':
                self._trs_mode = None # reset
            else:
                self._trs_mode = 'S'

    def eventFilter(self, obj, event): # TODO update tmat / init sensible trihedra scale / esc -> reset tmat / grab cursor loc (got to next space)
        if event.type() == pyqtc.QEvent.Type.KeyPress:
            pressed_key = event.key()
            if self._trs_mode is not None and pressed_key == pyqtc.Qt.Key.Key_Space: # Pause TRS mode mouse grab start
                self._pressed_spacebar = True
                # Prevent Space from being typed into QLineEdit
                event.accept()
                return True
            
            elif pressed_key in [pyqtc.Qt.Key.Key_T, pyqtc.Qt.Key.Key_R, pyqtc.Qt.Key.Key_S]:
                if self._trs_focussed_widget is None:
                    self._trs_focussed_widget = self.parent_viewer.focusWidget()

                # Only activate if mouse is currently over this GL widget
                if isinstance(self._trs_focussed_widget, StrTransformDescriptiveQLineEdit) and self.underMouse(): # transform qline + hovered viewer
                    if not event.isAutoRepeat():
                        self._pressed_spacebar = False # reset
                        self.trs_mode_switcher(pressed_key)
                        if self._trs_mode is None:
                            self._trs_focussed_widget = None
                            self.delete_scale_accurate_TRS_trihedra()
                        else:
                            editor_tmat = self._trs_focussed_widget.eval_tmat()
                            if editor_tmat is not None:
                                self.add_scale_accurate_TRS_trihedra(editor_tmat)
                            print('TRS mode ON: ', self._trs_mode, self._trs_focussed_widget.text())

                    # Prevent T / R / S from being typed into QLineEdit
                    event.accept()
                    return True

                else:
                    self._trs_focussed_widget = None

        if event.type() == pyqtc.QEvent.Type.KeyRelease:
            released_key = event.key()
            if self._trs_mode is not None and released_key == pyqtc.Qt.Key.Key_Space: # Pause TRS mode mouse grab end
                self._pressed_spacebar = False

        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        if self._pressed_spacebar is False and self._trs_mode is not None:
            pos = event.position()
            x = pos.x()
            y = pos.y()

            editor_tmat = self._trs_focussed_widget.eval_tmat()
            if editor_tmat is not None:
                self.update_scale_accurate_TRS_trihedra(editor_tmat)
                print("TRS", self._trs_mode, self._trs_focussed_widget.text(), "Mouse viewer pos: ", x, y)

            event.accept()

        else: # Normal GLViewWidget mouse handling
            super().mouseMoveEvent(event)

    def add_scale_accurate_TRS_trihedra(self, transform_matrix, line_width=6):
        """ Render an axes trihedra corresponding to a given transform_matrix. Axes length correspond to their actual scale. """
        x_vec = transform_matrix[0, :3]
        y_vec = transform_matrix[1, :3]
        z_vec = transform_matrix[2, :3]
        origin = transform_matrix[3, :3]
        
        x_glaxis = gl.GLLinePlotItem(pos=np.array([origin, origin+x_vec]), width=line_width, color=self.parent_viewer.x_RED, antialias=True, glOptions='translucent')
        y_glaxis = gl.GLLinePlotItem(pos=np.array([origin, origin+y_vec]), width=line_width, color=self.parent_viewer.y_GREEN, antialias=True, glOptions='translucent')
        z_glaxis = gl.GLLinePlotItem(pos=np.array([origin, origin+z_vec]), width=line_width, color=self.parent_viewer.z_BLUE, antialias=True, glOptions='translucent')

        self.delete_scale_accurate_TRS_trihedra()
        self._trs_ogsc_trihedras = [x_glaxis, y_glaxis, z_glaxis]

        self.addItem(x_glaxis, name='_trs trihedra ogsc x axis')
        self.addItem(y_glaxis, name='_trs trihedra ogsc y axis')
        self.addItem(z_glaxis, name='_trs trihedra ogsc z axis')

    def update_scale_accurate_TRS_trihedra(self, transform_matrix):
        x_vec = transform_matrix[0, :3]
        y_vec = transform_matrix[1, :3]
        z_vec = transform_matrix[2, :3]
        origin = transform_matrix[3, :3]
        
        self._trs_ogsc_trihedras[0].setData(pos=np.array([origin, origin+x_vec]))
        self._trs_ogsc_trihedras[1].setData(pos=np.array([origin, origin+y_vec]))
        self._trs_ogsc_trihedras[2].setData(pos=np.array([origin, origin+z_vec]))

    def delete_scale_accurate_TRS_trihedra(self):
        """ Remove all debug trihedras """
        for trihedra_gl_obj in self._trs_ogsc_trihedras:
            self.removeItem(trihedra_gl_obj)
        self._trs_ogsc_trihedras = []

    # ---

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
        self.gl_items_toggler.update_list_view()

    def removeItem(self, item):
        super().removeItem(item)
        self.gl_items_toggler.update_list_view()

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

# ----- Custom Mesh Shader -----
# Src: https://github.com/pyqtgraph/pyqtgraph/discussions/3230

vert_shader = """
    #version 120

    uniform mat4 u_mvp;
    uniform mat3 u_normal;

    attribute vec4 a_position;
    attribute vec3 a_normal;
    attribute vec4 a_color;

    varying vec4 v_color;
    varying vec3 v_normal;

    void main()
    {
        v_normal = normalize(u_normal * a_normal);
        v_color = a_color;
        gl_Position = u_mvp * a_position;
    }
"""
frag_shader = """
    #version 120

    varying vec4 v_color;
    varying vec3 v_normal;

    void main()
    {
        float shade = (v_normal.y + 1.0) * 0.4;
        gl_FragColor = vec4(v_color.rgb * shade, v_color.a);
    }
"""

gl.shaders.Shaders.append(gl.shaders.ShaderProgram('softShade', [
    gl.shaders.VertexShader(vert_shader),
    gl.shaders.FragmentShader(frag_shader),
]))

AVAILABLE_SHADER_NAMES = [name for name in gl.shaders.Shaders[0].names if name is not None]