import numpy as np
from algorithms.base_algorithm import SchedulingAlgorithm

class MaxWeightScheduler(SchedulingAlgorithm):
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
        """Micro-step scheduling hook for MaxWeight: Rate * Queue Length."""
        if not uav.assigned_users:
            return None

        best_user_id = None
        max_weight = -1.0

        for uid in uav.assigned_users:
            user = next((u for u in all_users if u.entity_id == uid), None)
            if user:
                sinr = self.interference_model.calculate_uplink_sinr(user, uav, [user])
                rate = self.interference_model.shannon_capacity_bps(sinr)
                q_len = user.queue.total_bits

                weight = rate * q_len

                if weight > max_weight:
                    max_weight = weight
                    best_user_id = uid

        return best_user_id
