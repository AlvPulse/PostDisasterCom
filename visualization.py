import matplotlib.pyplot as plt
import os

class Visualizer:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def plot_timeseries(self, times, data_dict, title, ylabel, filename):
        plt.figure(figsize=(10, 6))
        for label, data in data_dict.items():
            plt.plot(times, data, label=label)

        plt.title(title)
        plt.xlabel('Time (s)')
        plt.ylabel(ylabel)
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
