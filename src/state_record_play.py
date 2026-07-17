import time
import json
import os

class StateRecorder:
    def __init__(self, filename="recording.json"):
        self.filename = filename
        self.is_recording = False
        self.start_time = 0.0
        self.events = []
        
    def start(self):
        self.is_recording = True
        self.start_time = time.perf_counter()
        self.events = []
        
    def stop(self):
        self.is_recording = False
        self.save()
        
    def record_event(self, state_dict: dict):
        if not self.is_recording:
            return
            
        now = time.perf_counter()
        elapsed = now - self.start_time
        
        # Save a snapshot of the parsed controller state along with timestamp
        self.events.append({
            "timestamp": elapsed,
            "state": state_dict
        })
        
    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({"events": self.events}, f, indent=4)
        except Exception as e:
            print(f"Failed to save recording: {e}")

class StatePlayer:
    def __init__(self, filename="recording.json"):
        self.filename = filename
        self.is_playing = False
        self.events = []
        self.current_idx = 0
        self.start_time = 0.0
        
    def load(self):
        if not os.path.exists(self.filename):
            return False
            
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.events = data.get("events", [])
            return True
        except:
            return False
            
    def start(self):
        if not self.events:
            if not self.load():
                return False
                
        if not self.events:
            return False
            
        self.is_playing = True
        self.current_idx = 0
        self.start_time = time.perf_counter()
        return True
        
    def stop(self):
        self.is_playing = False
        
    def get_current_state(self):
        """
        Returns the interpolated state based on elapsed playback time.
        If playback is finished, returns None.
        """
        if not self.is_playing:
            return None
            
        now = time.perf_counter()
        elapsed = now - self.start_time
        
        while self.current_idx < len(self.events) and self.events[self.current_idx]["timestamp"] <= elapsed:
            self.current_idx += 1
            
        if self.current_idx >= len(self.events):
            self.stop()
            return None
            
        # Return the most recent state
        if self.current_idx == 0:
            return self.events[0]["state"]
            
        return self.events[self.current_idx - 1]["state"]
