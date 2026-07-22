import math
import customtkinter as ctk

class CircularityCalibrationModal(ctk.CTkToplevel):
    def __init__(self, parent, title, section, on_finish=None):
        super().__init__(parent)
        self.parent = parent
        self.section = section
        self.is_left = ("left" in section.lower())
        self.on_finish = on_finish
        
        self.title(f"{title} - Circularity Calibration")
        self.geometry("500x550")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.focus()
        
        self.calib_state = "REST"
        self.center_x = 0.0
        self.center_y = 0.0
        self.center_samples_x = []
        self.center_samples_y = []
        self.bounds_data = [0.0] * 360
        self.timer = 0
        self.last_theta = None
        self.accum_cw = 0.0
        self.accum_ccw = 0.0
        self.speed_warn_timer = 0
        
        lbl_title = ctk.CTkLabel(self, text=f"Calibrating {title}", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_title.pack(pady=10)
        
        self.lbl_instruct = ctk.CTkLabel(self, text="Step 1: Leave the stick at rest without touching it.\nSampling center offset...", font=ctk.CTkFont(size=14))
        self.lbl_instruct.pack(pady=5)
        
        self.lbl_warning = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color="red")
        self.lbl_warning.pack()
        
        self.canvas = ctk.CTkCanvas(self, width=300, height=300, bg="#222222", highlightthickness=0)
        self.canvas.pack(pady=10)
        
        self.btn_action = ctk.CTkButton(self, text="Wait...", state="disabled")
        self.btn_action.pack(pady=10)
        
        self.lbl_result = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.lbl_result.pack()
        
        self.draw_grid()
        self.update_loop()
        
    def draw_grid(self):
        w, h = 300, 300
        cx, cy = w/2, h/2
        self.canvas.create_line(cx, 0, cx, h, fill="#444444", dash=(2, 2))
        self.canvas.create_line(0, cy, w, cy, fill="#444444", dash=(2, 2))
        self.canvas.create_oval(10, 10, w-10, h-10, outline="#555555", width=2, dash=(2, 2))
        
    def get_raw_input(self):
        state = getattr(self.parent, 'current_state', None)
        if not state:
            return 0.0, 0.0
        
        if self.is_left:
            return state.lx, -state.ly
        else:
            return state.rx, -state.ry
            
    def update_loop(self):
        if not self.winfo_exists():
            return
            
        raw_x, raw_y = self.get_raw_input()
        
        if self.calib_state == "REST":
            self.center_samples_x.append(raw_x)
            self.center_samples_y.append(raw_y)
            self.timer += 1
            if self.timer > 60: # approx 1 second
                self.center_x = sum(self.center_samples_x) / len(self.center_samples_x)
                self.center_y = sum(self.center_samples_y) / len(self.center_samples_y)
                self.calib_state = "WAIT_SWEEP"
                self.lbl_instruct.configure(text="Step 2: Push the stick fully outward and slowly rotate it\n360 degrees 3 times clockwise, then 3 times counter-clockwise.")
                self.btn_action.configure(text="Start Sweep", state="normal", command=self.start_sweep)
                
        elif self.calib_state == "SWEEP":
            dx = raw_x - self.center_x
            dy = raw_y - self.center_y
            r = math.sqrt(dx**2 + dy**2)
            if r > 0.1: # Only record if actually pushed
                theta = int(math.degrees(math.atan2(dy, dx))) % 360
                
                if self.last_theta is not None:
                    delta = (theta - self.last_theta + 180) % 360 - 180
                    if delta > 0:
                        self.accum_ccw += delta
                    elif delta < 0:
                        self.accum_cw += abs(delta)
                        
                    if abs(delta) > 30:
                        self.speed_warn_timer = 60
                        self.lbl_warning.configure(text="Too Fast! Slow down.")
                        
                self.last_theta = theta
                
                # Smear slightly to nearby angles to fill gaps
                for i in range(-2, 3):
                    idx = (theta + i) % 360
                    if r > self.bounds_data[idx]:
                        self.bounds_data[idx] = r
                        
            if self.speed_warn_timer > 0:
                self.speed_warn_timer -= 1
                if self.speed_warn_timer == 0:
                    self.lbl_warning.configure(text="")
                    
            if self.accum_cw >= 3 * 360 and self.accum_ccw >= 3 * 360:
                if self.btn_action.cget("state") == "disabled":
                    self.btn_action.configure(text="Finish", state="normal", command=self.finish_sweep)
            else:
                if self.btn_action.cget("state") == "disabled":
                    cw_rem = max(0, 3 - int(self.accum_cw / 360))
                    ccw_rem = max(0, 3 - int(self.accum_ccw / 360))
                    self.btn_action.configure(text=f"Sweep {cw_rem}x CW, {ccw_rem}x CCW")
                        
            # Draw real-time
            self.canvas.delete("live")
            cx, cy = 150, 150
            scale = 140 # 1.0 -> 140px
            px = cx + (raw_x * scale)
            py = cy - (raw_y * scale)
            self.canvas.create_oval(px-4, py-4, px+4, py+4, fill="#00D4FF", outline="", tags="live")
            
            # Draw bounds poly
            self.draw_bounds()
            
        self.after(16, self.update_loop)
        
    def draw_bounds(self):
        self.canvas.delete("bounds")
        cx, cy = 150, 150
        scale = 140
        pts = []
        for a in range(360):
            r = self.bounds_data[a]
            if r > 0:
                rad = math.radians(a)
                x = cx + r * math.cos(rad) * scale
                y = cy - r * math.sin(rad) * scale
                pts.append(x)
                pts.append(y)
        if len(pts) > 4:
            self.canvas.create_polygon(pts, outline="#AF00FA", fill="", width=2, tags="bounds")
            
    def start_sweep(self):
        self.calib_state = "SWEEP"
        self.btn_action.configure(text="Sweep 3x CW, 3x CCW", state="disabled")
        
    def interpolate_bounds(self):
        # Fill any zeros by interpolating between nearest non-zeros
        non_zeros = [(i, r) for i, r in enumerate(self.bounds_data) if r > 0]
        if not non_zeros:
            return
            
        for i in range(360):
            if self.bounds_data[i] == 0:
                # Find left and right neighbors
                left_idx = i
                while self.bounds_data[left_idx] == 0:
                    left_idx = (left_idx - 1) % 360
                right_idx = i
                while self.bounds_data[right_idx] == 0:
                    right_idx = (right_idx + 1) % 360
                    
                left_r = self.bounds_data[left_idx]
                right_r = self.bounds_data[right_idx]
                
                # Distance
                dl = (i - left_idx) % 360
                dr = (right_idx - i) % 360
                total = dl + dr
                if total > 0:
                    self.bounds_data[i] = left_r * (dr/total) + right_r * (dl/total)
                    
    def finish_sweep(self):
        self.calib_state = "DONE"
        self.interpolate_bounds()
        self.draw_bounds()
        
        import math_utils
        error_pct = math_utils.calculate_circularity_error(self.bounds_data)
        
        self.lbl_instruct.configure(text="Calibration Complete!")
        self.lbl_result.configure(text=f"Average Circularity Error: {error_pct:.2f}%\nCenter Offset: ({self.center_x:.3f}, {self.center_y:.3f})")
        
        self.btn_action.pack_forget()
        
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)
        
        btn_apply = ctk.CTkButton(self.btn_frame, text="Apply Changes", command=self.save_and_close, fg_color="#1f538d")
        btn_apply.pack(side="left", padx=10)
        
        btn_discard = ctk.CTkButton(self.btn_frame, text="Discard", command=self.destroy, fg_color="#8d1f1f")
        btn_discard.pack(side="left", padx=10)
        
    def save_and_close(self):
        config = self.parent.config
        if not config.has_section(self.section):
            config.add_section(self.section)
            
        bounds_str = ",".join(f"{r:.4f}" for r in self.bounds_data)
        config.set(self.section, 'circularity_center_x', str(round(self.center_x, 4)))
        config.set(self.section, 'circularity_center_y', str(round(self.center_y, 4)))
        config.set(self.section, 'circularity_bounds', bounds_str)
        
        # If mode was disabled, auto-enable it to "before"
        current_mode = config.get(self.section, 'circularity_mode', fallback='disabled')
        if current_mode == 'disabled':
            config.set(self.section, 'circularity_mode', 'before')
            
        self.parent.save_config()
        if self.on_finish:
            self.on_finish()
        self.destroy()
