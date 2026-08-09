from brainglobe_atlasapi.bg_atlas import BrainGlobeAtlas
import brainglobe_space as bgs
import brainglobe_atlasapi
import matplotlib.pyplot as plt
import pyqtgraph as pg
import functools, json

from coperniFUS import *
from coperniFUS.modules.module_base import Module
from coperniFUS.modules._multilayer_ndimage_LUT_handler import MultiLayerNDImageLUT

# Worker thread
class AsynchronousOnlineAtlasListRetrieval(pyqtc.QThread):
    """ Handles network issues when retrieving online atlas lists. """
    
    finished = pyqtc.pyqtSignal()
    """ Signal emitted whenever the atlas retreival is done (or has failed). """

    def __init__(self, skip_online_atlas_retreival):
        super().__init__()
        self.skip_online_atlas_retreival = skip_online_atlas_retreival
        self.formatted_online_atlases = None

    def run(self):
        if self.skip_online_atlas_retreival:
            self.formatted_online_atlases = {
                None: 'Offline mode -> Showing downloaded atlases only'
            }
        else:
            try:
                online_atlases = brainglobe_atlasapi.list_atlases.get_all_atlases_lastversions()
                online_atlases_names = list(online_atlases.keys())
                online_atlases_versions = list(online_atlases.values())

                self.formatted_online_atlases = {
                    f'online_{atlas_name}': f'{atlas_name} | v{online_atlases_versions[ii]} (online)'
                    for (ii, atlas_name) in enumerate(online_atlases_names)
                }
            except Exception as e:
                print(f'> Could not proceed with online altas retrieval: {type(e).__name__}: {str(e)}\nBrainGlobe Atlas API servers could not be reached..\nEnsure that your internet connection works properly and run "brainglobe list" in a terminal.\nIf you do not have any atlases installed locally you can install one using "brainglobe install -a <atlas_name>"')
                self.formatted_online_atlases = {
                    None: 'Online atlas retrieval has failed -> Showing downloaded atlases only'
                }
        self.finished.emit()


class BrainAtlasMultiLayerNDImageLUT(MultiLayerNDImageLUT):

    _CYCLIC_STRUCTURES_COLORS = [tuple([int(255*cc) for cc in plt.get_cmap('Set1')(ii)]) for ii in range(5)]

    def __init__(self, parent_viewer, parent_brainatlas_module, ndimage_name='Multi-layer ndimage', **kwargs):
        super().__init__(parent_viewer, ndimage_name, **kwargs)
        self.parent_brainatlas_module = parent_brainatlas_module

    @property
    def ndimage_tmat(self):
        return self.parent_brainatlas_module.brain_atlas_tmat

    @ndimage_tmat.setter
    def ndimage_tmat(self, value):
        if value is not None:
            if value.shape != (4, 4):
                raise ValueError('Transformation matrix should be of shape (4, 4)')
        self.parent_brainatlas_module.brain_atlas_tmat = value

    def _on_layers_update(self):
        super()._on_layers_update()
        self.parent_brainatlas_module._save_layers_state_to_cache()

    def _get_layer_ndimage_data(self, layer_name, apply_mask=True):
        """
        layers: dictionary of all the layers
        layer_name: dict key of the layer from which ndimage data has to be retreived
        All layers should contain either 'ref_altas_name' or 'ndimage_from_layer_name' fields referencing ndimage data
        """
        subs_stride = self.parent_brainatlas_module.get_user_param('subsampling_stride', default_value=self.parent_brainatlas_module._default_subsampling_stride)

        if '_ndimage_data' in self.layers[layer_name] and '_subs_stride' in self.layers[layer_name] and self.layers[layer_name]['_subs_stride'] == subs_stride:
            ndimage_data = self.layers[layer_name]['_ndimage_data']
        else: # Evaluate data content if '_ndimage_data' not in dict
            if 'ref_altas_name' in self.layers[layer_name]:
                ndimage_data = self.parent_brainatlas_module._reference_atlas_ndimage_data(self.layers[layer_name]['ref_altas_name'], subsampling_stride=subs_stride)
            elif 'ndimage_from_layer_name'in self.layers[layer_name]:
                ndimage_data = self._get_layer_ndimage_data(self.layers[layer_name]['ndimage_from_layer_name'], apply_mask=False)
            else:
                raise ValueError(f'ndimage data reference not provided in layer {layer_name}')

            # Store in dict for future use
            self.layers[layer_name]['_ndimage_data'] = ndimage_data
            self.layers[layer_name]['_subs_stride'] = subs_stride
        
        if apply_mask is True and ('atlas_structure_name' in self.layers[layer_name] or 'atlas_structure_hemisphere' in self.layers[layer_name] or '_ndimage_mask' in self.layers[layer_name]):
            if '_ndimage_mask' in self.layers[layer_name] and '_mask_subs_stride' in self.layers[layer_name] and self.layers[layer_name]['_mask_subs_stride'] == subs_stride:
                ndimage_mask = self.layers[layer_name]['_ndimage_mask']
            else: # Evaluate mask data content if '_ndimage_mask' not in dict
                if 'atlas_structure_name' in self.layers[layer_name] and 'atlas_structure_hemisphere' in self.layers[layer_name]:
                    ndimage_mask = self.parent_brainatlas_module._get_struct_mask(
                        self.layers[layer_name]['atlas_structure_name'],
                        self.layers[layer_name]['atlas_structure_hemisphere'],
                        subsampling_stride=subs_stride
                    )
                else:
                    raise ValueError(f'_ndimage_mask or atlas_structure_name/atlas_structure_hemisphere not provided in layer {layer_name}')

            # Store in dict for future use
            self.layers[layer_name]['_ndimage_mask'] = ndimage_mask
            self.layers[layer_name]['_mask_subs_stride'] = subs_stride
            
            ndimage_data = ndimage_data[ndimage_mask] # Apply mask

        return ndimage_data

    def _get_highlighted_structure_lut_preset(self, structure_index=0):
        rgb_color = self._CYCLIC_STRUCTURES_COLORS[structure_index%len(self._CYCLIC_STRUCTURES_COLORS)][:3]
        lut_state = {
            'mode': 'rgb',
            'ticks': [
                (0.0, (*rgb_color, 0)),
                (0.5, (*rgb_color, 255))],
            'ticksVisible': True
        }
        return lut_state

    def _get_ref_atlas_lut_preset(self):
        ALTAS_OPACITY = 20
        lut_state = {
            'mode': 'rgb',
            'ticks': [
                (0.0, (0, 0, 0, 0)),
                (0.05, (0, 0, 0, 0)),
                (0.06, (25, 25, 25, ALTAS_OPACITY)),
                (1.0, (255, 255, 255, ALTAS_OPACITY)),
            ],
            'ticksVisible': True
        }
        return lut_state


