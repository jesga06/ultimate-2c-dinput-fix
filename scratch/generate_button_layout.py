import json
import os

def generate_layout():
    # Relative positions (0.0 to 1.0) on a standard Xbox-style layout canvas
    # The canvas will map these to real X/Y coordinates based on its current width/height
    layout = {
        "dpad_up": {"x": 0.35, "y": 0.65},
        "dpad_down": {"x": 0.35, "y": 0.85},
        "dpad_left": {"x": 0.25, "y": 0.75},
        "dpad_right": {"x": 0.45, "y": 0.75},
        
        "a": {"x": 0.72, "y": 0.75},
        "b": {"x": 0.82, "y": 0.65},
        "x": {"x": 0.62, "y": 0.65},
        "y": {"x": 0.72, "y": 0.55},
        
        "lb": {"x": 0.25, "y": 0.35},
        "rb": {"x": 0.75, "y": 0.35},
        
        "lt": {"x": 0.25, "y": 0.10},
        "rt": {"x": 0.75, "y": 0.10},
        
        "l3": {"x": 0.28, "y": 0.45},
        "r3": {"x": 0.62, "y": 0.85},
        
        "select": {"x": 0.43, "y": 0.45},
        "start": {"x": 0.57, "y": 0.45},
        "home": {"x": 0.50, "y": 0.55}
    }
    
    # Standard PS layout fallback (swaps D-Pad and Left Stick)
    ps_layout = layout.copy()
    ps_layout["dpad_up"] = {"x": 0.28, "y": 0.35}
    ps_layout["dpad_down"] = {"x": 0.28, "y": 0.55}
    ps_layout["dpad_left"] = {"x": 0.18, "y": 0.45}
    ps_layout["dpad_right"] = {"x": 0.38, "y": 0.45}
    ps_layout["l3"] = {"x": 0.35, "y": 0.75}
    
    output = {
        "xbox": layout,
        "playstation": ps_layout
    }
    
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "resources"), exist_ok=True)
    out_path = os.path.join(os.path.dirname(__file__), "..", "resources", "button_layout.json")
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=4)
        
    print(f"Generated {out_path}")

if __name__ == "__main__":
    generate_layout()
