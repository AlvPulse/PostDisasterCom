class AdvancedEnergyModel:
    def __init__(self, battery_capacity=500000.0, hover_power=300.0, movement_power_per_mps=20.0, tx_power_watts=2.0):
        self.battery_capacity = battery_capacity
        self.hover_power = hover_power
        self.movement_power_per_mps = movement_power_per_mps
        self.tx_power_watts = tx_power_watts

    def init_energy(self, uav):
        uav.battery_capacity = self.battery_capacity
        uav.energy_remaining = self.battery_capacity
        uav.is_active = True

    def consume_energy(self, uav, speed, is_transmitting, dt):
        if not uav.is_active:
            return

        power = self.hover_power
        power += speed * self.movement_power_per_mps
        if is_transmitting:
            power += self.tx_power_watts

        energy_used = power * dt
        uav.energy_remaining -= energy_used
        uav.energy_consumed += energy_used # for tracking

        if uav.energy_remaining <= 0:
            uav.energy_remaining = 0
            uav.is_active = False
