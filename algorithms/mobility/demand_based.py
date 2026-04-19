import numpy as np
from algorithms.base_algorithm import MobilityAlgorithm

class DemandBasedMobility(MobilityAlgorithm):
    def observe(self, state):
        self.users = state['users']
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']

    def decide(self):
        movements = {}

        # Service UAVs follow their assigned users
        for uav in self.service_uavs:
            assigned_users = [u for u in self.users if u.assigned_service_uav == uav]
            if not assigned_users:
                movements[uav.entity_id] = 0 # Hover if no users
            else:
                com_x = np.mean([u.position[0] for u in assigned_users])
                com_y = np.mean([u.position[1] for u in assigned_users])

                dx = com_x - uav.position[0]
                dy = com_y - uav.position[1]

                # Simple greedy step towards centroid
                # Actions: 0: Hover, 1: North, 2: South, 3: East, 4: West
                if abs(dx) > abs(dy):
                    if dx > 0: movements[uav.entity_id] = 3
                    else: movements[uav.entity_id] = 4
                else:
                    if dy > 0: movements[uav.entity_id] = 1
                    else: movements[uav.entity_id] = 2

        # Relay UAVs hover (or could follow Service UAVs, but we'll stick to hover for baseline)
        for uav in self.relay_uavs:
            movements[uav.entity_id] = 0

        return {'movements': movements}

    def apply(self, environment):
        pass
