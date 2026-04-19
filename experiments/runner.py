import argparse
import yaml
import os
import csv
import numpy as np

from core.simulator import Simulator
from metrics import Metrics

def parse_args():
    parser = argparse.ArgumentParser(description="Run batch experiments for UAV Simulator")
    parser.add_argument('scenario', type=str, help='Path to scenario config YAML')
    parser.add_argument('--runs', type=int, default=1, help='Number of seeds/runs')
    parser.add_argument('--schedulers', type=str, nargs='+',
                        default=['round_robin', 'max_throughput', 'proportional_fair'],
                        help='List of schedulers to test')
    parser.add_argument('--mobility', type=str, nargs='+',
                        default=['static_positions', 'demand_based'],
                        help='List of mobility controllers to test')
    parser.add_argument('--routing', type=str, default='best_relay', help='Routing algorithm')
    return parser.parse_args()

def init_csv(filepath, fieldnames):
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

def append_csv(filepath, row_dict):
    with open(filepath, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=row_dict.keys())
        writer.writerow(row_dict)

def run_experiment(config, algo_name, seed, result_paths):
    np.random.seed(seed)

    sim = Simulator(config)

    num_service = int(config.get('experiments_overrides', {}).get('service_uavs', 8))
    num_relay = int(config.get('experiments_overrides', {}).get('relay_uavs', 3))

    sim.setup_scenario(num_service, num_relay)

    sim_duration_sec = float(config.get('experiments_overrides', {}).get('simulation_time', 60.0))
    control_step = float(config['simulation']['control_step'])
    num_steps = int(sim_duration_sec / control_step)

    for _ in range(num_steps):
        stats = sim.step()

        t = stats['time']
        thr_mbps = (stats['delivered_bits'] / control_step) / 1e6

        user_thr = list(sim.user_throughputs.values()) if sim.user_throughputs else [0]
        jfi = Metrics.jains_fairness_index(user_thr)

        total_energy = sum(u.energy_consumed for u in sim.service_uavs) + sum(u.energy_consumed for u in sim.relay_uavs)

        # Log Timeseries
        append_csv(result_paths['throughput'], {'time': t, 'algorithm': algo_name, 'seed': seed, 'metric_value': thr_mbps})
        append_csv(result_paths['fairness'], {'time': t, 'algorithm': algo_name, 'seed': seed, 'metric_value': jfi})

        sim.total_bits_delivered = 0

    # Log End of Run
    pdr = Metrics.calculate_pdr(sim.packets_delivered, sim.packets_generated)
    append_csv(result_paths['pdr'], {'time': sim_duration_sec, 'algorithm': algo_name, 'seed': seed, 'metric_value': pdr})
    append_csv(result_paths['energy'], {'time': sim_duration_sec, 'algorithm': algo_name, 'seed': seed, 'metric_value': total_energy})

    # Log Delays
    for d in sim.delays:
        append_csv(result_paths['delay'], {'time': sim_duration_sec, 'algorithm': algo_name, 'seed': seed, 'metric_value': d})

    # Save positions for final animation (only for seed 0 to save space)
    if seed == 0:
        import json
        history_path = os.path.join(os.path.dirname(result_paths['throughput']), f"{algo_name}_positions.json")

        # We need to serialize numpy arrays to lists
        def numpy_to_list(d):
            return {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in d.items()}

        with open(history_path, 'w') as f:
            json.dump({
                'uav_positions': numpy_to_list(stats['uav_positions']),
                'user_positions': numpy_to_list(stats['user_positions'])
            }, f)

def main():
    args = parse_args()

    with open(args.scenario, 'r') as f:
        base_config = yaml.safe_load(f)

    # Inject overrides for benchmark
    base_config['experiments_overrides'] = {
        'service_uavs': 8,
        'relay_uavs': 3,
        'simulation_time': 60.0 # Shortened from 600s for testing
    }

    out_dir = 'results'
    os.makedirs(out_dir, exist_ok=True)

    paths = {
        'throughput': os.path.join(out_dir, 'throughput.csv'),
        'delay': os.path.join(out_dir, 'delay.csv'),
        'fairness': os.path.join(out_dir, 'fairness.csv'),
        'energy': os.path.join(out_dir, 'energy.csv'),
        'pdr': os.path.join(out_dir, 'pdr.csv')
    }

    # Init CSV headers
    for path in paths.values():
        init_csv(path, ['time', 'algorithm', 'seed', 'metric_value'])

    for sched in args.schedulers:
        for mob in args.mobility:
            algo_name = f"{sched}_{mob}"
            print(f"\n--- Testing Algorithm Combination: {algo_name} ---")

            # Setup specific config for this combination
            config = dict(base_config)
            config['algorithm'] = {
                'scheduler': sched,
                'routing': args.routing,
                'mobility': mob
            }

            for seed in range(args.runs):
                print(f"  Run {seed+1}/{args.runs}")
                run_experiment(config, algo_name, seed, paths)

if __name__ == "__main__":
    main()
