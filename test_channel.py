import numpy as np
import matplotlib.pyplot as plt
from config_loader import config
from network.channel import ChannelModel

def verify_path_loss():
    cm = ChannelModel(config)

    distances_2d = np.linspace(10, 3000, 300)
    h_uav = 120.0

    pl_los_list = []
    pl_nlos_list = []
    prob_los_list = []

    for d in distances_2d:
        p_user = np.array([0, 0, 0])
        p_uav = np.array([d, 0, h_uav])

        d_3d, d_2d, h_diff = cm.compute_distance(p_user, p_uav)
        fspl = cm.get_fspl_db(d_3d)

        pl_los_list.append(fspl)
        pl_nlos_list.append(fspl + cm.pl_los_add_nlos)

        # Prob LoS
        theta_rad = np.arctan(h_uav / d)
        theta_deg = np.degrees(theta_rad)
        p_los = 1.0 / (1.0 + cm.a * np.exp(-cm.b * (theta_deg - cm.a)))
        prob_los_list.append(p_los)

    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(distances_2d, pl_los_list, label='LoS Path Loss')
    plt.plot(distances_2d, pl_nlos_list, label='NLoS Path Loss')
    plt.title('3GPP/Al-Hourani Path Loss vs 2D Distance')
    plt.xlabel('2D Distance (m)')
    plt.ylabel('Path Loss (dB)')
    plt.legend()
    plt.grid(True)

    plt.subplot(1, 2, 2)
    plt.plot(distances_2d, prob_los_list, color='green')
    plt.title('Al-Hourani Prob(LoS) vs 2D Distance (h=120m)')
    plt.xlabel('2D Distance (m)')
    plt.ylabel('Probability')
    plt.grid(True)

    plt.tight_layout()
    plt.savefig('path_loss_verification.png')
    print("Saved 'path_loss_verification.png'")

if __name__ == "__main__":
    verify_path_loss()
