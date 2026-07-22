import customtkinter as ctk
import json
import os

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "resources", "button_layout.json")

class DraggableButton(ctk.CTkButton):
    def __init__(self, builder, master, btn_name, relx, rely, update_callback, **kwargs):
        if 'text' not in kwargs:
            kwargs['text'] = btn_name.upper()
        super().__init__(master, **kwargs)
        self.builder = builder
        self.btn_name = btn_name
        self.update_callback = update_callback
        self.relx = relx
        self.rely = rely
        self.place(relx=relx, rely=rely, anchor="center")
        self.bind("<B1-Motion>", self.on_drag)

    def on_drag(self, event):
        x = self.master.winfo_pointerx() - self.master.winfo_rootx()
        y = self.master.winfo_pointery() - self.master.winfo_rooty()
        
        w = self.master.winfo_width()
        h = self.master.winfo_height()
        
        if w <= 1 or h <= 1:
            return
            
        grid_sz = self.builder.grid_size
        
        # Snap pixel coordinates to nearest grid interval
        snapped_x = round(x / grid_sz) * grid_sz
        snapped_y = round(y / grid_sz) * grid_sz
        
        snapped_x = max(0, min(w, snapped_x))
        snapped_y = max(0, min(h, snapped_y))
        
        self.relx = snapped_x / w
        self.rely = snapped_y / h
        
        self.place(relx=self.relx, rely=self.rely, anchor="center")
        self.update_callback(self.btn_name, self.relx, self.rely)

    def snap_to_grid(self):
        w = self.master.winfo_width()
        h = self.master.winfo_height()
        if w <= 1 or h <= 1:
            return
            
        grid_sz = self.builder.grid_size
        
        pixel_x = self.relx * w
        pixel_y = self.rely * h
        
        snapped_x = round(pixel_x / grid_sz) * grid_sz
        snapped_y = round(pixel_y / grid_sz) * grid_sz
        
        snapped_x = max(0, min(w, snapped_x))
        snapped_y = max(0, min(h, snapped_y))
        
        self.relx = snapped_x / w
        self.rely = snapped_y / h
        
        self.place(relx=self.relx, rely=self.rely, anchor="center")
        self.update_callback(self.btn_name, self.relx, self.rely)

class LayoutBuilder(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Interactive Layout Builder")
        self.geometry("900x650")
        
        self.layout_data = {}
        if os.path.exists(OUT_PATH):
            with open(OUT_PATH, 'r', encoding='utf-8') as f:
                self.layout_data = json.load(f)
        else:
            print(f"File not found: {OUT_PATH}. Please ensure resources/button_layout.json exists.")
            self.layout_data = {"xbox": {}, "playstation": {}}
            
        self.current_layout = "xbox"
        self.grid_size = 10
        
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(top_frame, text="Xbox Layout", command=lambda: self.switch_layout("xbox")).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="PlayStation Layout", command=lambda: self.switch_layout("playstation")).pack(side="left", padx=5)
        
        # Grid slider controls
        grid_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        grid_frame.pack(side="left", padx=15)
        
        self.grid_label = ctk.CTkLabel(grid_frame, text="Grid: 10px")
        self.grid_label.pack(side="left", padx=5)
        
        self.grid_slider = ctk.CTkSlider(grid_frame, from_=5, to=20, number_of_steps=15, command=self.on_grid_slider_change, width=150)
        self.grid_slider.set(10)
        self.grid_slider.pack(side="left", padx=5)
        
        ctk.CTkButton(top_frame, text="Save Layout", command=self.save_layout, fg_color="green").pack(side="right", padx=5)
        
        # Background Canvas for Grid lines underneath buttons
        self.canvas = ctk.CTkCanvas(self, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=20)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        self.buttons = []
        self.switch_layout("xbox")
        
    def on_grid_slider_change(self, val):
        self.grid_size = int(round(val))
        self.grid_label.configure(text=f"Grid: {self.grid_size}px")
        self.draw_grid()
        self.snap_all_buttons()

    def draw_grid(self):
        self.canvas.delete("grid_line")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            return
            
        grid_sz = self.grid_size
        grid_color = "#2a2a2a"
        
        for x in range(0, w, grid_sz):
            self.canvas.create_line(x, 0, x, h, fill=grid_color, tags="grid_line")
        for y in range(0, h, grid_sz):
            self.canvas.create_line(0, y, w, y, fill=grid_color, tags="grid_line")
            
        self.canvas.tag_lower("grid_line")

    def on_canvas_configure(self, event):
        self.draw_grid()
        self.snap_all_buttons()

    def snap_all_buttons(self):
        for b in self.buttons:
            b.snap_to_grid()

    def switch_layout(self, layout_name):
        self.current_layout = layout_name
        for b in self.buttons:
            b.destroy()
        self.buttons.clear()
        
        layout = self.layout_data.get(layout_name, {})
        for btn, pos in layout.items():
            btn_text = btn.upper()
            if btn.startswith("dpad_"):
                btn_text = btn.split("_")[1].upper()
                
            b = DraggableButton(self, self.canvas, btn, pos["x"], pos["y"], self.update_pos, width=60, height=40, text=btn_text)
            self.buttons.append(b)
            
        self.after(50, self.snap_all_buttons)
            
    def update_pos(self, btn, x, y):
        self.layout_data[self.current_layout][btn] = {"x": round(x, 3), "y": round(y, 3)}
        
    def save_layout(self):
        with open(OUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.layout_data, f, indent=4)
        print(f"Saved layout to {OUT_PATH}")


if __name__ == "__main__":
    app = LayoutBuilder()
    app.mainloop()
