import numpy as np
from algorithms.base_algorithm import SchedulingAlgorithm

class CLCBCScheduler(SchedulingAlgorithm):
    def __init__(self):
        self.alpha = 1e-6 # scale rate
        self.beta = 1.0   # scale queue
        self.gamma = 1e6  # scale backhaul congestion

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
                if not getattr(uav, 'is_active', True): continue
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
        """Cross-Layer Congestion Balanced Control Scheduler"""
        if not uav.assigned_users:
            return None

        best_user_id = None
        max_score = -float('inf')

        # B_u = congestion level of serving UAV backhaul
        b_u = uav.queue.total_bits / 1e6 # MBits

        for uid in uav.assigned_users:
            user = next((u for u in all_users if u.entity_id == uid), None)
            if user:
                sinr = self.interference_model.calculate_uplink_sinr(user, uav, [user])
                rate = self.interference_model.shannon_capacity_bps(sinr)
                q_i = user.queue.total_bits / 1e6 # MBits

                score = self.alpha * rate + self.beta * q_i - self.gamma * b_u

                if score > max_score:
                    max_score = score
                    best_user_id = uid

        return best_user_id
