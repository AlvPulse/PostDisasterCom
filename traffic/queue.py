from collections import deque

class Packet:
    def __init__(self, packet_id, size_bits, creation_time):
        self.packet_id = packet_id
        self.original_size_bits = size_bits
        self.remaining_bits = size_bits
        self.creation_time = creation_time

class PacketQueue:
    def __init__(self, max_size_packets=float('inf')):
        self.packets = deque()
        self.max_size_packets = max_size_packets
        self.total_bits = 0

    def enqueue(self, packet):
        if len(self.packets) >= self.max_size_packets:
            return False # Queue full, drop packet
        self.packets.append(packet)
        self.total_bits += packet.remaining_bits
        return True

    def drain(self, bits_to_drain):
        bits_drained_total = 0
        drained_packets = []

        while self.packets and bits_to_drain > 0:
            current_packet = self.packets[0]
            if bits_to_drain >= current_packet.remaining_bits:
                bits_drained = current_packet.remaining_bits
                bits_to_drain -= bits_drained
                bits_drained_total += bits_drained
                self.total_bits -= bits_drained

                drained_packets.append(self.packets.popleft())
            else:
                current_packet.remaining_bits -= bits_to_drain
                self.total_bits -= bits_to_drain
                bits_drained_total += bits_to_drain
                bits_to_drain = 0

        return bits_drained_total, drained_packets

    def __len__(self):
        return len(self.packets)
