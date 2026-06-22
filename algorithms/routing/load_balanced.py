import numpy as np
from algorithms.base_algorithm import RoutingAlgorithm

class LoadBalancedRouting(RoutingAlgorithm):
    def observe(self, state):
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']
        self.interference_model = state['interference_model']

    def decide(self):
        service_associations = {}

        # Sort service UAVs randomly to avoid systematic bias
        s_uavs = self.service_uavs.copy()
        np.random.shuffle(s_uavs)

        relay_loads = {r.entity_id: 0 for r in self.relay_uavs if getattr(r, 'is_active', True)}

        for s_uav in s_uavs:
            best_relay = None
            min_score = float('inf')

            for r_uav in self.relay_uavs:
                if not getattr(r_uav, 'is_active', True): continue
                # We want to minimize (load + path_loss_penalty)
                # This is a simple load balancer that considers distance and current assigned load
                dist = np.linalg.norm(s_uav.position - r_uav.position)
                score = relay_loads[r_uav.entity_id] * 1000 + dist

                if score < min_score:
                    min_score = score
                    best_relay = r_uav

            if best_relay:
                service_associations[s_uav.entity_id] = best_relay
                relay_loads[best_relay.entity_id] += 1

        return {'service_associations': service_associations}

    def apply(self, environment):
        decision = self.decide()

        for r_uav in environment.relay_uavs:
            r_uav.assigned_service_uavs = []

        for s_uav in environment.service_uavs:
            assigned_relay = decision['service_associations'].get(s_uav.entity_id)
            if assigned_relay:
                s_uav.assigned_relay_uav = assigned_relay
                assigned_relay.assigned_service_uavs.append(s_uav.entity_id)
