import numpy as np
from algorithms.base_algorithm import RoutingAlgorithm

class BestRelayRouting(RoutingAlgorithm):
    def observe(self, state):
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']
        self.interference_model = state['interference_model']

    def decide(self):
        service_associations = {}
        for s_uav in self.service_uavs:
            best_relay = None
            max_capacity = -1.0

            for r_uav in self.relay_uavs:
                # We use SINR approximation with 0 interference for Best Relay
                # because we just want the highest capacity link (i.e. shortest distance/best LoS)
                sinr = self.interference_model.calculate_backhaul_sinr(s_uav, r_uav, [s_uav])
                cap = self.interference_model.shannon_capacity_bps(sinr)
                if cap > max_capacity:
                    max_capacity = cap
                    best_relay = r_uav

            service_associations[s_uav.entity_id] = best_relay
        return {'service_associations': service_associations}

    def apply(self, environment):
        decision = self.decide()

        # Reset current associations
        for r_uav in environment.relay_uavs:
            r_uav.assigned_service_uavs = []

        for s_uav in environment.service_uavs:
            assigned_relay = decision['service_associations'].get(s_uav.entity_id)
            if assigned_relay:
                s_uav.assigned_relay_uav = assigned_relay
                assigned_relay.assigned_service_uavs.append(s_uav.entity_id)
