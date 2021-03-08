import numpy as np
from qcodes.utils.validators import Numbers, Arrays
from qcodes.instrument.parameter import ParameterWithSetpoints, Parameter, DelegateParameter
from qcodes.instrument_drivers.stanford_research.SR830 import SR830 




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


class Lockin(SR830):    
        
    def __init__(self, name, address, set_object, **kwargs):
        super().__init__(name, address, **kwargs)
        self.set_object = set_object
        self.add_parameter('sweep_start',
                           source=None,
                           parameter_class=DelegateParameter)

        self.add_parameter('sweep_stop',
                           source=None,
                           parameter_class=DelegateParameter)

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
        
        self.add_parameter(name='trace',
                           get_cmd=self._get_current_data,
                           label='Signal',
                           unit='V',
                           vals=Arrays(shape=(self.sweep_n_points.get_latest,)),
                           setpoints=(self.setpoints,),
                           parameter_class=ParameterWithSetpoints
                           )
        

    def _get_current_data(self):   
        axis = self.setpoints()
        self.buffer_reset()
        for x in axis:
            self.set_object(x)
            self.send_trigger()
        self.prepare_buffer_readout()    
        return self.ch1_databuffer.get()

    def set_sweep_parameters(self, start_parameter, stop_parameter, label=None):
        if start_parameter.unit != stop_parameter.unit:
            raise TypeError("You must sweep from and to "
                            "parameters with the same unit")
        self.sweep_start.source = start_parameter
        self.sweep_stop.source = stop_parameter
        self.setpoints.unit = start_parameter.unit
        if label != None:
            self.setpoints.label = label

