import numpy as np

class SchedulingAlgorithm:
    def observe(self, state):
        pass
    def decide(self):
        pass
    def apply(self, environment):
        pass

class BaseScheduler(SchedulingAlgorithm):
    def __init__(self, config):
        self.control_step = float(config['simulation']['control_step'])

    def observe(self, state):
        self.users = state['users']
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']
        self.interference_model = state['interference_model']

    def _get_relay_associations(self):
        # Common logic for relay associations (always closest)
        service_associations = {}
        for s_uav in self.service_uavs:
            best_relay = None
            min_dist = float('inf')
            for r_uav in self.relay_uavs:
                dist = np.linalg.norm(s_uav.position - r_uav.position)
                if dist < min_dist:
                    min_dist = dist
                    best_relay = r_uav
            service_associations[s_uav.entity_id] = best_relay
        return service_associations

    def apply(self, environment):
        decision = self.decide()

        # Apply User -> Service associations
        for uav in self.service_uavs:
            uav.assigned_users = []

        for user in self.users:
            assigned_uav = decision['associations'].get(user.entity_id)
            if assigned_uav:
                user.assigned_service_uav = assigned_uav
                assigned_uav.assigned_users.append(user.entity_id)

        # Apply Service -> Relay associations
        for r_uav in self.relay_uavs:
            r_uav.assigned_service_uavs = []

        for s_uav in self.service_uavs:
            assigned_relay = decision['service_associations'].get(s_uav.entity_id)
            if assigned_relay:
                s_uav.assigned_relay_uav = assigned_relay
                assigned_relay.assigned_service_uavs.append(s_uav.entity_id)

class ClosestFirstScheduler(BaseScheduler):
    """Associates users to the closest UAV and hovers."""
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

        # Hover for all movements (action=0)
        movements = {uav.entity_id: 0 for uav in self.service_uavs}

        return {'associations': associations,
                'service_associations': self._get_relay_associations(),
                'movements': movements}

class RandomScheduler(BaseScheduler):
    """Associates users randomly and moves randomly."""
    def decide(self):
        associations = {}
        for user in self.users:
            if self.service_uavs:
                associations[user.entity_id] = np.random.choice(self.service_uavs)

        # Random action in [0, 1, 2, 3, 4]
        movements = {uav.entity_id: np.random.randint(0, 5) for uav in self.service_uavs}

        return {'associations': associations,
                'service_associations': self._get_relay_associations(),
                'movements': movements}

class MaxWeightScheduler(BaseScheduler):
    """
    Associates users based on queue size (weight) and distance.
    Moves UAVs slightly towards the center of mass of their assigned heavily-loaded users.
    """
    def decide(self):
        associations = {}

        # 1. Association: Weight = queue_len / (distance^2 + 1)
        for user in self.users:
            best_uav = None
            max_weight = -1.0
            queue_len = len(user.queue)

            for uav in self.service_uavs:
                dist = np.linalg.norm(user.position - uav.position)
                weight = queue_len / (dist**2 + 1)

                if weight > max_weight:
                    max_weight = weight
                    best_uav = uav
            associations[user.entity_id] = best_uav

        # 2. Movement: Move towards Center of Mass of assigned users
        movements = {}
        for uav in self.service_uavs:
            assigned_users = [u for u in self.users if associations.get(u.entity_id) == uav]
            if not assigned_users:
                movements[uav.entity_id] = 0 # Hover
            else:
                com_x = np.mean([u.position[0] for u in assigned_users])
                com_y = np.mean([u.position[1] for u in assigned_users])

                dx = com_x - uav.position[0]
                dy = com_y - uav.position[1]

                if abs(dx) > abs(dy):
                    if dx > 0: movements[uav.entity_id] = 3 # East
                    else: movements[uav.entity_id] = 4 # West
                else:
                    if dy > 0: movements[uav.entity_id] = 1 # North
                    else: movements[uav.entity_id] = 2 # South

        return {'associations': associations,
                'service_associations': self._get_relay_associations(),
                'movements': movements}
