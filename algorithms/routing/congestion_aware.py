import numpy as np
from algorithms.base_algorithm import RoutingAlgorithm

class CongestionAwareRouting(RoutingAlgorithm):
    def observe(self, state):
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']
        self.interference_model = state['interference_model']

    def decide(self):
        service_associations = {}

        for s_uav in self.service_uavs:
            best_relay = None
            max_score = -1.0

            for r_uav in self.relay_uavs:
                if not getattr(r_uav, 'is_active', True): continue

                sinr = self.interference_model.calculate_backhaul_sinr(s_uav, r_uav, [s_uav])
                cap = self.interference_model.shannon_capacity_bps(sinr)

                # Capacity penalized by relay queue size (congestion)
                # Add 1 to avoid division by zero. Convert bits to Mbits for numerical stability
                q_relay_mbits = r_uav.queue.total_bits / 1e6
                score = cap / (1.0 + q_relay_mbits)

                if score > max_score:
                    max_score = score
                    best_relay = r_uav

            service_associations[s_uav.entity_id] = best_relay

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
