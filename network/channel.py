import numpy as np

class ChannelModel:
    def __init__(self, config):
        self.freq_hz = float(config['radio']['frequency'])
        self.freq_ghz = self.freq_hz / 1e9
        self.c = 3e8 # Speed of light

        # Al-Hourani parameters
        self.a = float(config['channel']['al_hourani']['a'])
        self.b = float(config['channel']['al_hourani']['b'])

        self.pl_los_add_nlos = float(config['channel']['path_loss']['los_additional_nlos'])
        self.std_los = float(config['channel']['path_loss']['shadowing_std_los'])
        self.std_nlos = float(config['channel']['path_loss']['shadowing_std_nlos'])

        self.weather_effects = {'extra_path_loss': 0.0, 'los_prob_multiplier': 1.0}

    def set_weather(self, weather_effects):
        self.weather_effects = weather_effects

    def compute_distance(self, pos1, pos2):
        d_3d = np.linalg.norm(pos1 - pos2)
        d_2d = np.linalg.norm((pos1[:2] - pos2[:2]))
        h_diff = abs(pos1[2] - pos2[2])
        return d_3d, d_2d, h_diff

    def get_fspl_db(self, d_3d):
        """Free Space Path Loss."""
        if d_3d < 1e-3:
            return 0.0
        return 20 * np.log10(d_3d) + 20 * np.log10(self.freq_ghz) + 32.44

    def is_los_al_hourani(self, d_2d, h_diff):
        """Probabilistic LoS based on Al-Hourani model."""
        if d_2d < 1e-3:
            theta_deg = 90.0
        else:
            theta_rad = np.arctan(h_diff / d_2d)
            theta_deg = np.degrees(theta_rad)

        p_los = 1.0 / (1.0 + self.a * np.exp(-self.b * (theta_deg - self.a)))
        p_los *= self.weather_effects['los_prob_multiplier']
        return np.random.rand() < p_los

    def apply_rayleigh_fading(self):
        # Rayleigh fading coefficient |h|^2 ~ Exp(1), in dB it's 10*log10(|h|^2)
        h_sq = np.random.exponential(1.0)
        return -10 * np.log10(h_sq + 1e-9)

    def get_path_loss_a2g(self, pos_ground, pos_uav):
        """Air-to-Ground path loss (User -> Service UAV)."""
        d_3d, d_2d, h_diff = self.compute_distance(pos_ground, pos_uav)
        fspl = self.get_fspl_db(d_3d)

        los = self.is_los_al_hourani(d_2d, h_diff)

        if los:
            pl = fspl
            shadowing = np.random.normal(0, self.std_los)
        else:
            pl = fspl + self.pl_los_add_nlos
            shadowing = np.random.normal(0, self.std_nlos)

        fading = self.apply_rayleigh_fading()

        total_pl_db = pl + shadowing + fading + self.weather_effects['extra_path_loss']
        return total_pl_db, los

    def get_path_loss_a2a(self, pos_uav1, pos_uav2):
        """Air-to-Air path loss (Service -> Relay). Modeled primarily as FSPL."""
        d_3d, _, _ = self.compute_distance(pos_uav1, pos_uav2)
        fspl = self.get_fspl_db(d_3d)

        # A2A links are mostly LoS. Add minor A2A shadowing
        shadowing = np.random.normal(0, self.std_los / 2.0)
        fading = self.apply_rayleigh_fading()

        return fspl + shadowing + fading + self.weather_effects['extra_path_loss']

    def get_packet_success_prob(self, sinr_linear, gamma_threshold=1.0):
        if sinr_linear <= 0:
            return 0.0
        return np.exp(-gamma_threshold / sinr_linear)
