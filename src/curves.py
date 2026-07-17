import math
import urllib.parse

def evaluate_curve(x: float, curve_type: str, power: float, custom_eq: str = "") -> float:
    """
    Evaluates a normalized input x [0.0, 1.0] using various advanced curves.
    """
    curve = curve_type.lower()
    
    if curve == 'linear':
        return x
    elif curve == 'custom':
        if not custom_eq:
            return x
        try:
            safe_dict = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            safe_dict['x'] = x
            safe_dict['power'] = power
            safe_dict['p'] = power
            return float(eval(custom_eq, {"__builtins__": None}, safe_dict))
        except Exception:
            return x
    elif curve in ['exponential', 'relaxed']:
        return x ** power
    elif curve == 'aggressive':
        return 1.0 - (1.0 - x) ** power
    elif curve == 'cubic':
        # Standard cubic curve centered on origin (since we only deal with positive magnitude [0,1], this is just x^3)
        return x ** 3
    elif curve == 'sigmoid':
        # Sigmoid function centered around 0.5. Power controls steepness.
        k = power * 5.0  # scale power to steepness
        x0 = 0.5
        # compute raw sigmoid
        s_raw = 1.0 / (1.0 + math.exp(-k * (x - x0)))
        # normalize to ensure f(0) = 0 and f(1) = 1
        s_min = 1.0 / (1.0 + math.exp(-k * (0 - x0)))
        s_max = 1.0 / (1.0 + math.exp(-k * (1 - x0)))
        return (s_raw - s_min) / (s_max - s_min)
    elif curve == 'bezier':
        # Simplified 1D cubic bezier approximation (ease-in-out)
        # using the power to bias the control points
        p1 = 1.0 - (1.0 / power) if power >= 1.0 else power
        p2 = 1.0 / power if power >= 1.0 else 1.0 - power
        # bezier formula: B(t) = 3(1-t)^2*t*p1 + 3(1-t)*t^2*p2 + t^3
        return 3 * ((1 - x) ** 2) * x * p1 + 3 * (1 - x) * (x ** 2) * p2 + (x ** 3)
    elif curve == 'dotted':
        import json
        try:
            dots = json.loads(custom_eq)
            dots.sort(key=lambda d: d[0])
            
            if not dots:
                return x
            if x <= dots[0][0]:
                return float(dots[0][1])
            if x >= dots[-1][0]:
                return float(dots[-1][1])
                
            for i in range(len(dots) - 1):
                p1, p2 = dots[i], dots[i+1]
                if p1[0] <= x <= p2[0]:
                    t = (x - p1[0]) / (p2[0] - p1[0])
                    return float(p1[1] + t * (p2[1] - p1[1]))
            return x
        except Exception:
            return x
    else:
        return x

def export_to_desmos(curve_type: str, power: float, inner_dz: float, anti_dz: float, rest_dz: float) -> str:
    """
    Generates a Desmos calculator URL displaying the response curve.
    """
    formulas = []
    # Base curve function f(x)
    c = curve_type.lower()
    if c == 'linear':
        formulas.append(f"f(x)=x")
    elif c in ['exponential', 'relaxed']:
        formulas.append(f"f(x)=x^{{{power}}}")
    elif c == 'aggressive':
        formulas.append(f"f(x)=1-(1-x)^{{{power}}}")
    elif c == 'cubic':
        formulas.append(f"f(x)=x^3")
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
        formulas.append(f"f(x)=x")
        
    # Full equation with deadzones
    full_eq = f"y={anti_dz}+f(\\frac{{x-{inner_dz}}}{{1-{inner_dz}}})*(1-{anti_dz}) \\left\\{{ {inner_dz} \\le x \\le 1 \\right\\}}"
    formulas.append(full_eq)
    
    # We could theoretically URL encode the LaTeX and pass it to Desmos API,
    # but Desmos doesn't easily accept equations via URL without their API.
    # We will simulate a share link format or just output the LaTeX strings.
    # Since we can't reliably generate a desmos.com URL without API keys, we just provide the LaTeX.
    
    return formulas

def export_to_latex(curve_type: str, power: float, inner_dz: float, anti_dz: float, rest_dz: float) -> str:
    """
    Generates LaTeX representation of the curve mapping.
    """
    formulas = export_to_desmos(curve_type, power, inner_dz, anti_dz, rest_dz)
    return "\\n".join(formulas)
