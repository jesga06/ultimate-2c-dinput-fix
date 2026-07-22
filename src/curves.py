import math
import json
import urllib.parse
from typing import List

# Pre-cached safe math dictionary for custom curve evaluations
_SAFE_MATH_DICT = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}

def evaluate_curve(x: float, curve_type: str, power: float, custom_eq: str = "") -> float:
    """
    Evaluates a normalized input x [0.0, 1.0] using various response curves.
    """
    curve = curve_type.lower()
    
    if curve == 'linear':
        return x
    elif curve == 'custom':
        if not custom_eq:
            return x
        try:
            eval_dict = _SAFE_MATH_DICT.copy()
            eval_dict['x'] = x
            eval_dict['power'] = power
            eval_dict['p'] = power
            return float(eval(custom_eq, {"__builtins__": None}, eval_dict))
        except Exception:
            return x
    elif curve in ['exponential', 'relaxed']:
        return x ** power
    elif curve == 'aggressive':
        return 1.0 - (1.0 - x) ** power
    elif curve == 'cubic':
        return x ** 3
    elif curve == 'sigmoid':
        # Sigmoid function centered around 0.5. Power controls steepness.
        k = power * 5.0
        x0 = 0.5
        s_raw = 1.0 / (1.0 + math.exp(-k * (x - x0)))
        s_min = 1.0 / (1.0 + math.exp(k * x0))
        s_max = 1.0 / (1.0 + math.exp(-k * (1.0 - x0)))
        denom = s_max - s_min
        if denom == 0.0:
            return x
        return (s_raw - s_min) / denom
    elif curve == 'bezier':
        # Simplified 1D cubic bezier approximation (ease-in-out)
        p1 = 1.0 - (1.0 / power) if power >= 1.0 else power
        p2 = 1.0 / power if power >= 1.0 else 1.0 - power
        return 3 * ((1 - x) ** 2) * x * p1 + 3 * (1 - x) * (x ** 2) * p2 + (x ** 3)
    elif curve == 'dotted':
        try:
            dots = json.loads(custom_eq)
            if not isinstance(dots, list) or not dots:
                return x
            dots.sort(key=lambda d: d[0])
            
            if x <= dots[0][0]:
                return float(dots[0][1])
            if x >= dots[-1][0]:
                return float(dots[-1][1])
                
            for i in range(len(dots) - 1):
                p1, p2 = dots[i], dots[i+1]
                if p1[0] <= x <= p2[0]:
                    dx = p2[0] - p1[0]
                    if dx == 0.0:
                        return float(p1[1])
                    t = (x - p1[0]) / dx
                    return float(p1[1] + t * (p2[1] - p1[1]))
            return x
        except Exception:
            return x
    else:
        return x

def export_to_desmos(curve_type: str, power: float, inner_dz: float, anti_dz: float, rest_dz: float) -> List[str]:
    """
    Generates LaTeX formula strings for visualization in Desmos.
    """
    formulas: List[str] = []
    c = curve_type.lower()
    if c == 'linear':
        formulas.append("f(x)=x")
    elif c in ['exponential', 'relaxed']:
        formulas.append(f"f(x)=x^{{{power}}}")
    elif c == 'aggressive':
        formulas.append(f"f(x)=1-(1-x)^{{{power}}}")
    elif c == 'cubic':
        formulas.append("f(x)=x^3")
    elif c == 'sigmoid':
        k = power * 5.0
        s_min = f"(1/(1+\\exp(-{k}*(0-0.5))))"
        s_max = f"(1/(1+\\exp(-{k}*(1-0.5))))"
        s_raw = f"(1/(1+\\exp(-{k}*(x-0.5))))"
        formulas.append(f"f(x)=({s_raw}-{s_min})/({s_max}-{s_min})")
    elif c == 'bezier':
        p1 = 1.0 - (1.0 / power) if power >= 1.0 else power
        p2 = 1.0 / power if power >= 1.0 else 1.0 - power
        formulas.append(f"f(x)=3(1-x)^2*x*{p1}+3(1-x)*x^2*{p2}+x^3")
    else:
        formulas.append("f(x)=x")
        
    # Full equation with deadzones
    full_eq = f"y={anti_dz}+f(\\frac{{x-{inner_dz}}}{{1-{inner_dz}}})*(1-{anti_dz}) \\left\\{{ {inner_dz} \\le x \\le 1 \\right\\}}"
    formulas.append(full_eq)
    
    return formulas

def export_to_latex(curve_type: str, power: float, inner_dz: float, anti_dz: float, rest_dz: float) -> str:
    """
    Generates LaTeX representation of the curve mapping.
    """
    formulas = export_to_desmos(curve_type, power, inner_dz, anti_dz, rest_dz)
    return "\n".join(formulas)

