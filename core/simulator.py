import numpy as np
from config_loader import config
from network.channel import ChannelModel
from network.interference import InterferenceModel
from mobility.mobility import MobilityManager, EnergyModel
from traffic.traffic import TrafficGenerator
from entities.entities import User, ServiceUAV, RelayUAV, HQ
from core.scheduler import DefaultScheduler

class Simulator:
    def __init__(self, config_dict, scheduler=None):
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
        self.energy_model = EnergyModel()

        self.traffic_gen = TrafficGenerator(
            int(self.config['traffic']['avg_packet_size_bits']),
            float(self.config['traffic']['packet_arrival_rate']),
            int(self.config['traffic']['target_users']),
            float(self.config['traffic']['user_lifetime']),
            float(self.config['network']['area'][0]),
            float(self.config['network']['area'][1])
        )

        self.scheduler = scheduler if scheduler else DefaultScheduler(self.config)

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
        self.delays = []

    def setup_scenario(self, num_service, num_relay):
        # Spawn UAVs
        h_s = float(self.config['network']['heights']['service_uav'])
        for i in range(num_service):
            x = np.random.uniform(0, self.config['network']['area'][0])
            y = np.random.uniform(0, self.config['network']['area'][1])
            self.service_uavs.append(ServiceUAV(i, x, y, h_s))

        h_r = float(self.config['network']['heights']['relay_uav'])
        for i in range(num_relay):
            x = np.random.uniform(0, self.config['network']['area'][0])
            y = np.random.uniform(0, self.config['network']['area'][1])
            self.relay_uavs.append(RelayUAV(i, x, y, h_r))

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
        self.scheduler.observe(state)
        self.scheduler.apply(self) # Applies associations and movements

        # Move UAVs and calculate energy
        for uav in self.service_uavs:
            # Placeholder: baseline doesn't move them, so action=0 (hover)
            v = self.mobility.move(uav, 0, float(self.config['simulation']['speed_limits']['service_uav']), self.control_step)
            self.energy_model.consume_energy(uav, v, self.control_step)

        for uav in self.relay_uavs:
            v = self.mobility.move(uav, 0, float(self.config['simulation']['speed_limits']['relay_uav']), self.control_step)
            self.energy_model.consume_energy(uav, v, self.control_step)

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
                if uav.assigned_users:
                    # Pick one user randomly to serve in this 1ms slot (baseline scheduler)
                    served_user_id = np.random.choice(uav.assigned_users)
                    user = next((u for u in self.users if u.entity_id == served_user_id), None)
                    if user and len(user.queue) > 0:
                        active_users.append(user)

            # Drain User queues
            for user in active_users:
                sinr = self.interference_model.calculate_uplink_sinr(user, user.assigned_service_uav, active_users)
                capacity_bps = self.interference_model.shannon_capacity_bps(sinr)
                bits_this_step = capacity_bps * self.timestep

                bits_drained, completed_packets = user.queue.drain(bits_this_step)

                # Forward to Service UAV queue
                for p in completed_packets:
                    p.remaining_bits = p.original_size_bits # Reset bits for next hop
                    user.assigned_service_uav.queue.enqueue(p)

            # --- 2b. Backhaul: Service UAV -> Relay UAV ---
            active_service_uavs = []
            for r_uav in self.relay_uavs:
                if r_uav.assigned_service_uavs:
                    served_s_uav_id = np.random.choice(r_uav.assigned_service_uavs)
                    s_uav = next((s for s in self.service_uavs if s.entity_id == served_s_uav_id), None)
                    if s_uav and len(s_uav.queue) > 0:
                        active_service_uavs.append(s_uav)

            # Drain Service UAV queues
            for s_uav in active_service_uavs:
                sinr = self.interference_model.calculate_backhaul_sinr(s_uav, s_uav.assigned_relay_uav, active_service_uavs)
                capacity_bps = self.interference_model.shannon_capacity_bps(sinr)
                bits_this_step = capacity_bps * self.timestep

                bits_drained, completed_packets = s_uav.queue.drain(bits_this_step)

                # Forward to Relay UAV queue
                for p in completed_packets:
                    p.remaining_bits = p.original_size_bits
                    s_uav.assigned_relay_uav.queue.enqueue(p)

            # --- 2c. Backhaul: Relay UAV -> HQ ---
            # Simplified: assuming dedicated high-capacity microwave link to HQ, no interference modeled.
            # Using constant high capacity for this final hop baseline.
            capacity_bps = 1e9 # 1 Gbps perfect link for HQ
            bits_this_step = capacity_bps * self.timestep

            for r_uav in self.relay_uavs:
                bits_drained, completed_packets = r_uav.queue.drain(bits_this_step)
                self.total_bits_delivered += bits_drained
                self.packets_delivered += len(completed_packets)

                for p in completed_packets:
                    delay = self.current_time - p.creation_time
                    self.delays.append(delay)

        # Metrics Collection
        q_sizes = []
        for u in self.users: q_sizes.append(len(u.queue))
        for s in self.service_uavs: q_sizes.append(len(s.queue))
        for r in self.relay_uavs: q_sizes.append(len(r.queue))

        return {
            'time': self.current_time,
            'delivered_bits': self.total_bits_delivered,
            'delivered_packets': self.packets_delivered,
            'generated_packets': self.packets_generated,
            'active_users': len(self.users),
            'avg_queue': np.mean(q_sizes) if q_sizes else 0,
            'peak_queue': np.max(q_sizes) if q_sizes else 0
        }
