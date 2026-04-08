import numpy as np
from network.antenna import Antenna

class InterferenceModel:
    def __init__(self, config, channel_model):
        self.config = config
        self.channel = channel_model

        # Power levels in Watts
        self.p_tx_user_w = self._dbm_to_w(self.config['radio']['tx_power_dbm']['user'])
        self.p_tx_service_w = self._dbm_to_w(self.config['radio']['tx_power_dbm']['service_uav'])

        # Noise power in Watts
        nf_dbm_hz = float(self.config['radio']['noise_figure_dbm_hz'])
        bandwidth = float(self.config['radio']['bandwidth'])
        noise_dbm = nf_dbm_hz + 10 * np.log10(bandwidth)
        self.noise_w = self._dbm_to_w(noise_dbm)

        # Antenna counts
        self.ant_user = int(self.config['radio']['antennas']['user'])
        self.ant_service = int(self.config['radio']['antennas']['service_uav'])
        self.ant_relay = int(self.config['radio']['antennas']['relay_uav'])

        self.null_att_db = float(self.config['radio']['nullforming_attenuation_db'])

    def _dbm_to_w(self, dbm):
        return 10 ** ((dbm - 30) / 10)

    def _db_to_linear(self, db):
        return 10 ** (db / 10)

    def calculate_uplink_sinr(self, user, target_uav, all_transmitting_users):
        """
        Calculate SINR for User -> Service UAV uplink.
        all_transmitting_users: list of user entities transmitting on the same channel in this timestep.
        Returns: SINR (linear)
        """
        # Desired signal
        pl_db, _ = self.channel.get_path_loss_a2g(user.position, target_uav.position)
        gain_db = Antenna.get_total_gain_db(self.ant_user, self.ant_service, float(self.config['radio']['pointing_loss_db']))

        rx_power_dbm = self.config['radio']['tx_power_dbm']['user'] + gain_db - pl_db
        s_w = self._dbm_to_w(rx_power_dbm)

        # Interference from other users
        i_w = 0.0
        for other_user in all_transmitting_users:
            if other_user.entity_id == user.entity_id:
                continue

            pl_i_db, _ = self.channel.get_path_loss_a2g(other_user.position, target_uav.position)
            # Interference is hit by the nullforming attenuation at the receiver
            g_i_db = Antenna.get_beamforming_gain_db(self.ant_user) + self.null_att_db

            rx_i_dbm = self.config['radio']['tx_power_dbm']['user'] + g_i_db - pl_i_db
            i_w += self._dbm_to_w(rx_i_dbm)

        sinr = s_w / (i_w + self.noise_w)
        return sinr

    def calculate_backhaul_sinr(self, service_uav, target_relay, all_transmitting_services):
        """
        Calculate SINR for Service UAV -> Relay UAV backhaul.
        Calculates using Friis/A2A path loss.
        """
        pl_db = self.channel.get_path_loss_a2a(service_uav.position, target_relay.position)
        gain_db = Antenna.get_total_gain_db(self.ant_service, self.ant_relay, float(self.config['radio']['pointing_loss_db']))

        rx_power_dbm = self.config['radio']['tx_power_dbm']['service_uav'] + gain_db - pl_db
        s_w = self._dbm_to_w(rx_power_dbm)

        i_w = 0.0
        for other_service in all_transmitting_services:
            if other_service.entity_id == service_uav.entity_id:
                continue

            pl_i_db = self.channel.get_path_loss_a2a(other_service.position, target_relay.position)
            g_i_db = Antenna.get_beamforming_gain_db(self.ant_service) + self.null_att_db

            rx_i_dbm = self.config['radio']['tx_power_dbm']['service_uav'] + g_i_db - pl_i_db
            i_w += self._dbm_to_w(rx_i_dbm)

        sinr = s_w / (i_w + self.noise_w)
        return sinr

    def shannon_capacity_bps(self, sinr_linear):
        bandwidth = float(self.config['radio']['bandwidth'])
        return bandwidth * np.log2(1 + sinr_linear)
