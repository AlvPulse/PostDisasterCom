import numpy as np

class Metrics:
    def __init__(self):
        pass

    @staticmethod
    def jains_fairness_index(values):
        """Calculates Jain's Fairness Index for a list of values."""
        if len(values) == 0 or sum(values) == 0:
            return 0.0
        n = len(values)
        sum_val = sum(values)
        sum_sq = sum(v**2 for v in values)
        return (sum_val**2) / (n * sum_sq)

    @staticmethod
    def max_min_fairness(values):
        """Returns the minimum value (Max-Min fairness aims to maximize this)."""
        if len(values) == 0:
            return 0.0
        return min(values)

    @staticmethod
    def calculate_pdr(delivered, generated):
        """Packet Delivery Ratio."""
        if generated == 0:
            return 1.0
        return delivered / generated
