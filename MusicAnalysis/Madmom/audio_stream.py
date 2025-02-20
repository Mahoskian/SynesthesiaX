import sounddevice as sd
import numpy as np

VIRTUAL_CABLE_INDEX = 2  # Voicemeeter Out B1 (VB-Audio Vo)
SAMPLE_RATE = 44100

def audio_callback(indata, frames, time, status):
    if status:
        print("🔴 Stream Error:", status)
    volume = np.mean(np.abs(indata))
    print(f"🔊 Real-time audio level: {volume:.6f}")

print("🎧 Listening to Voicemeeter Out B1... Press Ctrl+C to stop.")
with sd.InputStream(callback=audio_callback, device=VIRTUAL_CABLE_INDEX, channels=2, samplerate=SAMPLE_RATE):
    while True:
        pass  # Keep listening
