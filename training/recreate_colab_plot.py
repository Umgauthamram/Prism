import matplotlib.pyplot as plt
import numpy as np
import os

def generate_colab_curve():
    # Ensure the directory exists
    os.makedirs(r"g:\projects\prism\website\public", exist_ok=True)
    
    # Replicating the data from the user screenshot
    episodes = np.arange(0, 31)
    # The curve goes from ~0.305 to ~0.35
    rolling_avg = 0.35 - 0.045 * np.exp(-episodes / 12)
    episode_reward = np.full_like(episodes, 0.352, dtype=float) # The light blue line at the top
    
    plt.figure(figsize=(10, 5))
    
    # Plotting
    plt.plot(episodes, episode_reward, color='#b0b0ff', alpha=0.5, label='Episode Reward')
    plt.plot(episodes, rolling_avg, color='blue', linewidth=2.5, label='Rolling Average')
    
    # Styling to match the screenshot
    plt.title('prism RL Training - Behavioral Learning Curve', fontsize=14)
    plt.xlabel('Episode', fontsize=11)
    plt.ylabel('Total Reward', fontsize=11)
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.2)
    plt.xlim(-1, 31)
    plt.ylim(0.303, 0.354)
    
    # Saving
    save_path = r"g:\projects\prism\website\public\colab_learning_curve.png"
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Image saved to {save_path}")

if __name__ == "__main__":
    generate_colab_curve()
