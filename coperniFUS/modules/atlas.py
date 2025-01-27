from coperniFUS import *
from coperniFUS.modules.module_base import Module

class BrainAtlas(Module):

    _DEFAULT_PARAMS = {
        'default_atlas_name': 'whs_sd_rat_39um',
        'highlighted_structure': 'Select structure',
        'highlighted_structure_hemisphere': 'Both',
        'atlas_transforms_str' : 'Rx0deg Tz0um',
        'subsampling_stride': 10,
        'black_threshold': 5,
        'alpha': .1
    }

    def __init__(self, parent_viewer, skip_online_atlas_retreival=False, **kwargs) -> None:
        super().__init__(parent_viewer, 'atlas', **kwargs)

        self.test_atlas = False
        if 'running_test' in self.module_kwargs and self.module_kwargs['running_test']:
            print('running test')
            self.test_atlas = True
            self._DEFAULT_PARAMS['default_atlas_name'] = 'example_mouse_100um'

        self.skip_online_atlas_retreival = skip_online_atlas_retreival
        self.init_attributes()

    def init_attributes(self):
        self._available_atlases = None
        self._raw_highlighted_structure_volume = None
        self._raw_atlas_rgba_volume = None
        self._atlas_rgba_volume = None
        self._tmat_version_hash = None
        self._brain_atlas_tmat = None
        self.atlas_glvol = None
        self.bg_atlas = None
        self.bg_atlas_structures = {'Select structure': None}

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
        self.dock = pyqtw.QDockWidget('Brain Atlas Settings', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.BottomDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Adding Atlas selector
        self.atlas_selector = pyqtw.QComboBox()
        # self.atlas_selector.setStyleSheet("QComboBox { combobox-popup: 0; }")  # Limit dropdown height
        # self.atlas_selector.setMaxVisibleItems(20) # Limit dropdown height # BUG darkmode interference
        self.dock_layout.addWidget(self.atlas_selector, 0, 0, 1, 1) # Y, X, w, h
        self.atlas_selector.setToolTip('Select a brain atlas for download. Previously downloaded atlases are registered as (DOWNLOADED).<br>You can find detailed descriptions of the available atlases on BrainGlobe\'s documentation.')

        # Subsampling stride editor
        self.subsampling_stride_editor = pyqtw.QLineEdit(str(self._DEFAULT_PARAMS['subsampling_stride']))
        self.subsampling_stride_editor.editingFinished.connect(functools.partial(self._parse_editor, self.subsampling_stride_editor, 'subsampling_stride', '', 'int'))
        self.dock_layout.addWidget(self.subsampling_stride_editor, 0, 1, 1, 1) # Y, X, w, h
        self.subsampling_stride_editor.setToolTip('Atlas subsampling stride<br>Use 1 to show the altas in its full resolution, larger strides will however improve performances.')

        self.atlas_transform_editor = pyqtw.QLineEdit(str(self._DEFAULT_PARAMS['atlas_transforms_str']))
        self.atlas_transform_editor.editingFinished.connect(functools.partial(self._parse_editor, self.atlas_transform_editor, 'atlas_transforms_str', '', 'str'))
        self.dock_layout.addWidget(self.atlas_transform_editor, 0, 2, 1, 1) # Y, X, w, h
        self.atlas_transform_editor.setToolTip('STL mesh transformations<br> - S0.5: Apply a 0.5 scaling factor (Use Sx to scale along x)<br> - Ty1mm: 1mm translation along y<br> - Rz90deg: Rotate by 90 degrees around z axis')

        # Adding substructure selector
        self.structure_selector = pyqtw.QComboBox()
        # self.structure_selector.setStyleSheet("QComboBox { combobox-popup: 0; }") # Limit dropdown height
        # self.structure_selector.setMaxVisibleItems(20) # Limit dropdown height # BUG darkmode interference
        self.structure_selector.addItems(['Select structures'])
        self.structure_selector.setEnabled(False)
        self.dock_layout.addWidget(self.structure_selector, 1, 0, 1, 1)
        self.structure_selector.setToolTip('Select the brain structure to be highlighted then click on Highlight Structure.<br>You can find detailed descriptions of the available structure on BrainGlobe\'s documentation.')

        self.hemisphere_selector = pyqtw.QComboBox()
        self.hemisphere_selector.addItems(['Both', '1', '2'])
        self.hemisphere_selector.setEnabled(False)
        self.dock_layout.addWidget(self.hemisphere_selector, 1, 1, 1, 1)
        self.hemisphere_selector.setToolTip('Choose the hemisphere(s) where the structure will be highlighted.')

        self.highlight_structure_btn = pyqtw.QPushButton('Highlight Structure')
        self.highlight_structure_btn.clicked.connect(self._highlight_structure_btn_pressed)
        self.highlight_structure_btn.setEnabled(False)
        self.dock_layout.addWidget(self.highlight_structure_btn, 1, 2, 1, 1)

        self.update_atlas_selector()

    def add_rendered_object(self):
        self._add_atlas()

    def delete_rendered_object(self):
        if self.atlas_glvol in self.parent_viewer.gl_view.items:
            self.parent_viewer.gl_view.removeItem(self.atlas_glvol)
            self.atlas_glvol = None

    def update_rendered_object(self):
        if self.atlas_glvol is not None:
            self.update_atlas_transform()
            self.atlas_glvol.setData(self.atlas_rgba_volume)

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
                formatted_online_atlases = {None: 'No internet connection -> downloaded only'}

            self._available_atlases = {**formatted_offline_atlases, **formatted_online_atlases}
        return self._available_atlases
    
    @available_atlases.setter
    def available_atlases(self, value):
        self._available_atlases = value

    def _add_atlas(self):
        self.delete_rendered_object()
        self.init_attributes()

        selected_atlas_description = self.atlas_selector.currentText()

        # def download_atlas_wrapper(online_atlas_name):
        #     bg_atlas = BrainGlobeAtlas(online_atlas_name, check_latest=True)
        #     self._add_atlas()

        if self.test_atlas: # Only when testing application
            pass # TEMPORARY TODO implement proper test
        else:
            if selected_atlas_description is None:
                pass # TODO msg in status bar
            elif selected_atlas_description.endswith('(DOWNLOADED)'):
                offline_atlas_name = selected_atlas_description.split(' | ')[0]
                self.parent_viewer.statusBar().showMessage(f'Loading offline {offline_atlas_name}', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)
                self.bg_atlas = BrainGlobeAtlas(offline_atlas_name, check_latest=False)
            elif selected_atlas_description.endswith('(online)'):
                online_atlas_name = selected_atlas_description.split(' | ')[0]
                
                dialog = AcceptRejectDialog(parent=self.parent_viewer, title='Proceed with Brain Atlas download?', msg=f'Do you want to download {online_atlas_name} ?\nThis might take a few minutes')
                dialog_result = dialog.exec()
                if dialog_result == 1:
                    self.parent_viewer.statusBar().showMessage(f'Downloading {online_atlas_name}')
                    
                    # TODO reimplement threaded download
                    # self.threaded_atlas_download = threading.Thread(
                    #     target=download_atlas_wrapper,
                    #     args=(online_atlas_name,))
                    # self.threaded_atlas_download.start()
                    # TODO allow thread interruption
                    self.bg_atlas = BrainGlobeAtlas(online_atlas_name, check_latest=True)
                    
                else:
                    self.parent_viewer.statusBar().showMessage('Atlas Download Canceled!', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)

        if self.bg_atlas is not None:

            # Set transform str for rat atlas on blank projects
            if self.bg_atlas.atlas_name == 'whs_sd_rat_39um' and self.get_user_param('atlas_transforms_str') == self._DEFAULT_PARAMS['atlas_transforms_str']:
                self.set_user_param('atlas_transforms_str', 'S1.15 Rx-89.3deg Rz180deg Ry-5deg Ty.55mm Tx-5.5mm Tz-9.3mm')

            self.update_structure_selector()
            self.update_atlas_user_params_editors()
            self.parent_viewer.cache.set_attr('atlas.default_atlas_name', self.bg_atlas.atlas_name)

            # TODO -> tranfer to add_rendered_object ???
            self.atlas_glvol = gl.GLVolumeItem(self.atlas_rgba_volume, smooth=True, glOptions='translucent')
            self.parent_viewer.gl_view.addItem(self.atlas_glvol, name='Brain atlas')
            self.atlas_glvol.setDepthValue(1) # GL volumes -> render tree foreground
            self.update_atlas_transform()

        self.update_atlas_selector()

    @property
    def raw_atlas_rgba_volume(self):
        subs_stride = self.get_user_param('subsampling_stride')
        atlas_rgba_vol_id = f'{self.bg_atlas.atlas_name}.{subs_stride}'

        if self._raw_atlas_rgba_volume is None or self._raw_atlas_rgba_volume[0] != atlas_rgba_vol_id:

            # Subsample
            self.ref_atlas = self.bg_atlas.reference[::subs_stride, ::subs_stride, ::subs_stride]
        
            atlas_norm_func = plt.Normalize()
            rgba_vol = plt.cm.Greys_r(atlas_norm_func(self.ref_atlas)) * 255
            rgba_vol[:, :, :, 3] = self.get_user_param('alpha') * 255
            rgba_vol[:, :, :, 3][rgba_vol[:, :, :, 0] < self.get_user_param('black_threshold')] = 0 # Set black regions to transparent

            self._raw_atlas_rgba_volume = (atlas_rgba_vol_id, rgba_vol)
            del rgba_vol

        return self._raw_atlas_rgba_volume[1]

    @property
    def raw_highlighted_structure_volume(self):
        selected_hemisphere = self.get_user_param('highlighted_structure_hemisphere')
        selected_structure = self.get_user_param('highlighted_structure')
        subs_stride = self.get_user_param('subsampling_stride')
        structure_acronym = self.bg_atlas_structures[selected_structure]

        if structure_acronym is None:
            return None
        else:
            highlighted_structure_vol_id = f'{self.bg_atlas.atlas_name}.{subs_stride}.{structure_acronym}.{selected_hemisphere}'

            if self._raw_highlighted_structure_volume is None or self._raw_highlighted_structure_volume[0] != highlighted_structure_vol_id:
                self.parent_viewer.statusBar().showMessage('Loading atlas highlighted structure')
                if selected_hemisphere == 'Both':
                    hemi_struct = self.bg_atlas.get_structure_mask(structure_acronym)
                elif selected_hemisphere == '1' or selected_hemisphere == '2':
                    hemi_struct = self.bg_atlas.get_structure_mask(structure_acronym) * (self.bg_atlas.hemispheres == int(selected_hemisphere)).astype(int)
                self._raw_highlighted_structure_volume = (
                    highlighted_structure_vol_id,
                    hemi_struct[::subs_stride, ::subs_stride, ::subs_stride]
                )
                self.parent_viewer.statusBar().clearMessage()

            return self._raw_highlighted_structure_volume[1]

    @property
    def atlas_resolution(self):
        subs_stride = self.get_user_param('subsampling_stride')
        atlas_res = subs_stride * np.array(self.bg_atlas.resolution) * 1e-6 # um to meters
        return atlas_res
    
    @property
    def brain_atlas_tmat(self):
        if self._brain_atlas_tmat is None:
            resolution = self.atlas_resolution
            atlas_shape = self.raw_atlas_rgba_volume.shape
            self._brain_atlas_tmat = af_tr.scale_mat(resolution)
            self._brain_atlas_tmat = self._brain_atlas_tmat @ af_tr.translat_mat('x', -(resolution[0] * atlas_shape[0]) / 2)
            self._brain_atlas_tmat = self._brain_atlas_tmat @ af_tr.translat_mat('y', -(resolution[1] * atlas_shape[1]) / 2)
            self._brain_atlas_tmat = self._brain_atlas_tmat @ af_tr.translat_mat('z', -(resolution[2] * atlas_shape[2]) / 2)

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
        self._brain_atlas_tmat = value

    def update_atlas_selector(self):
        try: self.atlas_selector.currentIndexChanged.disconnect() 
        except Exception: pass

        self.available_atlases = None
        self.atlas_selector.clear()
        self.atlas_selector.addItems(self.available_atlases.values())

        # Init atlas selector
        default_offline_atlas = self.parent_viewer.cache.get_attr(
            'atlas.default_atlas_name', default_value=self._DEFAULT_PARAMS['default_atlas_name'])
        if f'offline_{default_offline_atlas}' in self.available_atlases.keys():
            self.atlas_selector.setCurrentIndex(list(self.available_atlases.keys()).index(f'offline_{default_offline_atlas}'))

        self.atlas_selector.currentIndexChanged.connect(self._add_atlas)

    def update_structure_selector(self):
        sorted_structure_dict = dict(sorted({f"{struct['name']} ({struct['acronym']})": struct['acronym'] for struct in self.bg_atlas.structures_list}.items()))
        self.bg_atlas_structures = {
            **{'Select structure': None},
            **sorted_structure_dict
        }

        self.structure_selector.clear()
        self.structure_selector.setEnabled(True)
        self.structure_selector.addItems(self.bg_atlas_structures.keys())
        # Set highlighted structure to cached name
        structure = self.get_user_param('highlighted_structure')
        if structure in self.bg_atlas_structures:
            self.structure_selector.setCurrentIndex(list(self.bg_atlas_structures.keys()).index(structure))

        self.hemisphere_selector.setEnabled(True)
        # Set highlighted structure hemisphere to cached name
        structure_hemisphere = self.get_user_param('highlighted_structure_hemisphere')
        self.hemisphere_selector.setCurrentText(structure_hemisphere)

        self.highlight_structure_btn.setEnabled(True)

    def update_atlas_user_params_editors(self):
        self.subsampling_stride_editor.setText(str(self.get_user_param('subsampling_stride')))
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
            atlas_shape = self.ref_atlas.shape
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

    def _highlight_structure_btn_pressed(self):
        selected_structure = self.structure_selector.currentText()
        selected_hemisphere = self.hemisphere_selector.currentText()
        self.set_user_param('highlighted_structure', selected_structure)
        self.set_user_param('highlighted_structure_hemisphere', selected_hemisphere)
        self.update_rendered_object()

    def highlight_structure(self):
        if self.raw_highlighted_structure_volume is not None:
            self._atlas_rgba_volume[self.raw_highlighted_structure_volume != 0, 0] = 200
            self._atlas_rgba_volume[self.raw_highlighted_structure_volume != 0, 1] = 0
            self._atlas_rgba_volume[self.raw_highlighted_structure_volume != 0, 2] = 0
            self._atlas_rgba_volume[self.raw_highlighted_structure_volume != 0, 3] = self.get_user_param('alpha') * 255

    @property
    def atlas_rgba_volume(self):
        self._atlas_rgba_volume = self.raw_atlas_rgba_volume.copy()

        self.compute_slicing_plane()

        self.highlight_structure()
        return self._atlas_rgba_volume

    def compute_slicing_plane(self):
        slicing_plane_pts = self.parent_viewer.slicing_plane_3pts
        if slicing_plane_pts is not None:
            if not self.parent_viewer.postpone_slicing_plane_computation or self._slicing_plane_mask is None:
                raveled_mask = np.dot(
                    self.atlas_voxel_coordinates - slicing_plane_pts[0],
                    np.cross(
                        slicing_plane_pts[1] - slicing_plane_pts[0],
                        slicing_plane_pts[2] - slicing_plane_pts[0]
                    )) > 0
                
                self._slicing_plane_mask = raveled_mask.reshape(self.ref_atlas.shape).astype(int) * self.get_user_param('alpha') * 255

            self._atlas_rgba_volume[:, :, :, 3] = self._slicing_plane_mask
            self._atlas_rgba_volume[:, :, :, 3][self._atlas_rgba_volume[:, :, :, 0] == 0] = 0