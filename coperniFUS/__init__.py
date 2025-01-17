# %%

print('Lauching CoperniFUS')

import sys, functools, os, json, pathlib, trimesh, scipy, matplotlib, pickle, shelve, pprint, copy, hashlib, time, h5py, napari, base64, threading, warnings, re
import PyQt6.QtGui as pyqtg
import PyQt6.QtCore as pyqtc
import PyQt6.QtWidgets as pyqtw
from bg_atlasapi.bg_atlas import BrainGlobeAtlas
import brainglobe_atlasapi
from si_prefix import si_format, si_parse
import matplotlib.pyplot as plt
import pyqtgraph.opengl as gl
from pyqtgraph import Qt
import pyqtgraph as pg
from PIL import Image
from stl import mesh
import numpy as np

from coperniFUS.modules import _jsonshelve


def clean_string(string):
    clean_string = ''.join(filter(str.isalnum, string))
    return clean_string


class CachedDataHandler:

    def __init__(self, cache_dir_name='.cachedDir', cached_settings_fname=None):
        self.cache_dir = pathlib.Path.home() / cache_dir_name
        
        # Make cache dir if it does not exists
        self.cache_dir.mkdir(exist_ok=True)

        successful_loading = False

        self.cached_settings_fname = None
        if cached_settings_fname is not None and self.is_cached_filename_existent(cached_settings_fname):
            self.cached_settings_fname = cached_settings_fname
        else:
            # .json file loading trial
            db_cached_fpaths = list(self.cache_dir.glob("*.json"))
            db_cached_fpaths = sorted(db_cached_fpaths, key=lambda x: "latest" not in x.stem) # prioritize files ending with latest
            if len(db_cached_fpaths) > 0:
                self.cached_settings_fname = db_cached_fpaths[0].name
        
        # Try loading cached_settings_fname
        if not successful_loading and self.cached_settings_fname is not None:
            try:
                cached_db = _jsonshelve.FlatShelf(self.cached_settings_fpath)
                with cached_db:
                    _ = dict(cached_db)
                cached_db.close()
                successful_loading = True
            except Exception as e:
                print(f'\nFailed to load .json cached settings file\n{db_cached_fpaths[0]}\n{type(e).__name__}: {str(e)}')

        if not successful_loading: # Creates a new cached database as a default
            self.cached_settings_fname = 'cached_db.json'

        print(f'Cached data file located at {self.cached_settings_fpath}')


    def is_cached_filename_existent(self, cache_fname):
        exists = (self.cache_dir / cache_fname).exists()
        return exists

    @property
    def cached_settings_fpath(self):
        return self.cache_dir / self.cached_settings_fname

    def _attribute_str_id(self, attribute_id):
        if isinstance(attribute_id, str):
            attribute_str_id = attribute_id
        elif isinstance(attribute_id, list):
            attribute_str_id = '.'.join(attribute_id)
        return attribute_str_id

    def set_attr(self, attribute_id, value):
        attribute_str_id = self._attribute_str_id(attribute_id)

        cached_db = _jsonshelve.FlatShelf(self.cached_settings_fpath)
        with cached_db:
            cached_db[attribute_str_id] = value
        cached_db.close()

    def get_attr(self, attribute_id, default_value=None):
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
        
        cached_db = _jsonshelve.FlatShelf(self.cached_settings_fpath)
        with cached_db:
            attributes_keys = list(cached_db.keys())
            attkeys_with_prefix = [attk.replace(attribute_prefix, '') for attk in attributes_keys if attk.startswith(attribute_prefix)]
            attkeys_with_prefix_splitted = [[k for k in attk.split('.') if len(k)>0] for attk in attkeys_with_prefix if len(attk)>0]
        cached_db.close()

        unique_child_names = np.unique([attk[0] for attk in attkeys_with_prefix_splitted])
        return unique_child_names


class AffineTransforms:
    """ Collection of affine transform function (Scale, Translate, Rotate)"""

    def scale_mat(self, scaling_ratio):
        scale_mat = np.eye(4, dtype=float)
        if isinstance(scaling_ratio, int) or isinstance(scaling_ratio, float):
            scale_mat *= scaling_ratio
            scale_mat[-1, -1] = 1
        elif isinstance(scaling_ratio, np.ndarray):
            scale_mat[np.arange(3), np.arange(3)] = scaling_ratio
        return scale_mat
        
    def rot_mat(self, rot_axis='x', theta=0, angular_units='degrees'):
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

