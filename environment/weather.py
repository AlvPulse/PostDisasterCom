import numpy as np

class WeatherModel:
    def __init__(self, mode='clear'):
        self.mode = mode
        # clear, rain, smoke, dust
        self.settings = {
            'clear': {'extra_path_loss': 0.0, 'los_prob_multiplier': 1.0},
            'rain': {'extra_path_loss': 5.0, 'los_prob_multiplier': 0.8},
            'smoke': {'extra_path_loss': 3.0, 'los_prob_multiplier': 0.6},
            'dust': {'extra_path_loss': 8.0, 'los_prob_multiplier': 0.4}
        }

    def get_weather_effects(self):
        return self.settings.get(self.mode, self.settings['clear'])
