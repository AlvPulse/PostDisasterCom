import numpy as np

class SchedulingAlgorithm:
    def observe(self, state):
        """Receive state from simulator."""
        pass

    def decide(self):
        """Return decisions (associations, movement)."""
        pass

    def apply(self, environment):
        """Apply decisions to the simulator."""
        pass

class DefaultScheduler(SchedulingAlgorithm):
    """
    A baseline greedy scheduler for testing the environment.
    """
    def __init__(self, config):
        self.control_step = float(config['simulation']['control_step'])

    def observe(self, state):
        self.users = state['users']
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']
        self.interference_model = state['interference_model']

    def decide(self):
        associations = {} # user_id -> service_uav

        # Simple Greedy Association based purely on distance (as a proxy for SINR in baseline)
        for user in self.users:
            best_uav = None
            min_dist = float('inf')
            for uav in self.service_uavs:
                dist = np.linalg.norm(user.position - uav.position)
                if dist < min_dist:
                    min_dist = dist
                    best_uav = uav
            associations[user.entity_id] = best_uav

        # Service UAV -> Relay UAV association
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

        return {'associations': associations, 'service_associations': service_associations, 'movements': {}}

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
