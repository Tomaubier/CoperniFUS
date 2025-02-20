# %%

from coperniFUS import *

from kwave.data import Vector

from kwave.kgrid import kWaveGrid
from kwave.kmedium import kWaveMedium
from kwave.ksensor import kSensor
from kwave.ksource import kSource
from kwave.utils.filters import extract_amp_phase
from kwave.utils.mapgen import focused_bowl_oneil
from kwave.utils.math import round_even
from kwave.utils.kwave_array import kWaveArray
from kwave.utils.signals import create_cw_signals

from kwave.kspaceFirstOrderAS import kspaceFirstOrderASC
from kwave.kspaceFirstOrder3D import kspaceFirstOrder3D
from kwave.kspaceFirstOrder2D import kspaceFirstOrder2D

from kwave.options.simulation_options import SimulationOptions, SimulationType
from kwave.options.simulation_execution_options import SimulationExecutionOptions

from scipy.spatial import cKDTree
from tqdm import tqdm


# ------ Axisymmetric -------

def axisymmetric_interpolation(f_rz, r_axisymm, z_axisymm, x_cart, y_cart, z_cart, **kwargs):
    """ Input: f_rz -> 2D axisymmetric field
        Output: F_xyz -> 3D interpolated field
    """
    # Create a 2D interpolator for the field
    interp_f = scipy.interpolate.RegularGridInterpolator((r_axisymm, z_axisymm), f_rz, bounds_error=False, fill_value=0, **kwargs)

    # Create a 3D Cartesian grid
    X, Y, Z = np.meshgrid(x_cart, y_cart, z_cart, indexing='ij')

    # Convert the Cartesian grid to cylindrical coordinates
    R = np.sqrt(X**2 + Y**2)

    # Interpolate the 2D field onto the 3D grid
    points = np.array([R.flatten(), Z.flatten()]).T
    F_xyz = interp_f(points).reshape(R.shape)

    # F_xyz now contains the interpolated 3D field in Cartesian coordinates
    return F_xyz


