import matplotlib.pyplot as plt
import numpy as np
import os

class JournalPlots:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def plot_cdf(self, data_dict, title, xlabel, filename):
        """Plot CDF for multiple datasets (e.g., comparing algorithms)."""
        plt.figure(figsize=(8, 6))
        for label, data in data_dict.items():
            if not data: continue
            sorted_data = np.sort(data)
            p = 1. * np.arange(len(data)) / (len(data) - 1)
            plt.plot(sorted_data, p, label=label, linewidth=2)

        plt.title(title, fontsize=14)
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel('CDF', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()

    def plot_violin(self, data_dict, title, ylabel, filename):
        """Plot Violin for multiple datasets (Energy, JFI)."""
        plt.figure(figsize=(8, 6))
        labels = list(data_dict.keys())
        data = [data_dict[l] for l in labels]

        parts = plt.violinplot(data, showmeans=True, showextrema=True)
        plt.xticks(np.arange(1, len(labels) + 1), labels, fontsize=12)
        plt.title(title, fontsize=14)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
