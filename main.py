import flet as ft
import flet.canvas as cv

# Explicitly import all components for both Bar and Line charts
from flet_charts import (
    BarChart, 
    BarChartGroup, 
    BarChartRod, 
    BarChartRodTooltip, 
    BarChartTooltip, 
    ChartAxis,
    LineChart,
    LineChartData,
    LineChartDataPoint
)

import random
import json
import os
import time
import asyncio

CONFIG_FILE = "sightplay_config.json"

class SightPlayApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "SightPlay"
        
        self.page.window.width = 390
        self.page.window.height = 844 
        self.page.window.resizable = False
        self.page.padding = 20
        self.page.theme_mode = ft.ThemeMode.DARK 
        
        self.bg_color = "#2D323F"          
        self.panel_bg = "#2A2A2A"          
        self.btn_bg = "#434A59"       
        self.page.bgcolor = self.bg_color

        self.all_notes_ordered = [
            'C7', 'B6', 'A6', 'G6', 'F6', 'E6', 'D6', 'C6', 'B5', 'A5', 'G5', 'F5', 
            'E5', 'D5', 'C5', 'B4', 'A4', 'G4', 'F4', 'E4', 'D4', 'C4', 'B3', 'A3', 
            'G3', 'F3', 'E3', 'D3', 'C3'
        ]
        
        self.note_coords = {note: 20 + (i * 10) for i, note in enumerate(self.all_notes_ordered)}
        self.current_note = None
        self.previous_note = None
        self.guess = ""
        self.status_color = ft.Colors.WHITE
        self.note_start_time = 0
        self.response_times = [] 
        self.show_incorrect_in_stats = False

        self.config = self.load_config()
        self.active_notes = []
        self.update_active_range()

        self.setup_ui()
        self.next_note()

    def load_config(self):
        default_config = {'high_note': 'F6', 'low_note': 'E3'}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if config.get('high_note') in self.all_notes_ordered and config.get('low_note') in self.all_notes_ordered:
                        return config
            except: pass
        return default_config

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def update_active_range(self):
        high_idx = self.all_notes_ordered.index(self.config['high_note'])
        low_idx = self.all_notes_ordered.index(self.config['low_note'])
        if high_idx > low_idx:
            high_idx, low_idx = low_idx, high_idx
        self.active_notes = self.all_notes_ordered[high_idx : low_idx + 1]

    def setup_ui(self):
        top_bar = ft.Row([
            ft.Text("Type Note & Octave", size=16, color="#AAAAAA", expand=True),
            ft.ElevatedButton("📊 Stats", on_click=self.open_stats, bgcolor=self.btn_bg, color=ft.Colors.WHITE),
            ft.ElevatedButton("⚙ Settings", on_click=self.open_settings, bgcolor=self.btn_bg, color=ft.Colors.WHITE)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.canvas = cv.Canvas(width=300, height=320)
        self.canvas_container = ft.Container(
            content=self.canvas,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            padding=10,
            alignment=ft.Alignment(0, 0)
        )

        self.input_text = ft.Text("Note   Oct", size=32, weight=ft.FontWeight.BOLD, color="#444444")
        self.input_container = ft.Container(
            content=self.input_text, 
            alignment=ft.Alignment(0, 0), 
            height=60,
        )

        self.keypad_area = ft.Container(alignment=ft.Alignment(0, 0))

        self.page.add(
            top_bar,
            ft.Container(height=10),
            ft.Row([self.canvas_container], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=10),
            self.input_container,
            ft.Container(height=10),
            self.keypad_area
        )

        self.page.on_keyboard_event = self.on_keyboard

    def update_keypad(self):
        self.keypad_area.content = None
        def make_btn(text, is_del=False):
            return ft.Container(
                content=ft.Text(text, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                alignment=ft.Alignment(0, 0),
                width=50, height=50,
                bgcolor=ft.Colors.RED_400 if is_del else self.panel_bg,
                border_radius=10,
                on_click=lambda e: self.process_input("DEL" if is_del else text),
                animate=ft.Animation(200, ft.AnimationCurve.DECELERATE),
            )

        if len(self.guess) == 0:
            items = [make_btn(n) for n in ['A', 'B', 'C', 'D', 'E', 'F', 'G']]
        else:
            items = [make_btn(n) for n in ['3', '4', '5', '6', '7']]
            items.append(make_btn("←", is_del=True)) 

        self.keypad_area.content = ft.Row(items, alignment=ft.MainAxisAlignment.CENTER, wrap=True, spacing=10)
        self.keypad_area.update()

    def process_input(self, key):
        if self.status_color == "#66BB6A" and hasattr(self, 'fade_job') and self.fade_job: return 
        
        if key == "DEL":
            self.guess = self.guess[:-1]
            self.update_input_display()
            self.update_keypad()
            return
            
        if len(self.guess) >= 2: return 
        
        if len(self.guess) == 0 and key in 'ABCDEFG':
            self.guess = key
            self.update_input_display()
            self.update_keypad()
        elif len(self.guess) == 1 and key in '34567':
            self.guess += key
            self.evaluate_guess()

    def evaluate_guess(self):
        time_taken = time.time() - self.note_start_time
        is_correct = (self.guess == self.current_note)
        self.response_times.append({"time": time_taken, "correct": is_correct})
        
        if hasattr(self, 'stats_chart_stack'):
            self.update_stats_chart()

        if is_correct:
            self.status_color = "#66BB6A"
            self.update_input_display()
            self.fade_job = self.page.run_task(self.fade_animation, True)
        else:
            self.status_color = "#FF5252"
            self.update_input_display()
            self.fade_job = self.page.run_task(self.fade_animation, False)

    async def fade_animation(self, is_correct):
        r_start, g_start, b_start = (102, 187, 106) if is_correct else (255, 82, 82)
        for step in range(16):
            ratio = step / 15.0
            r_curr = int(r_start - (r_start - 45) * ratio)
            g_curr = int(g_start - (g_start - 50) * ratio)
            b_curr = int(b_start - (b_start - 63) * ratio)
            self.input_text.color = f"#{r_curr:02x}{g_curr:02x}{b_curr:02x}"
            self.input_text.update()
            await asyncio.sleep(0.04)
        
        self.guess = ""
        self.status_color = ft.Colors.WHITE
        self.update_input_display()
        self.fade_job = None
        if is_correct: self.next_note()
        else: self.update_keypad()

    def update_input_display(self):
        if len(self.guess) == 0:
            self.input_text.value = "Note   Oct"
            self.input_text.color = "#444444"
        elif len(self.guess) == 1:
            self.input_text.value = f"{self.guess[0]}      Oct"
            self.input_text.color = ft.Colors.WHITE
        elif len(self.guess) == 2:
            self.input_text.value = f"{self.guess[0]}      {self.guess[1]}"
            self.input_text.color = self.status_color
        self.input_text.update()

    def on_keyboard(self, e: ft.KeyboardEvent):
        key = e.key.upper()
        if key == "BACKSPACE": key = "DEL"
        self.process_input(key)

    # --- Popups ---
    def open_stats(self, e):
        self.stats_bar_chart = BarChart(
            left_axis=ChartAxis(title=ft.Text("Seconds"), label_size=50), 
            bottom_axis=ChartAxis(show_labels=False), 
            tooltip=BarChartTooltip(bgcolor=ft.Colors.BLUE_GREY_900),
            expand=True
        )

        # 1. FIXED: Added a transparent "Seconds" label so the margins align perfectly with the BarChart
        self.stats_line_chart = LineChart(
            left_axis=ChartAxis(title=ft.Text("Seconds", color=ft.Colors.TRANSPARENT), label_size=50),
            bottom_axis=ChartAxis(show_labels=False),
            expand=True
        )

        # 2. FIXED: LineChart goes first, placing it behind the BarChart. Now Bar tooltips catch hovers properly.
        self.stats_chart_stack = ft.Stack(
            controls=[self.stats_line_chart, self.stats_bar_chart],
            expand=True
        )

        # 3. FIXED: Wrapping the chart stack in a container with dynamic width for scrolling
        self.chart_container = ft.Container(
            content=self.stats_chart_stack,
            width=360, # Will expand if there are many entries
            height=250
        )

        self.scrollable_chart = ft.Row(
            controls=[self.chart_container],
            scroll=ft.ScrollMode.ALWAYS,
            expand=True
        )

        self.update_stats_chart(should_update=False) 
        
        def toggle_incorrect(e):
            self.show_incorrect_in_stats = not self.show_incorrect_in_stats
            toggle_btn.text = "Hide Incorrect Notes" if self.show_incorrect_in_stats else "Show Incorrect Notes"
            self.update_stats_chart() 
            self.page.update()

        legend = ft.Text("— Cumulative Average", color=ft.Colors.YELLOW_400, weight=ft.FontWeight.BOLD, size=14)

        toggle_btn = ft.ElevatedButton(
            "Show Incorrect Notes" if not self.show_incorrect_in_stats else "Hide Incorrect Notes",
            on_click=toggle_incorrect, 
            bgcolor=self.btn_bg, 
            color=ft.Colors.WHITE
        )
        
        self.stats_dialog = ft.AlertDialog(
            title=ft.Text("Performance Stats", weight=ft.FontWeight.BOLD), 
            content=ft.Container(
                content=ft.Column(
                    [self.scrollable_chart, legend, toggle_btn], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15 
                ), 
                width=450, height=420, 
                padding=10
            )
        )
        
        self.page.overlay.append(self.stats_dialog)
        self.stats_dialog.open = True
        self.page.update()

    def update_stats_chart(self, should_update=True):
        if not hasattr(self, 'stats_chart_stack'): return

        data = self.response_times if self.show_incorrect_in_stats else [d for d in self.response_times if d["correct"]]
        
        if not data:
            self.stats_bar_chart.groups = []
            self.stats_line_chart.data_series = []
            if should_update: self.stats_chart_stack.update()
            return

        # Dynamically resize the chart container so it scrolls if there are lots of bars
        required_width = max(360, len(data) * 45)
        self.chart_container.width = required_width

        max_time = max(d["time"] for d in data)
        y_max = max_time * 1.2 
        
        groups = []
        avg_points = []
        total_time = 0
        
        for i, d in enumerate(data):
            bar_color = ft.Colors.GREEN_400 if d["correct"] else ft.Colors.RED_400
            groups.append(
                BarChartGroup(
                    x=i,
                    rods=[
                        BarChartRod(
                            from_y=0,
                            to_y=round(d["time"], 2),
                            color=bar_color,
                            width=15,
                            tooltip=BarChartRodTooltip(
                                f"{d['time']:.2f}s",
                                text_style=ft.TextStyle(
                                    color=ft.Colors.WHITE,
                                    weight=ft.FontWeight.BOLD,
                                    size=14
                                )
                            ),
                            border_radius=4
                        )
                    ]
                )
            )

            # 4. FIXED: Truncate to 2 decimal places for the average line tooltip
            total_time += d["time"]
            current_avg = total_time / (i + 1)
            avg_points.append(LineChartDataPoint(i, current_avg, tooltip=f"Avg: {current_avg:.2f}s"))

        self.stats_bar_chart.groups = groups
        self.stats_bar_chart.max_y = y_max
        self.stats_bar_chart.min_y = 0

        self.stats_line_chart.data_series = [
            LineChartData(
                points=avg_points, 
                stroke_width=4, 
                color=ft.Colors.YELLOW_400, 
                curved=True
            )
        ]
        self.stats_line_chart.max_y = y_max
        self.stats_line_chart.min_y = 0

        if should_update:
            self.chart_container.update()
            self.stats_chart_stack.update()

    def open_settings(self, e):
        def save(e):
            self.config['high_note'] = high_dd.value
            self.config['low_note'] = low_dd.value
            self.save_config()
            self.update_active_range()
            self.settings_dialog.open = False
            self.page.update()
            self.next_note()

        def reset_defaults(e):
            high_dd.value = 'F6'
            low_dd.value = 'E3'
            high_dd.update()
            low_dd.update()
            
        high_dd = ft.Dropdown(value=self.config['high_note'], options=[ft.dropdown.Option(n) for n in self.all_notes_ordered], width=100)
        low_dd = ft.Dropdown(value=self.config['low_note'], options=[ft.dropdown.Option(n) for n in self.all_notes_ordered], width=100)
        
        self.settings_dialog = ft.AlertDialog(
            title=ft.Text("Settings"), 
            content=ft.Column([
                ft.Row([ft.Text("Highest Note:"), high_dd]), 
                ft.Row([ft.Text("Lowest Note:"), low_dd])
            ], tight=True), 
            actions=[
                ft.TextButton("Reset Defaults", on_click=reset_defaults),
                ft.TextButton("Save & Apply", on_click=save)
            ]
        )
        
        self.page.overlay.append(self.settings_dialog)
        self.settings_dialog.open = True
        self.page.update()

    # --- Drawing Logic ---
    def draw_staff(self):
        self.canvas.shapes.clear()
        paint = ft.Paint(stroke_width=2, color=ft.Colors.BLACK)
        for y in [130, 150, 170, 190, 210]:
            self.canvas.shapes.append(cv.Line(20, y, 280, y, paint=paint))
        self.canvas.shapes.append(cv.Text(30, 120, "𝄞", ft.TextStyle(size=100, color=ft.Colors.BLACK)))

    def draw_note(self, y):
        paint = ft.Paint(stroke_width=2, color=ft.Colors.BLACK)
        if y <= 110:
            for ly in range(110, int(y) - 1, -20): self.canvas.shapes.append(cv.Line(130, ly, 170, ly, paint=paint))
        if y >= 230:
            for ly in range(230, int(y) + 1, 20): self.canvas.shapes.append(cv.Line(130, ly, 170, ly, paint=paint))
            
        self.canvas.shapes.append(cv.Circle(150, y, 10, paint=ft.Paint(style=ft.PaintingStyle.FILL, color=ft.Colors.BLACK)))
        
        stem_paint = ft.Paint(stroke_width=4, color=ft.Colors.BLACK)
        if y < 170: self.canvas.shapes.append(cv.Line(140, y, 140, y + 55, paint=stem_paint))
        else: self.canvas.shapes.append(cv.Line(160, y, 160, y - 55, paint=stem_paint))
        self.canvas.update()

    def next_note(self):
        new_note = random.choice(self.active_notes)
        while new_note == self.previous_note and len(self.active_notes) > 1: new_note = random.choice(self.active_notes)
        self.current_note = new_note; self.previous_note = new_note; self.guess = ""
        self.update_input_display(); self.update_keypad(); self.draw_staff()
        self.draw_note(self.note_coords[self.current_note]); self.note_start_time = time.time()


def main(page: ft.Page): 
    SightPlayApp(page)

if __name__ == "__main__": 
    ft.run(main)