class KwaveHomogeneousAxisymetricBowlSim():

    KWAVE_CPP_CMD_TYPE = 'powershell'

    DEFAULT_SIM_PARAMS = {
        # medium parameters (Material #0)
        'c_0': 1482.3, # sound speed [m/s]
        'rho_0': 994.04, # density [kg/m^3]
        'alpha_0': 0.0022, # water attenuation [dB/(MHz^y cm)]
        'alpha_power_0': 1., # water attenuation [dB/(MHz^y cm)]

        'alpha_mode': 'stokes',

        'c_tx_coupling_medium': 1482.3, # sound speed [m/s]
        'rho_tx_coupling_medium': 994.04, # density [kg/m^3]

        # source parameters
        'source_f0': 1e6, # source frequency [Hz]
        'source_roc': 15e-3, # bowl radius of curvature [m]
        'source_diameter': 15e-3, # bowl aperture diameter [m]
        # 'source_amp': 1.0e6, # source pressure [Pa]
        'source_ac_pwr': 0.0249, # [W]
        'source_phase': 0., # source phase [radians]

        # grid parameters
        'AS_domain_z_size': 30.0e-3,  # total grid size in the axial dimension [m]
        'AS_domain_r_size': 10.0e-3,  # total grid size in the lateral dimension [m]

        # computational parameters
        'ppw': 5,      # number of points per wavelength
        'n_reflections': 2,
        # 't_end': 4e-5,  # total compute time [s] (this must be long enough to reach steady state)
        'record_periods': 1,        # number of periods to record
        'cfl': 0.1,                # CFL number
        'source_z_offset': 20,      # grid points to offset the source
        'domain_z_extension': 20,   # grid points to extend the domain (preventing PML interference in AS-3D domain coupling)
        'bli_tolerance': 0.01,      # tolerance for truncation of the off-grid source points
        'upsampling_rate': 10,      # density of integration points relative to grid

        'cpp_engine': 'OMP',
        'cpp_io_files_directory_path': None,
        'run_through_external_cpp_solvers': False,
    }

    def __init__(self):
        self.verbose: bool = False
        self._simulation_params = None
        self._simulation_hash = None
        self._init_quantities()

    @property
    def cpp_engine(self):
        """ CUDA (gpu) or OMP (cpu) """
        if 'cpp_engine' in self.simulation_params:
            cpp_engine = self.simulation_params['cpp_engine']
        else:
            cpp_engine = 'OMP' # defaults to cpu
        return cpp_engine

    @property
    def cpp_io_files_dir_path(self):
        if 'cpp_io_files_directory_path' in self.simulation_params:
            dir_path = self.simulation_params['cpp_io_files_directory_path']
        else:
            dir_path = 'OMP' # defaults to cpu
        return dir_path

    def get_kwave_cpp_cmd(self, kw_hash):
        if self.KWAVE_CPP_CMD_TYPE == 'powershell':
            cmd = f"""$kwave_params_hash = '{kw_hash}'\n$t_sensor_start = {self.sensor.record_start_index}\n$kwave_io_dirpath = '{self.cpp_io_files_dir_path}'\n$input_fpath = $kwave_io_dirpath + 'kwave_AS_input_' + $kwave_params_hash + '.h5'\n$output_fpath = $kwave_io_dirpath + 'kwave_AS_output_' + $kwave_params_hash + '.h5'\nZ:\\kwave_python\\k-wave-toolbox-version-1.3-cpp-windows-executables/kspaceFirstOrder-{self.cpp_engine} -i $input_fpath -o $output_fpath -s $t_sensor_start --p_final --p_max -p -u"""
        else:
            cmd = ''
        return cmd

    def _init_quantities(self):
        self.kwave_AS_alpha_power = 2 # Always equal to 2 when using alpha_mode = 'stokes' -> see doc
        self._kgrid = None
        self._dx = None
        self._Nx = None
        self._Ny = None
        self._ppp = None
        self._dt = None
        self._Nt = None
        self._medium = None
        self._source = None
        self._sensor = None
        self._alpha_corrected = None
        self.sensor_data = None
        self._p_amp_zr = None
        self._p_amp_xyz = None
        self._phase_zr = None
        self._freq = None
        self._z_as = None
        self._r_as = None

    @property
    def simulation_params(self):
        if self._simulation_params is None:
            self._simulation_params = self.DEFAULT_SIM_PARAMS
            self._simulation_hash = object_list_hash(self._simulation_params)[:8]
        return self._simulation_params
    
    @simulation_params.setter
    def simulation_params(self, sim_param_dict):
        if sim_param_dict is None:
            self._simulation_hash = None
            self._simulation_params = None
        else:
            new_params_hash = object_list_hash(sim_param_dict)[:8]
            if new_params_hash != self._simulation_hash:
                self._simulation_hash = new_params_hash
                self._simulation_params = sim_param_dict
                self._init_quantities() # Reset quantities for re-computation with new input params
    
    def set_simulation_param(self, param_name, value):
        sim_params = copy.deepcopy(self.simulation_params)
        sim_params[param_name] = value
        self.simulation_params = sim_params

    @property
    def dx(self):
        if self._dx is None:
            self.kgrid # dx computation in kgrid definition
        return self._dx

    @dx.setter
    def dx(self, value):
        self._dx = value

    @property
    def Nx(self): 
        """ Acoustic axis (z) """
        if self._Nx is None:
            self.kgrid # Nx computation in kgrid definition
        return self._Nx

    @Nx.setter
    def Nx(self, value):
        self._Nx = value

    @property
    def Ny(self):
        """ Lateral axis (r) """
        if self._Ny is None:
            self.kgrid # Ny computation in kgrid definition
        return self._Ny

    @Ny.setter
    def Ny(self, value):
        self._Ny = value

    @property
    def ppp(self):
        if self._ppp is None:
            self.kgrid # Ny computation in kgrid definition
        return self._ppp
    
    @ppp.setter
    def ppp(self, value):
        self._ppp = value
    
    @property
    def dt(self):
        if self._dt is None:
            self.kgrid # Ny computation in kgrid definition
        return self._dt
    
    @dt.setter
    def dt(self, value):
        self._dt = value
    
    @property
    def Nt(self):
        if self._Nt is None:
            self.kgrid # Ny computation in kgrid definition
        return self._Nt
    
    @Nt.setter
    def Nt(self, value):
        self._Nt = value

    @property
    def alpha_corrected(self):
        """ Evaluating pseudo-alpha coeficient with k-Wave's AS constraint of alpha_power=2 """
        if self._alpha_corrected is None:
            self._alpha_corrected = self.simulation_params['alpha_0'] * ((self.simulation_params['source_f0']*1e-6) ** self.simulation_params['alpha_power_0']) / ((self.simulation_params['source_f0']*1e-6) ** self.kwave_AS_alpha_power) # [dB/(MHz^y cm)]
        return self._alpha_corrected
    
    @alpha_corrected.setter
    def alpha_corrected(self, value):
        self._alpha_corrected = value

    @property
    def kgrid(self):
        if self._kgrid is None:
            # calculate the grid spacing based on the PPW and F0
            self.dx = self.simulation_params['c_0'] / (self.simulation_params['ppw'] * self.simulation_params['source_f0']) # [m]

            # compute the size of the grid
            self.Nx = round_even(np.abs(self.simulation_params['AS_domain_z_size']) / self.dx) + self.simulation_params['source_z_offset'] + self.simulation_params['domain_z_extension']
            self.Ny = round_even(np.abs(self.simulation_params['AS_domain_r_size']) / self.dx)

            grid_size_points = Vector([self.Nx, self.Ny])
            grid_spacing_meters = Vector([self.dx, self.dx])

            # create the k-space grid
            self._kgrid = kWaveGrid(grid_size_points, grid_spacing_meters)

            # compute points per temporal period
            self.ppp = round(self.simulation_params['ppw'] / self.simulation_params['cfl'])

            # compute corresponding time spacing
            self.dt = 1.0 / (self.ppp * self.simulation_params['source_f0'])

            # create the time array using an integer number of points per period
            if 't_end' in self.simulation_params:
                t_end = self.simulation_params['t_end']
            elif 'n_reflections' in self.simulation_params:
                t_end = (self.Nx * self.dx) * self.simulation_params['n_reflections'] / self.simulation_params['c_0'];
            else:
                raise ValueError('Either t_end or n_reflections must be defined in the input simulation parameters.')
            
            self.Nt = round(t_end / self.dt)
            self._kgrid.setTime(self.Nt, self.dt)

            # calculate the actual CFL and PPW
            if self.verbose:
                print('PPW = ' + str(self.simulation_params['c_0'] / (self.dx * self.simulation_params['source_f0'])))
                print('CFL = ' + str(self.simulation_params['c_0'] * self.dt / self.dx))

        return self._kgrid
    
    @property
    def medium(self):
        if self._medium is None:
            self._medium = kWaveMedium(
                sound_speed=self.simulation_params['c_0'],
                density=self.simulation_params['rho_0'],
                alpha_coeff=np.array([self.alpha_corrected]),
                alpha_power=np.array([self.kwave_AS_alpha_power]),
                alpha_mode=self.simulation_params['alpha_mode'],
            )
        return self._medium
    
    @property
    def source(self):
        if self._source is None:
            self._source = kSource()

            # Generate array of continuous wave (CW) signals from amplitude and phase
            if 'source_amp' in self.simulation_params:
                source_p_amp = self.simulation_params['source_amp'] # Pressure [Pa]
            elif 'source_ac_pwr' in self.simulation_params:
                tx_surface_area = 2*np.pi * self.simulation_params['source_roc'] * (self.simulation_params['source_roc'] - np.sqrt(self.simulation_params['source_roc']**2 - (self.simulation_params['source_diameter'] / 2)**2));
                source_p_amp = np.sqrt(2) * np.sqrt((self.simulation_params['source_ac_pwr'] * self.simulation_params['rho_tx_coupling_medium'] * self.simulation_params['c_tx_coupling_medium']) / tx_surface_area); # Pressure [Pa]
            else:
                raise ValueError('Either source_amp or source_ac_pwr must be defined in the input simulation parameters.')

            # create time varying source
            source_sig = create_cw_signals(
                np.squeeze(self.kgrid.t_array),
                self.simulation_params['source_f0'],
                np.array([source_p_amp]),
                np.array([self.simulation_params['source_phase']])
            )

            # set arc position and orientation
            arc_pos = [self.kgrid.x_vec[0].item() + self.simulation_params['source_z_offset'] * self.kgrid.dx, 0]
            focus_pos = [self.kgrid.x_vec[-1].item(), 0]

            # create empty kWaveArray
            karray = kWaveArray(
                axisymmetric=True,
                bli_tolerance=self.simulation_params['bli_tolerance'],
                upsampling_rate=self.simulation_params['upsampling_rate'],
                single_precision=True
            )

            # add bowl shaped element
            karray.add_arc_element(arc_pos, self.simulation_params['source_roc'], self.simulation_params['source_diameter'], focus_pos)

            # assign binary mask
            self._source.p_mask = karray.get_array_binary_mask(self.kgrid)

            # assign source signals
            self._source.p = karray.get_distributed_source_signal(self.kgrid, source_sig)
        return self._source

    @property
    def sensor(self):
        if self._sensor is None:
            self._sensor = kSensor()

            # set sensor mask to record central plane, not including the source point
            self._sensor.mask = np.zeros((self.Nx, self.Ny), dtype=bool)
            self._sensor.mask[(self.simulation_params['source_z_offset'] + 1):, :] = True

            # record the pressure
            self._sensor.record = ['p', 'u']

            # record only the final few periods when the field is in steady state
            self._sensor.record_start_index = self.kgrid.Nt - (self.simulation_params['record_periods'] * self.ppp) + 1
        return self._sensor

    def run_simulation(self, io_h5files_directory_path=None) -> bool:
        """ Returns success bool """
        success = False
        save_to_disk_exit = False

        if io_h5files_directory_path is None:
            input_filepath = None
            output_filepath = None
        else:
            if self._simulation_hash is None:
                self.simulation_params # Update hash
            input_filepath = pathlib.Path(io_h5files_directory_path) / f'kwave_AS_input_{self._simulation_hash}.h5'
            output_filepath = pathlib.Path(io_h5files_directory_path) / f'kwave_AS_output_{self._simulation_hash}.h5'

        # if not self.simulation_params['run_through_external_cpp_solvers']:
        #     # Prepare kspaceFirstOrderASC call for local computation
        #     save_to_disk_exit = False

        if self.simulation_params['run_through_external_cpp_solvers']:
        # else: # Retreive output or generate input kWave C++ h5 file in the specified directory

            if output_filepath is not None and output_filepath.exists(): # Remote computation result retreival
                with h5py.File(output_filepath, "r") as output_file: # Load the C++ data back from disk using h5py
                    self.sensor_data = {}
                    for key in output_file.keys():
                        self.sensor_data[key] = output_file[f"/{key}"][0].squeeze()
                if self.sensor_data is not None:
                    success = True

            else: # Prepare kspaceFirstOrderASC call for remote computation
                save_to_disk_exit = True
                if io_h5files_directory_path is None:
                    raise ValueError('Please provide a valid io_h5files_directory_path path (specified in kwave_AS_h5_dir) when attempting to use run_through_external_cpp_solvers=True')
                input_filepath = pathlib.Path(io_h5files_directory_path) / f'kwave_AS_input_{self._simulation_hash}.h5'
                print(f'1. Run kwave C++ on\n{input_filepath} using\n\n{self.get_kwave_cpp_cmd(self._simulation_hash)}\n\nWhich will generate the output .h5 file in the same directory')

        if not success: # kspaceFirstOrderASC call
            if input_filepath is None:
                simulation_options = SimulationOptions(
                    simulation_type=SimulationType.AXISYMMETRIC,
                    data_cast='single',
                    data_recast=False,
                    save_to_disk=True,
                    save_to_disk_exit=save_to_disk_exit,
                    pml_inside=False)
            else:
                simulation_options = SimulationOptions(
                    simulation_type=SimulationType.AXISYMMETRIC,
                    data_cast='single',
                    data_recast=False,
                    save_to_disk=True,
                    save_to_disk_exit=save_to_disk_exit,
                    input_filename=input_filepath,
                    output_filename=output_filepath,
                    pml_inside=False)

            execution_options = SimulationExecutionOptions(
                is_gpu_simulation=False,
                delete_data=False,
                verbose_level=2)

            # self.sensor_data = kspaceFirstOrder2D(
            self.sensor_data = kspaceFirstOrderASC(
                medium=copy.deepcopy(self.medium),
                kgrid=copy.deepcopy(self.kgrid),
                source=copy.deepcopy(self.source),
                sensor=copy.deepcopy(self.sensor),
                simulation_options=simulation_options,
                execution_options=execution_options)
                    
        if self.sensor_data is not None and 'p' in self.sensor_data:
            success = True
        else:
            success = False
        return success
        
    @property
    def pamp_phase_freq_zr(self):
        if self._p_amp_zr is None or self._phase_zr is None or self._freq is None or self._z_as is None or self._r_as is None:
            self._p_amp_zr, self._phase_zr, self._freq  = extract_amp_phase(
                self.sensor_data['p'].T, 1.0 / self.kgrid.dt,
                self.simulation_params['source_f0'],
                dim=1, fft_padding=1, window='Rectangular'
            )

            # reshape data
            self._p_amp_zr = np.reshape(self._p_amp_zr, (self.Nx - (self.simulation_params['source_z_offset']+1), self.Ny), order='F')
            self._phase_zr = np.reshape(self._phase_zr, (self.Nx - (self.simulation_params['source_z_offset']+1), self.Ny), order='F')

            self._r_as = np.squeeze(self.kgrid.y_vec) - self.kgrid.y_vec[0].item()
            self._z_as = np.squeeze(self.kgrid.x_vec[(self.simulation_params['source_z_offset'] + 1):, :] - self.kgrid.x_vec[self.simulation_params['source_z_offset']])

        return (self._p_amp_zr, self._phase_zr, self._freq, self._z_as, self._r_as)
    
    @property
    def p_amp_zr(self):
        if self._p_amp_zr is None or self._z_as is None or self._r_as is None:
            self.pamp_phase_freq_zr
        return (self._p_amp_zr, self._z_as, self._r_as)
    
    @property
    def p_amp_xyz(self):
        if self._p_amp_xyz is None:
            p_amp_zr, z_as, r_as = self.p_amp_zr
            x_cart = np.linspace(-r_as[-1], r_as[-1], (len(r_as)*2-1))
            y_cart = np.linspace(-r_as[-1], r_as[-1], (len(r_as)*2-1))
            z_cart = np.linspace(z_as[0], z_as[-1], len(z_as))
            p_amp_xyz = axisymmetric_interpolation(p_amp_zr.T, r_as, z_as, x_cart, y_cart, z_cart)
            self._p_amp_xyz = (p_amp_xyz, x_cart, y_cart, z_cart)
        return self._p_amp_xyz


