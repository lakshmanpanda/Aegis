def calculate_c_pivot(
    delta_p: float, 
    s_rev: float, 
    v_soc: float, 
    m_macro: float, 
    r_risk: float,
    w1: float, 
    w2: float, 
    w3: float, 
    w4: float, 
    w5: float
) -> float:
    """
    AEGIS Strategy Formula
    Calculates the Pivot Confidence Score (C_pivot) deterministically.
    """
    
    # We use a Sensitivity Multiplier to make critical market shifts pop
    raw_score = (
        (delta_p * w1 * 1.5) + 
        (s_rev * w2 * 2.0) + 
        (v_soc * w3) + 
        (m_macro * w4) + 
        (r_risk * w5)
    )
    
    # Clamp the final score between 0.0 and 1.0
    c_pivot = max(0.0, min(1.0, raw_score))
    
    return round(c_pivot, 3)
    
def evaluate_execution_threshold(c_pivot_score: float) -> str:
    """
    Determines the routing logic based on the C_pivot score.
    """
    if c_pivot_score >= 0.1:
        return "AUTONOMOUS_EXECUTION"
    elif c_pivot_score >= 0.05:
        return "HUMAN_IN_THE_LOOP"
    else:
        return "MONITOR_ONLY"