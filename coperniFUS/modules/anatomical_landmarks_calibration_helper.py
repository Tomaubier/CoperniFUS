from coperniFUS import *
from coperniFUS.modules.module_base import Module


class AnatLandmarksCalib(Module):

    _DEFAULT_PARAMS = {
        'uncal_anatomical_landmarks_coords': { 
            'Lambda': [-1e-2, 0, 2e-3],
            'Bregma': [0, 0, 0]
        },
        'cal_anatomical_landmarks_coords': {
            'Lambda': [-1e-2, 0, 2e-3],
            'Bregma': [0, 0, 0]
        },
        'cal_tmat': np.eye(4),
    }

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, 'anat_calib', **kwargs)

        self.anat_landmarks_dict_name2ref = {
            'Uncalibrated': 'uncal_anatomical_landmarks_coords',
            'Calibrated': 'cal_anatomical_landmarks_coords',
        }
        self._landmarks_calib_tmat = None
        self._landmarks_gl_items = {}

    # --- Required module attributes ---

    def init_dock(self):
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Anatomical Landmarks Calibration', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        # Landmark to tooltip selector
        self.landmark_selector = pyqtw.QComboBox()
        self.update_landmark_selector_elements()
        self.dock_layout.addWidget(self.landmark_selector, 0, 0, 1, 1) # Y, X, w, h

        # Landmark to tooltip button
        self.landmark_to_tooltip_btn = pyqtw.QPushButton('Set Landmark to Tooltip')
        self.landmark_to_tooltip_btn.clicked.connect(self.set_landmark_to_tooltip)
        self.dock_layout.addWidget(self.landmark_to_tooltip_btn, 0, 1, 1, 1) # Y, X, w, h

        # Landmark to tooltip button
        self.apply_calibration_tmat_btn = pyqtw.QPushButton('Apply Anatomical Landmark Transformation')
        self.apply_calibration_tmat_btn.clicked.connect(self.apply_calibration_tmat)
        self.update_calib_tmat_btn_status()
        self.dock_layout.addWidget(self.apply_calibration_tmat_btn, 1, 0, 1, 2) # Y, X, h, w

    def add_rendered_object(self):
        def add_landmarks_to_rendered_view(anat_landmarks_dict, landmark_name_prefix, pt_color, pt_size):
            for landmark_name, landmark_coords in anat_landmarks_dict.items():
                full_landmark_name = f'{landmark_name_prefix} {landmark_name}'
                self._landmarks_gl_items[full_landmark_name] = gl.GLScatterPlotItem(
                    pos=np.array(landmark_coords).reshape((1, 3)),
                    color=pt_color,
                    size=pt_size,
                    pxMode=True, # pt size expressed in pixels
                    glOptions='additive',
                )
                self._landmarks_gl_items[full_landmark_name].setDepthValue(5)
                self.parent_viewer.gl_view.addItem(self._landmarks_gl_items[full_landmark_name], name=full_landmark_name)
        add_landmarks_to_rendered_view(
            self.get_user_param('uncal_anatomical_landmarks_coords'),
            landmark_name_prefix='Uncalibrated',
            pt_color=(1, 0, 0, .7),
            pt_size=10)
        add_landmarks_to_rendered_view(
            self.get_user_param('cal_anatomical_landmarks_coords'),
            landmark_name_prefix='Calibrated',
            pt_color=(0, 1, 0, .7),
            pt_size=18)

    def delete_rendered_object(self):
        for landmark_name in self._landmarks_gl_items:
            self.parent_viewer.gl_view.removeItem(self._landmarks_gl_items[landmark_name])
        self._landmarks_gl_items = {}

    def update_rendered_object(self):
        def update_rendered_landmarks(anat_landmarks_dict, landmark_name_prefix):
            for landmark_name, landmark_coords in anat_landmarks_dict.items():
                full_landmark_name = f'{landmark_name_prefix} {landmark_name}'
                self._landmarks_gl_items[full_landmark_name].setData(pos=np.array(landmark_coords).reshape((1, 3)))
        update_rendered_landmarks(
            self.get_user_param('uncal_anatomical_landmarks_coords'),
            landmark_name_prefix='Uncalibrated')
        update_rendered_landmarks(
            self.get_user_param('cal_anatomical_landmarks_coords'),
            landmark_name_prefix='Calibrated')
        
    # --- Module specific attributes ---
        
    @property
    def landmarks_calib_tmat(self):
        if self._landmarks_calib_tmat is None:
            landmarks_hash = None
            self._landmarks_calib_tmat = (np.eye(4), landmarks_hash) # tmat + hash for version tracking
        return self._landmarks_calib_tmat[0]

    @property
    def mamed_anat_landmarks_dict(self):
        full_lm_dict = {}
        for lm_dict_full_name, lm_dict_name in self.anat_landmarks_dict_name2ref.items():
            full_lm_dict = {**full_lm_dict, **{f'{lm_dict_full_name} {landmark_name}': (lm_dict_name, landmark_name) for landmark_name in self.get_user_param(lm_dict_name).keys()}}
        return full_lm_dict
    
    def set_landmark_to_tooltip(self):
        landmark_dict_name, landmark_name = self.mamed_anat_landmarks_dict[self.landmark_selector.currentText()]
        anat_landmarks_dict = copy.deepcopy(self.get_user_param(landmark_dict_name))
        anat_landmarks_dict[landmark_name] = list(self.parent_viewer.tooltip.tooltip_tmat[3, :3])
        self.set_user_param(landmark_dict_name, anat_landmarks_dict)
        self.update_rendered_object()
        self.update_calib_tmat_btn_status()

    def _get_anat_landmarks_dicts_hash(self):
        dicts_hash = object_list_hash([
            self.get_user_param('uncal_anatomical_landmarks_coords'),
            self.get_user_param('cal_anatomical_landmarks_coords')
        ])
        return dicts_hash

    def get_tmat_from_anat_landmarks(self, anat_landmarks_dict):
        """ anat_landmarks_dict should repect the format {'landmark #0': np.array(landmark_coords)}
        anat_landmarks_dict """

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
            raise NotImplementedError('Only anat_landmarks_dicts containing two landmarks are supported at the moment')
        
        return anat_landmarks_tmat

    def update_landmark_selector_elements(self):
        self.landmark_selector.addItems(self.mamed_anat_landmarks_dict.keys())

    def update_calib_tmat_btn_status(self):
        self.landmarks_calib_tmat # Ensures that self._landmarks_calib_tmat[1] exists
        landmarks_hash = self._get_anat_landmarks_dicts_hash()
        if landmarks_hash == self._landmarks_calib_tmat[1]:
            self.apply_calibration_tmat_btn.setStyleSheet("background-color: green; color: white;")
        else:
            self.apply_calibration_tmat_btn.setStyleSheet("background-color: red; color: white;")

    def apply_calibration_tmat(self):
        uncal_tmat = self.get_tmat_from_anat_landmarks(
            self.get_user_param('uncal_anatomical_landmarks_coords')
        )
        cal_tmat = self.get_tmat_from_anat_landmarks(
            self.get_user_param('cal_anatomical_landmarks_coords')
        )

        # Debug -> uncalibrated and calibrated coordinate frame vizualisation
        # self.parent_viewer.delete_debug_trihedras()
        # self.parent_viewer.add_debug_trihedra_og_scale(cal_tmat.T)
        # self.parent_viewer.add_debug_trihedra_og_scale(uncal_tmat.T)

        # Calibration matrix evaluation
        calibration_tmat = (cal_tmat @ np.linalg.inv(uncal_tmat)).T

        landmarks_hash = self._get_anat_landmarks_dicts_hash()
        self._landmarks_calib_tmat = (calibration_tmat, landmarks_hash) # tmat + hash for version tracking
        self.parent_viewer.update_rendered_view()
        self.update_calib_tmat_btn_status()

        # Set btn to calibration reset
        self.apply_calibration_tmat_btn.setText('Disable Anatomical Landmark Transformation')

        try: self.apply_calibration_tmat_btn.clicked.disconnect()
        except Exception: pass

        self.apply_calibration_tmat_btn.clicked.connect(self.disable_calibration_tmat)

    def disable_calibration_tmat(self):
        landmarks_hash = None
        self._landmarks_calib_tmat = (np.eye(4), landmarks_hash) # tmat + hash for version tracking
        self.parent_viewer.update_rendered_view()
        self.update_calib_tmat_btn_status()

        # Set btn to calibration reset
        self.apply_calibration_tmat_btn.setText('Apply Anatomical Landmark Transformation')

        try: self.apply_calibration_tmat_btn.clicked.disconnect()
        except Exception: pass

        self.apply_calibration_tmat_btn.clicked.connect(self.apply_calibration_tmat)
