import math

def process_analog_stick(x: float, y: float, inner_dz: float, anti_dz: float, curve_type: str, power: float, rest_dz: float = 0.0):
    """
    Processes an analog stick's X and Y coordinates.
    Applies a radial inner deadzone.
    Applies a rest deadzone (secondary buffer to prevent anti-deadzone from activating on drift).
    Applies a mathematical response curve to the *magnitude* to preserve circular diagonals.
    Applies an anti-deadzone offset to the magnitude.
    Returns the new (x, y).
    """
    magnitude = math.sqrt(x**2 + y**2)
    
    if magnitude < inner_dz:
        return 0.0, 0.0
        
    # Cap magnitude at 1.0 (outer deadzone essentially 1.0)
    magnitude = min(magnitude, 1.0)
    
    # Normalize magnitude between inner_dz and 1.0 to [0.0, 1.0]
    norm_mag = (magnitude - inner_dz) / (1.0 - inner_dz) if inner_dz < 1.0 else 0.0
    
    # Rest deadzone: if the normalized magnitude is below this threshold,
    # treat it as zero to prevent drift from activating the anti-deadzone.
    if norm_mag < rest_dz:
        return 0.0, 0.0
    # Remap [rest_dz, 1.0] to [0.0, 1.0]
    if rest_dz < 1.0:
        norm_mag = (norm_mag - rest_dz) / (1.0 - rest_dz)
    else:
        norm_mag = 0.0
    
    # Apply curve to normalized magnitude
    if curve_type.lower() == 'exponential' or curve_type.lower() == 'relaxed':
        norm_mag = norm_mag ** power
    elif curve_type.lower() == 'aggressive':
        norm_mag = 1.0 - (1.0 - norm_mag) ** power
        
    # Apply anti-deadzone
    final_mag = anti_dz + norm_mag * (1.0 - anti_dz)
    final_mag = max(0.0, min(1.0, final_mag))
    
    # Reconstruct X and Y
    if magnitude > 0.0:
        ratio = final_mag / magnitude
        return x * ratio, y * ratio
    return 0.0, 0.0

def process_trigger(val: float, inner_dz: float, anti_dz: float, curve_type: str, power: float, rest_dz: float = 0.0):
    """
    Processes an analog trigger's 1D value [0.0, 1.0].
    Applies an inner deadzone.
    Applies a rest deadzone (secondary buffer to prevent anti-deadzone from activating on drift).
    Applies a mathematical response curve.
    Applies an anti-deadzone offset.
    Returns the new value [0.0, 1.0].
    """
    if val < inner_dz:
        return 0.0
        
    val = min(val, 1.0)
    
    # Normalize value between inner_dz and 1.0 to [0.0, 1.0]
    norm_val = (val - inner_dz) / (1.0 - inner_dz) if inner_dz < 1.0 else 0.0
    
    # Rest deadzone: if normalized value is below this, treat as zero
    if norm_val < rest_dz:
        return 0.0
    if rest_dz < 1.0:
        norm_val = (norm_val - rest_dz) / (1.0 - rest_dz)
    else:
        norm_val = 0.0
    
    # Apply curve
    if curve_type.lower() == 'exponential' or curve_type.lower() == 'relaxed':
        norm_val = norm_val ** power
    elif curve_type.lower() == 'aggressive':
        norm_val = 1.0 - (1.0 - norm_val) ** power
        
    # Apply anti-deadzone
    final_val = anti_dz + norm_val * (1.0 - anti_dz)
    return max(0.0, min(1.0, final_val))
