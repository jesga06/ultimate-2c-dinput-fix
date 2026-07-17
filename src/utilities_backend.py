import time
import collections

class LatencyMonitor:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.poll_intervals = collections.deque(maxlen=window_size)
        self.process_latencies = collections.deque(maxlen=window_size)
        
        self.last_poll_time = 0.0
        
        # UDP Setup for live input graph
        import socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def record_poll(self):
        now = time.perf_counter()
        if self.last_poll_time > 0:
            self.poll_intervals.append(now - self.last_poll_time)
        self.last_poll_time = now
        return now
        
    def record_process(self, start_time):
        now = time.perf_counter()
        self.process_latencies.append(now - start_time)
        
    def broadcast_state(self, state):
        import json
        try:
            # Broadcast on loopback port 9999
            msg = json.dumps({"lx": state.lx, "ly": state.ly, "rx": state.rx, "ry": state.ry, "lt": state.lt, "rt": state.rt}).encode('utf-8')
            self.sock.sendto(msg, ("127.0.0.1", 9999))
        except Exception:
            pass
        
    def get_stats(self):
        if not self.poll_intervals or not self.process_latencies:
            return {
                "polling_rate_hz": 0.0,
                "avg_process_ms": 0.0,
                "max_process_ms": 0.0
            }
            
        avg_poll = sum(self.poll_intervals) / len(self.poll_intervals)
        hz = 1.0 / avg_poll if avg_poll > 0 else 0.0
        
        avg_lat = sum(self.process_latencies) / len(self.process_latencies)
        max_lat = max(self.process_latencies)
        
        return {
            "polling_rate_hz": round(hz, 1),
            "avg_process_ms": round(avg_lat * 1000.0, 3),
            "max_process_ms": round(max_lat * 1000.0, 3)
        }
        
    def start_logging(self):
        import threading
        import json
        import os
        import time
        
        def _loop():
            while True:
                time.sleep(0.5)
                stats = self.get_stats()
                try:
                    with open('diagnostics.json', 'w') as f:
                        json.dump(stats, f)
                except Exception:
                    pass
                    
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

monitor = LatencyMonitor()
monitor.start_logging()
