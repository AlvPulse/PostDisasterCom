import numpy as np
from traffic.queue import Packet
from entities.entities import User

class TrafficGenerator:
    def __init__(self, avg_packet_size_bits, packet_arrival_rate, target_users, user_lifetime, area_x, area_y):
        self.avg_packet_size_bits = avg_packet_size_bits
        self.packet_arrival_rate = packet_arrival_rate
        self.target_users = target_users
        self.user_lifetime = user_lifetime
        self.area_x = area_x
        self.area_y = area_y

        # Calculate optimal spawn rate (Little's Law: N = lambda * W -> lambda = N / W)
        self.user_spawn_rate = self.target_users / self.user_lifetime
        self.next_user_id = 0
        self.next_packet_id = 0

    def generate_packets(self, users, current_time, timestep):
        """Generates packets for all active users based on Poisson arrivals."""
        # Expected arrivals = rate * timestep
        expected_arrivals = self.packet_arrival_rate * timestep

        for user in users:
            # Poisson distributed number of arrivals
            num_packets = np.random.poisson(expected_arrivals)
            for _ in range(num_packets):
                # Pareto distributed packet size with expected value = avg_packet_size_bits
                # Mean of Pareto(a, m) = a*m / (a - 1)
                # Let's use a standard shape parameter a = 2.5
                shape = 2.5
                scale = self.avg_packet_size_bits * (shape - 1) / shape

                size_bits = int(np.random.pareto(shape) * scale)
                # Minimum size to avoid 0 length
                size_bits = max(size_bits, 100)

                packet = Packet(self.next_packet_id, user.entity_id, size_bits, current_time)
                user.queue.enqueue(packet)
                self.next_packet_id += 1
        return self.next_packet_id

    def spawn_and_expire_users(self, current_users, current_time, timestep):
        """Spawns new users and removes expired ones to maintain target average population."""
        expected_spawns = self.user_spawn_rate * timestep
        num_spawns = np.random.poisson(expected_spawns)

        for _ in range(num_spawns):
            x = np.random.uniform(0, self.area_x)
            y = np.random.uniform(0, self.area_y)
            # Sample lifetime from exponential distribution
            lifetime = np.random.exponential(self.user_lifetime)
            user = User(self.next_user_id, x, y, 0.0, current_time)
            user.expiration_time = current_time + lifetime
            current_users.append(user)
            self.next_user_id += 1

        # Expire old users
        active_users = [u for u in current_users if u.expiration_time > current_time]
        return active_users
