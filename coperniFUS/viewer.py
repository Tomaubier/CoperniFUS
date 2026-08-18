import coperniFUS
from coperniFUS import *
from coperniFUS.modules.anatomical_landmarks_calibration_helper import AnatLandmarksCalib
from coperniFUS.modules.internal_console import InternalConsoleModule
from coperniFUS.modules.stereotaxic_frame import StereotaxicFrame
from coperniFUS.modules.img_as_plane import RefImageAsPlane
from coperniFUS.modules.stl_handler import StlHandlerGUI
from coperniFUS.modules.atlas import BrainAtlas
from coperniFUS.modules.tooltip import Tooltip
import shutil, functools


class Window(pyqtw.QMainWindow):
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

    def __init__(self, app, assets_dir_path='', disable_internal_console=False, disable_threaded_wrappers=False, **kwargs) -> None:
        self.assets_dir_path = pathlib.Path(assets_dir_path)
        self.disable_internal_console = disable_internal_console
        self.disable_threaded_wrappers = disable_threaded_wrappers
        
        if not self.disable_internal_console:
            print('\n> Info: Like any text outputs, warnings and error messages will be outputed to the internal console, to change this behaviour, feel free to set disable_internal_console to True.')

        print(f'\n> Info: Referencing assets located in {self.assets_dir_path} directory.')

        self.app_kwargs = kwargs
        self.app = app
        self.app.setStyle('Fusion')
        super().__init__()

        self.debug_trihedras = []

        self.slicing_plane_direction = 1
        self.slicing_plane_name = None
        self._slicing_plane_def = np.array([
            [0, 0, 0, 1],
            [0, 1, 0, 1],
            [0, 0, 1, 1],
            [1, 0, 0, 1],
        ])

        self.cache = CachedDataHandler('coperniFUSCache')

        self._update_window_title()
        self.setGeometry(*self.cache.get_attr('viewer.geometry', default_value=[100, 100, 1500, 1000]))

        self._init_gui()
        self._init_menu_bar()
        self._init_modules()
        self.show()
        self.showMaximized()

    # ==== Public attributes ====
    
    def get_module_object_from_name(self, module_name=None):
        """ Returns the module object handle associated to a module name. Call get_module_object_from_name() to get the list of all module names. """
        builtin_modules_dict = {
            module.__class__.__name__: module
            for module in [self.tooltip, self.anat_calib, self.stereotaxic_frame, *([self.console_dock] if not self.disable_internal_console else [])]
        }
        optional_module_names = [
            module.__class__.__name__
            for module in self._modules
        ]

        if module_name is None:
            print(f'Please specify a module name.\nBuilt-in Modules:\n\t- {"\n\t- ".join(builtin_modules_dict.keys())}\nOptionnal Modules Available:\n\t- {"\n\t- ".join(optional_module_names)}')
            return None
        if module_name in optional_module_names:
            brain_atlas_module_index = optional_module_names.index(module_name)
            return self._modules[brain_atlas_module_index]
        elif module_name in builtin_modules_dict:
            return builtin_modules_dict[module_name]
        else:
            raise ValueError(f'{module_name} not available in modules.\nBuilt-in Modules:\n\t- {"\n\t- ".join(builtin_modules_dict.keys())}\nOptionnal Modules Available:\n\t- {"\n\t- ".join(optional_module_names)}')
        
    # --- Debug trihedras ---
    
    def add_debug_trihedra(self, transform_matrix, axes_len=5e-3, line_width=6):
        """ Render an axes trihedra corresponding to a given transform_matrix with a fixed axes length (axes_len). """
        x_tri_loc = np.array([[0,0,0,1], [axes_len,0,0,1]]).T
        y_tri_loc = np.array([[0,0,0,1], [0,axes_len,0,1]]).T
        z_tri_loc = np.array([[0,0,0,1], [0,0,axes_len,1]]).T

        x_glaxis = gl.GLLinePlotItem(pos=(transform_matrix @ x_tri_loc)[:3].T, width=line_width, color=self.x_RED, antialias=True, glOptions='translucent')
        y_glaxis = gl.GLLinePlotItem(pos=(transform_matrix @ y_tri_loc)[:3].T, width=line_width, color=self.y_GREEN, antialias=True, glOptions='translucent')
        z_glaxis = gl.GLLinePlotItem(pos=(transform_matrix @ z_tri_loc)[:3].T, width=line_width, color=self.z_BLUE, antialias=True, glOptions='translucent')

        self.debug_trihedras = [*self.debug_trihedras, x_glaxis, y_glaxis, z_glaxis] # Append

        self.gl_view.addItem(x_glaxis, name='debug trihedra x axis')
        self.gl_view.addItem(y_glaxis, name='debug trihedra y axis')
        self.gl_view.addItem(z_glaxis, name='debug trihedra z axis')

    def add_scale_accurate_debug_trihedra(self, transform_matrix, line_width=6):
        """ Render an axes trihedra corresponding to a given transform_matrix. Axes length correspond to their actual scale. """
        x_vec = transform_matrix[:3, 0]
        y_vec = transform_matrix[:3, 1]
        z_vec = transform_matrix[:3, 2]
        origin = transform_matrix[:3, 3]

        x_glaxis = gl.GLLinePlotItem(pos=np.array([origin, origin+x_vec]), width=line_width, color=self.x_RED, antialias=True, glOptions='translucent')
        y_glaxis = gl.GLLinePlotItem(pos=np.array([origin, origin+y_vec]), width=line_width, color=self.y_GREEN, antialias=True, glOptions='translucent')
        z_glaxis = gl.GLLinePlotItem(pos=np.array([origin, origin+z_vec]), width=line_width, color=self.z_BLUE, antialias=True, glOptions='translucent')

        self.debug_trihedras = [*self.debug_trihedras, x_glaxis, y_glaxis, z_glaxis] # Append

        self.gl_view.addItem(x_glaxis, name='debug trihedra ogsc x axis')
        self.gl_view.addItem(y_glaxis, name='debug trihedra ogsc y axis')
        self.gl_view.addItem(z_glaxis, name='debug trihedra ogsc z axis')

    def delete_debug_trihedras(self):
        """ Remove all debug trihedras """
        for trihedra_gl_obj in self.debug_trihedras:
            self.gl_view.removeItem(trihedra_gl_obj)
        self.debug_trihedras = []

    # --- Error message handling wrapper method ---

    def show_error_popup(self, error_title, error_description=None):
        """ Error message handling wrapper method. Call to show an error popup window with a custom message. """
        error_msg_box = pyqtw.QMessageBox(self)
        error_msg_box.setIcon(pyqtw.QMessageBox.Icon.Critical)
        error_msg_box.setText(error_title)
        if error_description is not None:
            error_msg_box.setInformativeText(error_description)
        error_msg_box.exec()

    # --- Cache handler ---

    def load_example_configuration(self, example_configuration_name):
        """ Switch to a configuration provided in CoperniFUS example directory """
        extension_free_name = example_configuration_name.split('.')[0]
        examples_dir_path = coperniFUS_location.parent / 'examples'
        example_configuration_fpath = examples_dir_path / f'{extension_free_name}.json'
        if not example_configuration_fpath.exists():
            raise ValueError(f'{example_configuration_name} does not exist in {examples_dir_path}.')
        if self.cache.is_cached_filename_already_defined(extension_free_name):
            raise ValueError(f'{example_configuration_name} already exists in the cache {self.cache.cache_dir}, please remove it or rename it before retrying.')
        target_fpath = self.cache.cache_dir / f'{extension_free_name}.json'
        try:
            shutil.copyfile(example_configuration_fpath, target_fpath)
            self.switch_cached_settings_file(extension_free_name)
        except Exception as e:
            raise ValueError(f'extension_free_name could not be copied from {example_configuration_fpath} to {target_fpath}\n{type(e).__name__}: {str(e)}\n -> Please copy it manually and load it in CoperniFUS using switch_cached_settings_file(\'{extension_free_name}\')')

    def switch_cached_settings_file(self, cached_settings_fname, force_create_new=False):
        """ Switch between cached configuration files available in cache directory or create new ones. The list of avalable configuration files can be assessed by calling cached_settings_files. Setting force_create_new to True will force the creation a a new config file by adding a suffix to cached_settings_fname if it already exists."""
        print(f'> Info: Switching to {cached_settings_fname}')

        def get_safe_config_name(name):
            safe_name = copy.deepcopy(name)
            # Increment suffix until an unused name is found
            suffix_index = 1
            while self.cache.is_cached_filename_already_defined(safe_name):
                safe_name = f'{copy.deepcopy(name)} {suffix_index}'
                suffix_index += 1
            return safe_name

        if force_create_new and self.cache.is_cached_filename_already_defined(cached_settings_fname):
            cached_settings_fname = get_safe_config_name(cached_settings_fname)

        # Freeze wnidow to prevent user interactions during reloading
        self.setEnabled(False)
        pyqtw.QApplication.processEvents()

        # Set new cached file name
        # self.cache.cached_settings_fname = cached_settings_fname
        self.cache = CachedDataHandler(cache_dir_name='coperniFUSCache', cached_settings_fname=cached_settings_fname)

        # Clear rendered view
        self.clear_rendered_view()
        self._update_window_title()

        # Find all dock widgets in the main window
        docks = self.findChildren(pyqtw.QDockWidget)
        for dock in docks: # Remove each dock widget
            self.removeDockWidget(dock)
            dock.deleteLater()  # Optionally delete the dock widget to free memory

        # Remove all widgets from the status bar
        status_bar_widgets = self.status_bar.findChildren(pyqtw.QWidget) # Find all QLabel widgets in the status bar
        for widget in status_bar_widgets:
            if not isinstance(widget, pyqtw.QSizeGrip): # Bugfix: prevents application crash
                self.status_bar.removeWidget(widget)
                widget.deleteLater() # Delete the widget to free memory
        self.status_bar.clearMessage() # Clear any message from the status bar

        # Re-initialize modules
        self._init_modules()

        # Freeze wnidow to prevent user interactions during reloading
        self.setEnabled(True)

    @property
    def cached_settings_files(self):
        """ Get the list of available cache configuration files in the cache directory """
        cached_files_dict = {ff.name: str(ff) for ff in self.cache.cache_dir.glob('*.json')}
        cached_files_dict = {kk: cached_files_dict[kk] for kk in sorted(cached_files_dict.keys())}
        return cached_files_dict

    def _open_cached_settings_dir(self):
        pyqtg.QDesktopServices.openUrl(pyqtc.QUrl.fromLocalFile(str(self.cache.cached_settings_fpath.parent)))

    def _update_cached_settings_menu(self):
        self.cached_settings_menu.clear()

        open_cache_dir_action = pyqtg.QAction('Open Cached Configurations Directory', self)
        self.cached_settings_menu.addAction(open_cache_dir_action)
        open_cache_dir_action.triggered.connect(self._open_cached_settings_dir)
        self.cached_settings_menu.addSeparator() # Adds a separator line

        for cached_file_name in self.cached_settings_files.keys():
            action = pyqtg.QAction(cached_file_name, self)
            self.cached_settings_menu.addAction(action)
            if cached_file_name == self.cache.cached_settings_fname:
                action.setEnabled(False)
            else:
                action.triggered.connect(lambda checked, fname=cached_file_name: self.switch_cached_settings_file(fname))
    
    def _update_modules_menu(self):
        self.modules_menu.clear()

        modules_docks_objects = {module.dock.windowTitle(): module for module in 
            [*([self.console_dock] if not self.disable_internal_console else []), self.gl_view.gl_items_toggler, self.stereotaxic_frame, self.anat_calib]
        }
        modules_docks_objects.update({module.dock.windowTitle(): module for module in self._modules})
        modules_docks_objects.update({module.dock.windowTitle(): module for module in self._modules})
        modules_docks_visibility = {module_name: module_obj.dock.isVisible() for module_name, module_obj in modules_docks_objects.items()}

        for module_name, is_module_dock_visible in modules_docks_visibility.items():
            module_item = pyqtg.QAction(module_name, self)
            module_item.setCheckable(True)
            module_item.setChecked(is_module_dock_visible)

            module_item.toggled.connect(lambda visibility, module_name=module_name: self.hide_show_module_dock(modules_docks_objects[module_name].dock, module_name, visibility))

            self.modules_menu.addAction(module_item)
    
    # ==== Other attributes ====

    # --- Rendering methods ---

    def init_rendered_view(self):
        """ Calls add_rendered_object for all loaded modules """
        self.tooltip.add_rendered_object() # Init Tooltip globjects
        self.stereotaxic_frame.add_rendered_object()
        self.anat_calib.add_rendered_object()

        self._show_axes()
        for mm in self._modules:
            mm.add_rendered_object()

    def update_rendered_view(self):
        """ Calls update_rendered_object for all loaded modules """
        # Update armature tmat inheritance + tooltip tmat for proper plane slicing operations
        self.stereotaxic_frame.update_armature_inheritance()
        self.stereotaxic_frame.update_tooltip_on_armature()
        self.tooltip.update_rendered_object() # Update Tooltip globjects
        for mm in self._modules:
            mm.update_rendered_object()
        self.stereotaxic_frame.update_rendered_object()

    def clear_rendered_view(self):
        """ Calls delete_rendered_object for all loaded modules """
        self.tooltip.delete_rendered_object()
        self.stereotaxic_frame.delete_rendered_object()
        self.anat_calib.delete_rendered_object()

        for mm in self._modules:
            mm.delete_rendered_object()
        
        # Delete any residual gl items
        for gl_item in copy.copy(self.gl_view.items):
            self.gl_view.removeItem(gl_item)

    # --- Gui init ---

    def _init_modules(self):
        # Built-in modules objects init
        self.tooltip = Tooltip(self, **self.app_kwargs)
        self.anat_calib = AnatLandmarksCalib(self, **self.app_kwargs)
        self.stereotaxic_frame = StereotaxicFrame(self, **self.app_kwargs)

        self._modules = [ # optionnal modules
            RefImageAsPlane(self, **self.app_kwargs),
            BrainAtlas(self, **self.app_kwargs),
            StlHandlerGUI(self, **self.app_kwargs),
        ]

        if not self.disable_internal_console:
            self.console_dock = InternalConsoleModule(self)

        self._init_status_bar()
        self._init_modules_docks()
        self.init_rendered_view()
        
    def _init_menu_bar(self):
        menu_bar = self.menuBar()

        # --- File menu ---
        file_menu = menu_bar.addMenu('File')

        new_config_action = pyqtg.QAction('New Configuration', self)
        file_menu.addAction(new_config_action)
        new_config_action.triggered.connect(self._open_new_config_popup)

        self.cached_settings_menu = file_menu.addMenu('Open Existing Configuration')
        self.cached_settings_menu.aboutToShow.connect(self._update_cached_settings_menu)

        # --- Modules visibility menu ---
        self.modules_menu = menu_bar.addMenu('Modules')
        visible_modules_placeholder = pyqtg.QAction('Visible modules', self)
        self.modules_menu.addAction(visible_modules_placeholder)
        self.modules_menu.aboutToShow.connect(self._update_modules_menu)

    def _open_new_config_popup(self):
        self.new_config_popup = NewConfigNamePopup(self)
        if self.new_config_popup.exec():
            self.switch_cached_settings_file(self.new_config_popup.new_config_name)

    def _init_gui(self):

        # Window layout setup
        self.viewer_widget = pyqtw.QWidget()
        self.viewer_layout = pyqtw.QGridLayout()
        self.viewer_widget.setLayout(self.viewer_layout)
        self.viewer_widget.setContentsMargins(0, 0, 0, 0)
        self.viewer_layout.setContentsMargins(0, 0, 0, 0)

        # GLview setup
        self.gl_view = NamedGLViewWidget(parent_viewer=self)
        self.gl_view.opts['distance'] = 20
        self.gl_view.opts['fov'] = 1
        self._update_gl_viewer_theme()

        # Add to layout
        self.viewer_layout.addWidget(self.gl_view, 0, 0, 1, 3) # row, col
        self.setCentralWidget(self.viewer_widget)

    def _get_screen_dimensions(self):
        screen = self.windowHandle().screen()
        if screen:
            screen_geometry = screen.geometry()
            width = screen_geometry.width()
            height = screen_geometry.height()
            return np.array([width, height])
        return None

    def _init_status_bar(self):
        # Create status bar
        self.status_bar = pyqtw.QStatusBar()
        self.setStatusBar(self.status_bar)
        # Populate status bar
        self.tooltip._init_status_bar_widget() # Init Tooltip gui
        self._init_slicing_plane_gui()

    def _init_modules_docks(self):
        self.gl_view.gl_items_toggler.init_dock()
        self.stereotaxic_frame.init_dock()
        self.anat_calib.init_dock()
        if not self.disable_internal_console:
            self.console_dock.init_dock()
        for mm in self._modules:
            mm.init_dock()

    def hide_show_module_dock(self, module_dock, module_name, visibility):
        """ Hide and show module docks """
        if visibility:
            module_dock.show()
        else:
            module_dock.hide()

    # --- Slicing plane ---

    def _init_slicing_plane_gui(self):
        self.slicing_plane_button_group = pyqtw.QButtonGroup()
        self.slicing_plane_buttons = {}
        slicing_plane_ui_label = pyqtw.QLabel('Slicing plane')
        self.statusBar().insertPermanentWidget(0, slicing_plane_ui_label)

        def add_slicing_plane_btn(sl_plane_name, statusbar_loc_index):
            self.slicing_plane_buttons[sl_plane_name] = pyqtw.QRadioButton(sl_plane_name.upper())
            self.slicing_plane_button_group.addButton(self.slicing_plane_buttons[sl_plane_name])
            self.slicing_plane_buttons[sl_plane_name].clicked.connect(
                functools.partial(self._on_slicing_plane_btn_pressed, sl_plane_name))
            self.statusBar().insertPermanentWidget(statusbar_loc_index, self.slicing_plane_buttons[sl_plane_name])

        for statusbar_loc_index, sl_plane_name in enumerate(['x', 'y', 'z']):
            add_slicing_plane_btn(sl_plane_name, statusbar_loc_index+1)

        self.reverse_slicing_plane_checkbox = pyqtw.QCheckBox('Reverse')
        self.statusBar().insertPermanentWidget(statusbar_loc_index+2, self.reverse_slicing_plane_checkbox)
        self.reverse_slicing_plane_checkbox.stateChanged.connect(self._on_reverse_plane_slicing_checked)

    def _on_slicing_plane_btn_pressed(self, sl_plane_name):
        if sl_plane_name == self.slicing_plane_name: # Repeated click on plane -> disable slicing plane
            self.slicing_plane_name = None
            self.slicing_plane_button_group.setExclusive(False)
            self.slicing_plane_buttons[sl_plane_name].setChecked(False)
            self.slicing_plane_button_group.setExclusive(True)
        else:
            self.slicing_plane_name = sl_plane_name
        
            if self.slicing_plane_name == 'x':
                self._slicing_plane_def = np.array([
                    [0, 0, 0, 1], # origin
                    [0, 1, 0, 1], # ax1 -> y
                    [0, 0, 1, 1], # ax2 -> z
                    [1, 0, 0, 1], # ax0 -> x
                ], dtype=float).T
            elif self.slicing_plane_name == 'y':
                self._slicing_plane_def = np.array([
                    [0, 0, 0, 1], # origin
                    [0, 0, 1, 1], # ax1 -> z
                    [1, 0, 0, 1], # ax2 -> x
                    [0, 1, 0, 1], # ax0 -> x
                ], dtype=float).T
            elif self.slicing_plane_name == 'z':
                self._slicing_plane_def = np.array([
                    [0, 0, 0, 1], # origin
                    [1, 0, 0, 1], # ax1 -> x
                    [0, 1, 0, 1], # ax2 -> y
                    [0, 0, 1, 1], # ax0 -> z
                ], dtype=float).T
        self.update_rendered_view()

    def _on_reverse_plane_slicing_checked(self):
        if self.reverse_slicing_plane_checkbox.checkState() == pyqtc.Qt.CheckState.Checked:
            self.slicing_plane_direction = -1
        else:
            self.slicing_plane_direction = 1
        self.update_rendered_view()

    @property
    def slicing_plane_def(self):
        """ Slicing plane definition. Refer to slicing_plane_3pts and slicing_plane_normal_vect to get the plane location in other conventions. """
        d = self.slicing_plane_direction
        directed_slicing_plane_def = self._slicing_plane_def * np.vstack([d, d, d, 1])
        if d < 0:
            directed_slicing_plane_def = directed_slicing_plane_def[:, [0, 2, 1, 3]]
        elif d > 0:
            directed_slicing_plane_def = directed_slicing_plane_def[:, [0, 1, 2, 3]]
        return directed_slicing_plane_def

    @property
    def slicing_plane_3pts(self):
        """ Get the set of three points defining the location of the slicing plane """
        if self.slicing_plane_name is not None:
            if self.tooltip.tooltip_tmat is not None:
                sp_3pts = (self.tooltip.tooltip_tmat @ self.slicing_plane_def)[:3, :3].T
            else:
                sp_3pts = self.slicing_plane_def[:3, :3].T
        else:
            sp_3pts = None
        return sp_3pts
    
    @property
    def slicing_plane_normal_vect(self):
        """ Get the normal vector defining the location of the slicing plane """
        if self.slicing_plane_name is not None:
            if self.tooltip.tooltip_tmat is not None:
                sp_normal_vect = (self.tooltip.tooltip_tmat @ self.slicing_plane_def)[:3, [0, 3]].T
            else:
                sp_normal_vect = self.slicing_plane_def[:3, [0, 3]].T
        else:
            sp_normal_vect = None
        return sp_normal_vect
    
    @property
    def _postpone_slicing_plane_computation(self):
        param_button_long_press = self.app.mouseButtons() == pyqtc.Qt.MouseButton.LeftButton
        return param_button_long_press

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

    # --- Misc ---

    def _update_window_title(self):
        try:
            config_name_window_title_suffix = f' - {self.cache.cached_settings_fname.replace(".json", "")}'
        except Exception as e:
            config_name_window_title_suffix = ''
        self.setWindowTitle(f"CoperniFUS {version('coperniFUS')}{config_name_window_title_suffix}")

    @property
    def _is_dark_mode(self):
        palette = pyqtw.QApplication.palette()
        background_color = palette.color(pyqtg.QPalette.ColorRole.Window)
        text_color = palette.color(pyqtg.QPalette.ColorRole.WindowText)
        # Assuming a dark mode if the background is darker than the text
        _is_dark_mode = background_color.value() < text_color.value()
        return _is_dark_mode
    
    def _update_gl_viewer_theme(self):
        if self._is_dark_mode:
            gl_viwer_bg_color = [30]*3 # rgb value
        else:
            gl_viwer_bg_color = [226]*3 # rgb value
        self.gl_view.setBackgroundColor(gl_viwer_bg_color)

    def update_theme(self):
        """ Update CoperniFUS dark / light window theme. """
        self._update_gl_viewer_theme()
        # for mm in self._modules:
        #     mm.update_theme() # toimplement if needed

    def event(self, event):
        """ Handles app signals like system theme changes. """
        if event.type() == pyqtc.QEvent.Type.PaletteChange:
            self.update_theme() # Set/unset dark mode on system theme change
        return super().event(event)

    def closeEvent(self, event):
        """ Called when closing CoperniFUS. """
        # Restore stdout and stderr when closing the application
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        super().closeEvent(event)


def _is_running_in_ipython():
    """ Checks if coperniFUSviewer is running in interactive mode in an IPython console / notebook """
    try:
        from IPython import get_ipython
        is_ipython = get_ipython() is not None
        if is_ipython:
            get_ipython().enable_gui("qt")
        return is_ipython
    except ImportError:
        return False


def coperniFUSviewer(assets_dir_path=None, disable_internal_console=False, **kwargs):
    if assets_dir_path is None:
        assets_dir_path = pathlib.Path(coperniFUS.__file__).parent / 'examples' / 'assets'
        if not assets_dir_path.exists():
            raise ValueError(f'assets_dir_path does not exist: {assets_dir_path}')
    if _is_running_in_ipython():
        _instance = pyqtw.QApplication.instance()
        if not _instance:
            _instance = pyqtw.QApplication([])
        app = _instance
        window = Window(app,
            assets_dir_path=assets_dir_path,
            disable_internal_console=disable_internal_console,
            **kwargs
        )
    else:
        app = pyqtw.QApplication(sys.argv)
        window = Window(app,
            assets_dir_path=assets_dir_path,
            disable_internal_console=disable_internal_console,
            **kwargs
        )
        sys.exit(app.exec())
        window.exec_()
    return window
