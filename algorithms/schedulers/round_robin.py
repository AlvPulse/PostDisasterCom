import numpy as np
from algorithms.base_algorithm import SchedulingAlgorithm

class RoundRobinScheduler(SchedulingAlgorithm):
    def __init__(self):
        self.uav_user_indices = {}

    def observe(self, state):
        self.users = state['users']
        self.service_uavs = state['service_uavs']

    def decide(self):
        associations = {}
        # Step 1: Default to closest Service UAV to populate the assigned users
        # (Since RR schedules among "associated" users, they first must be associated)
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

    def get_active_user(self, uav):
        """Micro-step scheduling hook for the simulator."""
        if not uav.assigned_users:
            return None

        # Initialize index if new UAV
        if uav.entity_id not in self.uav_user_indices:
            self.uav_user_indices[uav.entity_id] = 0

        idx = self.uav_user_indices[uav.entity_id]
        if idx >= len(uav.assigned_users):
            idx = 0

        served_user_id = uav.assigned_users[idx]

        # Advance pointer for next time
        self.uav_user_indices[uav.entity_id] = (idx + 1) % len(uav.assigned_users)

        return served_user_id
