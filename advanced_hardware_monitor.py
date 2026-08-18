import csv
from datetime import datetime
import os
import sys
import threading
import time
import tkinter as tk
import webbrowser
import customtkinter as ctk

# Matplotlib embedded canvas backend
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# Data & Interactive Plotting for HTML Reports
try:
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Native Windows Toast Notifications
try:
    from windows_toasts import InteractableWindowsToaster, Toast
    TOASTER_AVAILABLE = True
except ImportError:
    TOASTER_AVAILABLE = False

# Initialize C# DLL Bridge
dll_name = "LibreHardwareMonitorLib.dll"
dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), dll_name)
if not os.path.exists(dll_path):
    print(f"Error: {dll_name} not found in script directory.")
    sys.exit(1)

import clr
clr.AddReference(dll_path)
from LibreHardwareMonitor.Hardware import Computer


class HardwareMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuration & Window Properties
        self.title("Advanced Python/C# Hardware Monitor")
        self.geometry("1300x840")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # Dynamic Configuration States
        self.poll_interval = 1.5      # Seconds between hardware updates
        self.temp_threshold = 80.0    # Degrees Celsius trigger point
        
        # Windows Toast Notifier Setup
        self.toaster = InteractableWindowsToaster("Hardware Monitor") if TOASTER_AVAILABLE else None
        self.last_alert_time = {}     # Tracks last alert timestamp per sensor key
        self.alert_cooldown = 60      # Minimum seconds between repeated alerts
        
        # Hardware Engine Setup
        self.computer = Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsMotherboardEnabled = True
        self.computer.IsControllerEnabled = True
        self.computer.Open()
        
        # Application States & Logging
        self.is_logging = False
        self.log_file = None
        self.csv_writer = None
        self.current_csv_filename = None
        
        # Time Windows (30 data points buffer)
        self.time_data = []
        self.cpu_temp_data = []
        self.gpu_temp_data = []
        self.cpu_load_data = []
        self.gpu_load_data = []
        self.cpu_fan_data = []
        self.gpu_fan_data = []
        self.start_time = time.time()
        
        self.setup_ui()
        
        # Initialize Background Performance Thread
        self.running = True
        self.monitor_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.monitor_thread.start()
        
        # Secure Window Closing Protocol
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)
        
        # ================= LEFT SIDE PANEL =================
        self.left_frame = ctk.CTkFrame(self, width=420, corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        self.title_lbl = ctk.CTkLabel(self.left_frame, text="System Telemetry", font=("Arial", 18, "bold"))
        self.title_lbl.grid(row=0, column=0, padx=10, pady=(15, 5), sticky="w")
        
        # Scrollable Viewbox for Telemetry
        self.stats_scroll = ctk.CTkScrollableFrame(self.left_frame)
        self.stats_scroll.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.label_cache = {}
        
        # Sliders Control Panel
        self.control_frame = ctk.CTkFrame(self.left_frame, corner_radius=8)
        self.control_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.control_frame.grid_columnconfigure(1, weight=1)
        
        # Slider 1: Polling Interval
        self.interval_lbl = ctk.CTkLabel(self.control_frame, text=f"Poll Rate: {self.poll_interval:.1f}s", font=("Arial", 12))
        self.interval_lbl.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.interval_slider = ctk.CTkSlider(
            self.control_frame, 
            from_=0.5, 
            to=5.0, 
            number_of_steps=45,
            command=self.on_interval_change
        )
        self.interval_slider.set(self.poll_interval)
        self.interval_slider.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Slider 2: Thermal Alert Threshold
        self.threshold_lbl = ctk.CTkLabel(self.control_frame, text=f"Alert Limit: {int(self.temp_threshold)}°C", font=("Arial", 12))
        self.threshold_lbl.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.threshold_slider = ctk.CTkSlider(
            self.control_frame, 
            from_=50.0, 
            to=100.0, 
            number_of_steps=50,
            command=self.on_threshold_change
        )
        self.threshold_slider.set(self.temp_threshold)
        self.threshold_slider.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Logging & Export Interface Panel
        self.log_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.log_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(1, weight=1)
        
        self.log_btn = ctk.CTkButton(
            self.log_frame, 
            text="Start CSV Logging", 
            fg_color="#2ecc71", 
            hover_color="#27ae60", 
            command=self.toggle_logging
        )
        self.log_btn.grid(row=0, column=0, padx=3, pady=3, sticky="ew")
        
        self.export_btn = ctk.CTkButton(
            self.log_frame, 
            text="Export HTML Report", 
            fg_color="#34495e", 
            hover_color="#2c3e50", 
            state="disabled",
            command=self.export_plotly_report
        )
        self.export_btn.grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        
        self.log_status_lbl = ctk.CTkLabel(self.log_frame, text="Logging: Stopped", text_color="#7f8c8d")
        self.log_status_lbl.grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="w")

        # ================= RIGHT SIDE PANEL (3-TIER MATPLOTLIB PLOTS) =================
        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self.right_frame.grid_rowconfigure(0, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        
        # 3 Subplots: [0] Thermals, [1] Hardware Load, [2] Fan Speeds
        self.fig, (self.ax_temp, self.ax_load, self.ax_fan) = plt.subplots(
            nrows=3, ncols=1, figsize=(7, 9), facecolor='#1e1e1e', sharex=True
        )
        self.fig.subplots_adjust(hspace=0.25, top=0.95, bottom=0.08, left=0.10, right=0.95)

        # --- Graph 1: Thermals (°C) ---
        self.ax_temp.set_facecolor('#151515')
        self.ax_temp.set_title("Thermal Trajectory (°C)", color="white", fontsize=11, pad=6)
        self.ax_temp.tick_params(colors='white', labelsize=9)
        self.ax_temp.grid(True, color='#2c2c2c')
        self.cpu_temp_line, = self.ax_temp.plot([], [], color="#e74c3c", label="CPU Temp", linewidth=2)
        self.gpu_temp_line, = self.ax_temp.plot([], [], color="#e67e22", label="GPU Temp", linewidth=2)
        self.threshold_line = self.ax_temp.axhline(
            y=self.temp_threshold, color="#ff4757", linestyle="--", linewidth=1.2, label="Limit", alpha=0.8
        )
        self.ax_temp.legend(loc="upper right", facecolor='#1e1e1e', edgecolor='none', labelcolor='white', fontsize=8)

        # --- Graph 2: Hardware Load (%) ---
        self.ax_load.set_facecolor('#151515')
        self.ax_load.set_title("Hardware Load (%)", color="white", fontsize=11, pad=6)
        self.ax_load.tick_params(colors='white', labelsize=9)
        self.ax_load.set_ylim(-2, 105)
        self.ax_load.grid(True, color='#2c2c2c')
        self.cpu_load_line, = self.ax_load.plot([], [], color="#3498db", label="CPU Load", linewidth=2)
        self.gpu_load_line, = self.ax_load.plot([], [], color="#9b59b6", label="GPU Load", linewidth=2)
        self.ax_load.legend(loc="upper right", facecolor='#1e1e1e', edgecolor='none', labelcolor='white', fontsize=8)

        # --- Graph 3: Fan Speeds (RPM) ---
        self.ax_fan.set_facecolor('#151515')
        self.ax_fan.set_title("Fan Speeds (RPM)", color="white", fontsize=11, pad=6)
        self.ax_fan.tick_params(colors='white', labelsize=9)
        self.ax_fan.grid(True, color='#2c2c2c')
        self.cpu_fan_line, = self.ax_fan.plot([], [], color="#2ecc71", label="CPU Fan", linewidth=2)
        self.gpu_fan_line, = self.ax_fan.plot([], [], color="#1abc9c", label="GPU Fan", linewidth=2)
        self.ax_fan.legend(loc="upper right", facecolor='#1e1e1e', edgecolor='none', labelcolor='white', fontsize=8)

        # Link Figure to CustomTkinter widget tree
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def on_interval_change(self, value):
        self.poll_interval = round(float(value), 1)
        self.interval_lbl.configure(text=f"Poll Rate: {self.poll_interval:.1f}s")

    def on_threshold_change(self, value):
        self.temp_threshold = round(float(value), 0)
        self.threshold_lbl.configure(text=f"Alert Limit: {int(self.temp_threshold)}°C")
        self.threshold_line.set_ydata([self.temp_threshold, self.temp_threshold])
        self.ui_refresh_graph()

    def send_thermal_notification(self, hw_name, sensor_name, temp_val):
        if not self.toaster:
            return
        
        now = time.time()
        alert_key = f"{hw_name}_{sensor_name}"
        
        if alert_key in self.last_alert_time:
            if now - self.last_alert_time[alert_key] < self.alert_cooldown:
                return
        
        self.last_alert_time[alert_key] = now
        
        def _notify():
            toast = Toast()
            toast.text_fields = [
                "⚠️ High Temperature Alert!",
                f"{hw_name} ({sensor_name}) reached {temp_val:.1f}°C (Threshold: {int(self.temp_threshold)}°C)"
            ]
            self.toaster.show_toast(toast)
            
        threading.Thread(target=_notify, daemon=True).start()

    def toggle_logging(self):
        if not self.is_logging:
            self.current_csv_filename = f"hardware_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                self.log_file = open(self.current_csv_filename, mode='w', newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.log_file)
                self.csv_writer.writerow(["Timestamp", "Hardware", "Sensor Name", "Value", "Type"])
                
                self.is_logging = True
                self.log_btn.configure(text="Stop CSV Logging", fg_color="#e74c3c", hover_color="#c0392b")
                self.export_btn.configure(state="disabled")
                self.log_status_lbl.configure(text=f"Logging: Active ({self.current_csv_filename})", text_color="#2ecc71")
            except Exception:
                self.log_status_lbl.configure(text="Error opening log file!", text_color="#e74c3c")
        else:
            self.is_logging = False
            if self.log_file:
                self.log_file.close()
                self.log_file = None
            self.log_btn.configure(text="Start CSV Logging", fg_color="#2ecc71", hover_color="#27ae60")
            self.log_status_lbl.configure(text=f"Saved: {self.current_csv_filename}", text_color="#7f8c8d")
            
            # Enable Plotly export button once a valid CSV is saved
            if PLOTLY_AVAILABLE and self.current_csv_filename and os.path.exists(self.current_csv_filename):
                self.export_btn.configure(state="normal", fg_color="#9b59b6", hover_color="#8e44ad")

    def export_plotly_report(self):
        if not PLOTLY_AVAILABLE or not self.current_csv_filename or not os.path.exists(self.current_csv_filename):
            self.log_status_lbl.configure(text="Error: Missing CSV or Plotly package", text_color="#e74c3c")
            return

        def _generate_report():
            try:
                self.log_status_lbl.configure(text="Generating Plotly Report...", text_color="#f39c12")
                
                df = pd.read_csv(self.current_csv_filename)
                df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                df = df.dropna(subset=['Value'])

                # Filter distinct metric groups
                types_present = df['Type'].unique().tolist()
                sensor_groups = [t for t in ['Temperature', 'Load', 'Fan', 'Power', 'Clock'] if t in types_present]
                
                if not sensor_groups:
                    sensor_groups = types_present[:3]

                fig = make_subplots(
                    rows=len(sensor_groups), 
                    cols=1, 
                    shared_xaxes=True,
                    vertical_spacing=0.06,
                    subplot_titles=[f"Metric: {group}" for group in sensor_groups]
                )

                for row_idx, group in enumerate(sensor_groups, start=1):
                    group_df = df[df['Type'] == group]
                    unique_sensors = group_df[['Hardware', 'Sensor Name']].drop_duplicates()

                    for _, row in unique_sensors.iterrows():
                        hw, sname = row['Hardware'], row['Sensor Name']
                        trace_df = group_df[(group_df['Hardware'] == hw) & (group_df['Sensor Name'] == sname)]
                        
                        fig.add_trace(
                            go.Scatter(
                                x=trace_df['Timestamp'],
                                y=trace_df['Value'],
                                mode='lines',
                                name=f"{hw} - {sname}",
                                hovertemplate='%{x|%H:%M:%S}<br><b>Value</b>: %{y:.1f}<extra></extra>'
                            ),
                            row=row_idx, 
                            col=1
                        )
                        
                    # Add Alert Threshold Line on Temperature panel
                    if group == 'Temperature':
                        fig.add_hline(
                            y=self.temp_threshold, 
                            line_dash="dash", 
                            line_color="red", 
                            annotation_text=f"Alert Limit ({int(self.temp_threshold)}°C)", 
                            annotation_position="top right",
                            row=row_idx, 
                            col=1
                        )

                fig.update_layout(
                    title=f"Hardware Telemetry Session Log: {os.path.basename(self.current_csv_filename)}",
                    template="plotly_dark",
                    height=280 * len(sensor_groups) + 120,
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )

                html_filename = self.current_csv_filename.replace('.csv', '_report.html')
                fig.write_html(html_filename)
                
                self.log_status_lbl.configure(text=f"Exported: {os.path.basename(html_filename)}", text_color="#2ecc71")
                webbrowser.open('file://' + os.path.abspath(html_filename))
            except Exception as e:
                self.log_status_lbl.configure(text=f"Export Failed: {str(e)[:30]}", text_color="#e74c3c")

        threading.Thread(target=_generate_report, daemon=True).start()

    def update_loop(self):
        while self.running:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_elapsed = time.time() - self.start_time
            
            max_cpu_t, max_gpu_t = None, None
            max_cpu_l, max_gpu_l = None, None
            max_cpu_f, max_gpu_f = None, None
            
            for hardware in self.computer.Hardware:
                hardware.Update()
                
                for sub_hw in hardware.SubHardware:
                    sub_hw.Update()
                    
                all_devices = [hardware] + list(hardware.SubHardware)
                
                for dev in all_devices:
                    hw_name = dev.Name
                    is_cpu = "CPU" in hw_name.upper()
                    is_gpu = any(g in hw_name.upper() for g in ("GPU", "NVIDIA", "AMD", "RADEON", "INTEL ARC"))
                    
                    for sensor in dev.Sensors:
                        if sensor.Value is None:
                            continue
                        
                        sensor_key = f"{hw_name}_{sensor.Name}_{sensor.SensorType}"
                        val_str = f"{sensor.Value:.1f}"
                        s_type = str(sensor.SensorType)
                        
                        if self.is_logging and self.csv_writer:
                            try:
                                self.csv_writer.writerow([timestamp, hw_name, sensor.Name, val_str, s_type])
                            except Exception:
                                pass
                        
                        if "Temperature" in s_type:
                            if sensor.Value > self.temp_threshold:
                                self.send_thermal_notification(hw_name, sensor.Name, sensor.Value)
                            if is_cpu:
                                max_cpu_t = max(max_cpu_t, sensor.Value) if max_cpu_t is not None else sensor.Value
                            elif is_gpu:
                                max_gpu_t = max(max_gpu_t, sensor.Value) if max_gpu_t is not None else sensor.Value
                                
                        elif "Load" in s_type:
                            if is_cpu and ("TOTAL" in sensor.Name.upper() or "CORE" in sensor.Name.upper()):
                                max_cpu_l = max(max_cpu_l, sensor.Value) if max_cpu_l is not None else sensor.Value
                            elif is_gpu and ("CORE" in sensor.Name.upper() or "GPU" in sensor.Name.upper() or "D3D" in sensor.Name.upper()):
                                max_gpu_l = max(max_gpu_l, sensor.Value) if max_gpu_l is not None else sensor.Value
                                
                        elif "Fan" in s_type:
                            if is_gpu:
                                max_gpu_f = max(max_gpu_f, sensor.Value) if max_gpu_f is not None else sensor.Value
                            else:
                                max_cpu_f = max(max_cpu_f, sensor.Value) if max_cpu_f is not None else sensor.Value
                        
                        self.after(0, self.ui_sync_label, sensor_key, hw_name, sensor.Name, val_str, s_type, sensor.Value)
            
            self.time_data.append(current_elapsed)
            self.cpu_temp_data.append(max_cpu_t if max_cpu_t is not None else (self.cpu_temp_data[-1] if self.cpu_temp_data else 0))
            self.gpu_temp_data.append(max_gpu_t if max_gpu_t is not None else (self.gpu_temp_data[-1] if self.gpu_temp_data else 0))
            self.cpu_load_data.append(max_cpu_l if max_cpu_l is not None else (self.cpu_load_data[-1] if self.cpu_load_data else 0))
            self.gpu_load_data.append(max_gpu_l if max_gpu_l is not None else (self.gpu_load_data[-1] if self.gpu_load_data else 0))
            self.cpu_fan_data.append(max_cpu_f if max_cpu_f is not None else (self.cpu_fan_data[-1] if self.cpu_fan_data else 0))
            self.gpu_fan_data.append(max_gpu_f if max_gpu_f is not None else (self.gpu_fan_data[-1] if self.gpu_fan_data else 0))
            
            if len(self.time_data) > 30:
                self.time_data.pop(0)
                self.cpu_temp_data.pop(0)
                self.gpu_temp_data.pop(0)
                self.cpu_load_data.pop(0)
                self.gpu_load_data.pop(0)
                self.cpu_fan_data.pop(0)
                self.gpu_fan_data.pop(0)
            
            self.after(0, self.ui_refresh_graph)
            time.sleep(self.poll_interval)

    def ui_sync_label(self, key, hw_name, s_name, val, s_type, raw_val):
        if hw_name not in self.label_cache:
            hdr = ctk.CTkLabel(self.stats_scroll, text=f"\n■ {hw_name}", font=("Arial", 13, "bold"), text_color="#3498db")
            hdr.pack(anchor="w", padx=5)
            self.label_cache[hw_name] = hdr
            
        if key not in self.label_cache:
            lbl = ctk.CTkLabel(self.stats_scroll, text="", font=("Arial", 11))
            lbl.pack(anchor="w", padx=15, pady=1)
            self.label_cache[key] = lbl
            
        display_color = "white"
        font_weight = "normal"
        if "Temperature" in s_type and raw_val > self.temp_threshold:
            display_color = "#e74c3c"
            font_weight = "bold"

        self.label_cache[key].configure(
            text=f"{s_name}: {val} {s_type}",
            text_color=display_color,
            font=("Arial", 11, font_weight)
        )

    def ui_refresh_graph(self):
        try:
            if not self.time_data:
                return

            x_min, x_max = min(self.time_data), max(self.time_data) + 1

            # 1. Update Thermal Graph
            self.cpu_temp_line.set_data(self.time_data, self.cpu_temp_data)
            self.gpu_temp_line.set_data(self.time_data, self.gpu_temp_data)
            self.ax_temp.set_xlim(x_min, x_max)
            all_temps = [t for t in (self.cpu_temp_data + self.gpu_temp_data) if t is not None] + [self.temp_threshold]
            if all_temps:
                self.ax_temp.set_ylim(max(0, min(all_temps) - 5), max(all_temps) + 5)

            # 2. Update Load Graph
            self.cpu_load_line.set_data(self.time_data, self.cpu_load_data)
            self.gpu_load_line.set_data(self.time_data, self.gpu_load_data)

            # 3. Update Fan Speeds Graph
            self.cpu_fan_line.set_data(self.time_data, self.cpu_fan_data)
            self.gpu_fan_line.set_data(self.time_data, self.gpu_fan_data)
            all_fans = [f for f in (self.cpu_fan_data + self.gpu_fan_data) if f is not None and f > 0]
            if all_fans:
                self.ax_fan.set_ylim(max(0, min(all_fans) - 100), max(all_fans) + 150)
            else:
                self.ax_fan.set_ylim(0, 3000)

            self.canvas.draw_idle()
        except Exception:
            pass

    def on_close(self):
        self.running = False
        self.is_logging = False
        if self.log_file:
            self.log_file.close()
        self.computer.Close()
        self.destroy()


if __name__ == "__main__":
    app = HardwareMonitorApp()
    app.mainloop()