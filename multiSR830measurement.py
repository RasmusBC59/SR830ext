

def do2d(param_set1, start1, stop1, num_points1, delay1,
         param_set2, start2, stop2, num_points2, delay2,
         *param_meas):
    '''Scan 2D of param_set and measure param_meas.'''
    meas = Measurement()
    refresh_time = 1. # in s
    meas.write_period = refresh_time
    meas.register_parameter(param_set1)
    param_set1.post_delay = delay1
    meas.register_parameter(param_set2)
    param_set2.post_delay = delay2
    output = []
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set1, param_set2))
        output.append([parameter, None])
    progress_bar = progressbar.ProgressBar(max_value=num_points1 * num_points2)
    points_taken = 0
    time.sleep(0.1)
    
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        last_time = time.time()
        for set_point1 in np.linspace(start1, stop1, num_points1):
            param_set2.set(start2)
            param_set1.set(set_point1)
            outputs = []
            for set_point2 in np.linspace(start2, stop2, num_points2):
                param_set2.set(set_point2)
                
                # notice that output is a list of tuples and it is created from scratch at each new iteration                
                output = ([(param_set1, set_point1), (param_set2, set_point2)] +
                          [(parameter, parameter.get()) for parameter in param_meas])
                outputs.append(output)
                points_taken += 1
            for output in outputs:
                datasaver.add_result(*output)
                # current_time = time.time()
                # if current_time - last_time >= refresh_time:
                #     last_time = current_time
                #     progress_bar.update(points_taken)
            progress_bar.update(points_taken)
    return run_id
