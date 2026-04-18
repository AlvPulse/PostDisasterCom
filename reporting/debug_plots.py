import matplotlib.pyplot as plt
import numpy as np
import os

class DebugPlots:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def plot_with_confidence_intervals(self, times, data_dict, title, ylabel, filename):
        """Plot mean and 95% CI shaded region.
           data_dict[algo] = list of lists, where each sublist is a run.
        """
        plt.figure(figsize=(10, 6))
        for label, runs in data_dict.items():
            if not runs: continue
            runs_arr = np.array(runs)
            mean_val = np.mean(runs_arr, axis=0)
            std_val = np.std(runs_arr, axis=0)
            ci = 1.96 * std_val / np.sqrt(runs_arr.shape[0]) # 95% CI

            plt.plot(times, mean_val, label=label, linewidth=2)
            plt.fill_between(times, mean_val - ci, mean_val + ci, alpha=0.2)

        plt.title(title, fontsize=14)
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()

    def plot_radar(self, algo_metrics, labels, title, filename):
        """Plot a radar chart comparing algos on multiple dimensions."""
        # Normalize data manually for spider plot if needed, but here assume it's pre-normalized or raw
        num_vars = len(labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

        for algo, values in algo_metrics.items():
            vals = values + values[:1]
            ax.plot(angles, vals, label=algo, linewidth=2)
            ax.fill(angles, vals, alpha=0.25)

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles[:-1]), labels)
        plt.title(title, size=15, y=1.1)
        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()