# ----- QT misc classes ------

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
    TEMPORARY FIX for trimesh==4.0.1

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
    # start kwargs with initial value
    result = as_dict.copy()
    # map of constructors
    loaders = {"Arc": trimesh.path.entities.Arc, "Line": trimesh.path.entities.Line}
    # pre- allocate entity array
    entities = [None] * len(as_dict["entities"])
    # run constructor for dict kwargs
    for entity_index, entity in enumerate(as_dict["entities"]):
        if entity["type"] == 'Line':
            entities[entity_index] = loaders[entity["type"]](
                points=entity["points"]
            )
        else:
            entities[entity_index] = loaders[entity["type"]](
                points=entity["points"], closed=entity["closed"]
            )
    result["entities"] = entities

    return result


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

    def init_dock(self):
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Viewer Layers', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)
        # self.dock_widget.setContentsMargins(0, 0, 0, 0)
        # self.dock_layout.setContentsMargins(0, 0, 0, 0)

        # Set up the list view
        self.gl_layers_editor = pyqtw.QListView()
        self.gl_layers_editor.setSelectionMode(pyqtw.QListView.SelectionMode.NoSelection)
        self.gl_layers_editor.setModel(self.model)
        self.update_list_view()
        self.dock_layout.addWidget(self.gl_layers_editor, 0, 0, 1, 1) # Y, X, w, h
        self.model.itemChanged.connect(self.on_item_changed)

    def update_list_view(self):
        self.model.clear()
        for gl_item_name, gl_item in self.gl_view.gl_items_named_dict.items():
            list_view_item = pyqtg.QStandardItem(gl_item_name)
            list_view_item.setCheckable(True)
            if gl_item.visible():
                list_view_item.setCheckState(pyqtc.Qt.CheckState.Checked)
            else:
                list_view_item.setCheckState(pyqtc.Qt.CheckState.Unchecked)
            self.model.appendRow(list_view_item)

    def on_item_changed(self, list_view_item):
        edited_gl_item = self.gl_view.get_gl_item_from_name(list_view_item.text())
        if list_view_item.checkState() == pyqtc.Qt.CheckState.Checked:
            edited_gl_item.show()
        else:
            edited_gl_item.hide()


class NamedGLViewWidget(gl.GLViewWidget):

    def __init__(self, parent_viewer, **kwargs):
        self.parent_viewer = parent_viewer
        super().__init__(**kwargs)
        self.gl_items_toggler = GlItemsToggler(parent_viewer=parent_viewer, gl_view=self)

    def get_safe_gl_item_name(self, name, existing_names):
        safe_name = copy.deepcopy(name)

        # Increment suffix until an unused name is found
        suffix_index = 1
        while safe_name in existing_names:
            safe_name = f'{copy.deepcopy(name)} {suffix_index}'
            suffix_index += 1

        return safe_name

    def addItem(self, item, name=None):
        """ addItem overloaded with the handling of a gl_item name attribute + GlItemsToggler """
        existing_names = self.gl_items_names

        if name is None:
            name = f'{item.__class__.__name__}_{id(item)}'
        item.name = self.get_safe_gl_item_name(name, existing_names)
        
        super().addItem(item)
        self.gl_items_toggler.update_list_view()

    def removeItem(self, item):
        super().removeItem(item)
        self.gl_items_toggler.update_list_view()

    @property
    def gl_items_names(self):
        return [gl_item.name for gl_item in self.parent_viewer.gl_view.items]
    
    @property
    def gl_items_named_dict(self):
        return {gl_item.name: gl_item for gl_item in self.parent_viewer.gl_view.items}
    
    def get_gl_item_from_name(self, gl_item_name):
        name2item_dict = self.gl_items_named_dict
        if gl_item_name in name2item_dict:
            return name2item_dict[gl_item_name]
        else:
            return None

# ----- Custom Mesh Shaders -----
# Src: https://stackoverflow.com/a/68989314/9645937

gl.shaders.Shaders.append(gl.shaders.ShaderProgram('boneShader', [
    gl.shaders.VertexShader("""
            varying vec3 normal;
            void main() {
                // compute here for use in fragment shader
                normal = normalize(gl_NormalMatrix * gl_Normal);
                gl_FrontColor = gl_Color;
                gl_BackColor = gl_Color;
                gl_Position = ftransform();
            }
        """),
    gl.shaders.FragmentShader("""
            varying vec3 normal;
            void main() {
                vec4 color = gl_Color;
                color.x = (normal.y + 1.0) * 0.972 * .4;
                color.y = (normal.y + 1.0) * 0.760 * .4;
                color.z = (normal.y + 1.0) * 0.568 * .4;
                color.w = 0.8;
                gl_FragColor = color;
            }
        """)
]))

gl.shaders.Shaders.append(gl.shaders.ShaderProgram('bwShader', [
    gl.shaders.VertexShader("""
            varying vec3 normal;
            void main() {
                // compute here for use in fragment shader
                normal = normalize(gl_NormalMatrix * gl_Normal);
                gl_FrontColor = gl_Color;
                gl_BackColor = gl_Color;
                gl_Position = ftransform();
            }
        """),
    gl.shaders.FragmentShader("""
            varying vec3 normal;
            void main() {
                vec4 color = gl_Color;
                color.x = (normal.y + 1.0) * .4;
                color.y = (normal.y + 1.0) * .4;
                color.z = (normal.y + 1.0) * .4;
                color.w = 0.8;
                gl_FragColor = color;
            }
        """)
]))