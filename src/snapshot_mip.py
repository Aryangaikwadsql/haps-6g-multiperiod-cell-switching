import pulp
import numpy as np

def solve_snapshot_mip(traffic_slot, P_O=50.0, P_T=20.0, P_S=10.0, HAPS_cap=4.0):
    """
    Solves an independent single-snapshot MIP optimization for a single time slot t.
    Excludes temporal penalties and past-state awareness.
    """
    num_sbs = len(traffic_slot)
    prob = pulp.LpProblem("Snapshot_CS", pulp.LpMinimize)
    
    # Decision Variables
    delta = pulp.LpVariable.dicts("delta", range(num_sbs), cat=pulp.LpBinary)
    offload = pulp.LpVariable.dicts("offload", range(num_sbs), lowBound=0, upBound=1, cat=pulp.LpContinuous)
    
    # Objective: Minimize terrestrial SBS grid power only
    prob += pulp.lpSum([
        (P_O + traffic_slot[j] * P_T) * delta[j] + P_S * (1 - delta[j])
        for j in range(num_sbs)
    ])
    
    # Constraints
    for j in range(num_sbs):
        # Active SBS must serve its traffic, offloaded traffic goes to HAPS
        prob += delta[j] + offload[j] >= traffic_slot[j]
        
    # HAPS Offloading Capacity Constraint
    prob += pulp.lpSum([offload[j] for j in range(num_sbs)]) <= HAPS_cap
    
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    active_states = [int(pulp.value(delta[j])) for j in range(num_sbs)]
    offload_values = [pulp.value(offload[j]) for j in range(num_sbs)]
    grid_power = pulp.value(prob.objective)
    
    return active_states, offload_values, grid_power