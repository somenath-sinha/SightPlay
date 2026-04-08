import json
import os

CONFIG_FILE = "sightplay_config.json"

# All possible notes and their vertical Y coordinates on the canvas
ALL_NOTES = [
    'C7', 'B6', 'A6', 'G6', 'F6', 'E6', 'D6', 'C6', 'B5', 'A5', 'G5', 'F5', 
    'E5', 'D5', 'C5', 'B4', 'A4', 'G4', 'F4', 'E4', 'D4', 'C4', 'B3', 'A3', 
    'G3', 'F3', 'E3', 'D3', 'C3'
]

NOTE_COORDS = {note: 20 + (i * 10) for i, note in enumerate(ALL_NOTES)}

# MIDI mapping (Middle C / C4 = 60)
MIDI_TO_NOTE = {
    108: 'C7', 107: 'B6', 105: 'A6', 103: 'G6', 101: 'F6', 100: 'E6', 98: 'D6', 
    96: 'C6', 95: 'B5', 93: 'A5', 91: 'G5', 89: 'F5', 88: 'E5', 86: 'D5', 
    84: 'C5', 83: 'B4', 81: 'A4', 79: 'G4', 77: 'F4', 76: 'E4', 74: 'D4', 
    72: 'C4', 71: 'B3', 69: 'A3', 67: 'G3', 65: 'F3', 64: 'E3', 62: 'D3', 60: 'C3'
}

def load_config():
    default = {
        'high_note': 'F6', 
        'low_note': 'E3', 
        'input_mode': 'Type', # Type, MIDI, Audio
        'midi_device': None,
        'audio_device': None,
        'mic_threshold': 0.1
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                default.update(data)
        except Exception: pass
    return default

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)