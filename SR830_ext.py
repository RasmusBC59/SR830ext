import numpy as np
import qcodes as qc
import qcodes.utils.validators as vals
from qcodes.instrument.base import Parameter
from qcodes.instrument.parameter import ParameterWithSetpoints
from qcodes.instrument_drivers.stanford_research.SR830 import SR830 





class Buff(ParameterWithSetpoints):
    def get_raw(self):    
        axis = self.root_instrument.freq_axis()
        self.root_instrument.buffer_reset()
        for x in axis:
            self.root_instrument.frequency.set(x)
            self.root_instrument.send_trigger()
        self.root_instrument.ch1_databuffer.prepare_buffer_readout()    
        return self.root_instrument.ch1_databuffer.get()
 

class BuffAxis(Parameter):

    def get_raw(self):
        f_start = self.root_instrument.f_start()
        f_end = self.root_instrument.f_end()
        f_npts = self.root_instrument.f_npts()        
        return np.linspace(f_start, f_end, f_npts)


class Lockin(SR830):    
        

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)
        
        


        self.add_parameter(name='f_npts',
                           initial_value=500,
                           label='Number of points',
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter(name='f_start',
                           initial_value=1,
                           label='f_start',
                           unit='Hz',
                           get_cmd=None,
                           set_cmd=None)
        
        self.add_parameter(name='f_end',
                           initial_value=5000,
                           label='f_end',
                           unit='Hz',
                           get_cmd=None,
                           set_cmd=None)
        

        self.add_parameter(name='freq_axis',
                           label='Frequency',
                           unit='Hz',
                           vals=vals.Arrays(shape=(self.f_npts,)),
                           parameter_class=BuffAxis)

        self.add_parameter(name='trace',
                           label='Signal',
                           unit='V',
                           vals=vals.Arrays(shape=(self.f_npts,)),
                           setpoints=(self.freq_axis,),
                           parameter_class=Buff
                           )
        



