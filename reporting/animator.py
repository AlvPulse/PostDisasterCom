import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import os

class Animator:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def create_battlefield_animation(self, history, area_x, area_y, filename="battlefield.mp4"):
        """
        history: list of dicts over time.
        Each dict has 'uav_positions': {id: [x,y,h]} and 'user_positions': {id: [x,y,h]}
        """
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xlim(0, area_x)
        ax.set_ylim(0, area_y)
        ax.set_title("Battlefield Live View (UAVs & Users)")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")

        # We can add a static SINR background if needed, but for now we plot nodes
        uav_scatter = ax.scatter([], [], c='red', marker='^', s=150, label='UAVs')
        user_scatter = ax.scatter([], [], c='blue', marker='o', s=20, alpha=0.5, label='Users')

        ax.legend()
        ax.grid(True)

        def init():
            uav_scatter.set_offsets(np.empty((0, 2)))
            user_scatter.set_offsets(np.empty((0, 2)))
            return uav_scatter, user_scatter

        def update(frame):
            state = history[frame]

            uav_pts = []
            for uid, pos in state['uav_positions'].items():
                uav_pts.append([pos[0], pos[1]])
            if uav_pts:
                uav_scatter.set_offsets(uav_pts)

            user_pts = []
            for uid, pos in state['user_positions'].items():
                user_pts.append([pos[0], pos[1]])
            if user_pts:
                user_scatter.set_offsets(user_pts)

            return uav_scatter, user_scatter

        ani = animation.FuncAnimation(fig, update, frames=len(history),
                                      init_func=init, blit=True, interval=100)

        # Save as MP4. Fallback to gif if ffmpeg not installed
        try:
            ani.save(os.path.join(self.output_dir, filename), writer='ffmpeg')
            print(f"Saved animation to {filename}")
        except Exception as e:
            print("Failed to save mp4, trying gif... (Install ffmpeg for mp4)")
            gif_filename = filename.replace('.mp4', '.gif')
            ani.save(os.path.join(self.output_dir, gif_filename), writer='imagemagick')
            print(f"Saved animation to {gif_filename}")
        finally:
            plt.close()
