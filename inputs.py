import mido
import sounddevice as sd
import numpy as np
from config import MIDI_TO_NOTE

class InputManager:
    # Safely accepts the legacy update_meter_callback so we don't have to rewrite main.py
    def __init__(self, callback, update_meter_callback=None):
        self.callback = callback 
        self.midi_port = None
        self.audio_stream = None
        self.threshold = 0.1
        self.current_rms = 0.0 # Exposing this safely for the UI to poll

    def get_midi_devices(self):
        return mido.get_input_names()

    def get_audio_devices(self):
        try:
            devices = sd.query_devices()
            return [{"name": d['name'], "id": i} for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        except Exception as e:
            print(f"Error querying audio devices: {e}")
            return []

    def set_mode(self, mode, midi_dev=None, audio_dev_id=None, threshold=0.1):
        self.stop_all()
        self.threshold = float(threshold)
        self.current_rms = 0.0
        
        if mode == "MIDI":
            devices = self.get_midi_devices()
            if not midi_dev and devices:
                midi_dev = devices[0]
            if midi_dev:
                try:
                    self.midi_port = mido.open_input(midi_dev, callback=self._midi_callback)
                    print(f"Successfully connected to MIDI: {midi_dev}")
                except Exception as e:
                    print(f"Failed to open MIDI: {e}")

        elif mode == "Audio":
            devices = self.get_audio_devices()
            if audio_dev_id is None and devices:
                audio_dev_id = devices[0]['id']

            if audio_dev_id is not None and str(audio_dev_id).isdigit():
                try:
                    self.audio_stream = sd.InputStream(
                        device=int(audio_dev_id), channels=1, samplerate=44100, 
                        callback=self._audio_callback, blocksize=2048
                    )
                    self.audio_stream.start()
                    print("Audio stream started successfully! Mic is live.")
                except Exception as e:
                    print(f"Failed to open Audio Stream: {e}")

    def _midi_callback(self, message):
        if message.type == 'note_on' and message.velocity > 0:
            if message.note in MIDI_TO_NOTE:
                self.callback(MIDI_TO_NOTE[message.note])

    def _audio_callback(self, indata, frames, time, status):
        try:
            if indata.size == 0: return
            
            # FIXED: We no longer force the UI to update from this thread. We just update memory.
            rms = float(np.sqrt(np.mean(indata**2)))
            self.current_rms = rms 

            if rms > self.threshold:
                window = np.hanning(len(indata))
                fft_data = np.fft.rfft(indata[:, 0] * window)
                freqs = np.fft.rfftfreq(len(indata), 1/44100.0)
                
                peak_freq = freqs[np.argmax(np.abs(fft_data))]
                
                if peak_freq > 60: 
                    midi_note = int(round(69 + 12 * np.log2(peak_freq / 440.0)))
                    if midi_note in MIDI_TO_NOTE:
                        self.callback(MIDI_TO_NOTE[midi_note])
        except Exception:
            pass 

    def stop_all(self):
        if self.midi_port:
            self.midi_port.close()
            self.midi_port = None
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None