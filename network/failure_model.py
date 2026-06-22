import numpy as np

class FailureModel:
    def __init__(self, p_fail_per_hour=0.01, failure_duration=60.0):
        self.p_fail_per_hour = p_fail_per_hour
        self.failure_duration = failure_duration
        self.p_fail_per_sec = p_fail_per_hour / 3600.0

    def check_failure(self, uav, current_time):
        if not hasattr(uav, 'failed_until'):
            uav.failed_until = 0.0

        if current_time < uav.failed_until:
            return True # Currently failed

        if np.random.rand() < self.p_fail_per_sec:
            uav.failed_until = current_time + self.failure_duration
            return True

        return False
