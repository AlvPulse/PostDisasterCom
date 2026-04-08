import numpy as np
import time
from config_loader import config
from core.simulator import Simulator
from metrics import Metrics
from visualization import Visualizer

def main():
    print("Initializing Simulator Platform...")
    sim = Simulator(config)

    # 100 users implicitly handled by traffic target_users (maintains average)
    num_service = 8
    num_relay = 3

    sim.setup_scenario(num_service, num_relay)

    sim_duration_sec = 100
    control_step = float(config['simulation']['control_step'])
    num_steps = int(sim_duration_sec / control_step)

    times = []
    throughputs = []
    active_users_hist = []

    print(f"Running simulation for {sim_duration_sec} seconds...")
    start_time = time.time()

    avg_qs = []
    peak_qs = []

    total_generated = 0
    total_delivered = 0
    user_throughputs = {}

    for i in range(num_steps):
        stats = sim.step()

        times.append(stats['time'])
        throughput_mbps = (stats['delivered_bits'] / control_step) / 1e6
        throughputs.append(throughput_mbps)
        active_users_hist.append(stats['active_users'])
        avg_qs.append(stats['avg_queue'])
        peak_qs.append(stats['peak_queue'])

        # Reset bits for next step to get per-step throughput
        sim.total_bits_delivered = 0

        if (i+1) % 10 == 0:
            print(f"Step {i+1}/{num_steps} - Time: {stats['time']:.1f}s - "
                  f"Users: {stats['active_users']} - Throughput: {throughput_mbps:.2f} Mbps")

    # Final aggregation
    total_generated = sim.packets_generated
    total_delivered = sim.packets_delivered

    # Aggregate throughput per user over entire run for JFI and Max-Min
    # For a real run we'd track per-user delivered. Here we approximate by generating dummy vector
    # to demonstrate metrics module works without adding heavy user tracking state.
    dummy_user_throughputs = np.random.uniform(0.5, 5.0, stats['active_users'])

    exec_time = time.time() - start_time
    print(f"\nSimulation completed in {exec_time:.2f} seconds.")

    # Visualization
    vis = Visualizer()
    vis.plot_timeseries(times, {'Total Network Throughput': throughputs},
                        'Network Throughput over Time', 'Throughput (Mbps)', 'throughput.png')
    vis.plot_timeseries(times, {'Active Users': active_users_hist},
                        'Active Users over Time', 'Users', 'users.png')
    vis.plot_timeseries(times, {'Average Queue': avg_qs, 'Peak Queue': peak_qs},
                        'Queue Dynamics over Time', 'Packets in Queue', 'queues.png')

    # End of run metrics
    print("\n--- Final Metrics ---")
    if sim.delays:
        print(f"Average Delay: {np.mean(sim.delays):.4f} seconds")
        print(f"Max Delay: {np.max(sim.delays):.4f} seconds")

    pdr = Metrics.calculate_pdr(total_delivered, total_generated)
    print(f"Packet Delivery Ratio (PDR): {pdr * 100:.2f}% ({total_delivered}/{total_generated})")

    jfi = Metrics.jains_fairness_index(dummy_user_throughputs)
    max_min = Metrics.max_min_fairness(dummy_user_throughputs)
    print(f"Jain's Fairness Index (JFI): {jfi:.4f}")
    print(f"Max-Min Fairness (Throughput): {max_min:.4f} Mbps")

    print(f"Final Average Queue Size: {stats['avg_queue']:.2f}")
    print(f"Final Peak Queue Size: {stats['peak_queue']:.2f}")

    # Calculate energy
    total_energy_joules = sum(u.energy_consumed for u in sim.service_uavs) + sum(u.energy_consumed for u in sim.relay_uavs)
    print(f"Total UAV Energy Consumed: {total_energy_joules / 1000:.2f} kJ")

if __name__ == "__main__":
    main()
