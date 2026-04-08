# Changelog


## [0.9.0]

### Added
- **MIDI Input Support:** Integration for physical MIDI keyboards to play notes directly into the app.
- **Audio Pitch Detection:** Real-time microphone listening to convert instrumental/vocal frequencies into MIDI notes.
- **Real-time Audio DSP:** Background FFT (Fast Fourier Transform) processing for high-accuracy pitch tracking.
- **Live Input Meter:** Visual dB level indicator and RMS threshold slider in Settings for microphone calibration.
- **Cumulative Average Line:** A yellow trend line in Stats to track response time progression across practice sessions.
- **System Sound Effects:** Native macOS/Windows success chimes and error buzzers for instant auditory feedback.
- **Validation Marks:** Visual Check (✅) and Cross (❌) indicators appearing next to note guesses.
- **Clear Stats:** A dedicated function to reset performance data.

### Changed
- **Modular Architecture:** Refactored the monolithic script into four distinct modules (`main`, `dialogs`, `inputs`, `config`) for stability and scalability.
- **Responsive Layout:** Updated UI to match standard smartphone aspect ratios (iPhone 13/14 base resolution).
- **4x2 Keypad Grid:** Redesigned keypad layout for more ergonomic touch-friendly input.
- **Bar Chart Visualization:** Switched from a static line chart to a dynamic, scrollable Bar Chart with color-coded results (Green for Correct, Red for Incorrect).
- **Dialog Composition Pattern:** Rebuilt all popups using a composition pattern to resolve rendering panics in Flet 0.84.0.
- **Enhanced Tooltips:** Combined specific response time and cumulative average data into unified, high-legibility tooltips.

### Fixed
- **Flet 0.84 API Migration:** Resolved multiple breaking changes including `on_change` to `on_select`, `data_points` to `points`, and the removal of the `page.open()` method.
- **Scrolling Y-Axis:** Decoupled the measurement scale from the scrollable chart container so numbers remain pinned to the left while data scrolls.
- **Hardware Bottlenecking:** Moved audio processing to a non-blocking background thread to prevent UI WebSocket congestion.
- **Silence Crashing:** Wrapped NumPy audio arrays in robust error handling to prevent application exit during periods of silence.
- **Overlay Clipping:** Fixed layout issues where the "Clear Stats" button and graph labels were being cut off on smaller screens.


## [ v0.8 ]
Final monolithic version; Basic PoC. Only supports text based input (touch/type).