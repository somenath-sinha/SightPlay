import flet as ft
import flet.canvas as cv
import random
import time
import asyncio
import os
import platform
import config
from inputs import InputManager
from dialogs import StatsDialog, SettingsDialog

# Helper to trigger native OS system sounds
def play_system_sound(success=True):
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            if success:
                os.system("afplay /System/Library/Sounds/Glass.aiff &")
            else:
                os.system("afplay /System/Library/Sounds/Basso.aiff &")
        elif system == "Windows":
            import winsound
            if success:
                winsound.MessageBeep(winsound.MB_OK)
            else:
                winsound.MessageBeep(winsound.MB_ICONHAND)
        else:  # Linux fallback
            print('\a')
    except Exception:
        pass


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

        self.current_note = None
        self.previous_note = None
        self.guess = ""
        self.status_color = ft.Colors.WHITE
        self.note_start_time = 0
        self.response_times = [] 
        self.fade_job = None

        self.config = config.load_config()
        self.active_notes = []
        
        # Initialize Managers 
        self.stats_dialog_ui = StatsDialog(self)
        self.settings_dialog_ui = SettingsDialog(self)
        
        self.input_manager = InputManager(
            callback=self.hardware_note_received, 
            update_meter_callback=self.settings_dialog_ui.update_meter
        )

        self.setup_ui()
        self.apply_settings()

    def hardware_note_received(self, note_str):
        # FIXED: Explicitly ignore incoming notes if the Settings menu is actively open
        if getattr(self.settings_dialog_ui, 'dialog', None) and self.settings_dialog_ui.dialog.open:
            return 
            
        if self.fade_job is None: 
            self.guess = note_str
            self.evaluate_guess()

    def apply_settings(self):
        h_idx = config.ALL_NOTES.index(self.config['high_note'])
        l_idx = config.ALL_NOTES.index(self.config['low_note'])
        if h_idx > l_idx: h_idx, l_idx = l_idx, h_idx
        self.active_notes = config.ALL_NOTES[h_idx : l_idx + 1]
        
        mode = self.config['input_mode']
        self.keypad_area.visible = (mode == "Type")
        if mode != "Type":
            self.input_text.value = f"Listening via {mode}..."
        
        self.input_manager.set_mode(
            mode, 
            self.config.get('midi_device'), 
            self.config.get('audio_device_id'), 
            self.config.get('mic_threshold', 0.1)
        )
        
        self.page.update()
        self.next_note()

    def setup_ui(self):
        top_bar = ft.Row([
            ft.Text("Note & Octave", size=16, color="#AAAAAA", expand=True),
            ft.ElevatedButton("📊 Stats", on_click=lambda e: self.stats_dialog_ui.open_dialog(), bgcolor=self.btn_bg, color=ft.Colors.WHITE),
            ft.ElevatedButton("⚙ Settings", on_click=lambda e: self.settings_dialog_ui.open_dialog(), bgcolor=self.btn_bg, color=ft.Colors.WHITE)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.canvas = cv.Canvas(width=300, height=320)
        self.canvas_container = ft.Container(content=self.canvas, bgcolor=ft.Colors.WHITE, border_radius=10, padding=10, alignment=ft.Alignment(0, 0))

        self.input_text = ft.Text("Note   Oct", size=32, weight=ft.FontWeight.BOLD, color="#444444")
        self.input_container = ft.Container(content=self.input_text, alignment=ft.Alignment(0, 0), height=60)
        self.keypad_area = ft.Container(alignment=ft.Alignment(0, 0))

        self.page.add(top_bar, ft.Container(height=10), ft.Row([self.canvas_container], alignment=ft.MainAxisAlignment.CENTER), ft.Container(height=10), self.input_container, ft.Container(height=10), self.keypad_area)
        self.page.on_keyboard_event = self.on_keyboard

    def update_keypad(self):
        if self.config['input_mode'] != "Type": return
        self.keypad_area.content = None
        def make_btn(text, is_del=False):
            return ft.Container(
                content=ft.Text(text, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), alignment=ft.Alignment(0, 0), 
                width=60, height=60, 
                bgcolor=ft.Colors.RED_400 if is_del else self.panel_bg, border_radius=10,
                on_click=lambda e: self.process_input("DEL" if is_del else text), animate=ft.Animation(200, ft.AnimationCurve.DECELERATE),
            )
        
        if len(self.guess) == 0:
            row1 = [make_btn(n) for n in ['A', 'B', 'C', 'D']]
            row2 = [make_btn(n) for n in ['E', 'F', 'G']]
        else:
            row1 = [make_btn(n) for n in ['3', '4', '5', '6']]
            row2 = [make_btn(n) for n in ['7']] + [make_btn("←", True)]
            
        self.keypad_area.content = ft.Column([
            ft.Row(row1, alignment=ft.MainAxisAlignment.CENTER, spacing=15),
            ft.Row(row2, alignment=ft.MainAxisAlignment.CENTER, spacing=15)
        ], spacing=15)
        
        self.keypad_area.update()

    def process_input(self, key):
        if self.config['input_mode'] != "Type" or (self.status_color == "#66BB6A" and self.fade_job): return 
        if key == "DEL":
            self.guess = self.guess[:-1]; self.update_input_display(); self.update_keypad()
            return
        if len(self.guess) >= 2: return 
        if len(self.guess) == 0 and key in 'ABCDEFG':
            self.guess = key; self.update_input_display(); self.update_keypad()
        elif len(self.guess) == 1 and key in '34567':
            self.guess += key; self.evaluate_guess()

    def evaluate_guess(self):
        time_taken = time.time() - self.note_start_time
        is_correct = (self.guess == self.current_note)
        self.response_times.append({"time": time_taken, "correct": is_correct})
        
        if is_correct:
            self.status_color = "#66BB6A"
            play_system_sound(success=True)
            self.input_text.value = f"✅  {self.guess[0]}      {self.guess[1]}"
            self.input_text.color = self.status_color
            if self.page: self.input_text.update()
            self.fade_job = self.page.run_task(self.fade_animation, True)
        else:
            self.status_color = "#FF5252"
            play_system_sound(success=False)
            self.input_text.value = f"❌  {self.guess[0]}      {self.guess[1]}"
            self.input_text.color = self.status_color
            if self.page: self.input_text.update()
            self.fade_job = self.page.run_task(self.fade_animation, False)

    async def fade_animation(self, is_correct):
        r_start, g_start, b_start = (102, 187, 106) if is_correct else (255, 82, 82)
        for step in range(16):
            ratio = step / 15.0
            r_curr, g_curr, b_curr = int(r_start - (r_start - 45) * ratio), int(g_start - (g_start - 50) * ratio), int(b_start - (b_start - 63) * ratio)
            self.input_text.color = f"#{r_curr:02x}{g_curr:02x}{b_curr:02x}"
            self.input_text.update()
            await asyncio.sleep(0.04)
        
        self.guess = ""; self.status_color = ft.Colors.WHITE; self.fade_job = None
        self.update_input_display()
        if is_correct: self.next_note()
        else: self.update_keypad()

    def update_input_display(self):
        if self.config['input_mode'] != "Type":
            if not self.guess: 
                self.input_text.value = f"Listening ({self.config['input_mode']})..."
                self.input_text.color = "#AAAAAA"
        else:
            if len(self.guess) == 0: 
                self.input_text.value = "Note   Oct"; self.input_text.color = "#444444"
            elif len(self.guess) == 1: 
                self.input_text.value = f"{self.guess[0]}      Oct"; self.input_text.color = ft.Colors.WHITE
        if self.page: self.input_text.update()

    def on_keyboard(self, e: ft.KeyboardEvent):
        key = e.key.upper()
        if key == "BACKSPACE": key = "DEL"
        self.process_input(key)

    # --- Drawing Logic ---
    def draw_staff(self):
        self.canvas.shapes.clear()
        paint = ft.Paint(stroke_width=2, color=ft.Colors.BLACK)
        for y in [130, 150, 170, 190, 210]: self.canvas.shapes.append(cv.Line(20, y, 280, y, paint=paint))
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
        self.draw_note(config.NOTE_COORDS[self.current_note]); self.note_start_time = time.time()


def main(page: ft.Page): SightPlayApp(page)

if __name__ == "__main__": ft.run(main)