from dataclasses import dataclass

@dataclass
class ControllerState:
    a: bool = False
    b: bool = False
    x: bool = False
    y: bool = False
    lb: bool = False
    rb: bool = False
    l4: bool = False
    r4: bool = False
    
    select: bool = False
    start: bool = False
    home: bool = False
    l3: bool = False
    r3: bool = False
    
    # D-pad directions
    dpad_up: bool = False
    dpad_down: bool = False
    dpad_left: bool = False
    dpad_right: bool = False
    
    # Sticks (0-255)
    lx: int = 128
    ly: int = 128
    rx: int = 128
    ry: int = 128
    
    # Triggers (0-255)
    lt: int = 0
    rt: int = 0

class Decoder:
    @staticmethod
    def decode(data) -> ControllerState:
        state = ControllerState()
        
        # Ensure we have enough data
        if len(data) < 10:
            return state
            
        b2 = data[1]
        state.a = bool(b2 & (1 << 0))
        state.b = bool(b2 & (1 << 1))
        state.l4 = bool(b2 & (1 << 2))
        state.x = bool(b2 & (1 << 3))
        state.y = bool(b2 & (1 << 4))
        state.r4 = bool(b2 & (1 << 5))
        state.lb = bool(b2 & (1 << 6))
        state.rb = bool(b2 & (1 << 7))
        
        b3 = data[2]
        state.select = bool(b3 & (1 << 2))
        state.start = bool(b3 & (1 << 3))
        state.home = bool(b3 & (1 << 4))
        state.l3 = bool(b3 & (1 << 5))
        state.r3 = bool(b3 & (1 << 6))
        
        b4 = data[3]
        hat = b4 & 0x0F
        
        # Hat switch values:
        # 0: Up, 1: Up-Right, 2: Right, 3: Down-Right
        # 4: Down, 5: Down-Left, 6: Left, 7: Up-Left, 15: Center
        state.dpad_up = hat in (7, 0, 1)
        state.dpad_right = hat in (1, 2, 3)
        state.dpad_down = hat in (3, 4, 5)
        state.dpad_left = hat in (5, 6, 7)
        
        # Based on initial findings, stick centers might be slightly off.
        # But we'll pass them raw and map them in the virtual pad.
        state.rx = data[4]
        state.ry = data[5]
        state.lx = data[6]
        state.ly = data[7]
        
        state.rt = data[8]
        state.lt = data[9]
        
        return state
