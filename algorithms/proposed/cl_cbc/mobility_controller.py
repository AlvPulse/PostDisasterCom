import numpy as np
from algorithms.base_algorithm import MobilityAlgorithm

class CLCBCMobility(MobilityAlgorithm):
    def observe(self, state):
        self.users = state['users']
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']

    def decide(self):
        movements = {}

        for uav in self.service_uavs:
            if not getattr(uav, 'is_active', True):
                movements[uav.entity_id] = 0
                continue

            assigned_users = [u for u in self.users if u.assigned_service_uav == uav]
            if not assigned_users:
                movements[uav.entity_id] = 0
                continue

            # CL-CBC Mobility: score = user_density_gain + service_rate_gain - backhaul_congestion_penalty - energy_cost
            # We approximate this by moving towards the weighted center of mass of users,
            # where weights are queue sizes, penalized if uav queue is high (don't move, save energy)

            b_u = uav.queue.total_bits / 1e6
            energy_cost = 1.0 # arbitrary normalized cost

            # If backhaul is super congested, stay put to save energy
            if b_u > 50.0:
                movements[uav.entity_id] = 0
                continue

            com_x = 0
            com_y = 0
            total_weight = 0
            for u in assigned_users:
                w = u.queue.total_bits + 1
                com_x += u.position[0] * w
                com_y += u.position[1] * w
                total_weight += w

            com_x /= total_weight
            com_y /= total_weight

            dx = com_x - uav.position[0]
            dy = com_y - uav.position[1]

            if abs(dx) > abs(dy):
                if dx > 0: movements[uav.entity_id] = 3
                else: movements[uav.entity_id] = 4
            else:
                if dy > 0: movements[uav.entity_id] = 1
                else: movements[uav.entity_id] = 2

        for uav in self.relay_uavs:
            movements[uav.entity_id] = 0

        return {'movements': movements}

    def apply(self, environment):
        pass
