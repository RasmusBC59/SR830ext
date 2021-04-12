import numpy as np
import logging
import concurrent.futures
import time
from tqdm import tqdm_notebook as tqdm
from qcodes.instrument.parameter import _BaseParameter
from qcodes import Measurement
from typing import List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
file_handler = logging.FileHandler('bundletimeing.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def do2d_multi(param_slow: _BaseParameter, start_slow: float, stop_slow: float,
               num_points_slow: int, delay_slow: float,
               param_fast: _BaseParameter, start_fast: float, stop_fast: float,
               num_points_fast: int, delay_fast: float,
               lockins,
               devices_no_buffer = None,
               write_period: float = 1.,
               threading: List[bool] = [True, True, True, True],
               label: str = None
               ):
    """
    This is a do2d to be used for buffered instruments.

    Args:
        param_slow: The QCoDeS parameter to sweep over in the outer loop
        start_slow: Starting point of sweep in outer loop
        stop_slow: End point of sweep in the outer loop
        num_points_slow: Number of points to measure in the outer loop
        delay_slow: Delay after setting parameter in the outer loop
        param_fast: The QCoDeS parameter to sweep over in the inner loop
        start_fast: Starting point of sweep in inner loop
        stop_fast: End point of sweep in the inner loop
        num_points_fast: Number of points to measure in the inner loop
        delay_fast: Delay after setting parameter before measurement is performed
        write_period: The time after which the data is actually written to the
                      database.
        threading: For each ellement which are True, write_in_background, buffer_reset,
                   and send_trigger and get_trace will be threaded respectively
        show_progress_bar: should a progress bar be displayed during the
                           measurement.
    """

    logger.info('Starting do2d_multi with {}'.format(num_points_slow * num_points_fast))
    logger.info('write_in_background {},threading buffer_reset {},threading send_trigger {},threading  get trace {}'.format(*threading))
    begin_time = time.perf_counter()
    meas = Measurement()
    


    for lockin in lockins:
        lockin.buffer_SR("Trigger")
        lockin.buffer_trig_mode.set('ON')
        lockin.set_sweep_parameters(param_fast, start_fast, stop_fast, num_points_fast, label=label)
    
    interval_slow = tqdm(np.linspace(start_slow, stop_slow, num_points_slow),position=0)
    interval_slow.set_description("Slow parameter")
    set_points_fast = lockins[0].sweep_setpoints

    meas.write_period = write_period
    meas.register_parameter(set_points_fast)
    meas.register_parameter(param_fast)
    meas.register_parameter(param_slow)

    param_fast.post_delay = delay_fast
    param_slow.post_delay = delay_slow

    #bundle_parameters = bundle.__dict__['parameters']
    traces = [lockin.ch1_datatrace for lockin in lockins]
    #traces = [bundle_parameters[key] for key in bundle_parameters.keys() if 'trace' in key]
    for trace in traces:
        meas.register_parameter(trace, setpoints=(param_slow, set_points_fast))
    
    if devices_no_buffer is not None:
        meas_no_buffer = Measurement()
        meas_no_buffer.write_period = write_period
        meas_no_buffer.register_parameter(param_fast)
        meas_no_buffer.register_parameter(param_slow)
        for device in devices_no_buffer:
            meas_no_buffer.register_parameter(device, setpoints=(param_slow, param_fast))


    time_fast_loop = 0.0
    time_set_fast = 0.0
    time_buffer_reset = 0.0
    time_trigger_send = 0.0
    time_get_trace = 0.0


    with meas.run(write_in_background=threading[0]) as datasaver, meas_no_buffer.run(write_in_background=threading[0])  as datasaver_no_buffer:


        for point_slow in interval_slow:
            param_slow.set(point_slow)
            data = []
            data.append((param_slow, param_slow.get()))

            if devices_no_buffer is not None:
                data_no_buffer = []
                data_no_buffer.append((param_slow, param_slow.get()))

            begin_time_temp_buffer = time.perf_counter()
            if threading[1]:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    for lockin in lockins:
                        executor.submit(lockin.buffer_reset)
            else:
                for lockin in lockins:
                    lockin.buffer_reset()
            time_buffer_reset += time.perf_counter() - begin_time_temp_buffer

            begin_time_temp_fast_loop = time.perf_counter()
            interval_fast = tqdm(set_points_fast.get(), position=1, leave=False)
            interval_fast.set_description("Fast parameter")
            for point_fast in interval_fast:
                begin_time_temp_set_fast = time.perf_counter()
                param_fast.set(point_fast)

                time_set_fast += time.perf_counter() - begin_time_temp_set_fast
                begin_time_temp_trigger = time.perf_counter()
                if threading[2]:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for lockin in lockins:
                            executor.submit(lockin.send_trigger)
                else:
                    for lockin in lockins:
                        lockin.send_trigger()

                time_trigger_send += time.perf_counter() - begin_time_temp_trigger
                
                if devices_no_buffer is not None:
                    fast = param_fast.get()
                    data_no_buffer.append((param_fast, fast))
                    for device in devices_no_buffer: 
                        device_value = device.get()
                        data_no_buffer.append((device, device_value))
                    datasaver_no_buffer.add_result(*data_no_buffer)

            time_fast_loop += time.perf_counter() - begin_time_temp_fast_loop

            begin_time_temp_trace = time.perf_counter()
            if threading[3]:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    data_trace = executor.map(trace_tuble, traces)

                data += list(data_trace)
            else:
                #data = []
                for trace in traces:
                    data.append((trace, trace.get()))
            time_get_trace += time.perf_counter() - begin_time_temp_trace

            #data.append((param_slow, param_slow.get()))
            data.append((set_points_fast, set_points_fast.get()))
            datasaver.add_result(*data)

    message = 'Have finished the measurement in {} seconds'.format(time.perf_counter()-begin_time)
    logger.info(message)
    message2 = 'Time used in buffer reset {}. Time used in send trigger {}. Time used in get trace {}'.format(time_buffer_reset, time_trigger_send, time_get_trace)
    logger.info(message2)
    logger.info('time in the fast loop {}'.format(time_fast_loop))
    logger.info('time setting in the fast loop {}'.format(time_set_fast))

def trace_tuble(trace):
    return (trace, trace.get())
