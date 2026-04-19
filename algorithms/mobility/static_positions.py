from algorithms.base_algorithm import MobilityAlgorithm

class StaticPositions(MobilityAlgorithm):
    def observe(self, state):
        self.service_uavs = state['service_uavs']
        self.relay_uavs = state['relay_uavs']

    def decide(self):
        # 0 corresponds to 'Hover' in MobilityManager
        movements = {}
        for uav in self.service_uavs:
            movements[uav.entity_id] = 0
        for uav in self.relay_uavs:
            movements[uav.entity_id] = 0
        return {'movements': movements}

    def apply(self, environment):
        pass # The environment will execute movements based on the decision
