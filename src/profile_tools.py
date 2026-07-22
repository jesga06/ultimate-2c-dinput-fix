import os
import json

def validate_hid_map(hid_map_path: str) -> str:
    """Validates a HID map file ({VID}_{PID}.json) for structural correctness."""
    if not os.path.exists(hid_map_path):
        return f"Error: HID map {hid_map_path} not found."
        
    try:
        with open(hid_map_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return f"Error: Invalid JSON.\n{e}"

        
    output = []
    output.append(f"Validating HID map: {data.get('name', 'Unknown')} ({hid_map_path})")
    
    reports = data.get('reports', {})
    if not reports:
        output.append("WARNING: No reports found in HID map.")
        
    mapped_bytes = {} # (report_id, byte) -> list of (input_name, mask)
    errors = 0
    warnings = 0
    
    for rep_id, rep_data in reports.items():
        inputs = rep_data.get('inputs', {})
        for in_name, cfg in inputs.items():
            b = cfg.get('byte')
            if b is None or b < 0:
                output.append(f"ERROR: '{in_name}' missing or invalid 'byte' field.")
                errors += 1
                continue
                
            length = cfg.get('length', 1)
            if length <= 0 or length > 8:
                output.append(f"ERROR: '{in_name}' has invalid length {length}.")
                errors += 1
                
            t = cfg.get('type')
            if t not in ['button', 'axis', 'trigger', 'hat']:
                output.append(f"WARNING: '{in_name}' has unknown type '{t}'.")
                warnings += 1
            
            for offset in range(length):
                b_offset = b + offset
                key = (rep_id, b_offset)
                if key not in mapped_bytes:
                    mapped_bytes[key] = []
                
                mask = cfg.get('bitmask', 0xFF)
                mapped_bytes[key].append((in_name, mask, t))
                
    for key, mappings in mapped_bytes.items():
        if len(mappings) > 1:
            # Check for overlaps
            # Multiple buttons can share a byte if masks don't overlap
            button_masks = 0
            for name, mask, t in mappings:
                if t != 'button':
                    output.append(f"WARNING: Byte {key[1]} at report {key[0]} is shared by non-button '{name}'.")
                    warnings += 1
                else:
                    if button_masks & mask:
                        output.append(f"ERROR: Mask overlap at byte {key[1]} between '{name}' and other buttons.")
                        errors += 1
                    button_masks |= mask
                    
    output.append(f"\nValidation Complete: {errors} Errors, {warnings} Warnings.")
    return "\n".join(output)

def diff_hid_maps(path1: str, path2: str) -> str:
    """Compares two HID maps and reports structural differences."""
    if not os.path.exists(path1) or not os.path.exists(path2):
        return "Error: One or both HID maps not found."
        
    try:
        with open(path1, 'r', encoding='utf-8') as f1, open(path2, 'r', encoding='utf-8') as f2:
            d1 = json.load(f1)
            d2 = json.load(f2)
    except Exception as e:
        return f"Error parsing JSON: {e}"
        
    output = []
    output.append(f"--- Diff: {d1.get('name', path1)} vs {d2.get('name', path2)} ---")
    
    r1 = d1.get('reports', {})
    r2 = d2.get('reports', {})
    
    all_reports = set(r1.keys()) | set(r2.keys())
    
    for rid in sorted(all_reports):
        if rid not in r1:
            output.append(f"Report {rid} only in HID map 2")
            continue
        if rid not in r2:
            output.append(f"Report {rid} only in HID map 1")
            continue
            
        in1 = r1[rid].get('inputs', {})
        in2 = r2[rid].get('inputs', {})
        
        all_inputs = set(in1.keys()) | set(in2.keys())
        for in_name in sorted(all_inputs):
            if in_name not in in1:
                output.append(f"[{rid}] '{in_name}' ADDED in HID map 2")
            elif in_name not in in2:
                output.append(f"[{rid}] '{in_name}' REMOVED in HID map 2")
            else:
                cfg1 = in1[in_name]
                cfg2 = in2[in_name]
                if cfg1 != cfg2:
                    diffs = []
                    for k in set(cfg1.keys()) | set(cfg2.keys()):
                        v1 = cfg1.get(k)
                        v2 = cfg2.get(k)
                        if v1 != v2:
                            diffs.append(f"{k}: {v1} -> {v2}")
                    if diffs:
                        output.append(f"[{rid}] '{in_name}' CHANGED: " + ", ".join(diffs))
                        
    if len(output) == 1:
        output.append("No differences found.")
        
    return "\n".join(output)