# ---------- 3D -----------


class Kwave3D():

    KWAVE_CPP_CMD_TYPE = 'powershell'

    DEFAULT_SIM_PARAMS = {
        # Material #0 -> Water
        'c_0': 1482.3, # sound speed [m/s]
        'rho_0': 994.04, # density [kg/m^3]
        'alpha_0': 0.0022, # water attenuation [dB/(MHz^y cm)]
        'alpha_power_0': 1., # water attenuation [dB/(MHz^y cm)]

        # Material #1 -> Bone
        'c_1': 2400, # sound speed [m/s]
        'rho_1': 1850, # density [kg/m^3]
        'alpha_1': 2.693, # water attenuation [dB/(MHz^y cm)]
        'alpha_power_1': 1.18, # water attenuation [dB/(MHz^y cm)]
        
        'alpha_mode': 'stokes',

        # source parameters
        'source_f0': 1.0e6,              # source frequency [Hz]
        'source_roc': 15e-3,              # bowl radius of curvature [m]
        'source_diameter': 8e-3,               # bowl aperture diameter [m]
        'source_amp': 1.0e6,              # source pressure [Pa]
        'source_phase': 0.0,    # source phase [radians]

        # grid parameters
        'AS_domain_z_size': 0, # IF
        'threeD_domain_x_size': 10e-3, # total grid size in the lateral dimension [m]
        'threeD_domain_y_size': 10e-3, # total grid size in the lateral dimension [m]
        'threeD_domain_z_size': 20e-3, # total grid size in the lateral dimension [m]

        # computational parameters
        'ppw': 4, # number of points per wavelength
        't_end': 40e-6,  # total compute time [s] (this must be long enough to reach steady state)
        'record_periods': 1, # number of periods to record
        'cfl': 0.3, # CFL number
        'source_z_offset': 10, # grid points to offset the source
        'bli_tolerance': 0.01, # tolerance for truncation of the off-grid source points
        'upsampling_rate': 10, # density of integration points relative to grid
        'verbose_level': 1, # verbosity of k-wave executable

        'cpp_engine': 'OMP',
        'cpp_io_files_directory_path': None,
        'run_through_external_cpp_solvers': False,
        'use_gpu': False,
    }

    def __init__(self):
        self.kwave_alpha_power = 2 # Corrected alpha coefs for safe usage of alpha_mode = 'stokes' -> see doc
        self.verbose: bool = False
        self._simulation_params = None
        self._simulation_hash = None
        self._init_quantities()

    @property
    def cpp_engine(self):
        """ CUDA (gpu) or OMP (cpu) """
        if 'cpp_engine' in self.simulation_params:
            cpp_engine = self.simulation_params['cpp_engine']
        else:
            cpp_engine = 'OMP' # defaults to cpu
        return cpp_engine

    @property
    def cpp_io_files_dir_path(self):
        if 'cpp_io_files_directory_path' in self.simulation_params:
            dir_path = self.simulation_params['cpp_io_files_directory_path']
        else:
            dir_path = 'OMP' # defaults to cpu
        return dir_path

    def get_kwave_cpp_cmd(self, kw_hash):
        if self.KWAVE_CPP_CMD_TYPE == 'powershell':
            cmd = f"""$kwave_params_hash = '{kw_hash}'\n$t_sensor_start = {self.sensor.record_start_index}\n$kwave_io_dirpath = '{self.cpp_io_files_dir_path}'\n$input_fpath = $kwave_io_dirpath + 'kwave_3D_input_' + $kwave_params_hash + '.h5'\n$output_fpath = $kwave_io_dirpath + 'kwave_3D_output_' + $kwave_params_hash + '.h5'\nZ:\\kwave_python\\k-wave-toolbox-version-1.3-cpp-windows-executables/kspaceFirstOrder-{self.cpp_engine} -i $input_fpath -o $output_fpath -s $t_sensor_start --p_final --p_max -p -u"""
        else:
            cmd = ''
        return cmd

    def _init_quantities(self):
        self._kgrid = None
        self._dx = None
        self._Nx = None
        self._Ny = None
        self._Nz = None
        self._ppp = None
        self._dt = None
        self._Nt = None
        self._medium = None
        self._source = None
        self._sensor = None
        self.sensor_data = None
        self._kgrid_coords = None
        self._p_amp_xyz = None
        self._phase_xyz = None
        self._freq = None

    @property
    def simulation_params(self):
        if self._simulation_params is None:
            self._simulation_params = self.DEFAULT_SIM_PARAMS
            self._simulation_hash = object_list_hash(self._simulation_params)[:8]
        return self._simulation_params
    
    @simulation_params.setter
    def simulation_params(self, sim_param_dict):
        if sim_param_dict is None:
            self._simulation_hash = None
            self._simulation_params = None
        else:
            new_params_hash = object_list_hash(sim_param_dict)[:8]
            if new_params_hash != self._simulation_hash:
                self._simulation_hash = new_params_hash
                self._simulation_params = sim_param_dict
                self._init_quantities() # Reset quantities for re-computation with new input params
    
    def set_simulation_param(self, param_name, value):
        sim_params = copy.deepcopy(self.simulation_params)
        sim_params[param_name] = value
        self.simulation_params = sim_params

    @property
    def dx(self):
        if self._dx is None:
            self.kgrid # dx computation in kgrid definition
        return self._dx

    @dx.setter
    def dx(self, value):
        self._dx = value

    @property
    def Nx(self): 
        if self._Nx is None:
            self.kgrid # Nx computation in kgrid definition
        return self._Nx

    @Nx.setter
    def Nx(self, value):
        self._Nx = value

    @property
    def Ny(self):
        if self._Ny is None:
            self.kgrid # Ny computation in kgrid definition
        return self._Ny

    @Ny.setter
    def Ny(self, value):
        self._Ny = value

    @property
    def Nz(self):
        if self._Nz is None:
            self.kgrid # Nz computation in kgrid definition
        return self._Nz

    @Nz.setter
    def Nz(self, value):
        self._Nz = value

    @property
    def ppp(self):
        if self._ppp is None:
            self.kgrid # Ny computation in kgrid definition
        return self._ppp
    
    @ppp.setter
    def ppp(self, value):
        self._ppp = value
    
    @property
    def dt(self):
        if self._dt is None:
            self.kgrid # Ny computation in kgrid definition
        return self._dt
    
    @dt.setter
    def dt(self, value):
        self._dt = value
    
    @property
    def Nt(self):
        if self._Nt is None:
            self.kgrid # Ny computation in kgrid definition
        return self._Nt
    
    @Nt.setter
    def Nt(self, value):
        self._Nt = value

    def c(self, material_index=0):
        key = f'c_{material_index}'
        if key in self.simulation_params:
            return self.simulation_params[key]
        else:
            raise ValueError(f'kWave AS-3D: No sound speed value found for material #{material_index}. Should be declared as {key}')
    
    def rho(self, material_index=0):
        key = f'rho_{material_index}'
        if key in self.simulation_params:
            return self.simulation_params[key]
        else:
            raise ValueError(f'kWave AS-3D: No density value found for material #{material_index}. Should be declared as {key}')
    
    def alpha(self, material_index=0):
        key = f'alpha_{material_index}'
        if key in self.simulation_params:
            return self.simulation_params[key]
        else:
            raise ValueError(f'kWave AS-3D: No attenuation found for material #{material_index}. Should be declared as {key}')
        
    def alpha_power(self, material_index=0):
        key = f'alpha_power_{material_index}'
        if key in self.simulation_params:
            return self.simulation_params[key]
        else:
            raise ValueError(f'kWave AS-3D: No attenuation found for material #{material_index}. Should be declared as {key}')
        
    def alpha_corrected(self, material_index=0):
        """ Evaluating pseudo-alpha coeficient with k-Wave's 'stokes' attenuation constraint of alpha_power=2 """
        alpha_corrected = self.alpha(material_index) * ((self.simulation_params['source_f0']*1e-6) ** self.alpha_power(material_index)) / ((self.simulation_params['source_f0']*1e-6) ** self.kwave_alpha_power) # [dB/(MHz^y cm)]
        return alpha_corrected

    @property
    def kgrid(self):
        if self._kgrid is None:
            # calculate the grid spacing based on the PPW and F0
            self.dx = self.simulation_params['c_0'] / (self.simulation_params['ppw'] * self.simulation_params['source_f0']) # [m]

            # compute the size of the grid
            self.Nx = round_even(np.abs(self.simulation_params['threeD_domain_x_size']) / self.dx)
            self.Ny = round_even(np.abs(self.simulation_params['threeD_domain_y_size']) / self.dx)
            self.Nz = round_even(np.abs(self.simulation_params['threeD_domain_z_size']) / self.dx) + self.simulation_params['source_z_offset']

            grid_size_points = Vector([self.Nx, self.Ny, self.Nz])
            grid_spacing_meters = Vector([self.dx, self.dx, self.dx])

            # create the k-space grid
            self._kgrid = kWaveGrid(grid_size_points, grid_spacing_meters)

            # compute points per temporal period
            self.ppp = round(self.simulation_params['ppw'] / self.simulation_params['cfl'])

            # compute corresponding time spacing
            self.dt = 1.0 / (self.ppp * self.simulation_params['source_f0'])

            # create the time array using an integer number of points per period
            self.Nt = round(self.simulation_params['t_end'] / self.dt)
            self._kgrid.setTime(self.Nt, self.dt)

            # calculate the actual CFL and PPW
            if self.verbose:
                print('PPW = ' + str(self.simulation_params['c_0'] / (self.dx * self.simulation_params['source_f0'])))
                print('CFL = ' + str(self.simulation_params['c_0'] * self.dt / self.dx))

        return self._kgrid

    @property
    def kgrid_coords(self): # kWave grid coordinates
        if self._kgrid_coords is None: # Defaults to homogeneous medium
            x_grid, y_grid, z_grid = np.meshgrid(
                np.squeeze(self.kgrid.x_vec),
                np.squeeze(self.kgrid.y_vec),
                np.squeeze(self.kgrid.z_vec) - self.kgrid.z_vec[0] + self.simulation_params['AS_domain_z_size'] - self.simulation_params['source_z_offset'] * self.dx
            )
            self._kgrid_coords = np.vstack([
                x_grid.transpose(1, 0, 2).ravel(),
                y_grid.transpose(1, 0, 2).ravel(),
                z_grid.transpose(1, 0, 2).ravel()
            ]).T
        return self._kgrid_coords
    
    @property
    def medium(self):
        if self._medium is None: # Defaults to homogeneous medium
            self._medium = kWaveMedium(
                sound_speed=self.c(0),
                density=self.rho(0),
                alpha_coeff=self.alpha_corrected(0),
                alpha_power=np.array([self.kwave_alpha_power]),
                alpha_mode=self.simulation_params['alpha_mode']
            )
        return self._medium
    
    @property
    def source(self):
        if self._source is None:  # Defaults to shperical bowl src
            self._source = kSource()

            # create time varying source
            source_sig = create_cw_signals(
                np.squeeze(self.kgrid.t_array),
                self.simulation_params['source_f0'],
                np.array([self.simulation_params['source_amp']]),
                np.array([self.simulation_params['source_phase']])
            )

            # set bowl position and orientation
            z0 = self.kgrid.z_vec[0].item() + self.simulation_params['source_z_offset'] * self.kgrid.dx
            focus_pos = [0., 0., z0 + self.simulation_params['source_roc']]
            bowl_pos = [0., 0., z0]

            # create empty kWaveArray
            karray = kWaveArray(
                bli_tolerance=self.simulation_params['bli_tolerance'],
                upsampling_rate=self.simulation_params['upsampling_rate'],
                single_precision=True
            )

            # add bowl shaped element
            karray.add_bowl_element(
                position=bowl_pos,
                radius=self.simulation_params['source_roc'],
                diameter=self.simulation_params['source_diameter'],
                focus_pos=focus_pos)

            # assign binary mask
            self._source.p_mask = karray.get_array_binary_mask(self.kgrid)

            # assign source signals
            self._source.p = karray.get_distributed_source_signal(self.kgrid, source_sig)
        return self._source

    @property
    def sensor(self):
        if self._sensor is None:
            self._sensor = kSensor()

            # set sensor mask to record central plane, not including the source point
            self._sensor.mask = np.zeros((self.Nx, self.Ny, self.Nz), dtype=bool)
            self._sensor.mask[:, :, self.simulation_params['source_z_offset']:] = True

            # record the pressure
            self._sensor.record = ['p', 'u']

            # record only the final few periods when the field is in steady state
            self._sensor.record_start_index = self.kgrid.Nt - (self.simulation_params['record_periods'] * self.ppp) + 1
        return self._sensor

    def run_simulation(self, io_h5files_directory_path=None) -> bool:
        """ Returns success bool """
        success = False

        if io_h5files_directory_path is None:
            input_filepath = None
            output_filepath = None
        else:
            if self._simulation_hash is None:
                self.simulation_params # Update hash
            input_filepath = pathlib.Path(io_h5files_directory_path) / f'kwave_3D_input_{self._simulation_hash}.h5'
            output_filepath = pathlib.Path(io_h5files_directory_path) / f'kwave_3D_output_{self._simulation_hash}.h5'
        
            # Retreive output or generate input kWave C++ h5 file in the specified directory
            if output_filepath is not None and output_filepath.exists(): # Remote computation result retreival
                print(f'\nLoading previously computed result\n{output_filepath}\n')
                with h5py.File(output_filepath, "r") as output_file: # Load the C++ data back from disk using h5py
                    self.sensor_data = {}
                    for key in output_file.keys():
                        self.sensor_data[key] = output_file[f"/{key}"][0].squeeze()
                if self.sensor_data is not None:
                    success = True

            else: # Prepare kspaceFirstOrder3D call for external computation (C++ OMP / CUDA)
                save_to_disk_exit = True
                if io_h5files_directory_path is None:
                    raise ValueError('Please provide a valid io_h5files_directory_path path (specified in kwave_3D_h5_dir) when attempting to use run_through_external_cpp_solvers=True')
                input_filepath = pathlib.Path(io_h5files_directory_path) / f'kwave_3D_input_{self._simulation_hash}.h5'
                print(f'1. Run kwave C++ on\n{input_filepath} using\n\n{self.get_kwave_cpp_cmd(self._simulation_hash)}\n\nWhich will generate the output .h5 file in the same directory')

        if not self.simulation_params['run_through_external_cpp_solvers']:
            # Prepare kspaceFirstOrder3D call for local computation
            save_to_disk_exit = False

        if not success: # kspaceFirstOrder3D call
            if input_filepath is None:
                simulation_options = SimulationOptions(
                    pml_auto=True,
                    pml_inside=False,
                    data_recast=True,
                    save_to_disk_exit=save_to_disk_exit,
                    save_to_disk=True)
            else:
                simulation_options = SimulationOptions(
                    pml_auto=True,
                    pml_inside=False,
                    data_recast=True,
                    save_to_disk_exit=save_to_disk_exit,
                    input_filename=input_filepath,
                    output_filename=output_filepath,
                    save_to_disk=True)
                
            if 'use_gpu' in self.simulation_params and self.simulation_params['use_gpu']:
                use_gpu = True
            else:
                use_gpu = False

            execution_options = SimulationExecutionOptions(
                is_gpu_simulation=use_gpu,
                delete_data=False,
                verbose_level=2)

            self.sensor_data = kspaceFirstOrder3D(
                medium=copy.deepcopy(self.medium),
                kgrid=copy.deepcopy(self.kgrid),
                source=copy.deepcopy(self.source),
                sensor=copy.deepcopy(self.sensor),
                simulation_options=simulation_options,
                execution_options=execution_options)
                    
        if self.sensor_data is not None and 'p' in self.sensor_data:
            success = True
        else:
            success = False
        return success
        
    @property
    def pamp_phase_freq_xyz(self):
        if self._p_amp_xyz is None or self._phase_xyz is None or self._freq is None or self._x_3d is None or self._y_3d is None or self._z_3d is None:
            p_amp_xyz_flat, phase_xyz_flat, self._freq  = extract_amp_phase(
                self.sensor_data['p'].T, 1.0 / self.kgrid.dt,
                self.simulation_params['source_f0'],
                dim=1, fft_padding=1, window='Rectangular')

            # reshape data
            self._p_amp_xyz = np.zeros((self.Nx, self.Ny, self.Nz), dtype=float)
            self._phase_xyz = np.zeros((self.Nx, self.Ny, self.Nz), dtype=float)
            self._p_amp_xyz = np.reshape(p_amp_xyz_flat, self._p_amp_xyz[:, :, self.simulation_params['source_z_offset']:].shape, order='F')
            self._phase_xyz = np.reshape(phase_xyz_flat, self._phase_xyz[:, :, self.simulation_params['source_z_offset']:].shape, order='F')
            del p_amp_xyz_flat, phase_xyz_flat

            # Mask source points from output pressure field
            # self._p_amp_xyz = self._p_amp_xyz * (~self.source.p_mask[:, :, self.simulation_params['source_z_offset']:]).astype(float)

            self._x_3d = np.squeeze(self.kgrid.x_vec)
            self._y_3d = np.squeeze(self.kgrid.y_vec)
            self._z_3d = np.squeeze(self.kgrid.z_vec) - self.kgrid.z_vec[0] + self.simulation_params['AS_domain_z_size'] - self.dx/2
            self._z_3d = self._z_3d[:-self.simulation_params['source_z_offset']] # Discard extra z points introduced by the source offset 

        return (self._p_amp_xyz, self._phase_xyz, self._freq, self._x_3d, self._y_3d, self._z_3d)
    
    @property
    def p_amp_xyz(self):
        if self._p_amp_xyz is None or self._x_3d is None or self._y_3d is None or self._z_3d is None:
            self.pamp_phase_freq_xyz
        return (self._p_amp_xyz, self._x_3d, self._y_3d, self._z_3d)
