import numpy as np

def generate_diurnal_traffic(T=96, num_sbs=16, seed=42):
    """
    Generates a 24-hour urban traffic profile across 96 time slots (15-min intervals).
    Combines two peak commuter humps with local random fluctuations per SBS.
    """
    np.random.seed(seed)
    t = np.linspace(0, 24, T)
    
    # Dual Gaussian humps for morning (8 AM) and evening (7 PM) traffic peaks
    base_curve = (0.35 + 
                  0.45 * np.exp(-((t - 8) ** 2) / 8) + 
                  0.55 * np.exp(-((t - 19) ** 2) / 10))
    
    traffic = np.zeros((num_sbs, T))
    for s in range(num_sbs):
        noise = np.random.normal(0, 0.05, T)
        traffic[s, :] = np.clip(base_curve + noise, 0.05, 1.0)
        
    return traffic

def generate_solar_profile(T=96):
    """
    Generates a diurnal solar generation profile (kW) peaking around 1:00 PM (slot 52).
    """
    t = np.linspace(0, 24, T)
    solar = 120.0 * np.maximum(0, np.sin(np.pi * (t - 6) / 12))  # Active between 6 AM - 6 PM
    return solar