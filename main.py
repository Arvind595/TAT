def get_relay_states(target_resistance: float) -> dict:
    """
    Calculates the required relay states to achieve the closest resistance 
    for the TAT Channel resistor network.
    
    Parameters:
        target_resistance (float): Desired resistance in Ohms (Ω).
        
    Returns:
        dict: Detailed dictionary containing target, actual achieved resistance,
              error, and active relay configurations.
    """
    FIXED_RESISTANCE = 30.0
    STEP_SIZE = 0.125
    MIN_RESISTANCE = 30.0
    MAX_RESISTANCE = 125.875

    # Clamp target within achievable limits
    clamped_target = max(MIN_RESISTANCE, min(MAX_RESISTANCE, target_resistance))
    
    # Calculate variable resistance needed
    r_var_needed = clamped_target - FIXED_RESISTANCE
    
    # Quantize to nearest 0.125 step
    step_count = round(r_var_needed / STEP_SIZE)
    
    # Determine Row 4 (32 Ohm stage)
    # R4-1 & R4-2 OPEN -> Inserts 32 ohms
    # R4-1 & R4-2 CLOSED -> Bypasses 32 ohms
    if step_count >= 256:  # 256 * 0.125 = 32.0 Ohms
        r4_bypass = False  # Inserts 32 ohms
        remaining_steps = step_count - 256
    else:
        r4_bypass = True   # Bypasses 32 ohms
        remaining_steps = step_count

    # Decode 3-digit Octal-like representation for Rows 3, 2, 1
    # Row 3 (8 Ohm per step = 64 x 0.125)
    r3_idx = remaining_steps // 64
    rem_after_r3 = remaining_steps % 64
    
    # Row 2 (1 Ohm per step = 8 x 0.125)
    r2_idx = rem_after_r3 // 8
    
    # Row 1 (0.125 Ohm per step)
    r1_idx = rem_after_r3 % 8

    # Calculate exact achieved resistance
    achieved_r4 = 0.0 if r4_bypass else 32.0
    achieved_r3 = r3_idx * 8.0
    achieved_r2 = r2_idx * 1.0
    achieved_r1 = r1_idx * 0.125
    actual_resistance = FIXED_RESISTANCE + achieved_r4 + achieved_r3 + achieved_r2 + achieved_r1

    # Formulate relay drive map
    relay_states = {
        "R4-1": "CLOSED (BYPASS)" if r4_bypass else "OPEN (ACTIVE)",
        "R4-2": "CLOSED (BYPASS)" if r4_bypass else "OPEN (ACTIVE)",
    }
    
    # Add Row 3 active relay
    for i in range(1, 9):
        relay_states[f"R3-{i}"] = "CLOSED" if i == (r3_idx + 1) else "OPEN"
        
    # Add Row 2 active relay
    for i in range(1, 9):
        relay_states[f"R2-{i}"] = "CLOSED" if i == (r2_idx + 1) else "OPEN"
        
    # Add Row 1 active relay
    for i in range(1, 9):
        relay_states[f"R1-{i}"] = "CLOSED" if i == (r1_idx + 1) else "OPEN"

    return {
        "target_resistance_ohms": target_resistance,
        "actual_resistance_ohms": round(actual_resistance, 3),
        "error_ohms": round(actual_resistance - target_resistance, 3),
        "active_relays": [k for k, v in relay_states.items() if "CLOSED" in v or "OPEN (ACTIVE)" in v],
        "full_relay_states": relay_states
    }

# --- Example Usage ---
if __name__ == "__main__":
    test_resistance = 30.11
    result = get_relay_states(test_resistance)

    print(f"Target Resistance : {result['target_resistance_ohms']} Ω")
    print(f"Actual Resistance : {result['actual_resistance_ohms']} Ω")
    print(f"Error             : {result['error_ohms']} Ω")
    print("\nActive Relays:")
    for relay in result['active_relays']:
        print(f"  - {relay}: {result['full_relay_states'][relay]}")
