import numpy as np

class CLCBCRelaySelection:
    # Used implicitly inside routing or as a separate layer.
    # We implemented the formula inside routing directly for path selection,
    # but we can provide this as a utility for the full stack.

    @staticmethod
    def get_relay_score(cap, q_relay, energy_rem, delta=1.0, eta=1e6, theta=0.1):
        # cap in bps, q_relay in bits, energy_rem in Joules
        q_relay_mbits = q_relay / 1e6
        score = delta * cap - eta * q_relay_mbits + theta * energy_rem
        return score
