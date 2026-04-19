import numpy as np
from algorithms.base_algorithm import SchedulingAlgorithm

class ProportionalFairScheduler(SchedulingAlgorithm):
    def __init__(self):
        self.avg_rates = {}
        self.alpha = 0.01

    def observe(self, state):
        self.users = state['users']
        self.service_uavs = state['service_uavs']
        self.interference_model = state['interference_model']

    def decide(self):
        associations = {}
        for user in self.users:
            best_uav = None
            min_dist = float('inf')
            for uav in self.service_uavs:
                dist = np.linalg.norm(user.position - uav.position)
                if dist < min_dist:
                    min_dist = dist
                    best_uav = uav
            associations[user.entity_id] = best_uav

        return {'associations': associations}

    def apply(self, environment):
        decision = self.decide()
        for uav in environment.service_uavs:
            uav.assigned_users = []

        for user in environment.users:
            assigned_uav = decision['associations'].get(user.entity_id)
            if assigned_uav:
                user.assigned_service_uav = assigned_uav
                assigned_uav.assigned_users.append(user.entity_id)

    def get_active_user(self, uav, all_users):
        """Micro-step scheduling hook for the simulator: Proportional Fair."""
        if not uav.assigned_users:
            return None

        best_user_id = None
        max_metric = -1.0

        achieved_rates_this_step = {}

        for uid in uav.assigned_users:
            user = next((u for u in all_users if u.entity_id == uid), None)
            if user:
                # Get instantaneous rate R_i(t)
                sinr = self.interference_model.calculate_uplink_sinr(user, uav, [user])
                rate = self.interference_model.shannon_capacity_bps(sinr)
                achieved_rates_this_step[uid] = rate

                # Get average rate \bar{R}_i(t)
                avg_rate = self.avg_rates.get(uid, 1e-6) # small value to avoid div-by-zero

                pf_metric = rate / avg_rate

                if pf_metric > max_metric:
                    max_metric = pf_metric
                    best_user_id = uid

        # Update exponential average for all assigned users
        for uid in uav.assigned_users:
            current_avg = self.avg_rates.get(uid, 0.0)

            if uid == best_user_id:
                rate = achieved_rates_this_step.get(uid, 0.0)
                self.avg_rates[uid] = (1 - self.alpha) * current_avg + self.alpha * rate
            else:
                self.avg_rates[uid] = (1 - self.alpha) * current_avg

        return best_user_id
