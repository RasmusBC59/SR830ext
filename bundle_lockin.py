import numpy as np
from time import sleep
from qcodes.utils.validators import Numbers, Arrays
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import ParameterWithSetpoints, Parameter, DelegateParameter

class BundleLockin(Instrument):
    def __init__(self, name: str, lockins, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)

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
                        get_cmd = _get_current_data(lockin),
                        unit='V',
                        vals=Arrays(shape=(self.sweep_n_points.get_latest,)),
                        setpoints=(self.setpoints,),
                        parameter_class=ParameterWithSetpoints)



    def _get_current_data(lockin):
        lockin.ch1_databuffer.prepare_buffer_readout()    
        return lockin.ch1_databuffer.get()       