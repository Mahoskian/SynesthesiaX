import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import sounddevice as sd
import threading
from madmom.audio.signal import Signal, FramedSignal
from madmom.audio.spectrogram import Spectrogram
from madmom.features.beats import BeatTrackingProcessor, RNNBeatProcessor

# Settings
SAMPLE_RATE = 44100
CHANNELS = 2
BUFFER_DURATION = 5  # seconds
BUFFER_SIZE = SAMPLE_RATE * BUFFER_DURATION  # total samples per channel
VIRTUAL_CABLE_INDEX = 2  # your device index

# Global audio buffer and index (ring-buffer approach)
audio_buffer = np.zeros((BUFFER_SIZE, CHANNELS), dtype=np.float32)
buffer_lock = threading.Lock()
buffer_index = 0

def audio_callback(indata, frames, time, status):
    global audio_buffer, buffer_index
    if status:
        print("🔴 Stream Error:", status)
    with buffer_lock:
        end_index = buffer_index + frames
        if end_index < BUFFER_SIZE:
            audio_buffer[buffer_index:end_index] = indata.copy()
        else:
            first_part = BUFFER_SIZE - buffer_index
            audio_buffer[buffer_index:] = indata[:first_part].copy()
            audio_buffer[:end_index % BUFFER_SIZE] = indata[first_part:].copy()
        buffer_index = (buffer_index + frames) % BUFFER_SIZE

# Start the input stream with a large blocksize to reduce callback frequency
stream = sd.InputStream(
    callback=audio_callback,
    device=VIRTUAL_CABLE_INDEX,
    channels=CHANNELS,
    samplerate=SAMPLE_RATE,
    blocksize=16384
)
stream.start()

# Set up PyQtGraph window with a GraphicsLayoutWidget
app = QtGui.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Audio Analysis")
win.resize(1000, 800)
win.setWindowTitle('Real-Time Audio Analysis')

# Create three plots:
# 1. Waveform Plot
waveform_plot = win.addPlot(title="Real-Time Waveform")
waveform_plot.setLabel('left', "Amplitude")
waveform_plot.setLabel('bottom', "Time (s)")
waveform_curve = waveform_plot.plot(pen='w')

# 2. Spectrogram Plot
win.nextRow()
spectrogram_plot = win.addPlot(title="Real-Time Spectrogram (dB)")
spectrogram_plot.setLabel('left', "Frequency Bands")
spectrogram_plot.setLabel('bottom', "Time Frames")
# Use an ImageItem to display the spectrogram
spectrogram_img = pg.ImageItem()
spectrogram_plot.addItem(spectrogram_img)
spectrogram_plot.setAspectLocked(False)

# 3. Beat Activation Plot
win.nextRow()
beat_plot = win.addPlot(title="Beat Activation")
beat_plot.setLabel('left', "Activation")
beat_plot.setLabel('bottom', "Frame Index")
beat_curve = beat_plot.plot(pen='r')

def update():
    global audio_buffer
    # Copy the current buffer data (with thread lock)
    with buffer_lock:
        current_audio = audio_buffer.copy()
    
    # Create a time axis for the current BUFFER_DURATION
    time_axis = np.linspace(0, BUFFER_DURATION, num=BUFFER_SIZE)
    
    # Create a mono signal by averaging the two channels
    mono_audio = np.mean(current_audio, axis=1)
    
    # ---- Update Waveform ----
    waveform_curve.setData(time_axis, mono_audio)
    
    # ---- Update Spectrogram ----
    # Create a Signal from the mono audio
    sig = Signal(mono_audio, sample_rate=SAMPLE_RATE)
    frame_size = 2048
    hop_size = 1024
    framed_signal = FramedSignal(sig, frame_size=frame_size, hop_size=hop_size)
    spec = Spectrogram(framed_signal)
    # Convert the spectrogram to decibels
    epsilon = 1e-6
    spec_db = 20 * np.log10(spec + epsilon)
    # Update the image; transpose so time is on x-axis
    spectrogram_img.setImage(spec_db.T, autoLevels=True)
    
    # ---- Update Beat Activation ----
    try:
        proc_beats = RNNBeatProcessor()
        # Depending on the RNNBeatProcessor implementation, it might expect a file or a numpy array.
        # Here, we try passing the current mono audio.
        beat_activation = proc_beats(mono_audio)
        beat_curve.setData(beat_activation)
    except Exception as e:
        print("Beat detection error:", e)

# Create a QTimer to update the plots every 1000 ms (adjust as needed)
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(1000)

if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()