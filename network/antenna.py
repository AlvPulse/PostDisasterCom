import numpy as np

class Antenna:
    @staticmethod
    def get_beamforming_gain_db(num_antennas):
        """Standard array gain G = 10 * log10(N)"""
        if num_antennas <= 1:
            return 0.0
        return 10.0 * np.log10(num_antennas)

    @staticmethod
    def get_nullforming_attenuation_db(nullforming_db=-25.0):
        """Simplified placeholder for null depth towards interferers."""
        return nullforming_db

    @staticmethod
    def get_total_gain_db(tx_antennas, rx_antennas, pointing_loss_db=2.0):
        """Total link gain assuming beam alignment."""
        gtx = Antenna.get_beamforming_gain_db(tx_antennas)
        grx = Antenna.get_beamforming_gain_db(rx_antennas)
        return gtx + grx - pointing_loss_db
