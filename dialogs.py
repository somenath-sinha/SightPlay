import flet as ft
from flet_charts import BarChart, BarChartGroup, BarChartRod, BarChartRodTooltip, BarChartTooltip, ChartAxis, LineChart, LineChartData, LineChartDataPoint
import config
import math
import asyncio

class StatsDialog:
    def __init__(self, app_ref):
        self.app = app_ref
        self.show_incorrect = False
        
        self.avg_label = ft.Text("Overall Avg: --", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.YELLOW_400)
        
        # FIXED: Removed the left_axis entirely from the charts so they don't scroll
        self.bar_chart = BarChart(
            left_axis=ChartAxis(show_labels=False), 
            bottom_axis=ChartAxis(show_labels=False), 
            tooltip=BarChartTooltip(bgcolor=ft.Colors.BLUE_GREY_900),
            expand=True
        )
        self.line_chart = LineChart(
            left_axis=ChartAxis(show_labels=False),
            bottom_axis=ChartAxis(show_labels=False), expand=True
        )
        
        self.chart_stack = ft.Stack(controls=[self.line_chart, self.bar_chart], expand=True)
        self.chart_container = ft.Container(content=self.chart_stack, width=320, height=220)
        self.scrollable = ft.Row(controls=[self.chart_container], scroll=ft.ScrollMode.ALWAYS, expand=True)
        
        # FIXED: Pinned Y-Axis column that stays completely locked
        self.y_axis_col = ft.Column(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, 
            height=220, 
            width=30, 
            controls=[ft.Text("0.0", size=12)] * 5
        )
        
        # Wrapper to hold the fixed axis next to the scrolling container
        self.chart_with_fixed_axis = ft.Row([self.y_axis_col, self.scrollable], height=240)
        
        self.toggle_btn = ft.ElevatedButton("Show Incorrect Notes", on_click=self.toggle_mode, bgcolor="#434A59", color=ft.Colors.WHITE)
        self.clear_btn = ft.ElevatedButton("Clear Stats", on_click=self.clear_stats, bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
        
        self.content_container = ft.Container(
            content=ft.Column([
                self.avg_label, 
                self.chart_with_fixed_axis, 
                ft.Text("— Cumulative Average", color=ft.Colors.YELLOW_400, size=12),
                ft.Row([self.toggle_btn, self.clear_btn], alignment=ft.MainAxisAlignment.CENTER, wrap=True)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            width=350, height=450, padding=10
        )
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Performance Stats", weight=ft.FontWeight.BOLD),
            content=self.content_container
        )

    def open_dialog(self):
        self.refresh_data()
        if self.dialog not in self.app.page.overlay:
            self.app.page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app.page.update()

    def toggle_mode(self, e):
        self.show_incorrect = not self.show_incorrect
        self.toggle_btn.text = "Hide Incorrect Notes" if self.show_incorrect else "Show Incorrect Notes"
        # FIXED: Color swap logic
        self.toggle_btn.bgcolor = ft.Colors.BLUE_700 if self.show_incorrect else "#434A59"
        self.refresh_data()

    def clear_stats(self, e):
        self.app.response_times.clear()
        self.refresh_data()

    def refresh_data(self):
        data = self.app.response_times if self.show_incorrect else [d for d in self.app.response_times if d["correct"]]
        
        if not data:
            self.bar_chart.groups = []
            self.line_chart.data_series = []
            self.avg_label.value = "Overall Avg: --"
            if self.app.page: self.app.page.update()
            return

        self.chart_container.width = max(300, len(data) * 45)
        y_max = max(d["time"] for d in data) * 1.2 
        
        # Populate the pinned Y-Axis labels evenly
        self.y_axis_col.controls = [
            ft.Text(f"{y_max:.1f}", size=12, color=ft.Colors.GREY_400),
            ft.Text(f"{y_max*0.75:.1f}", size=12, color=ft.Colors.GREY_400),
            ft.Text(f"{y_max*0.5:.1f}", size=12, color=ft.Colors.GREY_400),
            ft.Text(f"{y_max*0.25:.1f}", size=12, color=ft.Colors.GREY_400),
            ft.Text("0.0", size=12, color=ft.Colors.GREY_400),
        ]
        
        groups = []
        avg_points = []
        total = 0
        
        for i, d in enumerate(data):
            c = ft.Colors.GREEN_400 if d["correct"] else ft.Colors.RED_400
            total += d["time"]
            avg = total / (i + 1)
            
            groups.append(BarChartGroup(x=i, rods=[
                BarChartRod(
                    from_y=0, to_y=round(d["time"], 2), color=c, width=15, border_radius=4,
                    tooltip=BarChartRodTooltip(
                        f"Note: {d['time']:.2f}s\nAvg: {avg:.2f}s",
                        text_style=ft.TextStyle(color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                    )
                )
            ]))
            avg_points.append(LineChartDataPoint(i, avg))

        self.avg_label.value = f"Overall Avg: {(total/len(data)):.2f}s"
        
        self.bar_chart.groups = groups
        self.bar_chart.max_y = self.line_chart.max_y = y_max
        self.bar_chart.min_y = self.line_chart.min_y = 0
        self.line_chart.data_series = [LineChartData(points=avg_points, stroke_width=4, color=ft.Colors.YELLOW_400, curved=True)]
        
        if self.app.page: self.app.page.update()


class SettingsDialog:
    def __init__(self, app_ref):
        self.app = app_ref
        
        self.high_dd = ft.Dropdown(value=self.app.config['high_note'], options=[ft.dropdown.Option(n) for n in config.ALL_NOTES], width=100)
        self.low_dd = ft.Dropdown(value=self.app.config['low_note'], options=[ft.dropdown.Option(n) for n in config.ALL_NOTES], width=100)
        
        self.mode_dd = ft.Dropdown(
            value=self.app.config['input_mode'], width=150,
            options=[ft.dropdown.Option(m) for m in ["Type", "MIDI", "Audio"]],
            on_select=self.mode_changed 
        )
        self.device_dd = ft.Dropdown(width=250, on_select=self.device_changed)
        
        self.audio_panel = ft.Column(visible=False)
        self.thresh_slider = ft.Slider(min=0.01, max=0.5, value=self.app.config.get('mic_threshold', 0.1), on_change=self.threshold_changed)
        self.thresh_label = ft.Text(f"{self.app.config.get('mic_threshold', 0.1):.2f} RMS", color=ft.Colors.YELLOW_400, weight=ft.FontWeight.BOLD)
        
        self.meter_bar = ft.ProgressBar(value=0, color=ft.Colors.GREEN, bgcolor=ft.Colors.GREY_800, expand=True)
        self.meter_text = ft.Text("-100.0 dB", width=65, size=12)
        
        # FIXED: Proper Audio panel layout with clear scale indications
        self.audio_panel.controls = [
            ft.Row([ft.Text("Mic Threshold:"), self.thresh_label]), 
            self.thresh_slider, 
            ft.Text("Live Input Level:"), 
            ft.Row([self.meter_bar, self.meter_text])
        ]

        self.content_col = ft.Column([
            ft.Row([ft.Text("Input Mode:"), self.mode_dd]),
            ft.Row([ft.Text("Device:"), self.device_dd]),
            self.audio_panel,
            ft.Divider(),
            ft.Row([ft.Text("Highest Note:"), self.high_dd]), 
            ft.Row([ft.Text("Lowest Note:"), self.low_dd])
        ], tight=True)
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Settings"),
            content=self.content_col,
            on_dismiss=self.handle_dismiss, 
            actions=[
                ft.TextButton("Reset", on_click=self.reset_defaults),
                ft.TextButton("Save", on_click=self.save)
            ]
        )

    def open_dialog(self):
        self.populate_devices(self.app.config['input_mode'], should_update=False)
        if self.dialog not in self.app.page.overlay:
            self.app.page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app.page.update()
        
        # FIXED: Boot up the asynchronous, non-blocking UI meter loop
        self.app.page.run_task(self.meter_loop)

    def close_dialog(self):
        self.dialog.open = False
        if self.app.page: self.app.page.update()

    def handle_dismiss(self, e):
        self.app.apply_settings()

    async def meter_loop(self):
        # FIXED: Safely poll the hardware state 10 times a second without blocking the mic
        while getattr(self, 'dialog', None) and self.dialog.open:
            if self.mode_dd.value == "Audio" and hasattr(self.app.input_manager, 'current_rms'):
                rms = self.app.input_manager.current_rms
                db = 20 * math.log10(rms) if rms > 1e-7 else -100.0
                scaled = min(rms * 15, 1.0)
                
                self.meter_bar.value = scaled
                self.meter_bar.color = ft.Colors.RED if scaled > 0.8 else ft.Colors.GREEN
                self.meter_text.value = f"{db:.1f} dB"
                
                try:
                    self.meter_bar.update()
                    self.meter_text.update()
                except Exception:
                    pass
            await asyncio.sleep(0.1)

    def populate_devices(self, mode, should_update=True):
        self.device_dd.options.clear()
        self.audio_panel.visible = (mode == "Audio")
        
        if mode == "MIDI":
            devs = self.app.input_manager.get_midi_devices()
            if devs:
                self.device_dd.options = [ft.dropdown.Option(d) for d in devs]
                if self.app.config.get('midi_device') in devs:
                    self.device_dd.value = self.app.config.get('midi_device')
                else:
                    self.device_dd.value = devs[0]
            else:
                self.device_dd.options = [ft.dropdown.Option("None", text="No MIDI Devices Found")]
                self.device_dd.value = "None"
                
        elif mode == "Audio":
            devs = self.app.input_manager.get_audio_devices()
            if devs:
                self.device_dd.options = [ft.dropdown.Option(key=str(d['id']), text=d['name']) for d in devs]
                saved_id = str(self.app.config.get('audio_device_id', ''))
                valid_ids = [str(d['id']) for d in devs]
                
                if saved_id in valid_ids:
                    self.device_dd.value = saved_id
                else:
                    self.device_dd.value = str(devs[0]['id'])
            else:
                self.device_dd.options = [ft.dropdown.Option("None", text="No Audio Devices Found")]
                self.device_dd.value = "None"
                
        else:
            self.device_dd.options = [ft.dropdown.Option("None", text="N/A - Typing Mode")]
            self.device_dd.value = "None"
        
        self.start_preview()
        if should_update and self.app.page: 
            self.app.page.update()

    def mode_changed(self, e):
        self.populate_devices(self.mode_dd.value, should_update=True)

    def device_changed(self, e):
        self.start_preview()

    def threshold_changed(self, e):
        val = float(self.thresh_slider.value)
        self.app.input_manager.threshold = val
        self.thresh_label.value = f"{val:.2f} RMS"
        if self.app.page and self.dialog.open:
            try: self.thresh_label.update()
            except: pass

    def start_preview(self):
        mode = self.mode_dd.value
        dev = self.device_dd.value
        if dev == "None": dev = None
        
        self.app.input_manager.set_mode(
            mode,
            midi_dev=dev if mode == "MIDI" else None,
            audio_dev_id=dev if mode == "Audio" else None,
            threshold=self.thresh_slider.value
        )

    # Legacy fallback explicitly ignored in favor of meter_loop
    def update_meter(self, rms): 
        pass

    def reset_defaults(self, e):
        self.high_dd.value = 'F6'
        self.low_dd.value = 'E3'
        self.mode_dd.value = 'Type'
        self.mode_changed(None)

    def save(self, e):
        self.app.config['high_note'] = self.high_dd.value
        self.app.config['low_note'] = self.low_dd.value
        self.app.config['input_mode'] = self.mode_dd.value
        self.app.config['mic_threshold'] = self.thresh_slider.value
        
        if self.mode_dd.value == "MIDI": 
            self.app.config['midi_device'] = self.device_dd.value
        elif self.mode_dd.value == "Audio": 
            self.app.config['audio_device_id'] = self.device_dd.value
            
        config.save_config(self.app.config)
        self.app.apply_settings()
        self.close_dialog()