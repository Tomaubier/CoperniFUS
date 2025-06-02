from brainglobe_atlasapi.bg_atlas import BrainGlobeAtlas
import brainglobe_space as bgs
import brainglobe_atlasapi

from coperniFUS import *
from coperniFUS.modules.module_base import Module



class BrainAtlas(Module):

    """
    BrainAtlas module.

    Attributes:
        bg_atlas: BrainGlobe Atlas API atlas object.
    """

    _DEFAULT_N_VOXELS = 1e6 # target number of voxels for default atlas subsampling stride computation
    _DEFAULT_PARAMS = {
        'jsonable_layers_dict': "{}",
        'atlas_transforms_str' : 'Rx0deg Tz0um',
        'subsampling_stride': 10,
    }
    _CYCLIC_STRUCTURES_COLORS = [tuple([int(255*cc) for cc in plt.get_cmap('Set1')(ii)]) for ii in range(5)]


    def __init__(self, parent_viewer, skip_online_atlas_retreival=False, **kwargs) -> None:
        super().__init__(parent_viewer, 'atlas', **kwargs)

        self._layers = None
        self.skip_online_atlas_retreival = skip_online_atlas_retreival
        self._init_attributes()

    @property
    def layers(self):
        """ Atlas layer dict, keys starting with an underscore corresponds to large data that will be omitted in the version saved in cache. Make sure than other keys contain jsonable data
        
        General dict structure:
        'layer_name': {
            'ndimage': data, OR 'ndimage_from_layer_name': 'src_layer_name', OR 'atlas_structure_name' AND 'atlas_structure_hemisphere'
        }
        """
        if self._layers is None:
            self._layers = json.loads(self.parent_viewer.cache.get_attr(
                'atlas.jsonable_layers_dict', default_value=self._DEFAULT_PARAMS['jsonable_layers_dict']
            ))
        return self._layers
    
    @layers.setter
    def layers(self, value):
        if value is None:
            value = {}
        self._layers = value

    @property
    def jsonable_layers_dict(self):

        """ Provides a copy of the layers dict omitting non-jsonable data keys (starting with an underscore) """

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
            
        try:
            json_layers = json.dumps(private_keys_free_dict(self.layers), default=numpy_obj_serializer)
        except Exception as e:
            json_layers = "{}"
            raise ValueError(f'Error when attempting to cache jsonable_layers_dict:\n{str(e)}\n\nPlease create an issue on GitHub with the content of the data that needed to be cached:\n{nested_dict_formatter(private_keys_free_dict(self.layers))}')

        return json_layers

    def _init_attributes(self):
        self._loaded_structure_mask = {}
        self._ndimage_plane_slicing_application_mask = None
        self._tooltip_to_layer_centroid = None
        self._raw_rgba_ndimage_compound = None
        self._rgba_ndimage_compound = None
        self._available_atlases = None
        self._tmat_version_hash = None
        self._brain_atlas_tmat = None
        self.atlas_glvol = None
        self._bg_atlas = None
        self.bg_atlas_structures = {'Select Structure': None}

        self._atlas_voxel_coordinates = None
        self._slicing_plane_mask = None

    # --- Atlas specific cache wrapper ---
    
    def get_user_param(self, param_name, default_value=None):
        if self.bg_atlas is not None:
            param_value = super().get_user_param(
                param_name,
                additional_identifiers=[self.bg_atlas.atlas_name],
                default_value=default_value)
        else:
            param_value = self._DEFAULT_PARAMS[param_name]
            # if default_value is not None:
            #     param_value = default_value
            # else:
            #     param_value = self._DEFAULT_PARAMS[param_name]
        return param_value

    def set_user_param(self, param_name, param_value):
        if self.bg_atlas is not None:
            super().set_user_param(
                param_name,
                additional_identifiers=[self.bg_atlas.atlas_name],
                param_value=param_value)
            
    # --- Required module attributes ---
    
    def init_dock(self):
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

        self._init_LUT_editor_floating_dock()
        self.update_atlas_selector()
        self._init_module_from_cached_layers_dict()

    def _on_tree_view_resize(self):
        self.atlas_layers_tree_view.setColumnWidth(0, self.atlas_layers_tree_view.width() - 50)
        self.atlas_layers_tree_view.setColumnWidth(1, 50-30)
    
    def _init_LUT_editor_floating_dock(self):
        # Create dock widget
        self.lut_editor_dock = pyqtw.QDockWidget("Compound Atlas LUT editor", self.parent_viewer)
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
        self.atlas_layers_tree_view.doubleClicked.connect(self._show_LUT_editor_floating_dock)
    
    def _init_module_from_cached_layers_dict(self):
        for layer_name, layer in self.layers.items():
            if layer_name == 'Reference Atlas':
                self._reference_atlas_setup(layer_name)
            else:
                self._structure_layer_setup(layer_name)
    
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
                    clear_grid_layout(item.layout())  # Recursively clear nested layouts

        clear_grid_layout(self.lut_editor_dock_layout)

    def _add_lut_editor_to_dock(self, layer_name):
        if not layer_name in self.layers:
            raise ValueError(f'{layer_name} not in layers')
        layer = self.layers[layer_name]
        
        # Create HistogramLUTWidget objects
        layer['_lut_widgets'] = pg.HistogramLUTWidget(orientation='horizontal', fillHistogram=False)

        # Set HistogramLUTWidget with a dummy image with proper dynamic range for LUT control
        ndimage_data = self.get_layer_ndimage_data(layer_name, apply_mask=False)
        data_min, data_max = np.min(ndimage_data), np.max(ndimage_data)
        dummy_img = pg.ImageItem(np.array([[data_min], [data_max]]), dtype=np.ubyte)
        layer['_lut_widgets'].setImageItem(dummy_img)

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

    def _remove_lut_editor_from_dock(self, layer_name):
        if not layer_name in self.layers:
            raise ValueError(f'{layer_name} not in layers')
        layer = self.layers[layer_name]

        layer['_lut_widgets'].deleteLater()

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
            if layer_name in self.layers:
                self.layers[layer_name]['_visible'] = (changed_item.checkState() == pyqtc.Qt.CheckState.Checked)
                self._on_layers_update()

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

    def update_tooltip_to_layer_centroid(self):
        if self._tooltip_to_layer_centroid is not None and self._tooltip_to_layer_centroid in self.layers:
            layer = self.layers[self._tooltip_to_layer_centroid]

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
        self._tooltip_to_layer_centroid = None
        uncheck_all_checkboxes_in_qtree_column(self.atlas_layers_model, checkbox_column=1)
    
    def _structure_layer_setup(self, layer_name):
        self._add_layer_to_layers_tree_view(layer_name)
        self._add_lut_editor_to_dock(layer_name)
        self._on_layers_update()

    def add_structure_layer(self, structure, hemisphere):

        # Catch parameters errors
        if structure not in self.bg_atlas_structures:
            raise ValueError(f'{structure} structure not available for {self.bg_atlas.atlas_name}. Available structures are:\n\t- {"\n\t- ".join(self.bg_atlas_structures.keys())}')
        if hemisphere not in ['Both Hemispheres', 'Left Hemisphere', 'Right Hemisphere']:
            raise ValueError('Invalid hemisphere name -> hemisphere_id has to be either "Both Hemispheres", "Left Hemisphere" or "Right Hemisphere"')
        
        number_of_existing_struture_layers = len([kk for kk, ll in self.layers.items() if 'atlas_structure_name' in ll])
        layer_name = f'{structure} ({hemisphere})'

        layer_name_suffix = 1
        while layer_name in self.layers:
            layer_name = f'{layer_name} {layer_name_suffix}'
            layer_name_suffix += 1

        self.layers[layer_name] = {
            '_visible': True,
            'atlas_structure_name': structure,
            'atlas_structure_hemisphere': hemisphere,
            'ndimage_from_layer_name': 'Reference Atlas',
            'lut_preset': self.get_highlighted_structure_lut_preset(
                structure_index=number_of_existing_struture_layers
            ),
            'levels_preset': (0, 255),
            'skip_plane_slicing': True,
        }
        self._structure_layer_setup(layer_name)
        
    
    def remove_altas_layer(self, layer_name=None, tree_viewer_layer_index=None):
        
        if layer_name is None:
            if tree_viewer_layer_index is None:
                raise ValueError('Please provide either tree_viewer_layer_index or layer_name.')
            layer_name = self._get_layer_name_by_tree_viewer_layer_index(tree_viewer_layer_index)
            
        if layer_name not in self.layers:
            raise IndexError('{layer_name} not in atlas layers -> cannot be removed')
        
        if layer_name == 'Reference Atlas':
            self.remove_reference_atlas()
        else: # Rm individual structure layer
            self._remove_lut_editor_from_dock(layer_name)
            self._remove_layer_from_layers_tree_view(layer_name=layer_name, tree_viewer_layer_index=tree_viewer_layer_index)

            _ = self.layers.pop(layer_name)
        self._on_layers_update()

    def _add_structure_layer_btn_pressed(self):
        # Grab structure settings from GUI
        selected_structure = self.structure_selector.currentText()
        selected_hemisphere = self.hemisphere_selector.currentText()

        if selected_structure == 'Select Structure':
            pyqtw.QMessageBox.warning(self.parent_viewer, "Add Layer", "Please select a brain structure.")
            return

        self.add_structure_layer(selected_structure, selected_hemisphere)

    def _remove_altas_layer_btn_pressed(self):
        # Grab layer selected in treee view
        tree_viewer_layer_index = self.atlas_layers_tree_view.currentIndex()
        if not tree_viewer_layer_index.isValid():
            pyqtw.QMessageBox.warning(self.parent_viewer, "Remove Layer", "No altas layer selected.")
            return

        self.remove_altas_layer(tree_viewer_layer_index=tree_viewer_layer_index)

    @property
    def bg_atlas(self):
        if self._bg_atlas is None:
            if 'Reference Atlas' in self.layers:
                if 'ref_altas_name' not in self.layers['Reference Atlas']:
                    raise ValueError('"ref_altas_name" missing in "Reference Atlas" layer')
                
                offline_atlas_name = self.layers['Reference Atlas']['ref_altas_name']

                if offline_atlas_name not in brainglobe_atlasapi.list_atlases.get_downloaded_atlases():
                    raise ValueError(f'This atlas is not available locally.\n Run\n\tbrainglobe install -a {offline_atlas_name}\nin a Terminal to do so.\nRestart CoperniFUS once the download is complete.')
                
                self._init_attributes()
                self._bg_atlas = BrainGlobeAtlas(offline_atlas_name, check_latest=False)
        
        return self._bg_atlas
    
    def _reference_atlas_setup(self, layer_name):
        self.update_structure_selector()
        self._add_layer_to_layers_tree_view(layer_name)
        self._add_lut_editor_to_dock(layer_name)

        self.structure_selector.setEnabled(True)
        self.hemisphere_selector.setEnabled(True)
        self.add_structure_layer_btn.setEnabled(True)
        self.rm_structure_layer_btn.setEnabled(True)

        self._save_layers_state_to_cache()

    def add_reference_atlas(self, offline_atlas_name):
        
        if offline_atlas_name not in brainglobe_atlasapi.list_atlases.get_downloaded_atlases():
            raise ValueError(f'This atlas is not available locally.\n Run\n\tbrainglobe install -a {offline_atlas_name}\nin a Terminal to do so.\nRestart CoperniFUS once the download is complete.')

        self.remove_reference_atlas()
        
        layer_name = 'Reference Atlas'
        self.layers[layer_name] = {
            '_visible': True,
            'ref_altas_name': offline_atlas_name,
            'lut_preset': self.get_ref_atlas_lut_preset(),
            'levels_preset': (0, 255),
            'skip_plane_slicing': False,
        }

        self._reference_atlas_setup(layer_name)
        self.add_rendered_object()

    def remove_reference_atlas(self):
        self.delete_rendered_object()
        self._clear_layers_tree_view()
        self._clear_LUT_editor_floating_dock()
        self._init_attributes()
        self.layers = None
        self._save_layers_state_to_cache()

        self.update_atlas_selector()
        self.structure_selector.setEnabled(False)
        self.hemisphere_selector.setEnabled(False)
        self.add_structure_layer_btn.setEnabled(False)
        self.rm_structure_layer_btn.setEnabled(False)

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
            
            dialog = AcceptRejectDialog(parent=self.parent_viewer, title='This atlas has to be downloaded externally', msg=f'Run\n\tbrainglobe install -a {online_atlas_name}\nin a Terminal to do so\n\nClick OK to copy the command in the clipboard and close CoperniFUS.\nRestart CoperniFUS once the download is complete.')
            dialog_result = dialog.exec()
            if dialog_result == 1:
                # Download cmd to clipboard
                clipboard = self.parent_viewer.app.clipboard()
                clipboard.setText(f'brainglobe install -a {online_atlas_name}')
                # Close CoperniFUS
                self.parent_viewer.close()
            else:
                self.parent_viewer.statusBar().showMessage('Proceeding with offline atlases', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)

    # === RENDER FUNCS ===

    def add_rendered_object(self):
        self.delete_rendered_object()
        # self._new_reference_atlas_selected()

        if self.bg_atlas is not None:

            self.update_atlas_user_params_editors()

            self.atlas_glvol = gl.GLVolumeItem(self.rgba_ndimage_compound, smooth=True, glOptions='translucent')
            self.parent_viewer.gl_view.addItem(self.atlas_glvol, name='Brain atlas compound')
            self.atlas_glvol.setDepthValue(1) # GL volumes -> render tree foreground
            self.update_atlas_transform()

        self.update_atlas_selector()

    def delete_rendered_object(self):
        if self.atlas_glvol in self.parent_viewer.gl_view.items:
            self.parent_viewer.gl_view.removeItem(self.atlas_glvol)
            self.atlas_glvol = None

    def update_rendered_object(self):
        if self.atlas_glvol is not None:
            self.update_atlas_transform()
            self.atlas_glvol.setData(self.rgba_ndimage_compound)

    # --- Module specific attributes ---

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
    def available_atlases(self):
        if self._available_atlases is None:
            self._offline_atlases_names = brainglobe_atlasapi.list_atlases.get_downloaded_atlases()
            formatted_offline_atlases = {
                f'offline_{atlas_name}': f'{atlas_name} | v{brainglobe_atlasapi.list_atlases.get_local_atlas_version(atlas_name)} (DOWNLOADED)'
                for (ii, atlas_name) in enumerate(self._offline_atlases_names)
            }

            formatted_online_atlases = None
            if not self.skip_online_atlas_retreival:
                self.parent_viewer.statusBar().showMessage('Loading online atlas list')
                try:
                    online_atlases = brainglobe_atlasapi.list_atlases.get_all_atlases_lastversions()
                    self._online_atlases_names = list(online_atlases.keys())
                    online_atlases_versions = list(online_atlases.values())

                    formatted_online_atlases = {
                        f'online_{atlas_name}': f'{atlas_name} | v{online_atlases_versions[ii]} (online)'
                        for (ii, atlas_name) in enumerate(self._online_atlases_names)
                        if atlas_name not in formatted_offline_atlases
                    }
                except:
                    pass
            
            self.parent_viewer.statusBar().clearMessage()
            if formatted_online_atlases is None:
                formatted_online_atlases = {
                    None: 'Offline mode -> Only downloaded atlas are visible'
                }

            self._available_atlases = {
                'no_atlas': 'Select Atlas',
                **formatted_offline_atlases,
                **formatted_online_atlases
            }
        return self._available_atlases
    
    @available_atlases.setter
    def available_atlases(self, value):
        self._available_atlases = value

    @property
    def _default_subsampling_stride(self):
        return int((np.prod(self.bg_atlas.shape) / self._DEFAULT_N_VOXELS)**(1/3))

    @property
    def atlas_resolution(self):
        subs_stride = self.get_user_param('subsampling_stride', default_value=self._default_subsampling_stride)
        atlas_res = subs_stride * np.array(self.bg_atlas.resolution) * 1e-6 # um to meters
        return atlas_res
    
    @property
    def brain_atlas_tmat(self):
        if self._brain_atlas_tmat is None:
            resolution = self.atlas_resolution
            atlas_shape = self.raw_rgba_ndimage_compound.shape

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

    def update_atlas_selector(self):
        try: self.atlas_selector.currentIndexChanged.disconnect() 
        except Exception: pass

        self.available_atlases = None
        self.atlas_selector.clear()
        self.atlas_selector.addItems(self.available_atlases.values())

        # Init atlas selector
        if self.bg_atlas is not None: # TODO check
            selected_offline_atlas = self.bg_atlas.atlas_name
        else:
            selected_offline_atlas = 'no_atlas'

        if selected_offline_atlas == 'no_atlas':
            self.atlas_selector.setCurrentIndex(0) # set to "Select Atlas" option
        elif f'offline_{selected_offline_atlas}' in self.available_atlases.keys():
            self.atlas_selector.setCurrentIndex(list(self.available_atlases.keys()).index(f'offline_{selected_offline_atlas}'))

        self.atlas_selector.currentIndexChanged.connect(self._new_reference_atlas_selected)

    def update_structure_selector(self):
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

    def update_atlas_user_params_editors(self):
        self.subsampling_stride_editor.setText(str(self.get_user_param('subsampling_stride', default_value=self._default_subsampling_stride)))
        self.atlas_transform_editor.setText(self.get_user_param('atlas_transforms_str'))

    def update_atlas_transform(self):
        self.brain_atlas_tmat = None
        self.atlas_voxel_coordinates = None # Reset voxels coordinates
        if self.atlas_glvol is not None:
            self.atlas_glvol.resetTransform()
            self.atlas_glvol.applyTransform(pyqtg.QMatrix4x4(self.brain_atlas_tmat.T.ravel()), local=False)

    @property
    def atlas_voxel_coordinates(self):
        # Check if tmat has changed since last update
        if self._tmat_version_hash != object_list_hash([self.brain_atlas_tmat]):
            self._atlas_voxel_coordinates = None # Recompute if it is
        if self._atlas_voxel_coordinates is None:
            atlas_shape = self.raw_rgba_ndimage_compound.shape[:3]
            voxel_coords = np.mgrid[0:atlas_shape[0], 0:atlas_shape[1], 0:atlas_shape[2]]
            raveled_coords = voxel_coords.reshape(3, -1).T

            # Apply atlas spatial transformations
            self.update_atlas_transform()
            raveled_coords_4by = np.vstack([raveled_coords.T, np.ones(len(raveled_coords))]).T
            transformed_coords = raveled_coords_4by @ self.brain_atlas_tmat
            self._atlas_voxel_coordinates = transformed_coords[:, :3]
            self._tmat_version_hash = object_list_hash([self.brain_atlas_tmat])
        return self._atlas_voxel_coordinates
    
    @atlas_voxel_coordinates.setter
    def atlas_voxel_coordinates(self, value):
        self._atlas_voxel_coordinates = value

    def compute_slicing_plane(self):
        slicing_plane_pts = self.parent_viewer.slicing_plane_3pts
        if slicing_plane_pts is not None:
            if not self.parent_viewer.postpone_slicing_plane_computation or self._slicing_plane_mask is None:
                raveled_mask = np.dot(
                    self.atlas_voxel_coordinates - slicing_plane_pts[0],
                    np.cross(
                        slicing_plane_pts[1] - slicing_plane_pts[0],
                        slicing_plane_pts[2] - slicing_plane_pts[0]
                    )) < 0
                
                self._slicing_plane_mask = np.logical_and(
                    raveled_mask.reshape(self.ndimage_plane_slicing_application_mask.shape),
                    self.ndimage_plane_slicing_application_mask
                )

            self._rgba_ndimage_compound[self._slicing_plane_mask, 3] = 0

    # ========== Multi layer compound atlas eval ==========

    def get_highlighted_structure_lut_preset(self, structure_index=0):
        rgb_color = self._CYCLIC_STRUCTURES_COLORS[structure_index%len(self._CYCLIC_STRUCTURES_COLORS)][:3]
        lut_state = {
            'mode': 'rgb',
            'ticks': [
                (0.0, (*rgb_color, 0)),
                (0.5, (*rgb_color, 255))],
            'ticksVisible': True
        }
        return lut_state

    def get_ref_atlas_lut_preset(self):
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
    
    def apply_lut_to_ndimage(self, ndimage_data, lut, levels):
        """ Converts ndim image data to ndim RGBA based on a lookup table (LUT) """
        # Normalize data to levels
        min_val, max_val = levels
        scaled = np.clip((ndimage_data - min_val) / (max_val - min_val), 0, 1)
        indices = (scaled * (len(lut) - 1)).astype(np.ubyte)
        rgba = lut[indices]  # shape: (..., 4)
        return rgba

    def alpha_blend(self, background, foreground):
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
    
    def reference_atlas_ndimage_data(self, ref_altas_name, subsampling_stride):
        if self.bg_atlas.atlas_name != ref_altas_name:
            self._bg_atlas = None

        normalisation_func = plt.Normalize()
        ref_atlas_uint8 = (np.asarray(normalisation_func(self.bg_atlas.reference)) * 255).astype(np.ubyte)

        subsampled_ref_atlas_uint8 = ref_atlas_uint8[::subsampling_stride, ::subsampling_stride, ::subsampling_stride]

        return  subsampled_ref_atlas_uint8

    def get_struct_mask(self, structure_name, hemisphere_id, subsampling_stride):

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

    def get_layer_ndimage_data(self, layer_name, apply_mask=True):
        """
        layers: dictionary of all the layers
        layer_name: dict key of the layer from which ndimage data has to be retreived
        All layers should contain either 'ref_altas_name' or 'ndimage_from_layer_name' fields referencing ndimage data
        """
        subs_stride = self.get_user_param('subsampling_stride', default_value=self._default_subsampling_stride)

        if '_ndimage_data' in self.layers[layer_name] and '_subs_stride' in self.layers[layer_name] and self.layers[layer_name]['_subs_stride'] == subs_stride:
            ndimage_data = self.layers[layer_name]['_ndimage_data']
        else: # Evaluate data content if '_ndimage_data' not in dict
            if 'ref_altas_name' in self.layers[layer_name]:
                ndimage_data = self.reference_atlas_ndimage_data(self.layers[layer_name]['ref_altas_name'], subsampling_stride=subs_stride)
            elif 'ndimage_from_layer_name'in self.layers[layer_name]:
                ndimage_data = self.get_layer_ndimage_data(self.layers[layer_name]['ndimage_from_layer_name'], apply_mask=False)
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
                    ndimage_mask = self.get_struct_mask(
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
    
    @property
    def ndimage_plane_slicing_application_mask(self):
        if self._ndimage_plane_slicing_application_mask is None:
            self._ndimage_plane_slicing_application_mask = np.ones(self.raw_rgba_ndimage_compound.shape[:3], dtype=bool)
        return self._ndimage_plane_slicing_application_mask
    
    @property
    def raw_rgba_ndimage_compound(self):

        def apply_plane_slicing_on_layer(layer):
            apply_plane_slicing = not layer['skip_plane_slicing'] if 'skip_plane_slicing' in layer else False
            return apply_plane_slicing
        
        def layer_visible(layer):
            visible = layer['_visible'] if '_visible' in layer else True
            return visible

        subs_stride = self.get_user_param('subsampling_stride', default_value=self._default_subsampling_stride)
        ndimage_params_id = f'{subs_stride}'

        # Compute if undefined or subsampling stride has changed
        if self._raw_rgba_ndimage_compound is None or self._raw_rgba_ndimage_compound[0] != ndimage_params_id:

            base_layer_name = list(self.layers.keys())[0]
            layer = self.layers[base_layer_name]

            # Get ndimage data
            ndimage_data = self.get_layer_ndimage_data(base_layer_name, apply_mask=False)

            # Evaluate plane slicing binary mask for layer
            self._ndimage_plane_slicing_application_mask = apply_plane_slicing_on_layer(layer) * np.ones(ndimage_data.shape[:3], dtype=bool)
            
            # Get LUT from widget
            lut = layer['_lut_widgets'].item.getLookupTable(n=256, alpha=True)
            levels = layer['_lut_widgets'].item.getLevels()

            # Compute rgba ndimage
            _raw_rgba_ndimage_compound = self.apply_lut_to_ndimage(ndimage_data, lut, levels)
            if not layer_visible(layer):
                _raw_rgba_ndimage_compound[..., 3] = 0 # Make fully transparent

            for layer_ii, (layer_name, layer) in enumerate(self.layers.items()):
                if layer_ii > 0 and layer_visible(layer): # Skip base layer -> already processed AND invisible layers
                    # Get ndimage data
                    ndimage_data = self.get_layer_ndimage_data(layer_name, apply_mask=True)

                    # Get LUT from widget
                    lut = layer['_lut_widgets'].item.getLookupTable(n=256, alpha=True)
                    levels = layer['_lut_widgets'].item.getLevels()

                    # Compute rgba ndimage
                    rgba_ndimage = self.apply_lut_to_ndimage(ndimage_data, lut, levels)

                    if '_ndimage_mask' in layer:
                        _raw_rgba_ndimage_compound[layer['_ndimage_mask']] = self.alpha_blend(
                            _raw_rgba_ndimage_compound[layer['_ndimage_mask']], rgba_ndimage
                        )

                        # Evaluate plane slicing binary mask for layer
                        self._ndimage_plane_slicing_application_mask[layer['_ndimage_mask']] = apply_plane_slicing_on_layer(layer)

                    else:
                        _raw_rgba_ndimage_compound = self.alpha_blend(_raw_rgba_ndimage_compound, rgba_ndimage)

                        # Evaluate plane slicing binary mask for layer
                        self._ndimage_plane_slicing_application_mask = np.logical_and(
                            self._ndimage_plane_slicing_application_mask,
                            apply_plane_slicing_on_layer(layer) * np.ones(ndimage_data.shape[:3], dtype=bool)
                        )

            self._raw_rgba_ndimage_compound = (ndimage_params_id, _raw_rgba_ndimage_compound)

        return self._raw_rgba_ndimage_compound[1]
    
    @property
    def rgba_ndimage_compound(self):
        self._rgba_ndimage_compound = self.raw_rgba_ndimage_compound.copy()
        self.compute_slicing_plane()

        return self._rgba_ndimage_compound
    
    def _on_layers_update(self):
        """ Callback to update RGBA volume on LUT edition """

        self._raw_rgba_ndimage_compound = None # reset
        if self.atlas_glvol is not None:
            self.atlas_glvol.setData(self.rgba_ndimage_compound)

        self._save_layers_state_to_cache()

    def _save_layers_state_to_cache(self):
        for layer_name, layer in self.layers.items():
            if '_lut_widgets' in layer:
                self.layers[layer_name]['levels_preset'] = layer['_lut_widgets'].getLevels()
                self.layers[layer_name]['lut_preset'] = layer['_lut_widgets'].gradient.saveState()
        self.parent_viewer.cache.set_attr('atlas.jsonable_layers_dict', self.jsonable_layers_dict)