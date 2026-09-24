import pulp
import numpy as np

def solve_multiperiod_mip(traffic_matrix, solar_profile, 
                         P_O=50.0, P_T=20.0, P_S=10.0, E_wake=8.0, T_min=4,
                         E_max=500.0, E_min=50.0, eta_ch=0.9, eta_dis=0.9, HAPS_cap=2.2):
    """
    Multi-Period MIP with tight HAPS capacity (2.2) forcing SBSs to activate 
    during peak traffic hours in clean, non-oscillating blocks.
    """
    num_sbs, T = traffic_matrix.shape
    prob = pulp.LpProblem("MultiPeriod_CS", pulp.LpMinimize)
    
    # Decision Variables
    delta = pulp.LpVariable.dicts("delta", (range(num_sbs), range(T)), cat=pulp.LpBinary)
    delta_plus = pulp.LpVariable.dicts("delta_plus", (range(num_sbs), range(T)), lowBound=0, cat=pulp.LpContinuous)
    offload = pulp.LpVariable.dicts("offload", (range(num_sbs), range(T)), lowBound=0, upBound=1, cat=pulp.LpContinuous)
    
    # Battery Variables
    E = pulp.LpVariable.dicts("SoC", range(T + 1), lowBound=E_min, upBound=E_max, cat=pulp.LpContinuous)
    P_ch = pulp.LpVariable.dicts("P_ch", range(T), lowBound=0, cat=pulp.LpContinuous)
    P_dis = pulp.LpVariable.dicts("P_dis", range(T), lowBound=0, cat=pulp.LpContinuous)
    
    # Objective Function
    objective_terms = []
    for t in range(T):
        for j in range(num_sbs):
            sbs_pwr = (P_O + traffic_matrix[j, t] * P_T) * delta[j][t] + P_S * (1 - delta[j][t])
            wake_pwr = E_wake * delta_plus[j][t]
            objective_terms.extend([sbs_pwr, wake_pwr])
        objective_terms.append(P_dis[t] * 0.1)
        
    prob += pulp.lpSum(objective_terms)
    
    # Initial Conditions
    prob += E[0] == 400.0
    prob += E[T] >= E[0]
    
    for t in range(T):
        for j in range(num_sbs):
            prob += delta[j][t] + offload[j][t] >= traffic_matrix[j, t]
            
            if t > 0:
                prob += delta_plus[j][t] >= delta[j][t] - delta[j][t - 1]
            else:
                prob += delta_plus[j][t] >= delta[j][0]
                
            # Minimum sleep duration constraint
            if t >= T_min and t > 0:
                sleep_sum = pulp.lpSum([1 - delta[j][tau] for tau in range(t, min(t + T_min, T))])
                prob += sleep_sum >= T_min * (delta[j][t - 1] - delta[j][t])
                
        # Per-slot HAPS capacity limit
        prob += pulp.lpSum([offload[j][t] for j in range(num_sbs)]) <= HAPS_cap
        
        # Battery dynamics
        total_offload_kw = pulp.lpSum([offload[j][t] * 12.0 for j in range(num_sbs)])
        prob += P_ch[t] <= solar_profile[t]
        prob += P_dis[t] >= total_offload_kw + 15.0 - (solar_profile[t] - P_ch[t])
        prob += E[t + 1] == E[t] + 0.25 * (eta_ch * P_ch[t] - (P_dis[t] / eta_dis))

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    states = np.zeros((num_sbs, T))
    wake_ups = np.zeros((num_sbs, T))
    soc_history = [pulp.value(E[t]) for t in range(T + 1)]
    
    for j in range(num_sbs):
        for t in range(T):
            states[j, t] = pulp.value(delta[j][t])
            wake_ups[j, t] = pulp.value(delta_plus[j][t])
            
    return states, wake_ups, soc_history