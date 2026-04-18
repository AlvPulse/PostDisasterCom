import numpy as np
import time
from config_loader import config
from core.simulator import Simulator
from core.scheduler import ClosestFirstScheduler, RandomScheduler, MaxWeightScheduler
from metrics import Metrics
from reporting.data_exporter import DataExporter
from reporting.journal_plots import JournalPlots
from reporting.debug_plots import DebugPlots
from reporting.animator import Animator

NUM_SEEDS = 3
SIM_DURATION_SEC = 20 # shortened for batch testing
NUM_SERVICE = 6
NUM_RELAY = 2

def run_single_seed(algo_class, seed):
    np.random.seed(seed)

    sim = Simulator(config, algo_class(config))
    sim.setup_scenario(NUM_SERVICE, NUM_RELAY)

    control_step = float(config['simulation']['control_step'])
    num_steps = int(SIM_DURATION_SEC / control_step)

    history = []
    throughputs = []
    avg_qs = []

    for _ in range(num_steps):
        stats = sim.step()

        # Save positions for animation
        history.append({
            'uav_positions': stats['uav_positions'],
            'user_positions': stats['user_positions']
        })

        throughputs.append((stats['delivered_bits'] / control_step) / 1e6)
        avg_qs.append(stats['avg_queue'])
        sim.total_bits_delivered = 0

    pdr = Metrics.calculate_pdr(sim.packets_delivered, sim.packets_generated)

    user_thr = list(sim.user_throughputs.values()) if sim.user_throughputs else [0]
    jfi = Metrics.jains_fairness_index(user_thr)

    total_energy_joules = sum(u.energy_consumed for u in sim.service_uavs) + sum(u.energy_consumed for u in sim.relay_uavs)

    return {
        'history': history,
        'throughputs': throughputs,
        'avg_qs': avg_qs,
        'delays': sim.delays,
        'pdr': pdr,
        'jfi': jfi,
        'energy': total_energy_joules,
        'user_thr': user_thr
    }

def main():
    print("Starting Batch Experiments...")
    algorithms = {
        'Greedy (Closest)': ClosestFirstScheduler,
        'Random': RandomScheduler,
        'MaxWeight (SOTA)': MaxWeightScheduler
    }

    results = {algo: [] for algo in algorithms}

    for algo_name, algo_class in algorithms.items():
        for seed in range(NUM_SEEDS):
            print(f"Running {algo_name} - Seed {seed}...")
            res = run_single_seed(algo_class, seed)
            results[algo_name].append(res)

    # Process Results for Reporting
    exporter = DataExporter('output')
    journal = JournalPlots('output')
    debug = DebugPlots('output')
    animator = Animator('output')

    # 1. Summary CSV
    summary_rows = []
    for algo, runs in results.items():
        for i, r in enumerate(runs):
            summary_rows.append({
                'Algorithm': algo,
                'Seed': i,
                'PDR': r['pdr'],
                'JFI': r['jfi'],
                'Energy (J)': r['energy']
            })
    exporter.export_summary_csv(summary_rows)

    # 2. Journal Plots (CDF & Violin)
    all_delays = {algo: [] for algo in algorithms}
    jfi_dict = {algo: [] for algo in algorithms}
    energy_dict = {algo: [] for algo in algorithms}

    for algo, runs in results.items():
        for r in runs:
            all_delays[algo].extend(r['delays'])
            jfi_dict[algo].append(r['jfi'])
            energy_dict[algo].append(r['energy'])

    journal.plot_cdf(all_delays, 'CDF of User Delay', 'Delay (s)', 'journal_delay_cdf.png')
    journal.plot_violin(jfi_dict, 'Fairness Distribution across Seeds', 'JFI', 'journal_jfi_violin.png')
    journal.plot_violin(energy_dict, 'Energy Distribution across Seeds', 'Energy (J)', 'journal_energy_violin.png')

    # 3. Debug Plots (95% CI & Radar)
    times = np.arange(1, SIM_DURATION_SEC + 1)
    thr_runs = {algo: [r['throughputs'] for r in runs] for algo, runs in results.items()}
    debug.plot_with_confidence_intervals(times, thr_runs, 'Network Throughput (95% CI)', 'Throughput (Mbps)', 'debug_throughput_ci.png')

    # Radar requires normalized or relative metrics. We aggregate means:
    radar_data = {}
    for algo in algorithms:
        m_thr = np.mean([np.mean(r['throughputs']) for r in results[algo]])
        m_jfi = np.mean(jfi_dict[algo])
        # Energy is a cost, so invert or normalize it for radar.
        m_eng = np.mean(energy_dict[algo])
        m_eng_norm = 1.0 / (m_eng + 1e-6) # higher is better for radar
        radar_data[algo] = [m_thr, m_jfi, m_eng_norm]

    debug.plot_radar(radar_data, ['Avg Throughput', 'Fairness (JFI)', 'Energy Efficiency'], 'Performance Profile', 'debug_radar.png')

    # 4. Animation (Best run of MaxWeight)
    best_mw_run = max(results['MaxWeight (SOTA)'], key=lambda x: x['pdr'])
    animator.create_battlefield_animation(
        best_mw_run['history'],
        float(config['network']['area'][0]),
        float(config['network']['area'][1]),
        'maxweight_battlefield.mp4'
    )

    print("Experiments complete. Results saved to output/ directory.")

if __name__ == "__main__":
    main()
