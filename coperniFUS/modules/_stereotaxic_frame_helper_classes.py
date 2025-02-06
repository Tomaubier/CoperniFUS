from coperniFUS import *


class PythonSyntaxHighlighter(pyqtg.QSyntaxHighlighter):
    def __init__(self, document, dark_mode=False):
        super().__init__(document)
        self.highlighting_rules = []

        # Determine color scheme based on the theme
        if dark_mode:
            keyword_color = pyqtg.QColor("#ffb86c")
            string_color = pyqtg.QColor("#f1fa8c")
            comment_color = pyqtg.QColor("#6272a4")
            function_color = pyqtg.QColor("#8be9fd")
            bracket_color = pyqtg.QColor("#ff79c6")
            number_color = pyqtg.QColor("#bd93f9")
            variable_color = pyqtg.QColor("#50fa7b")
        else:
            keyword_color = pyqtg.QColor("blue")
            string_color = pyqtg.QColor("green")
            comment_color = pyqtg.QColor("gray")
            function_color = pyqtg.QColor("darkRed")
            bracket_color = pyqtg.QColor("darkMagenta")
            number_color = pyqtg.QColor("darkBlue")
            variable_color = pyqtg.QColor("darkGreen")

        # Brackets and parentheses
        bracket_format = pyqtg.QTextCharFormat()
        bracket_format.setForeground(bracket_color)
        bracket_patterns = [
            r"\(", r"\)", r"\[", r"\]", r"\{", r"\}"
        ]
        for pattern in bracket_patterns:
            bracket_pattern = pyqtc.QRegularExpression(pattern)
            self.highlighting_rules.append((bracket_pattern, bracket_format))

        # Numbers (integers, floats, and scientific notation)
        number_format = pyqtg.QTextCharFormat()
        number_format.setForeground(number_color)
        number_pattern = pyqtc.QRegularExpression(r"\b\d+(\.\d+)?([eE][+-]?\d+)?\b")
        self.highlighting_rules.append((number_pattern, number_format))

        # Variable names (assuming variables follow Python naming conventions)
        variable_format = pyqtg.QTextCharFormat()
        variable_format.setForeground(variable_color)
        variable_pattern = pyqtc.QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
        self.highlighting_rules.append((variable_pattern, variable_format))

        # Strings
        string_format = pyqtg.QTextCharFormat()
        string_format.setForeground(string_color)
        string_pattern = pyqtc.QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"')
        self.highlighting_rules.append((string_pattern, string_format))
        string_pattern = pyqtc.QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'")
        self.highlighting_rules.append((string_pattern, string_format))

        # Keywords
        keyword_format = pyqtg.QTextCharFormat()
        keyword_format.setForeground(keyword_color)
        keyword_format.setFontWeight(pyqtg.QFont.Weight.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def", 
            "del", "elif", "else", "except", "False", "finally", "for", 
            "from", "global", "if", "import", "in", "is", "lambda", "None", 
            "nonlocal", "not", "or", "pass", "raise", "return", "True", 
            "try", "while", "with", "yield"
        ]
        for word in keywords:
            pattern = pyqtc.QRegularExpression(rf"\b{word}\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Comments
        comment_format = pyqtg.QTextCharFormat()
        comment_format.setForeground(comment_color)
        comment_pattern = pyqtc.QRegularExpression(r"#.*")
        self.highlighting_rules.append((comment_pattern, comment_format))

        # Function names
        function_format = pyqtg.QTextCharFormat()
        function_format.setFontItalic(True)
        function_format.setForeground(function_color)
        function_pattern = pyqtc.QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\()")
        self.highlighting_rules.append((function_pattern, function_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = pattern.globalMatch(text)
            while expression.hasNext():
                match = expression.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
        self.setCurrentBlockState(0)


class ArmatureTextEditPopup(pyqtw.QDialog):

    FONT_SIZE = 13

    def __init__(self, parent_viewer, armature_object, dark_mode=False, armature_config_csts_str=None, uneval_armature_config_dict_str=None):
        self.parent_viewer = parent_viewer
        self.armature_object = armature_object

        super().__init__(self.parent_viewer)

        self._edited_armature_config_csts = None
        self._edited_uneval_armature_config_dict = None

        # Layout for the dialog
        layout = pyqtw.QVBoxLayout()
        self.setLayout(layout)
        splitter = pyqtw.QSplitter(pyqtc.Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        # csts_editor_title = pyqtw.QLabel('Joints constants definition')
        # splitter.addWidget(csts_editor_title)
        csts_editor_group_box = pyqtw.QGroupBox("Armature constants definition")
        csts_editor_layout = pyqtw.QVBoxLayout()
        csts_editor_layout.setContentsMargins(0, 0, 0, 0)
        csts_editor_group_box.setLayout(csts_editor_layout)
        splitter.addWidget(csts_editor_group_box)

        # Set up the QTextEdit widgets
        self.armature_config_csts_editor = pyqtw.QTextEdit(self)
        if armature_config_csts_str is not None:
            self.armature_config_csts_editor.setText(armature_config_csts_str)
        # Set the font to Fira Code
        font = pyqtg.QFont("Fira Code", self.FONT_SIZE)
        self.armature_config_csts_editor.setFont(font)
        # Apply the Python syntax highlighter
        self.armature_config_csts_highlighter = PythonSyntaxHighlighter(self.armature_config_csts_editor.document(), dark_mode)
        csts_editor_layout.addWidget(self.armature_config_csts_editor)

        # joints_editor_title = pyqtw.QLabel('Joints definition')
        # splitter.addWidget(joints_editor_title)
        joints_editor_group_box = pyqtw.QGroupBox("Armature configuration definition - Constant values defined above can be used in expressions by calling csts (eg. \"csts['constant_A'] * np.sin(np.deg2rad(csts['constant_B']))\" )")
        joints_editor_layout = pyqtw.QVBoxLayout()
        joints_editor_layout.setContentsMargins(0, 0, 0, 0)
        joints_editor_group_box.setLayout(joints_editor_layout)
        splitter.addWidget(joints_editor_group_box)

        # Set up the QTextEdit widgets
        self.armature_config_dict_editor = pyqtw.QTextEdit(self)
        if uneval_armature_config_dict_str is not None:
            self.armature_config_dict_editor.setText(uneval_armature_config_dict_str)
        # Set the font to Fira Code
        font = pyqtg.QFont("Fira Code", self.FONT_SIZE)
        self.armature_config_dict_editor.setFont(font)
        # Apply the Python syntax highlighter
        self.armature_config_dict_highlighter = PythonSyntaxHighlighter(self.armature_config_dict_editor.document(), dark_mode)
        joints_editor_layout.addWidget(self.armature_config_dict_editor)

        # Set up the button box
        self.button_box = pyqtw.QDialogButtonBox(
            pyqtw.QDialogButtonBox.StandardButton.Cancel | pyqtw.QDialogButtonBox.StandardButton.Ok)
        # Connect buttons to actions
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.on_accept)
        layout.addWidget(self.button_box)

        self.setWindowTitle(f'Armature editor - {self.armature_object.armature_display_name} ({self.armature_object.__class__.__name__})')
        self.setGeometry(*(self.parent_viewer._get_screen_dimensions() * .1).astype(int), *(self.parent_viewer._get_screen_dimensions() * .8).astype(int))
        splitter.setSizes((self.parent_viewer._get_screen_dimensions()[1] * np.array([.3, .7])).astype(int))

    def parse_edited_dictionnaries(self):
        is_data_valid = False
        armature_config_csts_str = self.armature_config_csts_editor.toPlainText()
        uneval_armature_config_dict_str = self.armature_config_dict_editor.toPlainText()

        # Default to empty dict if armature_config_csts_str contains no text
        if len(armature_config_csts_str) < 2:
            armature_config_csts_str = "{}"

        try:
            self._edited_armature_config_csts = eval(armature_config_csts_str)
            is_data_valid = True
        except Exception as e:
            is_data_valid = False

            self.parent_viewer.show_error_popup(
                f"Error in {self.armature_object.armature_display_name} armature constants definition",
                f'{type(e).__name__}: {str(e)}'
            )

        if is_data_valid:
            try:
                self._edited_uneval_armature_config_dict = eval(uneval_armature_config_dict_str)
                # check transforms args values str expr validity
                self.armature_object.evaluate_armature_config_dict(self._edited_uneval_armature_config_dict, self._edited_armature_config_csts, raise_errors=True)
                is_data_valid = True
            except Exception as e:
                is_data_valid = False

                self.parent_viewer.show_error_popup(
                    f"Error in {self.armature_object.armature_display_name} armature parameter definition",
                    f'{type(e).__name__}: {str(e)}'
                )

        return is_data_valid

    def on_accept(self):
        # Check if the input is valid
        if self.parse_edited_dictionnaries():
            # If valid, close the dialog with accept()
            self.accept()

    @property
    def edited_armature_config_csts(self):
        return self._edited_armature_config_csts
    
    @property
    def edited_uneval_armature_config_dict(self):
        return self._edited_uneval_armature_config_dict


class CustomTreeView(pyqtw.QTreeView):

    def expand_all_items(self, model):
        # Recursively expand all items
        def expand_index(index):
            if not index.isValid():
                return
            self.expand(index)
            for i in range(model.rowCount(index)):
                child_index = model.index(i, 0, index)
                expand_index(child_index)

        # Start with the root index
        root_index = model.index(0, 0, model.invisibleRootItem().index())
        expand_index(root_index)


class ArmatureParamsEditorWidget:

    def __init__(self, parent_viewer, armature_object):
        self.parent_viewer = parent_viewer
        self.armature_object = armature_object
        self._armature_params_editor_gui_elements = None
        self._armature_params_editor_widget = None

    def increment_button_pressed(self, param_gui_order_ii, increment_sign=1):
        gui_elems = self.armature_params_editor_gui_elements_dict[param_gui_order_ii]
        nested_keys = gui_elems['nested_keys']

        param_flat_dict = self.armature_object.armature_config_dict
        for nested_key in nested_keys:
            param_flat_dict = param_flat_dict[nested_key]

        increment = param_flat_dict['_edit_increment']
        og_value = param_flat_dict['args'][1]
        unit = param_flat_dict['_unit']
        new_value = og_value + increment_sign * increment

        gui_elems['_value_editor'][1].setText(si_format(new_value, format_str='{value} {prefix}'+unit))
        self.armature_object._update_armature_dict_value(nested_keys, new_value)

        self.parent_viewer.update_rendered_view()

    def value_edited(self, param_gui_order_ii):
        gui_elems = self.armature_params_editor_gui_elements_dict[param_gui_order_ii]
        nested_keys = gui_elems['nested_keys']
        unit = gui_elems['unit']

        # Parse value
        value_editor_text = gui_elems['_value_editor'][1].text().replace(' ', '') # remove spaces
        value_editor_text = value_editor_text[:-len(unit)] # remove unit text
        new_value = si_parse(value_editor_text.replace('u', 'µ'))

        param_flat_dict = self.armature_object.armature_config_dict
        for nested_key in nested_keys:
            param_flat_dict = param_flat_dict[nested_key]

        gui_elems['_value_editor'][1].setText(si_format(new_value, format_str='{value} {prefix}'+unit))
        self.armature_object._update_armature_dict_value(nested_keys, new_value)

        self.parent_viewer.update_rendered_view()

    @property
    def armature_params_editor_gui_elements_dict(self):
        if self._armature_params_editor_gui_elements is None:
            
            # Retreive parameters to add to the editor
            editable_nested_keys = recursive_key_finder(self.armature_object.armature_config_dict, target_key='_is_editable')
            editable_nested_keys = [nkey[0] for nkey in editable_nested_keys if nkey[1] is True] # Discard params where _is_editable is set to False

            # --- Setup gui element order (based on forced location) ---
            param_gui_order_ii = 0
            armature_params_editor_gui_elements_order = {}
            # Add elements with constrained order
            for nested_keys in editable_nested_keys:
                param_flat_dict = self.armature_object.armature_config_dict
                for nested_key in nested_keys:
                    param_flat_dict = param_flat_dict[nested_key]
                if '_force_gui_location_to' in param_flat_dict:
                    param_id = '&&'.join(nested_keys) # Create unique id from nested_keys
                    armature_params_editor_gui_elements_order[param_id] = param_flat_dict['_force_gui_location_to']
                    param_gui_order_ii += 1

            # Add elements with unconstrained order
            for nested_keys in editable_nested_keys:
                param_flat_dict = self.armature_object.armature_config_dict
                for nested_key in nested_keys:
                    param_flat_dict = param_flat_dict[nested_key]
                if '_force_gui_location_to' not in param_flat_dict:
                    param_id = '&&'.join(nested_keys) # Create unique id from nested_keys
                    armature_params_editor_gui_elements_order[param_id] = param_gui_order_ii
                    param_gui_order_ii += 1

            # --- Populate armature_params_editor_gui_elements_dict ---
            self._armature_params_editor_gui_elements = {}

            for nested_keys in editable_nested_keys:
                param_flat_dict = self.armature_object.armature_config_dict
                for nested_key in nested_keys:
                    param_flat_dict = param_flat_dict[nested_key]
                    
                default_value = param_flat_dict['args'][1]
                if '_unit' in param_flat_dict:
                    unit = param_flat_dict['_unit']
                else:
                    unit = ''
                
                if '_color' in param_flat_dict:
                    color = param_flat_dict['_color']
                    if color == 'x_RED':
                        color = self.parent_viewer.x_RED
                    elif color == 'y_GREEN':
                        color = self.parent_viewer.y_GREEN
                    elif color == 'z_BLUE':
                        color = self.parent_viewer.z_BLUE
                else:
                    color = 'grey'
                if '_param_label' in param_flat_dict:
                    param_label = param_flat_dict['_param_label']
                else: # Transform degree of freedom label as default
                    transf_axis = param_flat_dict['args'][0].upper()
                    param_label = f'{nested_keys[0]} {transf_axis} {nested_keys[-1].split("_")[0]}'

                # Gui location
                param_id = '&&'.join(nested_keys) # Unique id from nested_keys
                param_gui_order_ii = armature_params_editor_gui_elements_order[param_id]

                # Init transform widgets
                armature_param_label = pyqtw.QLabel(param_label)
                minus_button = pyqtw.QPushButton('-')
                plus_button = pyqtw.QPushButton('+')
                try:
                    value_editor = pyqtw.QLineEdit(si_format(default_value, format_str='{value} {prefix}'+unit))
                except TypeError as e:
                    self.parent_viewer.show_error_popup(
                        f"Error in {self.armature_object.armature_display_name} armature parameter definition",
                        f'{type(e).__name__}: Attempting to set {param_label} value editor widget of {self.armature_object.armature_display_name} armature with an object whose type is not supported by si_format\n\nOriginal error message:\n{str(e)}'
                    )
                    value_editor = pyqtw.QLineEdit(si_format(0, format_str='{value} {prefix}'+unit))
                    value_editor.setEnabled(False)

                # Connect signals
                minus_button.clicked.connect(
                    functools.partial(self.increment_button_pressed, param_gui_order_ii, -1))
                plus_button.clicked.connect(
                    functools.partial(self.increment_button_pressed, param_gui_order_ii, 1))
                value_editor.editingFinished.connect(
                    functools.partial(self.value_edited, param_gui_order_ii))
                
                # Ajust style
                minus_button.setFixedWidth(25)
                plus_button.setFixedWidth(25)
                value_editor.setFixedHeight(23)
                value_editor.setFixedWidth(70)
                value_editor.setAlignment(pyqtc.Qt.AlignmentFlag.AlignCenter)
                armature_param_label.setStyleSheet(f'color: {color};')

                # Handle long presses
                plus_button.setAutoRepeat(True)
                minus_button.setAutoRepeat(True)

                # Populate widget row (widget keys start with a underscore '_')
                self._armature_params_editor_gui_elements[param_gui_order_ii] = {
                    '_label': (0, armature_param_label), # (GUI column index, widget object)
                    '_minus_button': (1, minus_button),
                    '_plus_button': (2, plus_button),
                    '_value_editor': (3, value_editor),
                    'nested_keys': nested_keys,
                    'unit': unit,
                }

        return self._armature_params_editor_gui_elements
    
    @armature_params_editor_gui_elements_dict.setter
    def armature_params_editor_gui_elements_dict(self, value):
        self._armature_params_editor_gui_elements_dict = value
    
    @property
    def armature_params_editor_widget(self):
        if self._armature_params_editor_widget is None:

            self._armature_params_editor_widget = pyqtw.QWidget()
            self.armature_params_editor_layout = pyqtw.QGridLayout()
            self._armature_params_editor_widget.setLayout(self.armature_params_editor_layout)
            self.armature_params_editor_layout.setHorizontalSpacing(5)
            self.armature_params_editor_layout.setVerticalSpacing(5)

            self.armature_params_editor_gui_elements_dict = None
            for row_ii in sorted(self.armature_params_editor_gui_elements_dict):
                row_widget_keys = {row_elements_values[0]: row_elements_keys for (row_elements_keys, row_elements_values) in self.armature_params_editor_gui_elements_dict[row_ii].items() if row_elements_keys.startswith('_')}
                for column_ii in sorted(row_widget_keys):
                    widget = self.armature_params_editor_gui_elements_dict[row_ii][row_widget_keys[column_ii]][1]
                    self.armature_params_editor_layout.addWidget(widget, row_ii, column_ii, 1, 1)

            # Append custom widgets
            for custom_widget in self.armature_object.custom_armature_param_widgets(self.armature_params_editor_layout.rowCount(), self.armature_params_editor_layout.columnCount()):
                self.armature_params_editor_layout.addWidget(*custom_widget)
            
            # Add a spacer to push the grid layout to the top
            self.spacer = pyqtw.QSpacerItem(0, 0, pyqtw.QSizePolicy.Policy.Minimum, pyqtw.QSizePolicy.Policy.Expanding)
            self.armature_params_editor_layout.addItem(self.spacer)
            
            # Remove padding
            self._armature_params_editor_widget.setContentsMargins(0, 0, 0, 0)

        return self._armature_params_editor_widget

    @armature_params_editor_widget.setter
    def armature_params_editor_widget(self, value):
        self._armature_params_editor_widget = value


class NewArmaturePopup(pyqtw.QDialog):

    def __init__(self, parent_viewer, sterotaxframe_obj):
        self.parent_viewer = parent_viewer
        self.sterotaxframe_obj = sterotaxframe_obj

        super().__init__(self.parent_viewer)

        # Layout for the dialog
        self.setWindowTitle("Setup New Armature")
        self.popup_layout = pyqtw.QGridLayout()
        self.setLayout(self.popup_layout)

        # Armature class selector
        self.armature_class_selector = pyqtw.QComboBox()
        self.armature_class_selector.addItems(self.sterotaxframe_obj.AVAILABLE_ARMATURES)
        self.popup_layout.addWidget(self.armature_class_selector, 0, 0, 1, 1) # Y, X, w, h

        # Armature name editor
        self.armature_display_name_editor = pyqtw.QLineEdit('Armature Name')
        self.popup_layout.addWidget(self.armature_display_name_editor, 1, 0, 1, 1) # Y, X, w, h

        # Set up the button box
        self.button_box = pyqtw.QDialogButtonBox(pyqtw.QDialogButtonBox.StandardButton.Cancel | pyqtw.QDialogButtonBox.StandardButton.Ok)
        self.popup_layout.addWidget(self.button_box, 2, 0, 1, 1) # Y, X, w, h
        # Connect buttons to actions
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.on_accept)
    
    def on_accept(self):

        is_data_valid = True
        if self.new_armature_display_name == 'Armature Name':
            is_data_valid = False
            self.parent_viewer.show_error_popup("Invalid data", "Please specify an armature name")

        if self.new_armature_display_name in self.sterotaxframe_obj._armatures_objects:
            is_data_valid = False
            self.parent_viewer.show_error_popup("Invalid data", "This armature name already exists, please choose a different one")

        if is_data_valid:
            self.accept()

    @property
    def new_armature_display_name(self):
        return self.armature_display_name_editor.text()

    @property
    def new_armature_class(self):
        return self.armature_class_selector.currentText()
