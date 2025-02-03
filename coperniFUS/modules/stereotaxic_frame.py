from coperniFUS import *
from coperniFUS.modules.module_base import Module
from coperniFUS.modules._stereotaxic_frame_helper_classes import *
from coperniFUS.modules.armatures.base_armature import Armature
from coperniFUS.modules.armatures.mesh_armatures import STLMeshArmature, TrimeshScriptArmature, STLMeshBooleanArmature, STLMeshConvexHull
from coperniFUS.modules.armatures.kwave_armatures import KwaveAShomogeneousSimulationArmature, KWave3dSimulationArmature, KWaveAS3dSimulationArmature


class StereotaxicFrame(Module):

    """ --- Stereotaxic Frame posHelper Module ---
    Armatures objects can be found in _armatures_objects attribute.
    """

    AVAILABLE_ARMATURES = [
        'Armature',
        'TrimeshScriptArmature',
        'STLMeshArmature',
        'STLMeshBooleanArmature',
        'STLMeshConvexHull',
        'KwaveAShomogeneousSimulationArmature',
        'KWave3dSimulationArmature',
        'KWaveAS3dSimulationArmature',
    ]

    _DEFAULT_PARAMS = {
        '_steframe_arch_dict': {
            'Main frame': {
                'kWave 3D simulation': None,
            },
            'Skull acoustic window': None,
            'Brain mesh (skull convex Hull)': None,
        },
        '_steframe_armatures_objects_clsnames': {
            'Skull acoustic window': 'STLMeshBooleanArmature',
            'Brain mesh (skull convex Hull)': 'STLMeshConvexHull',
            'kWave 3D simulation': 'KWave3dSimulationArmature',
            'Main frame': 'Armature',
        }
    }

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, 'sterotax_frame', **kwargs)

        self._armatures_objects = {
            armature_display_name: eval(armature_cls_name)(
                armature_display_name=armature_display_name,
                parent_viewer=self.parent_viewer,
                stereotax_frame_instance=self)
            for armature_display_name, armature_cls_name in self.get_user_param('_steframe_armatures_objects_clsnames').items()
        }

    # --- Required module attributes ---

    def init_dock(self):
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Stereotaxic Frame', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Rm button
        self.remove_armature_btn = pyqtw.QPushButton('Remove armature')
        self.remove_armature_btn.clicked.connect(self._remove_selected_armature_from_tree)
        self.dock_layout.addWidget(self.remove_armature_btn, 0, 0, 1, 1) # Y, X, h, w
        # Add button
        self.add_armature_btn = pyqtw.QPushButton('Add armature')
        self.add_armature_btn.clicked.connect(self._add_armature_to_qtree)
        self.dock_layout.addWidget(self.add_armature_btn, 0, 1, 1, 1) # Y, X, h, w

        # Set up the tree view
        self.tree_view = CustomTreeView()
        self.dock_layout.addWidget(self.tree_view, 1, 0, 1, 2) # Y, X, h, w

        # Enable drag and drop
        self.tree_view.setDragDropMode(pyqtw.QTreeView.DragDropMode.InternalMove)
        self.tree_view.setDefaultDropAction(pyqtc.Qt.DropAction.MoveAction)

        # Set the model
        self.model = pyqtg.QStandardItemModel()
        self.tree_view.setModel(self.model)
        self.selection_model = self.tree_view.selectionModel()

        # Populate the tree view with data
        self._update_armatures_qtree()

        # Update view on armature architecture changes
        self.model.rowsRemoved.connect(self.update_rendered_object)
        self.model.rowsInserted.connect(self.update_rendered_object)

        # Edit armature configuration
        self.edit_armature_configuration_btn = pyqtw.QPushButton('Edit armature configuration')
        self.edit_armature_configuration_btn.clicked.connect(self._edit_armature_configuration)
        self.dock_layout.addWidget(self.edit_armature_configuration_btn, 2, 0, 1, 2) # Y, X, h, w
        self.edit_armature_configuration_btn.setEnabled(False)

        # Armature parameters widgets group
        self.armature_parameters_groupbox = pyqtw.QGroupBox("Armature parameters")
        self.armature_parameters_stacked_widget = pyqtw.QStackedWidget()
        armature_parameters_layout = pyqtw.QVBoxLayout()
        armature_parameters_layout.addWidget(self.armature_parameters_stacked_widget)
        self.armature_parameters_groupbox.setLayout(armature_parameters_layout)
        self.dock_layout.addWidget(self.armature_parameters_groupbox, 3, 0, 1, 2) # Y, X, h, w

        # Remove padding
        self.armature_parameters_groupbox.setContentsMargins(0, 20, 0, 0)
        self.armature_parameters_stacked_widget.setContentsMargins(0, 0, 0, 0)
        armature_parameters_layout.setContentsMargins(0, 0, 0, 0)

    def add_rendered_object(self):
        self.populate_armature_parameters_stacked_widget()
        self.update_armature_inheritance(gl_objects_exist=False)
        # for arm_name, arm_obj in self._armatures_objects.items(): # WINDOWS_DEBUGG
        #     arm_obj.add_render()

    def delete_rendered_object(self):
        for arm_name, arm_obj in self._armatures_objects.items():
            arm_obj.delete_render()

    def update_rendered_object(self):
        self.update_armature_inheritance()
        for arm_name, arm_obj in self._armatures_objects.items():

            arm_obj.update_render()
        self.update_tooltip_on_armature()

    # --- Module specific attributes ---

    @property
    def armatures_objects(self):
        """ Returns armatures objects loaded in the stereotaxic module """
        return self._armatures_objects

    def _update_armatures_qtree(self):
        # Disconnect signals if they exist
        try: self.selection_model.selectionChanged.disconnect() 
        except Exception: pass
        try: self.model.itemChanged.disconnect() 
        except Exception: pass

        # Clear tree
        self.model.clear()

        # Populate tree
        root_item = self.model.invisibleRootItem()
        self.model.setHorizontalHeaderLabels(["Armatures", "Tooltip"])
        self._populate_qtree(root_item, self.get_user_param('_steframe_arch_dict'))
        self._init_armatures_visibility_checkboxes()
        self.tree_view.expand_all_items(self.model)

        # (Re)connect the item changed signal to enforce single selection
        self.model.itemChanged.connect(self._on_checkbox_checked)
        # (Re)connect the selection model's selectionChanged signal
        self.selection_model.selectionChanged.connect(self._on_item_selected)

        # Set column widths
        self.tree_view.setColumnWidth(0, 300) # Set width of the first column (Key)
    
    def _add_armature_to_qtree(self):
        self.new_armature_popup = NewArmaturePopup(
            self.parent_viewer, sterotaxframe_obj=self,
        )
        if self.new_armature_popup.exec():

            # --- Add armature to _armatures_objects
            armature_obj = eval(self.new_armature_popup.new_armature_class)(
                armature_display_name=self.new_armature_popup.new_armature_display_name,
                parent_viewer=self.parent_viewer,
                stereotax_frame_instance=self)
            self._armatures_objects[self.new_armature_popup.new_armature_display_name] = armature_obj

            # --- Add to stacked parameter editor widgets ---
            self.armature_parameters_stacked_widget.addWidget(
                armature_obj.params_editor_widget.armature_params_editor_widget)

            # --- Add armature to _steframe_armatures_objects_clsnames ---
            armatures_objects_clsnames = self.get_user_param('_steframe_armatures_objects_clsnames')
            armatures_objects_clsnames[self.new_armature_popup.new_armature_display_name] = self.new_armature_popup.new_armature_class
            self.set_user_param('_steframe_armatures_objects_clsnames', armatures_objects_clsnames)

            # --- Add armature to _steframe_arch_dict ---
            arch_dict = self.get_user_param('_steframe_arch_dict')
            arch_dict[self.new_armature_popup.new_armature_display_name] = None
            self.set_user_param('_steframe_arch_dict', arch_dict)

            self._update_armatures_qtree()

    def _remove_selected_armature_from_tree(self):
        selected_armature = self.qtree_selected_armature
        if selected_armature is not None:

            # --- Pop armature from _steframe_arch_dict ---
            def pop_nested_key(d, key, popped_armature_childs=None):
                if isinstance(d, dict):
                    if key in d:
                        popped_armature_childs = d[key]
                        d.pop(key, None)
                    for k, v in d.items():
                        popped_armature_childs = pop_nested_key(v, key, popped_armature_childs)
                return popped_armature_childs

            arch_dict = self.get_user_param('_steframe_arch_dict')
            popped_armature_childs = pop_nested_key(arch_dict, selected_armature)
            if isinstance(popped_armature_childs, dict):
                arch_dict = {**arch_dict, **popped_armature_childs} # Add childs to the end of dict
            self.set_user_param('_steframe_arch_dict', arch_dict)

            # --- Pop armature from _steframe_armatures_objects_clsnames ---
            armatures_objects_clsnames = self.get_user_param('_steframe_armatures_objects_clsnames')
            if selected_armature in armatures_objects_clsnames:
                armatures_objects_clsnames.pop(selected_armature)
            self.set_user_param('_steframe_armatures_objects_clsnames', armatures_objects_clsnames)

            # --- Remove from stacked parameter editor widgets ---
            try:
                popped_armature_index = list(self._armatures_objects.keys()).index(selected_armature)
                widget_to_remove = self.armature_parameters_stacked_widget.widget(popped_armature_index)
                self.armature_parameters_stacked_widget.removeWidget(widget_to_remove)
                widget_to_remove.deleteLater()
            except ValueError as e: # selected_armature not in self._armatures_objects
                print('selected_armature not in self._armatures_objects')

            # --- Pop armature from _armatures_objects ---
            if selected_armature in self._armatures_objects:
                popped_armature_obj = self._armatures_objects.pop(selected_armature)
                popped_armature_obj.delete_render()

            self._update_armatures_qtree()

    def _set_checkbox_states(self, item, value_dict, checkbox_column=0):
        if item.hasChildren():
            for i in range(item.rowCount()):
                child_item = item.child(i)
                if child_item is not None:
                    armature_name = child_item.text()
                    if armature_name is not None and armature_name in value_dict:
                        checkbox = item.child(i, checkbox_column)
                        checkbox.setCheckState(
                            pyqtc.Qt.CheckState.Checked if value_dict[armature_name] else pyqtc.Qt.CheckState.Unchecked)
                        self._set_checkbox_states(child_item, value_dict, checkbox_column=checkbox_column)

    def _init_armatures_visibility_checkboxes(self):
        root_item = self.model.invisibleRootItem()
        armature_visibility = {arm_name: arm_obj.visible for arm_name, arm_obj in self._armatures_objects.items()}
        self._set_checkbox_states(root_item, armature_visibility, checkbox_column=0)

    @property
    def qtree_selected_armature(self):
        selected_armature = None
        indexes = self.tree_view.selectedIndexes()
        if indexes:
            selected_armature = indexes[0].data()
        return selected_armature
    
    @property
    def qtree_selected_armature_object(self):
        selected_armature_obj = None
        selected_armature_name = self.qtree_selected_armature
        if selected_armature_name:
            selected_armature_obj = self._armatures_objects[self.qtree_selected_armature]
        return selected_armature_obj

    def _edit_armature_configuration(self):
        armature_object = self.qtree_selected_armature_object
        if armature_object:
            self.armature_editor_popup = ArmatureTextEditPopup(
                self.parent_viewer,
                armature_object=armature_object,
                dark_mode=self.parent_viewer._is_dark_mode,
                armature_config_csts_str=nested_dict_formatter(armature_object.armature_config_csts),
                uneval_armature_config_dict_str=nested_dict_formatter(armature_object.uneval_armature_config_dict),
            )
            if self.armature_editor_popup.exec():
                armature_object.armature_config_csts = self.armature_editor_popup.edited_armature_config_csts
                armature_object.uneval_armature_config_dict = self.armature_editor_popup.edited_uneval_armature_config_dict
                armature_object.armature_config_dict = None # Reset evaluated armature_config_dict
                self.parent_viewer.statusBar().showMessage('Applying armature configuration', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)

                self._update_armature_parameters_widgets_on_configuration_change(armature_object)

                armature_object.delete_render()
                armature_object.add_render()
                self.parent_viewer.update_rendered_view()
            else:
                self.parent_viewer.statusBar().showMessage('Armature configuration edition canceled', self.parent_viewer._STATUS_BAR_MSG_TIMEOUT)

    def _update_armature_parameters_widgets_on_configuration_change(self, armature_object):
        stacked_widget_index = list(self._armatures_objects.keys()).index(armature_object.armature_display_name) + 1

        # Remove current param widget
        current_params_widget = self.armature_parameters_stacked_widget.widget(stacked_widget_index)
        self.armature_parameters_stacked_widget.removeWidget(current_params_widget)
        current_params_widget.deleteLater() # Free memory

        # Recreate params_editor_widget
        armature_object.params_editor_widget = ArmatureParamsEditorWidget(
            parent_viewer=self.parent_viewer,
            armature_object=armature_object
        )
        self.armature_parameters_stacked_widget.insertWidget(stacked_widget_index, armature_object.params_editor_widget.armature_params_editor_widget)
        self.armature_parameters_stacked_widget.setCurrentIndex(stacked_widget_index)

    def _get_checkbox_states_dict(self, checkbox_column=0, clicked_item=None):
        
        def _get_checkbox_states(item, checkbox_column=0, clicked_item=None):
            if item.hasChildren():
                result = []
                for i in range(item.rowCount()):
                    child_item = item.child(i)
                    if child_item is not None:
                        armature_name = child_item.text()
                        checkbox = item.child(i, checkbox_column)
                        checkbox_state = checkbox.checkState() == pyqtc.Qt.CheckState.Checked
                        if clicked_item is not None: # Allow only emitter to be checked
                            if checkbox_state and checkbox != clicked_item:
                                checkbox.setCheckState(pyqtc.Qt.CheckState.Unchecked)
                                checkbox_state = False
                        child_value = _get_checkbox_states(
                            child_item,
                            checkbox_column=checkbox_column,
                            clicked_item=clicked_item)
                        if child_value is not None:
                            result = [*result, (armature_name, checkbox_state), *child_value]
                        else:
                            result = [*result, (armature_name, checkbox_state)]
                return result
        
        root_item = self.model.invisibleRootItem()
        states_list = _get_checkbox_states(root_item, checkbox_column, clicked_item)
        states_dict = {key: val for (key, val) in states_list}
        return states_dict
    
    def _get_nested_dict_inheritance(self, nested_dict, parent_key=None, depth=0, result=None):
        if result is None:
            result = {}
        if nested_dict is None:
            result = {}
        else:
            for key, value in nested_dict.items():
                # Add the current key with its parent and depth
                result[key] = (parent_key, depth)
                if isinstance(value, dict):
                    # Recurse into nested dictionary
                    self._get_nested_dict_inheritance(value, key, depth + 1, result)
        return result
        
    def update_armature_inheritance(self, gl_objects_exist=True):
        qtree_as_dict = self.get_armature_tree_as_dict()
        if qtree_as_dict is not None:
            self.set_user_param('_steframe_arch_dict', qtree_as_dict)
        unsorted_hierarchy_dict = self._get_nested_dict_inheritance(self.get_user_param('_steframe_arch_dict'))
        self.stereotaxic_frame_hierarchy = {k: v[0] for k, v in sorted(unsorted_hierarchy_dict.items(), key=lambda item: item[1][1])}

        for child_armature_name, parent_armature_name in self.stereotaxic_frame_hierarchy.items():
            # stime = time.time()
            if child_armature_name in self._armatures_objects:
                if parent_armature_name is not None and parent_armature_name in self._armatures_objects:
                    self._armatures_objects[child_armature_name].parent_transform_mat = self._armatures_objects[parent_armature_name].end_transform_mat
                else:
                    self._armatures_objects[child_armature_name].parent_transform_mat = None

    def _on_checkbox_checked(self, item):
        # Armature column
        armature_column = 0
        if item.column() == armature_column:
            _visible_armatures_checkbox_states = self._get_checkbox_states_dict(
                checkbox_column=armature_column)
            for arm_name, arm_obj in self._armatures_objects.items():
                if arm_name in _visible_armatures_checkbox_states:
                    arm_obj.visible = _visible_armatures_checkbox_states[arm_name]
            self.update_rendered_object()

        # Tooltip column
        tooltip_column = 1
        if item.column() == tooltip_column:
            if item.checkState() == pyqtc.Qt.CheckState.Checked:
                self._tooltip_checkbox_states = self._get_checkbox_states_dict(
                    checkbox_column=tooltip_column,
                    clicked_item=item)
            else:
                self._tooltip_checkbox_states = self._get_checkbox_states_dict(
                    checkbox_column=tooltip_column)
            
            # Setting Tooltip to armature
            self.reset_tooltip_on_armatures()
            selected_armature_tooltips = [armature_name for armature_name, tooltip_checkbox_state in self._tooltip_checkbox_states.items() if tooltip_checkbox_state is True]
            if len(selected_armature_tooltips) > 0:
                armature_object = self._armatures_objects[selected_armature_tooltips[0]]
                armature_object.tooltip_on_armature = True

            self.parent_viewer.update_rendered_view()

    def reset_tooltip_on_armatures(self):
        for arm_name, arm_obj in self._armatures_objects.items():
            arm_obj.tooltip_on_armature = False

    def update_tooltip_on_armature(self):
        default_tooltip_loc = True
        for arm_name, arm_obj in self._armatures_objects.items():
            if arm_obj.tooltip_on_armature is True:
                self.parent_viewer.tooltip.tooltip_tmat = arm_obj.armature_tooltip_tmat
                default_tooltip_loc = False
                break
        if default_tooltip_loc: # If no tooltip on arm checkbox are checked
            self.parent_viewer.tooltip.tooltip_tmat = None

    def populate_armature_parameters_stacked_widget(self):
        placeholder_armature_parameters = pyqtw.QWidget()
        self.armature_parameters_stacked_widget.addWidget(placeholder_armature_parameters)
        for arm_name, arm_obj in self._armatures_objects.items():
            self.armature_parameters_stacked_widget.addWidget(
                arm_obj.params_editor_widget.armature_params_editor_widget)

    def update_armature_parameters_groupbox(self, armature_object):
        if armature_object is None or armature_object.armature_display_name not in self._armatures_objects:
            self.armature_parameters_stacked_widget.setCurrentIndex(0)
        else:
            stacked_widget_index = list(self._armatures_objects.keys()).index(armature_object.armature_display_name) + 1
            self.armature_parameters_stacked_widget.setCurrentIndex(stacked_widget_index)

    def reset_highlighted_armatures(self):
        for arm_name, arm_obj in self._armatures_objects.items():
            arm_obj.highlighted_in_render = False

    def _on_item_selected(self, selected):
        self.reset_highlighted_armatures()

        indexes = selected.indexes()
        if indexes:
            selected_armature_name = indexes[0].data() # Get the first selected index
            armature_object = self._armatures_objects[selected_armature_name]
            self.edit_armature_configuration_btn.setText(f'Edit {selected_armature_name} configuration')
            self.edit_armature_configuration_btn.setEnabled(True)

            # Highlight armature
            armature_object.highlighted_in_render = True
            self.update_rendered_object()

            self.update_armature_parameters_groupbox(
                armature_object=armature_object,
            )
        else:
            self.update_armature_parameters_groupbox(armature_object=None)
            self.edit_armature_configuration_btn.setText('Edit armature configuration')
            self.edit_armature_configuration_btn.setEnabled(False)
    
    def get_armature_tree_as_dict(self):
        """ Returns stereotaxic frame the armatures tree structure as a Python dictionary. """

        def _qtree_to_dict(item):
            """Recursively converts a QStandardItem back to a Python dictionary."""
            if item.hasChildren():
                result = {}
                for i in range(item.rowCount()):
                    child_item = item.child(i)
                    if child_item is not None:
                        child_key = child_item.text()
                        child_value = _qtree_to_dict(child_item)
                        result[child_key] = child_value
                    else:
                        result = None
                return result
            else:
                return None
        
        root_item = self.model.invisibleRootItem()
        try:
            qtree_as_dict = _qtree_to_dict(root_item)
        except TypeError:
            qtree_as_dict = None
        return qtree_as_dict

    def _populate_qtree(self, parent, data):
        """ Recursively adds dictionary elements to the tree view. """
        if isinstance(data, dict):
            for key, value in data.items():
                key_item = pyqtg.QStandardItem(key)
                key_item.setFlags(key_item.flags() | pyqtc.Qt.ItemFlag.ItemIsAutoTristate | pyqtc.Qt.ItemFlag.ItemIsUserCheckable)
                key_item.setCheckState(pyqtc.Qt.CheckState.Unchecked)
                key_item.setEditable(False)

                tooltip_checkbox_item = pyqtg.QStandardItem()
                tooltip_checkbox_item.setCheckable(True)
                tooltip_checkbox_item.setEditable(False)
                parent.appendRow([key_item, tooltip_checkbox_item])
                if value is not None:
                    self._populate_qtree(key_item, value)
        else:
            key_item = pyqtg.QStandardItem(str(data))
            key_item.setFlags(key_item.flags() | pyqtc.Qt.ItemFlag.ItemIsAutoTristate | pyqtc.Qt.ItemFlag.ItemIsUserCheckable)
            key_item.setCheckState(pyqtc.Qt.CheckState.Unchecked)
            key_item.setEditable(False)

            tooltip_checkbox_item = pyqtg.QStandardItem()
            tooltip_checkbox_item.setCheckable(True)
            tooltip_checkbox_item.setEditable(False)
            parent.appendRow([key_item, tooltip_checkbox_item])
