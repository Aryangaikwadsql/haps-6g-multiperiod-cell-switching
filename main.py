import os
import numpy as np
import matplotlib.pyplot as plt
from src.network_model import generate_diurnal_traffic, generate_solar_profile
from src.snapshot_mip import solve_snapshot_mip
from src.multiperiod_mip import solve_multiperiod_mip

def count_wakeups(states_matrix, threshold=0.5):
    """Calculates true 0 -> 1 state transition events across time slots."""
    binary_states = (states_matrix > threshold).astype(int)
    wakeups = 0
    num_sbs, T = binary_states.shape
    for j in range(num_sbs):
        for t in range(1, T):
            if binary_states[j, t] == 1 and binary_states[j, t - 1] == 0:
                wakeups += 1
    return wakeups

def main():
    print("==========================================================")
    print(" HAPS-Enhanced vHetNet Cell Switching Simulation Framework ")
    print("==========================================================")
    
    os.makedirs("results", exist_ok=True)
    
    T = 96
    num_sbs = 16
    traffic = generate_diurnal_traffic(T=T, num_sbs=num_sbs)
    solar = generate_solar_profile(T=T)
    
    print(f"\n[1/3] Running 96 Independent Snapshot Optimizations...")
    snapshot_states = np.zeros((num_sbs, T))
    for t in range(T):
        states, _, _ = solve_snapshot_mip(traffic[:, t])
        snapshot_states[:, t] = states
        
    # Calculate Snapshot Wake-up Transitions
    snapshot_wakeups = count_wakeups(snapshot_states)
    print(f" -> Snapshot Optimization Total Wake-Up Transitions: {snapshot_wakeups}")
    
    print(f"\n[2/3] Running Multi-Period Optimization with Transition Penalties & SoC...")
    mp_states, _, soc_history = solve_multiperiod_mip(traffic, solar)
    
    # Calculate Multi-Period Wake-up Transitions consistently
    total_mp_wakeups = count_wakeups(mp_states)
    
    reduction = ((snapshot_wakeups - total_mp_wakeups) / snapshot_wakeups) * 100 if snapshot_wakeups > 0 else 0
    print(f" -> Multi-Period Optimization Total Wake-Up Transitions: {total_mp_wakeups}")
    print(f" -> Transition Reduction: {reduction:.1f}%")
    
    print(f"\n[3/3] Generating Plots in 'results/' directory...")
    
    # Plot 1: State Toggling Comparison
    fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    
    ax[0].imshow(snapshot_states, aspect='auto', cmap='Blues', extent=[0, 24, 16, 1], vmin=0, vmax=1)
    ax[0].set_title(f"Baseline Snapshot MIP (Total Wake-Ups: {snapshot_wakeups})", fontsize=11, fontweight='bold')
    ax[0].set_ylabel("SBS Index")
    
    ax[1].imshow(mp_states, aspect='auto', cmap='Greens', extent=[0, 24, 16, 1], vmin=0, vmax=1)
    ax[1].set_title(f"Proposed Multi-Period MIP (Total Wake-Ups: {total_mp_wakeups})", fontsize=11, fontweight='bold')
    ax[1].set_ylabel("SBS Index")
    ax[1].set_xlabel("Time of Day (Hours)")
    
    plt.tight_layout()
    plt.savefig("results/ping_pong_comparison.png", dpi=300)
    plt.close()
    
    # Plot 2: HAPS Battery SoC Profile
    plt.figure(figsize=(9, 4))
    plt.plot(np.linspace(0, 24, T + 1), soc_history, color='black', linewidth=2, label='HAPS Battery SoC (kWh)')
    plt.axhline(y=50, color='r', linestyle='--', label='Minimum Safe Reserve (SoC_min)')
    plt.title("24-Hour Diurnal HAPS Battery State-of-Charge (SoC) Dynamics", fontsize=11, fontweight='bold')
    plt.xlabel("Time of Day (Hours)")
    plt.ylabel("Battery Energy (kWh)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig("results/haps_soc_profile.png", dpi=300)
    plt.close()
    
    print("\nSimulation Complete! Results saved to 'results/' folder.")
    print("==========================================================")

if __name__ == "__main__":
    main()