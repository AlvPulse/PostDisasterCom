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
    parser.add_argument('--runs', type=int, default=10, help='Number of seeds/runs')
    # Use stacks to evaluate:
    # 1. BaselineStack: PF + BestRelay + StaticMobility
    # 2. BackpressureStack: Backpressure + CongestionAware + DemandMobility
    # 3. ProposedStack: CLCBCScheduler + CLCBCRouting + CLCBCMobility
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

        # Service side metrics
        user_thr_5th = Metrics.percentile(user_thr, 5) / 1e6

        # Log Timeseries
        append_csv(result_paths['throughput'], {'time': t, 'algorithm': algo_name, 'seed': seed, 'metric_value': thr_mbps})
        append_csv(result_paths['fairness'], {'time': t, 'algorithm': algo_name, 'seed': seed, 'metric_value': jfi})
        append_csv(result_paths['relay_queue'], {'time': t, 'algorithm': algo_name, 'seed': seed, 'metric_value': stats['avg_relay_queue']})

        sim.total_bits_delivered = 0

        # Backhaul throughput & utilization calculation can be derived from relay delivered bits,
        # but overall throughput and energy covers main E2E.

        sim.total_bits_delivered = 0

    # Log End of Run
    pdr = Metrics.calculate_pdr(sim.packets_delivered, sim.packets_generated)
    append_csv(result_paths['pdr'], {'time': sim_duration_sec, 'algorithm': algo_name, 'seed': seed, 'metric_value': pdr})
    append_csv(result_paths['energy'], {'time': sim_duration_sec, 'algorithm': algo_name, 'seed': seed, 'metric_value': total_energy})

    # Save the 5th percentile throughput at the end as a distinct metric
    append_csv(result_paths['throughput_5th'], {'time': sim_duration_sec, 'algorithm': algo_name, 'seed': seed, 'metric_value': user_thr_5th})

    # Log Delays
    for d in sim.delays:
        append_csv(result_paths['delay'], {'time': sim_duration_sec, 'algorithm': algo_name, 'seed': seed, 'metric_value': d})

def main():
    args = parse_args()

    with open(args.scenario, 'r') as f:
        base_config = yaml.safe_load(f)

    scenario_name = os.path.splitext(os.path.basename(args.scenario))[0]
    out_dir = os.path.join('results', 'benchmark', scenario_name)
    os.makedirs(out_dir, exist_ok=True)

    paths = {
        'throughput': os.path.join(out_dir, 'throughput.csv'),
        'delay': os.path.join(out_dir, 'delay.csv'),
        'fairness': os.path.join(out_dir, 'fairness.csv'),
        'energy': os.path.join(out_dir, 'energy.csv'),
        'pdr': os.path.join(out_dir, 'pdr.csv'),
        'relay_queue': os.path.join(out_dir, 'relay_queue.csv'),
        'throughput_5th': os.path.join(out_dir, 'throughput_5th.csv')
    }

    # Init CSV headers
    for path in paths.values():
        init_csv(path, ['time', 'algorithm', 'seed', 'metric_value'])

    # Define Stacks
    stacks = {
        'BaselineStack': {'scheduler': 'proportional_fair', 'routing': 'best_relay', 'mobility': 'static_positions'},
        'BackpressureStack': {'scheduler': 'backpressure', 'routing': 'congestion_aware', 'mobility': 'demand_based'},
        'Proposed_CL_CBC': {
            'scheduler': 'proposed.cl_cbc.scheduler',
            'routing': 'proposed.cl_cbc.routing',
            'mobility': 'proposed.cl_cbc.mobility_controller'
        }
    }

    for algo_name, algo_config in stacks.items():
        print(f"\n--- Testing Stack: {algo_name} ---")

        config = dict(base_config)
        config['algorithm'] = algo_config

        for seed in range(args.runs):
            print(f"  Run {seed+1}/{args.runs}")
            run_experiment(config, algo_name, seed, paths)

if __name__ == "__main__":
    main()
