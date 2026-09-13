# Midi-Encoder-To-MA3-Mapper
Stand alone Python program that link midi rotary encoder to mouse position and increment or decrement pointed encoder as a mouse wheel.

Compilation command:
```python -m PyInstaller --noconfirm --onedir --windowed --onefile --noconsole --hidden-import=mido.backends.rtmidi --name "MA3_MIDI_Controller" midi-ma3-encoder.py```