class BrainAtlas(Module):

    """
    BrainAtlas module.
    """

    _DEFAULT_N_VOXELS = 1e6 # target number of voxels for default atlas subsampling stride computation
    _DEFAULT_PARAMS = {
        'jsonable_layers_dict': "{}",
        'atlas_transforms_str' : 'Rx0deg Tz0um',
        'subsampling_stride': 10,
    }
    """ Default configuration parameters used when a parameter value is not yet cached """

    def __init__(self, parent_viewer, skip_online_atlas_retreival=False, **kwargs) -> None:
        super().__init__(parent_viewer, 'atlas', **kwargs)

        self.atlas_ml_ndimg = BrainAtlasMultiLayerNDImageLUT(
            parent_viewer=parent_viewer,
            parent_brainatlas_module=self,
            ndimage_name='Brain Atlas',
        )
        # init layers with cached user preferences
        self.atlas_ml_ndimg.layers = json.loads(self.parent_viewer.cache.get_attr(
            'atlas.jsonable_layers_dict', default_value=self._DEFAULT_PARAMS['jsonable_layers_dict']
        ))
 
        self.skip_online_atlas_retreival = skip_online_atlas_retreival
        self._init_attributes()

        self._formatted_online_atlases = {
            None: 'Retrieving atlases available online...'
        }
        self.async_online_altas_list_handler = AsynchronousOnlineAtlasListRetrieval(skip_online_atlas_retreival)
        self.async_online_altas_list_handler.finished.connect(self._update_atlas_selector)
        self.async_online_altas_list_handler.start()
        self.parent_viewer.statusBar().showMessage('Loading online atlas list')

    def _init_attributes(self):
        self.atlas_ml_ndimg._init_attributes()
        self._loaded_structure_mask = {}
        self._tooltip_to_layer_centroid = None
        self._available_atlases = None
        self._brain_atlas_tmat = None
        self._bg_atlas = None
        self.bg_atlas_structures = {'Select Structure': None}

    # --- Module specific public attributes ---

    @property
    def atlas_resolution(self):
        """ Resultion of the reference altas in meters (x, y, z)
            Suplampling is accounted for in the returned value. """
        subs_stride = self.get_user_param('subsampling_stride', default_value=self._default_subsampling_stride)
        atlas_res = subs_stride * np.array(self.bg_atlas.resolution) * 1e-6 # um to meters
        return atlas_res
    
    @property
    def brain_atlas_tmat(self):
        """ Holds the atlas volume affine transformation matrix """
        if self._brain_atlas_tmat is None:
            resolution = self.atlas_resolution
            atlas_shape = self.atlas_ml_ndimg.raw_rgba_ndimage_compound.shape

            # Axes ordering correction
            source_space = bgs.AnatomicalSpace(self.bg_atlas.orientation, shape=atlas_shape[:3])
            target_space = bgs.AnatomicalSpace(get_flipped_atlas_space_convention(self.parent_viewer.ATLAS_SPACE_CONVENTION))
            axes_order_idx = source_space.map_to(target_space)[0]
            space_conversion_tmat = source_space.transformation_matrix_to(target_space)
            self._brain_atlas_tmat = space_conversion_tmat.T

            # Setting atlas scale based on resolution
            self._brain_atlas_tmat = self._brain_atlas_tmat @ af_tr.scale_mat(resolution)

            # Img space origin to atlas center
            self._brain_atlas_tmat = self._brain_atlas_tmat @ af_tr.translat_mat('x', -(resolution[0] * atlas_shape[axes_order_idx[0]]) / 2)
            self._brain_atlas_tmat = self._brain_atlas_tmat @ af_tr.translat_mat('y', -(resolution[1] * atlas_shape[axes_order_idx[1]]) / 2)
            self._brain_atlas_tmat = self._brain_atlas_tmat @ af_tr.translat_mat('z', -(resolution[2] * atlas_shape[axes_order_idx[2]]) / 2)

            atlas_transforms_matrices = af_tr_from_str.transform_matrices_from_str(
                self.get_user_param('atlas_transforms_str')
            )

            for tr_mat in atlas_transforms_matrices:
                self._brain_atlas_tmat = self._brain_atlas_tmat @ tr_mat
        
        # Apply anatomical landmark calibration transformation
        anatomically_calibrated_brain_atlas_tmat = self._brain_atlas_tmat @ self.parent_viewer.anat_calib.landmarks_calib_tmat
        
        return anatomically_calibrated_brain_atlas_tmat
    
    @brain_atlas_tmat.setter
    def brain_atlas_tmat(self, value):
        if value is not None:
            if value.shape != (4, 4):
                raise ValueError('Transformation matrix should be of shape (4, 4)')
        self._brain_atlas_tmat = value

    @property
    def bg_atlas(self):
        """ Holds the Brain Globe instance currently loaded in the module """
        if self._bg_atlas is None:
            if 'Reference Atlas' in self.atlas_ml_ndimg.layers:
                if 'ref_altas_name' not in self.atlas_ml_ndimg.layers['Reference Atlas']:
                    raise ValueError('"ref_altas_name" missing in "Reference Atlas" layer')
                
                offline_atlas_name = self.atlas_ml_ndimg.layers['Reference Atlas']['ref_altas_name']

                if offline_atlas_name not in brainglobe_atlasapi.list_atlases.get_downloaded_atlases():
                    raise ValueError(f'This atlas is not available locally.\n Run\n\tbrainglobe install -a {offline_atlas_name}\nin a Terminal to do so.\nRestart CoperniFUS once the download is complete.')
                
                self._init_attributes()
                self._bg_atlas = BrainGlobeAtlas(offline_atlas_name, check_latest=False)
        
        return self._bg_atlas

    @property
    def available_atlases(self):
        """ Get a list of all (online and offline) available atlases in the dictionary form """
        if self._available_atlases is None:
            self._offline_atlases_names = brainglobe_atlasapi.list_atlases.get_downloaded_atlases()
            formatted_offline_atlases = {
                f'offline_{atlas_name}': f'{atlas_name} | v{brainglobe_atlasapi.list_atlases.get_local_atlas_version(atlas_name)} (DOWNLOADED)'
                for (ii, atlas_name) in enumerate(self._offline_atlases_names)
            }

            if self.async_online_altas_list_handler.formatted_online_atlases is not None:
                self._formatted_online_atlases = self.async_online_altas_list_handler.formatted_online_atlases

            self._available_atlases = {
                'no_atlas': 'Select Atlas',
                **formatted_offline_atlases,
                **self._formatted_online_atlases
            }
        return self._available_atlases
    
    @available_atlases.setter
    def available_atlases(self, value):
        self._available_atlases = value

    def add_reference_atlas(self, offline_atlas_name):
        """ Add a reference atlas to the module """
        if offline_atlas_name not in brainglobe_atlasapi.list_atlases.get_downloaded_atlases():
            raise ValueError(f'This atlas is not available locally.\n Run\n\tbrainglobe install -a {offline_atlas_name}\nin a Terminal to do so.\nRestart CoperniFUS once the download is complete.')

        self.remove_reference_atlas()

        ref_atlas_layer_name = 'Reference Atlas'
        self.atlas_ml_ndimg.add_new_layer(
            layer_name=ref_atlas_layer_name,
            layer_attributes_dict={
                '_visible': True,
                'ref_altas_name': offline_atlas_name,
                'lut_preset': self.atlas_ml_ndimg._get_ref_atlas_lut_preset(),
                'levels_preset': (0, 255),
                'skip_plane_slicing': False,
            }
        )
        self._reference_atlas_setup(ref_atlas_layer_name)
        self.add_rendered_object()

    def remove_reference_atlas(self):
        """ Delete the reference atlas currently loaded in the module """
        self.delete_rendered_object()
        self._clear_layers_tree_view()
        self.atlas_ml_ndimg.clear_all_layers()
        self._init_attributes()
        self._save_layers_state_to_cache()

        self._update_atlas_selector()
        self.structure_selector.setEnabled(False)
        self.hemisphere_selector.setEnabled(False)
        self.add_structure_layer_btn.setEnabled(False)
        self.rm_structure_layer_btn.setEnabled(False)

    def add_structure_layer(self, structure, hemisphere):
        """ Add a brain structure layer to the atlas """

        print('add_structure_layer', structure, hemisphere)

        # Catch parameters errors
        if structure not in self.bg_atlas_structures:
            raise ValueError(f'{structure} structure not available for {self.bg_atlas.atlas_name}. Available structures are:\n\t- {"\n\t- ".join(self.bg_atlas_structures.keys())}')
        if hemisphere not in ['Both Hemispheres', 'Left Hemisphere', 'Right Hemisphere']:
            raise ValueError('Invalid hemisphere name -> hemisphere_id has to be either "Both Hemispheres", "Left Hemisphere" or "Right Hemisphere"')
        
        number_of_existing_struture_layers = len([kk for kk, ll in self.atlas_ml_ndimg.layers.items() if 'atlas_structure_name' in ll])
        layer_name = f'{structure} ({hemisphere})'

        layer_name_suffix = 1
        while layer_name in self.atlas_ml_ndimg.layers:
            layer_name = f'{layer_name} {layer_name_suffix}'
            layer_name_suffix += 1

        self.atlas_ml_ndimg.add_new_layer(
            layer_name=layer_name,
            layer_attributes_dict={
                '_visible': True,
                'atlas_structure_name': structure,
                'atlas_structure_hemisphere': hemisphere,
                'ndimage_from_layer_name': 'Reference Atlas',
                'lut_preset': self.atlas_ml_ndimg._get_highlighted_structure_lut_preset(
                    structure_index=number_of_existing_struture_layers
                ),
                'levels_preset': (0, 255),
                'skip_plane_slicing': True,
            }
        )
        self._add_layer_to_layers_tree_view(layer_name)

    def remove_altas_layer(self, layer_name=None, tree_viewer_layer_index=None):
        """ Delete one of the currently loaded brain structure layer from the rendered atlas """
        if layer_name is None:
            if tree_viewer_layer_index is None:
                raise ValueError('Please provide either tree_viewer_layer_index or layer_name.')
            layer_name = self._get_layer_name_by_tree_viewer_layer_index(tree_viewer_layer_index)
            
        if layer_name not in self.atlas_ml_ndimg.layers:
            raise IndexError('{layer_name} not in atlas layers -> cannot be removed')
        
        if layer_name == 'Reference Atlas':
            self.remove_reference_atlas()
        else: # Rm individual structure layer
            self._remove_layer_from_layers_tree_view(layer_name=layer_name)
            self.atlas_ml_ndimg.clear_layer(layer_name)

        self.atlas_ml_ndimg._on_layers_update()
    
    def update_tooltip_to_layer_centroid(self):
        """ Updates the Tooltip location according to the checkbox selection in the module dock """
        if self._tooltip_to_layer_centroid is not None and self._tooltip_to_layer_centroid in self.atlas_ml_ndimg.layers:
            layer = self.atlas_ml_ndimg.layers[self._tooltip_to_layer_centroid]

            # Layer mask retreival
            if '_ndimage_mask' in layer:
                layer_mask = layer['_ndimage_mask']
            else:
                atlas_shape = self.raw_rgba_ndimage_compound.shape[:3]
                layer_mask = np.ones(atlas_shape)
            
            # Get coordinates of all voxels in the structure
            coords = np.argwhere(layer_mask)

            # Convert voxel coordinates to physical space (microns)
            centroid_voxel = coords.mean(axis=0)
            centroid_physical_tmat = np.eye(4)
            centroid_physical_tmat[3, :3] = centroid_voxel
            centroid_physical_tmat = centroid_physical_tmat @ self.brain_atlas_tmat

            # Keep translation component only
            translation_only_centroid_tmat = np.eye(4)
            translation_only_centroid_tmat[3, :3] = centroid_physical_tmat[3, :3]

            # Apply tmat to tooltip
            self.parent_viewer.tooltip.release_from_modules(sender_module=self)
            self.parent_viewer.tooltip.tooltip_tmat = translation_only_centroid_tmat
            
        else: # Tooltip NOT on layer centroid
            self.parent_viewer.tooltip.tooltip_tmat = None
        
        self.parent_viewer.tooltip.update_rendered_object()
            
    def release_tooltip(self):
        """ Releases the tooltip location from the selected location in the module. Please call CoperniFUS viewer release_from_modules method to release the tooltip from all loaded modules. """
        self._tooltip_to_layer_centroid = None
        uncheck_all_checkboxes_in_qtree_column(self.atlas_layers_model, checkbox_column=1)
            
    # --- Required module attributes ---
    
    def init_dock(self):
        """ Called on GUI setup to add a module dock """
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Brain Atlas', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.BottomDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Adding Atlas selector
        self.atlas_selector = pyqtw.QComboBox()
        # self.atlas_selector.setStyleSheet("QComboBox { combobox-popup: 0; }")  # Limit dropdown height
        # self.atlas_selector.setMaxVisibleItems(20) # Limit dropdown height # BUG darkmode interference
        self.dock_layout.addWidget(self.atlas_selector, 0, 0, 1, 2) # Y, X, h, w
        self.atlas_selector.setToolTip('Select a brain atlas for download. Previously downloaded atlases are registered as (DOWNLOADED).<br>You can find detailed descriptions of the available atlases on BrainGlobe\'s documentation.')

        # Subsampling stride editor
        self.subsampling_stride_editor = descriptive_line_edit(str(self._DEFAULT_PARAMS['subsampling_stride']), 'Subsampling')
        self.subsampling_stride_editor.editingFinished.connect(functools.partial(self._parse_editor, self.subsampling_stride_editor, 'subsampling_stride', '', 'int'))
        self.dock_layout.addWidget(self.subsampling_stride_editor, 1, 0, 1, 1) # Y, X, h, w
        self.subsampling_stride_editor.setToolTip('Atlas subsampling stride<br>Use 1 to show the altas in its full resolution, larger strides will however improve performances.')

        # Transform string editor
        self.atlas_transform_editor = descriptive_line_edit(str(self._DEFAULT_PARAMS['atlas_transforms_str']), 'Transform')
        self.atlas_transform_editor.editingFinished.connect(functools.partial(self._parse_editor, self.atlas_transform_editor, 'atlas_transforms_str', '', 'str'))
        self.dock_layout.addWidget(self.atlas_transform_editor, 1, 1, 1, 1) # Y, X, h, w
        self.atlas_transform_editor.setToolTip('STL mesh transformations<br> - S0.5: Apply a 0.5 scaling factor (Use Sx to scale along x)<br> - Ty1mm: 1mm translation along y<br> - Rz90deg: Rotate by 90 degrees around z axis')

        # Altas layers viewer
        self.atlas_layers_tree_view = DynamicallyResizableTreeView()
        self.atlas_layers_tree_view.resized.connect(self._on_tree_view_resize)
        self.atlas_layers_model = pyqtg.QStandardItemModel()
        self.atlas_layers_tree_view.setModel(self.atlas_layers_model)
        self.atlas_layers_model.itemChanged.connect(self._on_layers_tree_view_checkbox_toggle)
        self.dock_layout.addWidget(self.atlas_layers_tree_view, 0, 2, 2, 2) # Y, X, h, w
        self._clear_layers_tree_view()
        self.atlas_layers_tree_view.setToolTip('Altases and any added layer overlays will be shown here. Double click on any layer to edit the color representation.')

        # Adding substructure selector
        self.structure_selector = pyqtw.QComboBox()
        self.structure_selector.addItems(self.bg_atlas_structures.keys())
        self.structure_selector.setEnabled(False)
        self.dock_layout.addWidget(self.structure_selector, 0, 4, 1, 1) # Y, X, h, w
        self.structure_selector.setToolTip('Select the brain structure to be highlighted then click on Add Structure Layer.<br>You can find detailed descriptions of the available structure on BrainGlobe\'s documentation.')

        # Brain structure hemisphere selector
        self.hemisphere_selector = pyqtw.QComboBox()
        self.hemisphere_selector.addItems(['Both Hemispheres', 'Left Hemisphere', 'Right Hemisphere'])
        self.hemisphere_selector.setEnabled(False)
        self.dock_layout.addWidget(self.hemisphere_selector, 0, 5, 1, 1)
        self.hemisphere_selector.setToolTip('Choose the hemisphere(s) where the structure will be highlighted.')

        # Brain structure layer button
        self.add_structure_layer_btn = pyqtw.QPushButton('Add Structure Layer')
        self.add_structure_layer_btn.clicked.connect(self._add_structure_layer_btn_pressed)
        self.add_structure_layer_btn.setEnabled(False)
        self.dock_layout.addWidget(self.add_structure_layer_btn, 1, 4, 1, 1)

        # Remove layer button
        self.rm_structure_layer_btn = pyqtw.QPushButton('Remove Selected Layer')
        self.rm_structure_layer_btn.clicked.connect(self._remove_altas_layer_btn_pressed)
        self.rm_structure_layer_btn.setEnabled(False)
        self.dock_layout.addWidget(self.rm_structure_layer_btn, 1, 5, 1, 1)

        # Equalize column widths
        self.dock_layout.setColumnStretch(0, 1)
        self.dock_layout.setColumnStretch(1, 3)
        self.dock_layout.setColumnStretch(2, 2)
        self.dock_layout.setColumnStretch(3, 2)
        self.dock_layout.setColumnStretch(4, 2)
        self.dock_layout.setColumnStretch(5, 2)

        self.atlas_layers_tree_view.doubleClicked.connect(self.atlas_ml_ndimg._show_LUT_editor_floating_dock)
        self._update_atlas_selector()
        self._init_module_from_cached_layers_dict()

    def add_rendered_object(self):
        """ Called when populating the viewer with the module rendered objects """
        self.delete_rendered_object()

        if self.bg_atlas is not None:
            self._update_atlas_user_params_editors()
            self.atlas_ml_ndimg.add_rendered_object()

        self._update_atlas_selector()

    def update_rendered_object(self):
        """ Called on render view updates """
        # set _ndimage_params_hash to prevent recomputation of raw rgba ndimage when substride has not changed
        if self.bg_atlas is not None:
            subs_stride = self.get_user_param('subsampling_stride', default_value=self._default_subsampling_stride)
            self.atlas_ml_ndimg._ndimage_params_hash = f'{subs_stride}'

        self.atlas_ml_ndimg.update_rendered_object()

    def delete_rendered_object(self):
        """ Called on deletion of the module rendered objects """
        self.atlas_ml_ndimg.delete_rendered_object()

    # --- Atlas specific cache wrapper ---
    
    def get_user_param(self, param_name, default_value=None):
        """ Get module configuration parameter stored in cache (or default values if non existant) """
        if self.bg_atlas is not None:
            param_value = super().get_user_param(
                param_name,
                additional_identifiers=[self.bg_atlas.atlas_name],
                default_value=default_value)
        else:
            param_value = self._DEFAULT_PARAMS[param_name]
        return param_value

    def set_user_param(self, param_name, param_value):
        """ Set module configuration parameter to cache """
        if self.bg_atlas is not None:
            super().set_user_param(
                param_name,
                additional_identifiers=[self.bg_atlas.atlas_name],
                param_value=param_value)
            
    # --- Module specific attributes ---

    def _on_tree_view_resize(self):
        self.atlas_layers_tree_view.setColumnWidth(0, self.atlas_layers_tree_view.width() - 50)
        self.atlas_layers_tree_view.setColumnWidth(1, 50-30)
    
    def _init_module_from_cached_layers_dict(self):
        for layer_name, layer in self.atlas_ml_ndimg.layers.items():
            if layer_name == 'Reference Atlas':
                self._reference_atlas_setup(layer_name)
            else:
                self._add_layer_to_layers_tree_view(layer_name)
                self.atlas_ml_ndimg._add_LUT_editor_to_floating_dock(layer_name)
            self.atlas_ml_ndimg._on_layers_update()


    def _get_tree_viewer_layer_index_by_name(self, layer_name: str):
        for row in range(self.atlas_layers_model.rowCount()):
            item = self.atlas_layers_model.item(row, 0) # column 0 is the Layer name
            if item.text() == layer_name:
                return self.atlas_layers_model.indexFromItem(item)
        return None # invalid index if not found

    def _get_layer_name_by_tree_viewer_layer_index(self, tree_viewer_layer_index):
        if not tree_viewer_layer_index.isValid():
            return None
        row = tree_viewer_layer_index.row()
        item = self.atlas_layers_model.item(row, 0) # column 0 contains the layer name
        return item.text()

    def _add_layer_to_layers_tree_view(self, layer_name):
        # Layer name item (with visibility checkbox)
        layer_item = pyqtg.QStandardItem(layer_name)
        layer_item.setCheckable(True)
        layer_item.setCheckState(pyqtc.Qt.CheckState.Checked)
        layer_item.setFlags(layer_item.flags() & ~pyqtc.Qt.ItemFlag.ItemIsEditable)

        # Tooltip item (mutually exclusive checkbox)
        tooltip_item = pyqtg.QStandardItem()
        tooltip_item.setCheckable(True)
        tooltip_item.setCheckState(pyqtc.Qt.CheckState.Unchecked)
        tooltip_item.setFlags(tooltip_item.flags() & ~pyqtc.Qt.ItemFlag.ItemIsEditable)

        self.atlas_layers_model.appendRow([layer_item, tooltip_item])

    def _remove_layer_from_layers_tree_view(self, tree_viewer_layer_index=None, layer_name=None):
        if tree_viewer_layer_index is None:
            if layer_name is None:
                raise ValueError('Please provide either tree_viewer_layer_index or layer_name.')
            tree_viewer_layer_index = self._get_tree_viewer_layer_index_by_name(layer_name)
        self.atlas_layers_model.removeRow(tree_viewer_layer_index.row())

    def _clear_layers_tree_view(self):
        self.atlas_layers_model.clear()
        self.atlas_layers_model.setHorizontalHeaderLabels(["Atlas Layer", "Tooltip"])
        self.atlas_layers_tree_view.setRootIsDecorated(False)

    def _on_layers_tree_view_checkbox_toggle(self, changed_item):
        layer_name = self.atlas_layers_model.item(changed_item.row(), 0).text()
        col = changed_item.column()

        # Layers visibility checkboxes
        if col == 0:
            if layer_name in self.atlas_ml_ndimg.layers:
                self.atlas_ml_ndimg.layers[layer_name]['_visible'] = (changed_item.checkState() == pyqtc.Qt.CheckState.Checked)
                self.atlas_ml_ndimg._on_layers_update()

        # Tooltip placement checkboxes
        if col == 1:
            self._tooltip_to_layer_centroid = None

            if changed_item.checkState() == pyqtc.Qt.CheckState.Checked:

                # Uncheck all other tooltip checkboxes
                for row in range(self.atlas_layers_model.rowCount()):
                    item = self.atlas_layers_model.item(row, 1)
                    if item is not changed_item:
                        item.setCheckState(pyqtc.Qt.CheckState.Unchecked)
                
                self._tooltip_to_layer_centroid = layer_name
            
            self.update_tooltip_to_layer_centroid()

    def _add_structure_layer_btn_pressed(self):
        # Grab structure settings from GUI
        selected_structure = self.structure_selector.currentText()
        selected_hemisphere = self.hemisphere_selector.currentText()

        if selected_structure == 'Select Structure':
            self.parent_viewer.show_error_popup(
                'Add Layer', error_description='Please select a brain structure.'
            )
            return

        self.add_structure_layer(selected_structure, selected_hemisphere)

    def _remove_altas_layer_btn_pressed(self):
        # Grab layer selected in treee view
        tree_viewer_layer_index = self.atlas_layers_tree_view.currentIndex()
        if not tree_viewer_layer_index.isValid():
            self.parent_viewer.show_error_popup(
                'Remove Layer', error_description='No altas layer selected.'
            )
            return

        self.remove_altas_layer(tree_viewer_layer_index=tree_viewer_layer_index)
    
    def _reference_atlas_setup(self, layer_name):
        self._update_structure_selector()
        self.atlas_ml_ndimg._add_LUT_editor_to_floating_dock(layer_name)
        self._add_layer_to_layers_tree_view(layer_name)

        self.structure_selector.setEnabled(True)
        self.hemisphere_selector.setEnabled(True)
        self.add_structure_layer_btn.setEnabled(True)
        self.rm_structure_layer_btn.setEnabled(True)

    def _new_reference_atlas_selected(self):
        """ Triggered whenever atlas_selector selection changes """

        selected_atlas_description = self.atlas_selector.currentText()

        if selected_atlas_description in ['Select Atlas', 'Offline mode -> Only downloaded atlas are visible']:
            self.remove_reference_atlas()
        elif selected_atlas_description.endswith('(DOWNLOADED)'):
            offline_atlas_name = selected_atlas_description.split(' | ')[0]
            self.parent_viewer.statusBar().showMessage(f'Loading offline {offline_atlas_name}', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)
            self.add_reference_atlas(offline_atlas_name)
        elif selected_atlas_description.endswith('(online)'):
            online_atlas_name = selected_atlas_description.split(' | ')[0]
            
            dialog = AcceptRejectDialog(
                parent=self.parent_viewer,
                title='This atlas has to be downloaded externally',
                msg=f'Run\n\tbrainglobe install -a {online_atlas_name}\nin a Terminal to do so\n\nClick OK to copy the command in the clipboard and close CoperniFUS.\nRestart CoperniFUS once the download is complete.'
            )
            dialog_result = dialog.exec()

            if dialog_result == 1:
                # Download cmd to clipboard
                clipboard = self.parent_viewer.app.clipboard()
                clipboard.setText(f'brainglobe install -a {online_atlas_name}')
                # Close CoperniFUS
                self.parent_viewer.close()
            else:
                self.parent_viewer.statusBar().showMessage('Proceeding with offline atlases', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)

    def _parse_editor(self, src_editor, param_name, unit='', param_type='float'):
        if param_type == 'int':
            edited_value = int(src_editor.text())
        elif param_type == 'float':
            edited_text = src_editor.text().replace(' ', '') # remove spaces
            edited_text_nounit = edited_text[:-len(unit)]
            edited_value = si_parse(edited_text_nounit.replace('u', 'µ'))
        else: # raw str
            edited_value = src_editor.text()

        self.set_user_param(param_name, edited_value)
        self.parent_viewer.update_rendered_view()

    @property
    def _default_subsampling_stride(self):
        return int((np.prod(self.bg_atlas.shape) / self._DEFAULT_N_VOXELS)**(1/3))

    def _update_atlas_selector(self):
        try: self.atlas_selector.currentIndexChanged.disconnect() 
        except Exception: pass

        self.available_atlases = None
        self.atlas_selector.clear()
        self.atlas_selector.addItems(self.available_atlases.values())

        # Init atlas selector
        if self.bg_atlas is not None:
            selected_offline_atlas = self.bg_atlas.atlas_name
        else:
            selected_offline_atlas = 'no_atlas'

        if selected_offline_atlas == 'no_atlas':
            self.atlas_selector.setCurrentIndex(0) # set to "Select Atlas" option
        elif f'offline_{selected_offline_atlas}' in self.available_atlases.keys():
            self.atlas_selector.setCurrentIndex(list(self.available_atlases.keys()).index(f'offline_{selected_offline_atlas}'))

        self.atlas_selector.currentIndexChanged.connect(self._new_reference_atlas_selected)

    def _update_structure_selector(self):
        if self.bg_atlas is None:
            self.bg_atlas_structures = {'Select Structure': None}
        else:
            sorted_structure_dict = dict(sorted({f"{struct['name']} ({struct['acronym']})": struct['acronym'] for struct in self.bg_atlas.structures_list}.items()))
            self.bg_atlas_structures = {
                **{'Select Structure': None},
                **sorted_structure_dict
            }

        self.structure_selector.clear()
        self.structure_selector.setEnabled(True)
        self.structure_selector.addItems(self.bg_atlas_structures.keys())
        # Set highlighted structure to default
        self.structure_selector.setCurrentIndex(0)

        # Set highlighted structure hemisphere to default
        self.hemisphere_selector.setCurrentText('Both Hemispheres')
        self.hemisphere_selector.setEnabled(True)

    def _update_atlas_user_params_editors(self):
        self.subsampling_stride_editor.setText(str(self.get_user_param('subsampling_stride', default_value=self._default_subsampling_stride)))
        self.atlas_transform_editor.setText(self.get_user_param('atlas_transforms_str'))

    # --- Atlas data handling ---

    def _reference_atlas_ndimage_data(self, ref_altas_name, subsampling_stride):
        if self.bg_atlas.atlas_name != ref_altas_name:
            self._bg_atlas = None

        normalisation_func = plt.Normalize()
        ref_atlas_uint8 = (np.asarray(normalisation_func(self.bg_atlas.reference)) * 255).astype(np.ubyte)

        subsampled_ref_atlas_uint8 = ref_atlas_uint8[::subsampling_stride, ::subsampling_stride, ::subsampling_stride]

        return  subsampled_ref_atlas_uint8

    def _get_struct_mask(self, structure_name, hemisphere_id, subsampling_stride):

        # Structure acronym retreival from name displayed in selector
        if structure_name not in self.bg_atlas_structures:
            raise ValueError(f'{structure_name} structure not available for {self.bg_atlas.atlas_name}. Available structures are:\n\t- {"\n\t- ".join(self.bg_atlas_structures.keys())}')
        structure_acronym = self.bg_atlas_structures[structure_name]
        
        if structure_acronym not in self._loaded_structure_mask:
            # Load only once for fast atlas updates
            self._loaded_structure_mask[structure_acronym] = self.bg_atlas.get_structure_mask(structure_acronym).astype(bool)

        if hemisphere_id == 'Both Hemispheres':
            struct_mask = self._loaded_structure_mask[structure_acronym]
        else:
            if hemisphere_id == 'Left Hemisphere':
                hemisphere_index = 1
            elif hemisphere_id == 'Right Hemisphere':
                hemisphere_index = 2
            else:
                raise ValueError('Invalid hemisphere name -> hemisphere_id has to be either "Both Hemispheres", "Left Hemisphere" or "Right Hemisphere"')
            struct_mask = (self._loaded_structure_mask[structure_acronym] * (self.bg_atlas.hemispheres == hemisphere_index)).astype(bool)
        
        subsampled_struct_mask = struct_mask[::subsampling_stride, ::subsampling_stride, ::subsampling_stride]

        return subsampled_struct_mask

    def _save_layers_state_to_cache(self):
        self.parent_viewer.cache.set_attr('atlas.jsonable_layers_dict', self.atlas_ml_ndimg.jsonable_layers_dict)