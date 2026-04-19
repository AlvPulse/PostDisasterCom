import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def plot_results(results_dir="results", output_dir="results/plots"):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Throughput vs Time
    try:
        df_thr = pd.read_csv(os.path.join(results_dir, 'throughput.csv'))
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df_thr, x='time', y='metric_value', hue='algorithm')
        plt.title('Throughput vs Time')
        plt.ylabel('Throughput (Mbps)')
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'throughput_vs_time.png'))
        plt.close()
    except Exception as e:
        print(f"Failed to plot throughput: {e}")

    # 2. Delay Distribution (CDF)
    try:
        df_del = pd.read_csv(os.path.join(results_dir, 'delay.csv'))
        plt.figure(figsize=(8, 6))
        sns.ecdfplot(data=df_del, x='metric_value', hue='algorithm')
        plt.title('Delay CDF')
        plt.xlabel('Delay (s)')
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'delay_cdf.png'))
        plt.close()
    except Exception as e:
        print(f"Failed to plot delay: {e}")

    # 3. Fairness over time
    try:
        df_fair = pd.read_csv(os.path.join(results_dir, 'fairness.csv'))
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df_fair, x='time', y='metric_value', hue='algorithm')
        plt.title('Jains Fairness Index over Time')
        plt.ylabel('JFI')
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'fairness_over_time.png'))
        plt.close()
    except Exception as e:
        print(f"Failed to plot fairness: {e}")

    # 4. Energy Summary (Bar plot of average across seeds)
    try:
        df_eng = pd.read_csv(os.path.join(results_dir, 'energy.csv'))
        plt.figure(figsize=(8, 6))
        sns.barplot(data=df_eng, x='algorithm', y='metric_value')
        plt.title('Total UAV Energy Consumption')
        plt.ylabel('Energy (Joules)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'energy_bar.png'))
        plt.close()
    except Exception as e:
        print(f"Failed to plot energy: {e}")

    print(f"Plots generated and saved to {output_dir}")

if __name__ == "__main__":
    plot_results()
