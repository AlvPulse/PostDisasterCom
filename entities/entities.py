import numpy as np
from traffic.queue import PacketQueue

class Entity:
    def __init__(self, entity_id, x, y, height):
        self.entity_id = entity_id
        self.position = np.array([x, y, height], dtype=float)
        self.queue = PacketQueue()

    def get_position(self):
        return self.position

class User(Entity):
    def __init__(self, entity_id, x, y, height, spawn_time):
        super().__init__(entity_id, x, y, height)
        self.spawn_time = spawn_time
        self.assigned_service_uav = None

class UAV(Entity):
    def __init__(self, entity_id, x, y, height):
        super().__init__(entity_id, x, y, height)
        self.energy_consumed = 0.0

class ServiceUAV(UAV):
    def __init__(self, entity_id, x, y, height):
        super().__init__(entity_id, x, y, height)
        self.assigned_users = [] # IDs of currently associated users
        self.assigned_relay_uav = None

class RelayUAV(UAV):
    def __init__(self, entity_id, x, y, height):
        super().__init__(entity_id, x, y, height)
        self.assigned_service_uavs = []

class HQ(Entity):
    def __init__(self, entity_id, x, y, height):
        super().__init__(entity_id, x, y, height)
