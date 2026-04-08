import numpy as np

class MobilityManager:
    def __init__(self, grid_resolution, limits_x, limits_y):
        self.grid_resolution = grid_resolution
        self.limits_x = limits_x
        self.limits_y = limits_y

    def move(self, uav, action, max_speed_mps, control_step_sec):
        """
        Actions: 0: Hover, 1: North, 2: South, 3: East, 4: West
        """
        # Distance allowed per control step based on max speed
        max_dist = max_speed_mps * control_step_sec
        # Constrain step to grid resolution if it exceeds max allowed distance
        # Actually, the user requirement: "Grid Resolution: Use a 20m grid (with 20m/s speed of UAVs)."
        # We will step by grid_resolution.
        step_size = self.grid_resolution

        if step_size > max_dist:
            step_size = max_dist # Respect physical speed limit

        dx, dy = 0.0, 0.0
        if action == 1: # North
            dy = step_size
        elif action == 2: # South
            dy = -step_size
        elif action == 3: # East
            dx = step_size
        elif action == 4: # West
            dx = -step_size

        new_x = uav.position[0] + dx
        new_y = uav.position[1] + dy

        # Enforce boundaries
        new_x = np.clip(new_x, 0, self.limits_x)
        new_y = np.clip(new_y, 0, self.limits_y)

        # Actual distance moved
        actual_dist = np.sqrt((new_x - uav.position[0])**2 + (new_y - uav.position[1])**2)
        v = actual_dist / control_step_sec

        uav.position[0] = new_x
        uav.position[1] = new_y

        return v

class EnergyModel:
    def __init__(self):
        # Parameters for Zeng's rotary-wing UAV power model
        self.W = 20  # Weight in Newtons (~2kg)
        self.rho = 1.225 # Air density
        self.A = 0.5 # Rotor disc area
        self.V_tip = 120 # Tip speed of rotor
        self.v_0 = 4.03 # Mean rotor induced velocity in hover
        self.d_0 = 0.015 # Fuselage drag ratio
        self.s = 0.05 # Rotor solidity
        self.P_0 = 79.8563 # Blade profile power in hover
        self.P_i = 88.6279 # Induced power in hover

    def get_power(self, v):
        """Calculate power consumption in Watts given velocity v."""
        # 1. Blade profile power
        P_b = self.P_0 * (1 + 3 * (v**2) / (self.V_tip**2))

        # 2. Induced power
        # For simplicity, finding roots for induced velocity v_i
        # v_i = v_0 (sqrt(1 + (v^4)/(4 * v_0^4)) - (v^2)/(2 * v_0^2))^(1/2)
        v_term = (v**4) / (4 * self.v_0**4)
        v_i = self.v_0 * np.sqrt(np.sqrt(1 + v_term) - (v**2) / (2 * self.v_0**2))
        P_ind = self.P_i * (v_i / self.v_0)

        # 3. Parasitic power
        P_p = 0.5 * self.d_0 * self.rho * self.s * self.A * (v**3)

        total_power_watts = P_b + P_ind + P_p
        return total_power_watts

    def consume_energy(self, uav, v, time_sec):
        power_watts = self.get_power(v)
        energy_joules = power_watts * time_sec
        uav.energy_consumed += energy_joules
        return energy_joules
