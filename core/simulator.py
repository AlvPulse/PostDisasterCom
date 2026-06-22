import numpy as np
from config_loader import config
from network.channel import ChannelModel
from network.interference import InterferenceModel
from mobility.mobility import MobilityManager
from traffic.traffic import TrafficGenerator
from entities.entities import User, ServiceUAV, RelayUAV, HQ
from algorithms.plugin import AlgorithmPlugin
from energy.uav_energy import AdvancedEnergyModel
from environment.weather import WeatherModel
from network.failure_model import FailureModel

class Simulator:
    def __init__(self, config_dict, plugin=None):
        self.config = config_dict
        self.timestep = float(self.config['simulation']['timestep'])
        self.control_step = float(self.config['simulation']['control_step'])

        self.channel_model = ChannelModel(self.config)
        self.interference_model = InterferenceModel(self.config, self.channel_model)
        self.mobility = MobilityManager(
            float(self.config['simulation']['grid_resolution']),
            float(self.config['network']['area'][0]),
            float(self.config['network']['area'][1])
        )
        self.energy_model = AdvancedEnergyModel()
        self.weather_model = WeatherModel(self.config.get('environment', {}).get('weather', 'clear'))
        self.failure_model = FailureModel(
            self.config.get('environment', {}).get('p_fail_per_hour', 0.01),
            self.config.get('environment', {}).get('failure_duration', 60.0)
        )
        self.channel_model.set_weather(self.weather_model.get_weather_effects())

        self.traffic_gen = TrafficGenerator(
            int(self.config['traffic']['avg_packet_size_bits']),
            float(self.config['traffic']['packet_arrival_rate']),
            int(self.config['traffic']['target_users']),
            float(self.config['traffic']['user_lifetime']),
            float(self.config['network']['area'][0]),
            float(self.config['network']['area'][1])
        )

        self.plugin = plugin if plugin else AlgorithmPlugin(self.config)

        self.current_time = 0.0
        self.users = []
        self.service_uavs = []
        self.relay_uavs = []
        self.hq = None

        # Metrics storage
        self.total_bits_delivered = 0
        self.packets_delivered = 0
        self.packets_dropped = 0
        self.packets_generated = 0
        self.packets_dropped = 0
        self.delays = []
        self.user_throughputs = {} # track total bits delivered per user
        self.user_delays = {} # track per-user delays

    def setup_scenario(self, num_service, num_relay):
        # Spawn UAVs
        h_s = float(self.config['network']['heights']['service_uav'])
        for i in range(num_service):
            x = np.random.uniform(0, self.config['network']['area'][0])
            y = np.random.uniform(0, self.config['network']['area'][1])
            uav = ServiceUAV(i, x, y, h_s)
            self.energy_model.init_energy(uav)
            self.service_uavs.append(uav)

        h_r = float(self.config['network']['heights']['relay_uav'])
        for i in range(num_relay):
            x = np.random.uniform(0, self.config['network']['area'][0])
            y = np.random.uniform(0, self.config['network']['area'][1])
            uav = RelayUAV(i, x, y, h_r)
            self.energy_model.init_energy(uav)
            self.relay_uavs.append(uav)

        h_hq = float(self.config['network']['heights']['hq'])
        self.hq = HQ(0, self.config['network']['area'][0]/2, self.config['network']['area'][1]/2, h_hq)

        # Initial users
        self.users = self.traffic_gen.spawn_and_expire_users([], self.current_time, self.control_step)

    def step(self):
        """Runs one control step (e.g., 1s), containing multiple physics timesteps (e.g., 1ms)."""
        # 1. Macro step: Control / RL Algorithm
        state = {
            'users': self.users,
            'service_uavs': self.service_uavs,
            'relay_uavs': self.relay_uavs,
            'interference_model': self.interference_model,
            'current_time': self.current_time
        }
        self.plugin.observe(state)
        self.plugin.apply(self) # Applies associations

        movements = self.plugin.get_movements()

        # Update Failures
        for uav in self.service_uavs + self.relay_uavs:
            self.failure_model.check_failure(uav, self.current_time)

        # Move UAVs and calculate energy
        for uav in self.service_uavs:
            if not uav.is_active or self.failure_model.check_failure(uav, self.current_time):
                continue
            action = movements.get(uav.entity_id, 0)
            v = self.mobility.move(uav, action, float(self.config['simulation']['speed_limits']['service_uav']), self.control_step)
            self.energy_model.consume_energy(uav, v, False, self.control_step)

        for uav in self.relay_uavs:
            if not uav.is_active or self.failure_model.check_failure(uav, self.current_time):
                continue
            action = movements.get(uav.entity_id, 0)
            v = self.mobility.move(uav, action, float(self.config['simulation']['speed_limits']['relay_uav']), self.control_step)
            self.energy_model.consume_energy(uav, v, False, self.control_step)

        # Spawn/expire users
        self.users = self.traffic_gen.spawn_and_expire_users(self.users, self.current_time, self.control_step)

        # Generate traffic for the control step
        total_gen = self.traffic_gen.generate_packets(self.users, self.current_time, self.control_step)
        self.packets_generated = total_gen

        # 2. Physics Micro-steps
        num_micro_steps = int(self.control_step / self.timestep)

        for _ in range(num_micro_steps):
            self.current_time += self.timestep

            # --- 2a. Uplink: User -> Service UAV ---
            active_users = []
            for uav in self.service_uavs:
                if not uav.is_active or self.failure_model.check_failure(uav, self.current_time):
                    continue
                if uav.assigned_users:
                    served_user_id = self.plugin.get_active_user(uav, self.users)
                    if served_user_id is not None:
                        user = next((u for u in self.users if u.entity_id == served_user_id), None)
                        if user and len(user.queue) > 0:
                            active_users.append(user)

            # Drain User queues
            for user in active_users:
                uav = user.assigned_service_uav
                self.energy_model.consume_energy(uav, 0, True, self.timestep)
                sinr = self.interference_model.calculate_uplink_sinr(user, uav, active_users)
                sinr_linear = 10**(np.clip(sinr, -100, 100)/10.0)
                sinr_linear = 10**(np.clip(sinr, -100, 100)/10.0)
                success_prob = self.channel_model.get_packet_success_prob(sinr_linear)

                capacity_bps = self.interference_model.shannon_capacity_bps(sinr)
                bits_this_step = capacity_bps * self.timestep

                bits_drained, completed_packets = user.queue.drain(bits_this_step)

                # Apply packet loss
                successful_packets = []
                for p in completed_packets:
                    if np.random.rand() < success_prob:
                        successful_packets.append(p)
                    else:
                        self.packets_dropped += 1
                completed_packets = successful_packets

                # Forward to Service UAV queue
                for p in completed_packets:
                    p.remaining_bits = p.original_size_bits # Reset bits for next hop
                    user.assigned_service_uav.queue.enqueue(p)

            # --- 2b. Backhaul: Service UAV -> Relay UAV ---
            active_service_uavs = []
            for r_uav in self.relay_uavs:
                if not r_uav.is_active or self.failure_model.check_failure(r_uav, self.current_time):
                    continue
                if r_uav.assigned_service_uavs:
                    served_s_uav_id = np.random.choice(r_uav.assigned_service_uavs)
                    s_uav = next((s for s in self.service_uavs if s.entity_id == served_s_uav_id), None)
                    if s_uav and len(s_uav.queue) > 0 and s_uav.is_active and not self.failure_model.check_failure(s_uav, self.current_time):
                        active_service_uavs.append(s_uav)

            # Drain Service UAV queues
            for s_uav in active_service_uavs:
                r_uav = s_uav.assigned_relay_uav
                self.energy_model.consume_energy(r_uav, 0, True, self.timestep)
                sinr = self.interference_model.calculate_backhaul_sinr(s_uav, r_uav, active_service_uavs)
                sinr_linear = 10**(np.clip(sinr, -100, 100)/10.0)
                success_prob = self.channel_model.get_packet_success_prob(sinr_linear)

                capacity_bps = self.interference_model.shannon_capacity_bps(sinr)
                bits_this_step = capacity_bps * self.timestep

                bits_drained, completed_packets = s_uav.queue.drain(bits_this_step)

                # Apply packet loss
                successful_packets = []
                for p in completed_packets:
                    if np.random.rand() < success_prob:
                        successful_packets.append(p)
                    else:
                        self.packets_dropped += 1
                completed_packets = successful_packets

                # Forward to Relay UAV queue
                for p in completed_packets:
                    p.remaining_bits = p.original_size_bits
                    r_uav.queue.enqueue(p)

            # --- 2c. Backhaul: Relay UAV -> HQ ---
            # Simplified: assuming dedicated high-capacity microwave link to HQ, no interference modeled.
            # Using constant high capacity for this final hop baseline.
            capacity_bps = 1e9 # 1 Gbps perfect link for HQ
            bits_this_step = capacity_bps * self.timestep

            for r_uav in self.relay_uavs:
                if not r_uav.is_active or self.failure_model.check_failure(r_uav, self.current_time):
                    continue
                bits_drained, completed_packets = r_uav.queue.drain(bits_this_step)
                self.total_bits_delivered += bits_drained
                self.packets_delivered += len(completed_packets)

                for p in completed_packets:
                    delay = self.current_time - p.creation_time
                    self.delays.append(delay)

                    if p.owner_id not in self.user_throughputs:
                        self.user_throughputs[p.owner_id] = 0
                        self.user_delays[p.owner_id] = []
                    self.user_throughputs[p.owner_id] += p.original_size_bits
                    self.user_delays[p.owner_id].append(delay)

        # Metrics Collection
        q_sizes = []
        for u in self.users: q_sizes.append(len(u.queue))
        for s in self.service_uavs: q_sizes.append(len(s.queue))

        relay_q_sizes = []
        for r in self.relay_uavs: relay_q_sizes.append(len(r.queue))

        # Copy snapshot of positions for animation
        uav_positions = {u.entity_id: u.position.copy() for u in self.service_uavs}
        user_positions = {u.entity_id: u.position.copy() for u in self.users}

        return {
            'time': self.current_time,
            'delivered_bits': self.total_bits_delivered,
            'delivered_packets': self.packets_delivered,
            'generated_packets': self.packets_generated,
            'dropped_packets': self.packets_dropped,
            'active_users': len(self.users),
            'avg_queue': np.mean(q_sizes) if q_sizes else 0,
            'peak_queue': np.max(q_sizes) if q_sizes else 0,
            'avg_relay_queue': np.mean(relay_q_sizes) if relay_q_sizes else 0,
            'max_relay_queue': np.max(relay_q_sizes) if relay_q_sizes else 0,
            'uav_positions': uav_positions,
            'user_positions': user_positions
        }
