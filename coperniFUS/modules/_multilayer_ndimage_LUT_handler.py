from coperniFUS import *
import pyqtgraph as pg
import json

class MultiLayerNDImageLUT(object):

    def __init__(self, parent_viewer, ndimage_name='Multi-layer ndimage'):
        self.parent_viewer = parent_viewer
        self.ndimage_name = ndimage_name
        self._layers = None
        self._init_attributes()
        self._init_LUT_editor_floating_dock()

    def _init_attributes(self):
        self._raw_rgba_ndimage_compound = None
        self._rgba_ndimage_compound = None
        self._ndimage_tmat = None
        self._voxel_coordinates = None
        self._ndimage_plane_slicing_application_mask = None
        self._slicing_plane_mask = None
        self._ndimage_params_hash = None # keeps track of modification to ndimage data to prevent useless computation of rgba values
        self._tmat_version_hash = None
        self.ndimage_glvol = None

    @property
    def ndimage_tmat(self):
        if self._ndimage_tmat is None:
            self._ndimage_tmat = np.eye(4)
        return self._ndimage_tmat

    @ndimage_tmat.setter
    def ndimage_tmat(self, value):
        if value is not None:
            if value.shape != (4, 4):
                raise ValueError('Transformation matrix should be of shape (4, 4)')
        self._ndimage_tmat = value

    @property 
    def voxel_coordinates(self):
        """ Holds the coordinates of the ndimage voxels """
        # Check if tmat has changed since last update
        if self._tmat_version_hash != object_list_hash([self.ndimage_tmat]):
            self._voxel_coordinates = None # Recompute if it has changed
        if self._voxel_coordinates is None:
            ndimage_shape = self.raw_rgba_ndimage_compound.shape[:-1]
            voxel_coords = np.mgrid[tuple(slice(0, n) for n in ndimage_shape)]
            raveled_coords = voxel_coords.reshape(len(ndimage_shape), -1).T

            # Apply ndimage spatial transformations
            self._update_transform()
            raveled_coords_4by = np.vstack([raveled_coords.T, np.ones(len(raveled_coords))]).T
            transformed_coords = raveled_coords_4by @ self.ndimage_tmat
            self._voxel_coordinates = transformed_coords[:, :3]
            self._tmat_version_hash = object_list_hash([self.ndimage_tmat])
        return self._voxel_coordinates
    
    @voxel_coordinates.setter
    def voxel_coordinates(self, value):
        self._voxel_coordinates = value

    @property
    def layers(self):
        """ MultiLayerNDImageLUT layer dict, keys starting with an underscore corresponds to large data that will be omitted in the version saved in cache. Make sure than other keys only contain jsonable data.
        
        General dict structure:
        'layer_name': {'ndimage': data, OR 'ndimage_from_layer_name': 'src_layer_name', OR 'atlas_structure_name' AND 'atlas_structure_hemisphere'}
        """
        if self._layers is None:
            self._layers = {}
        return self._layers

    @layers.setter
    def layers(self, layers_dict: dict):
        """ Holds the MultiLayerNDImageLUT layers to be rendered """
        if layers_dict is None:
            layers_dict = {}
        self._layers = layers_dict

    def _update_layers_lut_presets(self):
        """ save the state of the LUT editor floating dock elements in the layer dict """
        for layer_name, layer in self.layers.items():
            if '_lut_widgets' in layer:
                self.layers[layer_name]['levels_preset'] = layer['_lut_widgets'].getLevels()
                self.layers[layer_name]['lut_preset'] = layer['_lut_widgets'].gradient.saveState()

    @property
    def jsonable_layers_dict(self):
        """ Provides a copy of the layers dict omitting non-jsonable data keys (starting with an underscore) for caching purposes """
        def private_keys_free_dict(d):
            if isinstance(d, dict):
                return {
                    k: private_keys_free_dict(v)
                    for k, v in d.items()
                    if not k.startswith('_')
                }
            else:
                return d
            
        def numpy_obj_serializer(obj):
            if isinstance(obj, (np.integer, np.floating, np.bool_)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            raise TypeError(f"Type {type(obj)} not serializable")

        self._update_layers_lut_presets()
            
        try:
            json_layers = json.dumps(private_keys_free_dict(self.layers), default=numpy_obj_serializer)
        except Exception as e:
            json_layers = "{}"
            raise ValueError(f'Error when attempting to cache jsonable_layers_dict:\n{str(e)}\n\nPlease create an issue on GitHub with the content of the data that needed to be cached:\n{nested_dict_formatter(private_keys_free_dict(self.layers))}')

        return json_layers

    def clear_all_layers(self):
        self.layers = None
        self._clear_LUT_editor_floating_dock()

    def clear_layer(self, layer_name):
        if layer_name not in self.layers:
            raise IndexError('{layer_name} does not exist amongst the layers of this MultiLayerNDImageLUT -> cannot be removed')

        self._remove_lut_editor_from_floating_dock(layer_name)
        _ = self.layers.pop(layer_name)

    def add_new_layer(self, layer_name: str, layer_attributes_dict: dict):

        """ layer_attributes_dict expected format:
            {
                '_visible': bool, # start with underscore -> not stored in (json) cache

                # LUT settings
                'lut_preset': {
                    'mode': 'rgb',
                    'ticksVisible': True,
                    'ticks': [
                        [0.0, [0, 0, 0, 0]],
                        [0.05, [0, 0, 0, 0]],
                        [0.06, [25, 25, 25, 20]],
                        [1.0, [255, 255, 255, 20]]]
                },
                'levels_preset': [0, 255],

                # Plane slicing -> if true: voxel_coordinates
                'skip_plane_slicing': False,

                # Optinal attributes
                # eg bgatlas base layer
                'ref_altas_name': 'whs_sd_rat_39um',
                # eg bgatlas brain structures
                'atlas_structure_hemisphere': 'Right Hemisphere',
                'ndimage_from_layer_name': 'Reference Atlas',
            }
        """
        self.layers[layer_name] = layer_attributes_dict
        self._add_LUT_editor_to_floating_dock(layer_name) # TODO check
        self._on_layers_update()

    # --- ndimage data ---

    def _get_layer_ndimage_data(self, layer_name, apply_mask=True):
            """
            layers: dictionary of all the layers
            layer_name: dict key of the layer from which ndimage data has to be retreived
            """
    
            if '_ndimage_data' in self.layers[layer_name]:
                ndimage_data = self.layers[layer_name]['_ndimage_data']
            
            if apply_mask is True:
                raise NotImplementedError # see multilayer atlas subclass for ref
    
            return ndimage_data
    
    # --- Plane slicing ---

    @property
    def ndimage_plane_slicing_application_mask(self):
        """ Holds a boolean mask indicating the voxels where plane slicing is ignored """
        if self._ndimage_plane_slicing_application_mask is None:
            self._ndimage_plane_slicing_application_mask = np.ones(self.raw_rgba_ndimage_compound.shape[:3], dtype=bool)
        return self._ndimage_plane_slicing_application_mask

    def _compute_slicing_plane(self):
        """ Computes a binary mask based on the slicing plane location and hides (opacity=0) voxels affected by the slicing """
        slicing_plane_pts = self.parent_viewer.slicing_plane_3pts
        if slicing_plane_pts is not None:
            if not self.parent_viewer._postpone_slicing_plane_computation or self._slicing_plane_mask is None:
                raveled_mask = np.dot(
                    self.voxel_coordinates - slicing_plane_pts[0],
                    np.cross(
                        slicing_plane_pts[1] - slicing_plane_pts[0],
                        slicing_plane_pts[2] - slicing_plane_pts[0]
                    )) < 0
                
                self._slicing_plane_mask = np.logical_and(
                    raveled_mask.reshape(self.ndimage_plane_slicing_application_mask.shape),
                    self.ndimage_plane_slicing_application_mask
                )

            self._rgba_ndimage_compound[self._slicing_plane_mask, 3] = 0

    # --- rgba from LUT ---

    @property
    def raw_rgba_ndimage_compound(self):
        """ Holds the RGBA n-dimension image of the compounded layers before plane slicing operations (raw) """

        def apply_plane_slicing_on_layer(layer):
            apply_plane_slicing = not layer['skip_plane_slicing'] if 'skip_plane_slicing' in layer else False
            return apply_plane_slicing
        
        def layer_visible(layer):
            visible = layer['_visible'] if '_visible' in layer else True
            return visible

        # Compute if undefined or _ndimage_params_hash has changed
        if self._raw_rgba_ndimage_compound is None or self._raw_rgba_ndimage_compound[0] != self._ndimage_params_hash:

            base_layer_name = list(self.layers.keys())[0]
            layer = self.layers[base_layer_name]

            # Get ndimage data
            ndimage_data = self._get_layer_ndimage_data(base_layer_name, apply_mask=False)

            # Evaluate plane slicing binary mask for layer
            self._ndimage_plane_slicing_application_mask = apply_plane_slicing_on_layer(layer) * np.ones(ndimage_data.shape[:3], dtype=bool)
            
            # Get LUT from widget
            lut = layer['_lut_widgets'].item.getLookupTable(n=256, alpha=True)
            levels = layer['_lut_widgets'].item.getLevels()

            # Compute rgba ndimage
            _raw_rgba_ndimage_compound = self._apply_lut_to_ndimage(ndimage_data, lut, levels)
            if not layer_visible(layer):
                _raw_rgba_ndimage_compound[..., 3] = 0 # Make fully transparent

            for layer_ii, (layer_name, layer) in enumerate(self.layers.items()):
                if layer_ii > 0 and layer_visible(layer): # Skip base layer -> already processed AND invisible layers
                    # Get ndimage data
                    ndimage_data = self._get_layer_ndimage_data(layer_name, apply_mask=True)

                    # Get LUT from widget
                    lut = layer['_lut_widgets'].item.getLookupTable(n=256, alpha=True)
                    levels = layer['_lut_widgets'].item.getLevels()

                    # Compute rgba ndimage
                    rgba_ndimage = self._apply_lut_to_ndimage(ndimage_data, lut, levels)

                    if '_ndimage_mask' in layer:
                        _raw_rgba_ndimage_compound[layer['_ndimage_mask']] = self._alpha_blend(
                            _raw_rgba_ndimage_compound[layer['_ndimage_mask']], rgba_ndimage
                        )

                        # Evaluate plane slicing binary mask for layer
                        self._ndimage_plane_slicing_application_mask[layer['_ndimage_mask']] = apply_plane_slicing_on_layer(layer)

                    else:
                        _raw_rgba_ndimage_compound = self._alpha_blend(_raw_rgba_ndimage_compound, rgba_ndimage)

                        # Evaluate plane slicing binary mask for layer
                        self._ndimage_plane_slicing_application_mask = np.logical_and(
                            self._ndimage_plane_slicing_application_mask,
                            apply_plane_slicing_on_layer(layer) * np.ones(ndimage_data.shape[:3], dtype=bool)
                        )

            self._raw_rgba_ndimage_compound = (self._ndimage_params_hash, _raw_rgba_ndimage_compound)

        return self._raw_rgba_ndimage_compound[1]
    
    @property
    def rgba_ndimage_compound(self):
        """ Holds the RGBA n-dimension image of the compounded layers with plane slicing applied """
        self._rgba_ndimage_compound = self.raw_rgba_ndimage_compound.copy()
        self._compute_slicing_plane()

        return self._rgba_ndimage_compound

    def _apply_lut_to_ndimage(self, ndimage_data, lut, levels):
        """ Converts ndimage data to ndim RGBA based on a lookup table (LUT) """
        # Normalize data to levels
        min_val, max_val = levels
        scaled = np.clip((ndimage_data - min_val) / (max_val - min_val), 0, 1)
        indices = (scaled * (len(lut) - 1)).astype(np.ubyte)
        rgba = lut[indices]  # shape: (..., 4)
        return rgba

    def _alpha_blend(self, background, foreground):
        """
        Alpha blending of two N-dimensional uint8 RGBA images.

        Parameters:
            Foreground ndim image (..., 4), dtype=uint8
            Background ndim image (..., 4), dtype=uint8

        Returns:
            Blended RGBA ndim image, dtype=uint8
        """
        foreground_rgb = foreground[..., :3].astype(np.uint16)
        foreground_a = foreground[..., 3:4].astype(np.uint16)

        background_rgb = background[..., :3].astype(np.uint16)
        background_a = background[..., 3:4].astype(np.uint16)

        out_rgb = (foreground_rgb * foreground_a + background_rgb * (255 - foreground_a)) // 255
        out_a = foreground_a + (background_a * (255 - foreground_a)) // 255

        out = np.concatenate((out_rgb, out_a), axis=-1).astype(np.uint8)
        return out

    def _get_grayscale_lut_preset(self):
        lut_state = {
            'mode': 'rgb',
            'ticks': [
                (0.0, (0, 0, 0, 0)),
                (1.0, (255, 255, 255, 255)),
            ],
            'ticksVisible': True
        }
        return lut_state

    # --- Floating LUT editor dock ---

    def _init_LUT_editor_floating_dock(self):
        # Create dock widget
        self.lut_editor_dock = pyqtw.QDockWidget(f"{self.ndimage_name} LUT editor", self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.BottomDockWidgetArea, self.lut_editor_dock)
        self.lut_editor_dock.setFloating(True)  # Make it detached/floating
        self.lut_editor_dock.move(50, 50)  # Set default location
        self.lut_editor_dock.setAllowedAreas(pyqtc.Qt.DockWidgetArea.NoDockWidgetArea)
        self.lut_editor_dock.setMinimumWidth(500)
        self.lut_editor_dock.hide() # Hidden by default

        self.lut_editor_dock.setStyleSheet("""
            QDockWidget {
                background-color: black;
                color: white;
            }
        """)

        self.lut_editor_dock_widget = pyqtw.QWidget(self.lut_editor_dock)
        self.lut_editor_dock.setWidget(self.lut_editor_dock_widget)
        self.lut_editor_dock_layout = pyqtw.QGridLayout()
        self.lut_editor_dock_widget.setLayout(self.lut_editor_dock_layout)
        # self.atlas_layers_tree_view.doubleClicked.connect(self._show_LUT_editor_floating_dock) # TODO set double click action to viewer layer tree view

    def _show_LUT_editor_floating_dock(self):
        self.lut_editor_dock.show()

    def _clear_LUT_editor_floating_dock(self):
            
        def clear_grid_layout(layout):
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                elif item.layout() is not None:
                    clear_grid_layout(item.layout()) # Recursively clear nested layouts

        clear_grid_layout(self.lut_editor_dock_layout)

    def _add_LUT_editor_to_floating_dock(self, layer_name):
        if not layer_name in self.layers:
            raise ValueError(f'{layer_name} not in layers')
        layer = self.layers[layer_name]
        
        # Create HistogramLUTWidget objects
        layer['_lut_widgets'] = pg.HistogramLUTWidget(orientation='horizontal', fillHistogram=False)

        # Set HistogramLUTWidget with a dummy image with proper dynamic range for LUT control
        ndimage_data = self._get_layer_ndimage_data(layer_name, apply_mask=False)
        data_min, data_max = np.min(ndimage_data), np.max(ndimage_data)
        _dummy_img = pg.ImageItem(np.array([[data_min], [data_max]]), dtype=np.ubyte)
        layer['_lut_widgets'].setImageItem(_dummy_img)

        # Set layer name as axis label
        layer['_lut_widgets'].setFixedHeight(100)
        layer['_lut_widgets'].item.layout.itemAt(0).setLabel(layer_name)
        layer['_lut_widgets'].setFixedHeight(120)

        try:
            layer['_lut_widgets'].setLevels(*layer['levels_preset'])
            layer['_lut_widgets'].gradient.restoreState(layer['lut_preset'])
        except Exception as e:
            warnings.warn(f'lut_widgets could not be populated with cached values -> skipping\n{str(e)}')

        # Add widgets to GUI and connect signals
        self.lut_editor_dock_layout.addWidget(layer['_lut_widgets'])
        layer['_lut_widgets'].item.sigLookupTableChanged.connect(self._on_layers_update)
        layer['_lut_widgets'].item.sigLevelsChanged.connect(self._on_layers_update)

    def _remove_lut_editor_from_floating_dock(self, layer_name):
        if not layer_name in self.layers:
            raise ValueError(f'{layer_name} not in layers')
        layer = self.layers[layer_name]

        layer['_lut_widgets'].deleteLater()

    def _on_layers_update(self):
        """ Callback to update RGBA volume on LUT edition """

        self._raw_rgba_ndimage_compound = None # reset
        if self.ndimage_glvol is not None:
            self.ndimage_glvol.setData(self.rgba_ndimage_compound)

    def _update_transform(self):
        self.ndimage_tmat = None
        self.voxel_coordinates = None # Reset voxels coordinates
        if self.ndimage_glvol is not None:
            self.ndimage_glvol.resetTransform()
            self.ndimage_glvol.applyTransform(pyqtg.QMatrix4x4(self.ndimage_tmat.ravel()), local=False)

    # add / rm / update globj

    def add_rendered_object(self):
        """ Called when populating the viewer with the rendered objects """
        self.delete_rendered_object()

        self.ndimage_glvol = gl.GLVolumeItem(self.rgba_ndimage_compound, smooth=True, glOptions='translucent')
        self.parent_viewer.gl_view.addItem(self.ndimage_glvol, name=self.ndimage_name, double_click_event_func=self._show_LUT_editor_floating_dock)
        self.ndimage_glvol.setDepthValue(1) # GL volumes -> render tree foreground

        self._update_transform()

    def update_rendered_object(self):
        """ Called on render view updates """
        if self.ndimage_glvol is not None:
            self._update_transform()
            self.ndimage_glvol.setData(self.rgba_ndimage_compound)

    def delete_rendered_object(self):
        """ Called on deletion of the module rendered objects """
        if self.ndimage_glvol in self.parent_viewer.gl_view.items:
            self.parent_viewer.gl_view.removeItem(self.ndimage_glvol)
            self.ndimage_glvol = None
