from coperniFUS import *
from coperniFUS.modules.module_base import Module


class AnatLandmarksCalib(Module):

    _DEFAULT_PARAMS = {
        'uncal_anatomical_landmarks_coords': { 
            # 'Lambda': [-1e-2, 0, 2e-3],
            # 'Bregma': [0, 0, 0]
        },
        'cal_anatomical_landmarks_coords': {
            # 'Lambda': [-1e-2, 0, 2e-3],
            # 'Bregma': None # not specified
        },
        'cal_tmat': np.eye(4),
    }
    """ Default configuration parameters used when a parameter value is not yet cached """

    _LANDMARKS_STYLES_BY_SUBTYPE = {
        'Uncalibrated': {
            'pt_color': (1, 0, 0, .7), 'pt_size': 18,
        }, 'Calibrated': {
            'pt_color': (0, 1, 0, .7), 'pt_size': 16,
        }
    }

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, 'anat_calib', **kwargs)

        self._anat_landmarks_dict_name2ref = {
            'Uncalibrated': 'uncal_anatomical_landmarks_coords',
            'Calibrated': 'cal_anatomical_landmarks_coords',
        }
        self._anat_landmarks_dict_ref2name = {
            ref: name for name, ref in self._anat_landmarks_dict_name2ref.items()
        }

        self._tooltip_to_landmark_full_name = None
        self._landmarks_calib_tmat = None
        self._landmarks_gl_items = {}

    # --- Module specific public attributes ---

    @property
    def anat_landmarks_dict(self):
        anat_calib_dict = {}
        for landmark_subtype in self._anat_landmarks_dict_ref2name.keys():
            anat_calib_dict[landmark_subtype] = self.get_user_param(landmark_subtype)
        return anat_calib_dict
    
    @property
    def landmark_coords_from_full_name(self):
        """ Dictionary of all landmark coordinates and their associated full names """
        landmark_coords_dict = {
            x[0]: x[1]
            for xs in [[(f'{self._anat_landmarks_dict_ref2name[landmark_subtype]} {landmark_name}', coordinates) for landmark_name, coordinates in anat_sublandmarks_dict.items()] for landmark_subtype, anat_sublandmarks_dict in self.anat_landmarks_dict.items()]
            for x in xs
        }
        return landmark_coords_dict

    def show_anat_calib_debug_trihedras(self):
        """ Show trihedras to debug issues with anatomical calibration transform.
            Uncalibrated and calibrated coordinate frame vizualisation"""
        
        uncal_tmat = self.get_tmat_from_anat_landmarks(
            self.get_user_param('uncal_anatomical_landmarks_coords')
        )
        cal_tmat = self.get_tmat_from_anat_landmarks(
            self.get_user_param('cal_anatomical_landmarks_coords')
        )

        self.parent_viewer.delete_debug_trihedras()
        self.parent_viewer.add_scale_accurate_debug_trihedra(cal_tmat) # TODO TMAT check .T
        self.parent_viewer.add_scale_accurate_debug_trihedra(uncal_tmat)

    def get_tmat_from_anat_landmarks(self, anat_landmarks_dict):
        """ Computes the calibration transformation matrix based on calibrated and uncalibrated landmarks coordinates defined in anat_landmarks_dict
        anat_landmarks_dict should repect the format {'landmark #0': np.array(landmark_coords)}
        
        Note: The current implementation only supports calibrations based on a pair of anatomical landmarks. Please create an issue on GtHub if you have specific needs.
        """

        if len(anat_landmarks_dict) == 2:

            # # Unpack landmarks
            A, B = [np.array(ll) for ll in anat_landmarks_dict.values()]
            y_global = np.array([0, 1, 0])
            # Step 1: Compute the local x-axis
            x_local = B - A
            x_local /= np.linalg.norm(x_local)
            # Step 2: Compute the local z-axis
            z_local = np.cross(x_local, y_global)
            z_local /= np.linalg.norm(z_local)
            # Step 3: Compute the local y-axis
            y_local = np.cross(z_local, x_local)
            # Step 4: Construct the rotation matrix
            R = np.column_stack((x_local, y_local, z_local))
            # Step 5: Combine into a 4x4 transformation matrix
            anat_landmarks_tmat = np.eye(4)
            anat_landmarks_tmat[:3, :3] = R
            # Step 6: Set A as the local origin
            anat_landmarks_tmat[:3, 3] = A
            # Setp 7: Apply scale
            anat_landmarks_scale = np.linalg.norm(A - B)
            anat_landmarks_tmat = anat_landmarks_tmat @ af_tr.scale_mat(anat_landmarks_scale)
            
        else:
            raise NotImplementedError('Evaluation of calibration affine transformations matrix is only implemented for a pair of landmarks at the moment.')
        
        return anat_landmarks_tmat

    def apply_calibration_tmat(self):
        """ Applies the calibration transformation to all affected objects. """

        if len(self.anat_landmarks_dict['cal_anatomical_landmarks_coords']) < 2:
            self.parent_viewer.show_error_popup('Anatomical Calibration', error_description='Please add at least two anatomical landmarks before proceeding.')
            return
        
        if None in self.landmark_coords_from_full_name.values():
            self.parent_viewer.show_error_popup('Anatomical Calibration', error_description='Please make sure that the coordinates of all anatomical landmarks are set before proceeding.')
            return

        try:
            uncal_tmat = self.get_tmat_from_anat_landmarks(
                self.get_user_param('uncal_anatomical_landmarks_coords')
            )
            cal_tmat = self.get_tmat_from_anat_landmarks(
                self.get_user_param('cal_anatomical_landmarks_coords')
            )
        except Exception as e:
            self.parent_viewer.show_error_popup('Anatomical Calibration', error_description=str(e))
            return

        # Calibration matrix evaluation
        calibration_tmat = cal_tmat @ np.linalg.inv(uncal_tmat)

        landmarks_hash = self._get_anat_landmarks_dicts_hash()
        self._landmarks_calib_tmat = (calibration_tmat, landmarks_hash) # tmat + hash for version tracking
        self.parent_viewer.update_rendered_view()
        self._update_calib_tmat_btn_status()

        # Set btn to calibration reset
        self.apply_calibration_tmat_btn.setText('Disable Anatomical Landmark Transformation')

        try: self.apply_calibration_tmat_btn.clicked.disconnect()
        except Exception: pass

        self.apply_calibration_tmat_btn.clicked.connect(self.disable_calibration_tmat)

    def disable_calibration_tmat(self):
        """ Disables the calibration transformation on all affected objects. """
        landmarks_hash = None
        self._landmarks_calib_tmat = (np.eye(4), landmarks_hash) # tmat + hash for version tracking
        self.parent_viewer.update_rendered_view()
        self._update_calib_tmat_btn_status()

        # Set btn to calibration reset
        self.apply_calibration_tmat_btn.setText('Apply Anatomical Landmark Transformation')

        try: self.apply_calibration_tmat_btn.clicked.disconnect()
        except Exception: pass

        self.apply_calibration_tmat_btn.clicked.connect(self.apply_calibration_tmat)

    @property
    def landmarks_calib_tmat(self):
        """ Anatomical calibration affine transformation matrix evaluated in get_tmat_from_anat_landmarks """
        if self._landmarks_calib_tmat is None:
            landmarks_hash = None
            self._landmarks_calib_tmat = (np.eye(4), landmarks_hash) # tmat + hash for version tracking
        return self._landmarks_calib_tmat[0]

    def set_landmark_coordinates_from_tooltip(self):
        """ Sets the coordinates of a unique selected landmark based on the current location of the Tooltip """
        selected_sublandmarks = self._get_sublandmark_selection()
        if not isinstance(selected_sublandmarks, list):
            raise ValueError('selected_sublandmarks should be a list containing selected landmarks.')
        if len(selected_sublandmarks) != 1:
            raise ValueError('Only one sublandmark should be selected to set coordinates.')
        sublandmark_label_item, landmark_header_text, sublandmark_type_label = selected_sublandmarks[0]

        tooltip_loc = list(self.parent_viewer.tooltip.tooltip_tmat[:3, 3])

        self._set_coordinates_to_sublandmark_qtree_item(sublandmark_label_item, tooltip_loc)
        self._on_treeview_edit()
        self._update_anat_landmarks_dict_from_treeview_content()
        self._update_calib_tmat_btn_status()
        self.update_rendered_object()
    
    def update_tooltip_to_landmark(self):
        """ Updates the Tooltip location according to the checkbox selection in the module dock """
        if self._tooltip_to_landmark_full_name is not None and self._tooltip_to_landmark_full_name in self.landmark_coords_from_full_name:

            # Create translation only tmat
            landmark_loc_tooltip_tmat = np.eye(4)
            landmark_loc_tooltip_tmat[:3, 3] = self.landmark_coords_from_full_name[self._tooltip_to_landmark_full_name]

            # Apply tmat to tooltip
            self.parent_viewer.tooltip.release_from_modules(sender_module=self)
            self.parent_viewer.tooltip.tooltip_tmat = landmark_loc_tooltip_tmat
        
        else: # Tooltip NOT on layer centroid
            self.parent_viewer.tooltip.tooltip_tmat = None

        self.parent_viewer.tooltip.update_rendered_object()

    def release_tooltip(self):
        """ Releases the tooltip location from the selected location in the module. Please call CoperniFUS viewer release_from_modules method to release the tooltip from all loaded modules. """
        self._tooltip_to_landmark_full_name = None
        uncheck_all_checkboxes_in_qtree_column(self.model, checkbox_column=1)

    # --- Required module attributes ---

    def init_dock(self):
        """ Called on GUI setup to add a module dock """
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Anatomical Landmarks Calibration', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Tree view and model
        self.tree_view = DynamicallyResizableTreeView()
        self.tree_view.resized.connect(self._on_tree_view_resize)
        self.model = pyqtg.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Anatomical Landmarks", "Tooltip"])
        self.tree_view.setModel(self.model)
        self.dock_layout.addWidget(self.tree_view, 0, 0, 1, 3) # Y, X, h, w
        self._populate_treeview_cached_landmarks()
        self.tree_view.setMaximumHeight(100)

        # Add / Remove Landmarks Buttons
        self.add_landmark_button = pyqtw.QPushButton('+')
        self.add_landmark_button.setFixedWidth(25)
        self.dock_layout.addWidget(self.add_landmark_button, 1, 0, 1, 1) # Y, X, h, w
        self.add_landmark_button.clicked.connect(self._add_landmark_btn_pressed)
        self.add_landmark_button.setToolTip('Add an Anatomical Landmark. Landmarks names can be edited later in the list.')
        
        self.remove_landmark_button = pyqtw.QPushButton('-')
        self.remove_landmark_button.setFixedWidth(25)
        self.dock_layout.addWidget(self.remove_landmark_button, 1, 1, 1, 1) # Y, X, h, w
        self.remove_landmark_button.clicked.connect(self._remove_landmark_btn_pressed)
        self.remove_landmark_button.setToolTip('Remove the selected Anatomical Landmark.')

        # Connect model item changed signal
        self.model.itemChanged.connect(self._handle_landmark_item_change)

        # Set coords btn
        self.set_landmark_from_tooltip_button = pyqtw.QPushButton("Set selected landmark to Tooltip")
        self.set_landmark_from_tooltip_button.setEnabled(False)
        self.set_landmark_from_tooltip_button.clicked.connect(self.set_landmark_coordinates_from_tooltip)
        self.dock_layout.addWidget(self.set_landmark_from_tooltip_button, 1, 2, 1, 1) # Y, X, h, w
        self.set_landmark_from_tooltip_button.setToolTip('To set the coordinates of the landmark place the Tooltip on the desired location, ensure that the landmark to be edited is the only one made visible in the above list.')

        # Landmark to tooltip button
        self.apply_calibration_tmat_btn = pyqtw.QPushButton('Apply Anatomical Landmark Transformation')
        self.apply_calibration_tmat_btn.clicked.connect(self.apply_calibration_tmat)
        self._update_calib_tmat_btn_status()
        self.dock_layout.addWidget(self.apply_calibration_tmat_btn, 2, 0, 1, 3) # Y, X, h, w
        self.apply_calibration_tmat_btn.setToolTip('Once all landmark coordinates are set, coordinate transformation from Uncalibrated to Calibrated spaces can be performed.')

        # Resize to most comptact height
        self.dock.adjustSize()
        self.dock.setMinimumHeight(self.dock.sizeHint().height())
        self.dock.setMaximumHeight(self.dock.sizeHint().height())

    def add_rendered_object(self):
        """ Called when populating the viewer with the module rendered objects """
        self.delete_rendered_object()
        self._add_or_update_landmarks_to_rendered_view(
            self.get_user_param('uncal_anatomical_landmarks_coords'),
            landmark_subtype='Uncalibrated')
        self._add_or_update_landmarks_to_rendered_view(
            self.get_user_param('cal_anatomical_landmarks_coords'),
            landmark_subtype='Calibrated')
        
    def update_rendered_object(self):
        """ Called on render view updates """
        self._add_or_update_landmarks_to_rendered_view(
            self.get_user_param('uncal_anatomical_landmarks_coords'),
            landmark_subtype='Uncalibrated')
        self._add_or_update_landmarks_to_rendered_view(
            self.get_user_param('cal_anatomical_landmarks_coords'),
            landmark_subtype='Calibrated')

    def delete_rendered_object(self):
        """ Called on deletion of the module rendered objects """
        for full_landmark_name in self._landmarks_gl_items:
            if self._landmarks_gl_items[full_landmark_name] in self.parent_viewer.gl_view.items:
                self.parent_viewer.gl_view.removeItem(self._landmarks_gl_items[full_landmark_name])
        self._landmarks_gl_items = {}
        
    # --- Module specific attributes ---

    def _on_tree_view_resize(self):
        self.tree_view.setColumnWidth(0, self.tree_view.width() - 50)
        self.tree_view.setColumnWidth(1, 50-30)

    def _add_or_update_landmarks_to_rendered_view(self, anat_landmarks_dict, landmark_subtype):
        for landmark_name, landmark_coords in anat_landmarks_dict.items():
            # landmark_subtype_ref = self._anat_landmarks_dict_name2ref[landmark_subtype]
            full_landmark_name = f'{landmark_subtype} {landmark_name}'

            if isinstance(landmark_coords, list) and full_landmark_name in self.landmark_coords_from_full_name.keys() and full_landmark_name in self._visible_anat_landmarks_full_names_list: # valid and visible
                landmark_loc = np.array(landmark_coords).reshape((1, 3))

                if full_landmark_name in self._landmarks_gl_items: # Update if True
                    self._landmarks_gl_items[full_landmark_name].setData(pos=landmark_loc)
                    if self._landmarks_gl_items[full_landmark_name] not in self.parent_viewer.gl_view.items:
                        self.parent_viewer.gl_view.addItem(self._landmarks_gl_items[full_landmark_name], name=full_landmark_name)

                else: # Add if False
                    self._landmarks_gl_items[full_landmark_name] = gl.GLScatterPlotItem(
                        pos=landmark_loc,
                        color=self._LANDMARKS_STYLES_BY_SUBTYPE[landmark_subtype]['pt_color'],
                        size=self._LANDMARKS_STYLES_BY_SUBTYPE[landmark_subtype]['pt_size'],
                        pxMode=True, # pt size expressed in pixels
                        glOptions='additive',
                    )
                    self._landmarks_gl_items[full_landmark_name].setDepthValue(5)
                    self.parent_viewer.gl_view.addItem(self._landmarks_gl_items[full_landmark_name], name=full_landmark_name)

            else: # landmark_coords not a list -> delete
                if full_landmark_name in self._landmarks_gl_items:
                    if self._landmarks_gl_items[full_landmark_name] in self.parent_viewer.gl_view.items:
                        self.parent_viewer.gl_view.removeItem(self._landmarks_gl_items[full_landmark_name])

    def _populate_treeview_cached_landmarks(self):
        self._populate_treeview_from_dict(self.anat_landmarks_dict)

    def _get_available_landmark_name(self, landmark_name, sender_item=None):
        """ Alters the provided landmark name if a duplicate exists """
        available_landmark_name = landmark_name
        existing_landmarks_names = [
            item.text() for item in [
                self.model.item(ii, 0) for ii in range(self.model.rowCount())
            ] if item is not sender_item
        ]

        landmark_name_suffix = 1
        while available_landmark_name in existing_landmarks_names:
            available_landmark_name = f'{landmark_name} {landmark_name_suffix}'
            landmark_name_suffix += 1

        return available_landmark_name
    
    def _add_landmark_btn_pressed(self):
        landmark_name = self._get_available_landmark_name('Anatomical Landmark')
        landmark_header_item = pyqtg.QStandardItem(landmark_name)
        landmark_header_item.setEditable(True)
        landmark_header_item.setCheckable(False)
        landmark_header_tooltip = pyqtg.QStandardItem("") # No tooltip checkbox on header
        landmark_header_tooltip.setEditable(False)

        # Append the landmark_header with its two columns items
        self.model.appendRow([landmark_header_item, landmark_header_tooltip])

        # Create sublandmarks items with tooltip checkboxes in the second column
        uncal_sublandmark_label_item = pyqtg.QStandardItem(self._anat_landmarks_dict_ref2name['uncal_anatomical_landmarks_coords'])
        uncal_sublandmark_label_item.setEditable(False)
        uncal_sublandmark_label_item.setCheckable(True)
        self._set_coordinates_to_sublandmark_qtree_item(uncal_sublandmark_label_item, None)
        uncal_sublandmark_tooltip_item = pyqtg.QStandardItem()
        uncal_sublandmark_tooltip_item.setCheckable(True)
        uncal_sublandmark_tooltip_item.setEditable(False)

        cal_sublandmark_label_item = pyqtg.QStandardItem(self._anat_landmarks_dict_ref2name['cal_anatomical_landmarks_coords'])
        cal_sublandmark_label_item.setEditable(False)
        cal_sublandmark_label_item.setCheckable(True)
        self._set_coordinates_to_sublandmark_qtree_item(cal_sublandmark_label_item, None)
        cal_sublandmark_tooltip_item = pyqtg.QStandardItem()
        cal_sublandmark_tooltip_item.setCheckable(True)
        cal_sublandmark_tooltip_item.setEditable(False)

        landmark_header_item.appendRow([uncal_sublandmark_label_item, uncal_sublandmark_tooltip_item])
        landmark_header_item.appendRow([cal_sublandmark_label_item, cal_sublandmark_tooltip_item])

        self._on_treeview_edit()

    def _remove_landmark_btn_pressed(self):
        index = self.tree_view.currentIndex()
        if index.isValid():
            parent = index.parent()
            if not parent.isValid(): # Only allow removing header items
                self.model.removeRow(index.row())
        self._on_treeview_edit()

    def _get_sublandmark_selection(self):
        checked_sublandmarks = []
        for i in range(self.model.rowCount()):
            landmark_header_item = self.model.item(i, 0)
            for j in range(landmark_header_item.rowCount()):
                sublandmark_label_item = landmark_header_item.child(j, 0)
                if sublandmark_label_item.checkState() == pyqtc.Qt.CheckState.Checked:
                    checked_sublandmarks.append((sublandmark_label_item, landmark_header_item.text(), sublandmark_label_item.text()))  # (sublandmark_label_item, landmark_header_text, sublandmark_type_label)
        return checked_sublandmarks

    def _handle_landmark_item_change(self, changed_item):

        # Handle landmark header duplicate names -> add suffix if duplicate
        if changed_item.column() == 0 and changed_item.parent() is None:
            edited_landmark_name = changed_item.text()
            changed_item.setText(self._get_available_landmark_name(edited_landmark_name, sender_item=changed_item))

        # Ignorethe rest of the function if not a checkbox
        if not changed_item.isCheckable():
            return
        state = changed_item.checkState()

        # Allow a single tooltip checkbox to be selected at once
        if changed_item.column() == 1 and changed_item.parent() is not None: # Not a header checkbox -> sublandmark:
            self._tooltip_to_landmark_full_name = None

            if state == pyqtc.Qt.CheckState.Checked:
                # Uncheck all other checkboxes across the entire model
                for i in range(self.model.rowCount()):
                    landmark_header_item = self.model.item(i, 0)
                    for j in range(landmark_header_item.rowCount()):
                        other_tooltip_checkbox = landmark_header_item.child(j, 1)
                        if other_tooltip_checkbox is not changed_item:
                            other_tooltip_checkbox.setCheckState(pyqtc.Qt.CheckState.Unchecked)

                landmark_header_item = changed_item.parent()
                full_landmark_name = f'{landmark_header_item.child(changed_item.row(), 0).text()} {landmark_header_item.text()}'
                self._tooltip_to_landmark_full_name = full_landmark_name
            self.update_tooltip_to_landmark()

        self._update_landmark_from_tooltip_button_state()
        self._on_treeview_edit()

    def _update_landmark_from_tooltip_button_state(self):
        """ Enables set_landmark_from_tooltip_button only when a unique sublandmark is selected """
        if hasattr(self, 'set_landmark_from_tooltip_button'):
            self.set_landmark_from_tooltip_button.setEnabled(len(self._get_sublandmark_selection()) == 1)

    def _set_coordinates_to_sublandmark_qtree_item(self, sublandmark_label_item, coordinates=None):
        """ Set coordinates and update color state """
        if isinstance(coordinates, list) and len(coordinates) == 3:
            sublandmark_label_item.setData(coordinates, pyqtc.Qt.ItemDataRole.ForegroundRole)
        else:
            sublandmark_label_item.setForeground(pyqtg.QColor("red"))
            if coordinates is not None:
                raise ValueError('Attempting to set invalid coordinates to a landmark')

    def _clear_tree_view(self):
        self.model.removeRows(0, self.model.rowCount())

    def _get_treeview_content(self):
        landmarks_dict = {sublandmark_type_id: {} for sublandmark_type_id in self._anat_landmarks_dict_ref2name}
        for i in range(self.model.rowCount()):
            landmark_header_item = self.model.item(i, 0)
            landmark_header_text = landmark_header_item.text()
            for j in range(landmark_header_item.rowCount()):
                sublandmark_label_item = landmark_header_item.child(j, 0)
                sublandmark_label_text = sublandmark_label_item.text()
                coords = sublandmark_label_item.data(pyqtc.Qt.ItemDataRole.ForegroundRole)
                if sublandmark_label_text in self._anat_landmarks_dict_name2ref:
                    landmarks_dict[self._anat_landmarks_dict_name2ref[sublandmark_label_text]][landmark_header_text] = coords if isinstance(coords, list) else None
        return landmarks_dict
    
    def _update_anat_landmarks_dict_from_treeview_content(self):
        treeview_landmark_dict = self._get_treeview_content()
        for landmark_dict_name, anat_landmarks_dict in treeview_landmark_dict.items():
            self.set_user_param(landmark_dict_name, anat_landmarks_dict)

    def _on_treeview_edit(self):
        self._update_anat_landmarks_dict_from_treeview_content()
        self.update_rendered_object()

    def _populate_treeview_from_dict(self, landmarks_dict):
        self._clear_tree_view()
        self.model.removeRows(0, self.model.rowCount())

        anat_landmark_names = set()
        for sublandmark_dict in landmarks_dict.values():
            anat_landmark_names.update(sublandmark_dict.keys())
        anat_landmark_names = sorted(anat_landmark_names)

        for anat_landmark_name in anat_landmark_names:
            landmark_header_item = pyqtg.QStandardItem(anat_landmark_name)
            landmark_header_item.setEditable(True)
            landmark_header_item.setCheckable(False)

            tooltip_checkboxes_col = pyqtg.QStandardItem("") # No tooltip check box on header
            tooltip_checkboxes_col.setEditable(False)

            self.model.appendRow([landmark_header_item, tooltip_checkboxes_col])

            # Add calibrated and uncalibrated landmarks subitems
            for sublandmark_id, sublandmark_label in self._anat_landmarks_dict_ref2name.items():
                sublandmark_label_item = pyqtg.QStandardItem(sublandmark_label)
                sublandmark_label_item.setEditable(False)
                sublandmark_label_item.setCheckable(True)

                sublandmark_tooltip_item = pyqtg.QStandardItem()
                sublandmark_tooltip_item.setCheckable(True)
                sublandmark_tooltip_item.setEditable(False)

                coords = landmarks_dict.get(sublandmark_id, {}).get(anat_landmark_name)
                self._set_coordinates_to_sublandmark_qtree_item(sublandmark_label_item, coords)

                landmark_header_item.appendRow([sublandmark_label_item, sublandmark_tooltip_item])

        self._update_landmark_from_tooltip_button_state()

    @property
    def _visible_anat_landmarks_full_names_list(self):
        visible_full_names = [
            f'{sublandmark_type_label} {landmark_header_text}'
            for sublandmark_label_item, landmark_header_text, sublandmark_type_label
            in self._get_sublandmark_selection()
        ]
        return visible_full_names
    
    def _get_anat_landmarks_dicts_hash(self):
        dicts_hash = object_list_hash([
            self.get_user_param('uncal_anatomical_landmarks_coords'),
            self.get_user_param('cal_anatomical_landmarks_coords')
        ])
        return dicts_hash
    
    def _update_calib_tmat_btn_status(self):
        self.landmarks_calib_tmat # Ensures that self._landmarks_calib_tmat[1] exists
        landmarks_hash = self._get_anat_landmarks_dicts_hash()
        if landmarks_hash == self._landmarks_calib_tmat[1]:
            self.apply_calibration_tmat_btn.setStyleSheet("background-color: green; color: white;")
        else:
            self.apply_calibration_tmat_btn.setStyleSheet("background-color: red; color: white;")