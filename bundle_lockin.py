import numpy as np
import concurrent.futures
import time
from qcodes.utils.validators import Numbers, Arrays
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import ParameterWithSetpoints, Parameter, DelegateParameter
from qcodes import Measurement


class BundleLockin(Instrument):
    def __init__(self, name: str, lockins, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)

        self.lockins = lockins

        self.add_parameter('sweep_start',
                           unit='',
                           initial_value=0,
                           get_cmd=None,
                           set_cmd=None) 

        self.add_parameter('sweep_stop',
                           unit='',
                           initial_value=1,
                           get_cmd=None,
                           set_cmd=None)                                                 

        self.add_parameter('sweep_n_points',
                           unit='',
                           initial_value=10,
                           vals=Numbers(1,1e3),
                           get_cmd=None,
                           set_cmd=None)              

        self.add_parameter('setpoints',
                            parameter_class=GeneratedSetPoints,
                            startparam=self.sweep_start,
                            stopparam=self.sweep_stop,
                            numpointsparam=self.sweep_n_points,
                            vals=Arrays(shape=(self.sweep_n_points.get_latest,)))

        for lockin in lockins:
            self.add_parameter('trace_{}'.format(lockin.name),
                        label='Signal {}'.format(lockin.name),
                        get_cmd = lockin.prepare_and_get_buffer,
                        unit='V',
                        vals=Arrays(shape=(self.sweep_n_points.get_latest,)),
                        setpoints=(self.setpoints,),
                        parameter_class=ParameterWithSetpoints)



    def set_sweep_parameters(self,sweep_param, start, stop, n_points=10, label=None):
        
        self.sweep_start.unit = sweep_param.unit
        self.sweep_start.vals = sweep_param.vals
        self.sweep_start.set(start)
        
        self.sweep_stop.unit = sweep_param.unit
        self.sweep_stop.vals = sweep_param.vals
        self.sweep_stop.set(stop)
        self.sweep_n_points.set(n_points)
        self.setpoints.unit = sweep_param.unit
        if label != None:
            self.setpoints.label = label     


class GeneratedSetPoints(Parameter):
    """
    A parameter that generates a setpoint array from start, stop and num points
    parameters.
    """
    def __init__(self, startparam, stopparam, numpointsparam, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._startparam = startparam
        self._stopparam = stopparam
        self._numpointsparam = numpointsparam


    def get_raw(self):
        return np.linspace(self._startparam(), self._stopparam(),
                              self._numpointsparam())


def do2d_multi(param_slow, start_slow, stop_slow, num_points_slow, delay_slow,
         param_fast, start_fast, stop_fast, num_points_fast, delay_fast,
         bundle,
          refresh_time= 1.
              ):

    begin_time = time.time()
    meas = Measurement()
    bundle.set_sweep_parameters(param_fast, start_fast,stop_fast,num_points_fast, label="Voltage")
    interval_slow = np.linspace(start_slow,stop_slow,num_points_slow)
    meas.write_period = refresh_time
    set_points_fast = bundle.setpoints

    meas.register_parameter(set_points_fast)
    param_fast.post_delay = delay_fast
 
    meas.register_parameter(param_slow)
    param_slow.post_delay = delay_slow


    bundle_parameters = bundle.__dict__['parameters']
    traces = [bundle_parameters[key] for key in bundle_parameters.keys() if 'trace' in key]
    for trace in traces:
            meas.register_parameter(trace, setpoints=(param_slow, set_points_fast))

#progress_bar = progressbar.ProgressBar(max_value=num_points_slow * num_points_fast)
    points_taken = 0
    time.sleep(0.1)

    with meas.run(write_in_background=True) as datasaver:
        run_id = datasaver.run_id
    
        for point_slow in interval_slow:
            param_slow.set(point_slow)
        
            for lockin in bundle.lockins:
                lockin.buffer_reset()
                
            for point_fast in set_points_fast.get():
                param_slow.set(point_fast)
                time.sleep(0.1)
                for lockin in bundle.lockins:
                    lockin.send_trigger()
                    points_taken += 1
                    print(points_taken)
                    
            data = []
            for trace in traces:   
                data.append((trace,trace.get()))
            data.append((param_slow,param_slow.get()))
            data.append((set_points_fast,set_points_fast.get()))
            datasaver.add_result(*data)

    message = 'Have finished the measurement in {} seconds. run_id {}'.format(time.time()-begin_time,run_id)
    print(message)