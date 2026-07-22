import math
from typing import List, Tuple
import curves

def process_analog_stick(
    x: float,
    y: float,
    inner_dz: float,
    anti_dz: float,
    curve_type: str,
    power: float,
    rest_dz: float = 0.0,
    sensitivity: float = 1.0,
    custom_eq: str = ""
) -> Tuple[float, float]:
    """
    Processes an analog stick's X and Y coordinates.
    Applies a radial inner deadzone.
    Applies a rest deadzone (secondary buffer to prevent anti-deadzone from activating on drift).
    Applies a mathematical response curve to the magnitude to preserve circular diagonals.
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
    
    # Apply response curve to normalized magnitude
    norm_mag = curves.evaluate_curve(norm_mag, curve_type, power, custom_eq)
        
    # Apply anti-deadzone
    final_mag = anti_dz + norm_mag * (1.0 - anti_dz)
    final_mag = max(0.0, min(1.0, final_mag))
    
    # Reconstruct X and Y
    if magnitude > 0.0:
        ratio = final_mag / magnitude
        return x * ratio * sensitivity, y * ratio * sensitivity
    return 0.0, 0.0

def process_trigger(
    val: float,
    inner_dz: float,
    anti_dz: float,
    curve_type: str,
    power: float,
    rest_dz: float = 0.0,
    sensitivity: float = 1.0,
    custom_eq: str = ""
) -> float:
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
    norm_val = curves.evaluate_curve(norm_val, curve_type, power, custom_eq)
        
    # Apply anti-deadzone
    final_val = anti_dz + norm_val * (1.0 - anti_dz)
    final_val *= sensitivity
    return max(0.0, min(1.0, final_val))

def apply_circularity_correction(
    x: float,
    y: float,
    center_x: float,
    center_y: float,
    bounds_data: List[float]
) -> Tuple[float, float]:
    """
    Applies circularity correction to an analog stick.
    bounds_data: list of 360 floats representing max radius at each degree (0-359).
    Uses sub-degree linear interpolation between adjacent degree bounds.
    """
    if not bounds_data or len(bounds_data) != 360:
        return x, y
        
    dx = x - center_x
    dy = y - center_y
    r = math.sqrt(dx**2 + dy**2)
    
    if r == 0.0:
        return 0.0, 0.0
        
    deg_float = math.degrees(math.atan2(dy, dx)) % 360.0
    idx_lower = int(deg_float)
    idx_upper = (idx_lower + 1) % 360
    frac = deg_float - idx_lower

    r_max = (1.0 - frac) * bounds_data[idx_lower] + frac * bounds_data[idx_upper]
    
    if r_max <= 0.0:
        return x, y
        
    # Scale by (R_max * 0.98) to ensure we overshoot slightly (guarantee hitting 1.0)
    adjusted_r_max = r_max * 0.98
    
    new_r = min(r / adjusted_r_max, 1.0)
    
    new_x = new_r * (dx / r)
    new_y = new_r * (dy / r)
    
    return new_x, new_y

def calculate_circularity_error(bounds_data: List[float]) -> float:
    """
    Calculates the average percentage deviation from a perfect unit circle (radius 1.0).
    """
    if not bounds_data:
        return 0.0
        
    total_deviation = sum(abs(r - 1.0) for r in bounds_data)
    return (total_deviation / len(bounds_data)) * 100.0

def _scale_warped_axis(val: float, o_max: float) -> float:
    """Module-level helper to scale axis values against warped threshold maximums."""
    if val == 0.0:
        return 0.0
    sign = 1.0 if val >= 0.0 else -1.0
    scaled = abs(val) / o_max
    return sign * min(scaled, 1.0)

def apply_warped_stick_correction(x: float, y: float, threshold_pct: float) -> Tuple[float, float]:
    """
    Checks stick axis coordinates against a user-configurable threshold (e.g., 5-10% deviation).
    Dynamically scales outputs on weak/asymmetric directions to hit 1.0 without hard-clipping.
    """
    if threshold_pct <= 0.0:
        return x, y
        
    threshold_val = threshold_pct / 100.0
    outer_max = 1.0 - threshold_val
    
    if outer_max <= 0.0:
        return x, y
        
    return _scale_warped_axis(x, outer_max), _scale_warped_axis(y, outer_max)

def clamp_int(val: int, min_val: int, max_val: int) -> int:
    """Clamps an integer value to the range [min_val, max_val]."""
    return max(min_val, min(max_val, val))


