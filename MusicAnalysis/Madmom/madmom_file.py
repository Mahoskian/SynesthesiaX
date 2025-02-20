import os
import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Import Madmom modules for analysis
from madmom.audio.signal import Signal, FramedSignal
from madmom.audio.spectrogram import Spectrogram
from madmom.features.beats import BeatTrackingProcessor, RNNBeatProcessor
from madmom.features.onsets import OnsetPeakPickingProcessor, RNNOnsetProcessor
from madmom.features.tempo import TempoEstimationProcessor

# Define the file path (adjust as needed)
base_dir = os.path.dirname(os.path.abspath(__file__))
audio_file = os.path.join(base_dir, "music_files", "Ternion Sound - Artifice (Buunshin Remix).wav")
if not os.path.exists(audio_file):
    raise FileNotFoundError(f"File not found: {audio_file}")

# ---------- Analysis using Madmom ----------

# 1. Load the Audio and Create Waveform Data
# Load stereo audio; we use num_channels=2 to get the raw stereo data.
signal_stereo = Signal(audio_file, num_channels=2)
audio_data = signal_stereo.astype(np.float32)
# Create a mono version by averaging the two channels.
if audio_data.ndim > 1 and audio_data.shape[1] == 2:
    mono_audio = np.mean(audio_data, axis=1)
else:
    mono_audio = audio_data
duration = len(mono_audio) / signal_stereo.sample_rate
time_axis = np.linspace(0, duration, num=len(mono_audio))

# 2. Beat and Onset Analysis
proc_beats = RNNBeatProcessor()
beat_activation = proc_beats(audio_file)
beats = BeatTrackingProcessor(fps=100)(beat_activation)

proc_onsets = RNNOnsetProcessor()
onset_activation = proc_onsets(audio_file)
onsets = OnsetPeakPickingProcessor(fps=100)(onset_activation)

# 3. Tempo Estimation
proc_tempo = TempoEstimationProcessor(fps=100)
tempo_estimates = proc_tempo(beat_activation)
global_tempo = np.mean(tempo_estimates)

# 4. Spectrogram Analysis
# Load the audio as mono for spectrogram computation.
signal_mono = Signal(audio_file, num_channels=1)
frame_size = 2048
hop_size = 1024
framed_signal = FramedSignal(signal_mono, frame_size=frame_size, hop_size=hop_size)
spec = Spectrogram(framed_signal)
# Convert the spectrogram to decibels.
epsilon = 1e-6
spec_db = 20 * np.log10(spec + epsilon)

# ---------- PyQtGraph Plotting ----------

# Create the application and window
app = pg.mkQApp()
win = pg.GraphicsLayoutWidget(title="Audio Analysis")
win.resize(1600, 1200)

# Row 1, spanning both columns: Waveform with Beat and Onset markers
waveform_plot = win.addPlot(row=0, col=0, colspan=2, title="Audio Waveform with Beats and Onsets")
waveform_plot.setLabel('left', "Amplitude")
waveform_plot.setLabel('bottom', "Time (s)")
waveform_curve = waveform_plot.plot(time_axis, mono_audio, pen=pg.mkPen('w', width=1))
# Add vertical lines for beats (red dashed) and onsets (blue dotted)
for idx, beat in enumerate(beats):
    line = pg.InfiniteLine(pos=beat, angle=90, pen=pg.mkPen('r', style=QtCore.Qt.DashLine))
    waveform_plot.addItem(line)
for idx, onset in enumerate(onsets):
    line = pg.InfiniteLine(pos=onset, angle=90, pen=pg.mkPen('b', style=QtCore.Qt.DotLine))
    waveform_plot.addItem(line)

# Row 2, Column 0: Activation Functions
activation_plot = win.addPlot(row=1, col=0, title="Activation Functions")
activation_plot.setLabel('left', "Activation")
activation_plot.setLabel('bottom', "Frame Index")
activation_plot.plot(beat_activation, pen=pg.mkPen('r', width=1), name="Beat Activation")
activation_plot.plot(onset_activation, pen=pg.mkPen('b', width=1), name="Onset Activation")
activation_plot.addLegend()

# Row 2, Column 1: Tempo Information (Text)
tempo_plot = win.addPlot(row=1, col=1, title="Tempo Information")
tempo_plot.hideAxis('bottom')
tempo_plot.hideAxis('left')
tempo_text = f"Estimated Global Tempo:\n{global_tempo:.2f} BPM\n\nBeats Detected: {len(beats)}\nOnsets Detected: {len(onsets)}"
text_item = pg.TextItem(text=tempo_text, anchor=(0.5, 0.5), color='k')
tempo_plot.addItem(text_item)
# Position the text item roughly in the center of the plot
text_item.setPos(0.5, 0.5)

# Row 3, spanning both columns: Spectrogram in dB
spectrogram_plot = win.addPlot(row=2, col=0, colspan=2, title="Spectrogram (dB)")
spectrogram_plot.setLabel('left', "Frequency Bands")
spectrogram_plot.setLabel('bottom', "Time Frames")
# Create an ImageItem and set its image to the transposed spectrogram (so that time is x-axis)
spectrogram_img = pg.ImageItem(image=spec_db.T)
spectrogram_plot.addItem(spectrogram_img)
spectrogram_plot.setAspectLocked(False)
# Add a color scale bar (optional, using built-in functionality)
colormap = pg.colormap.get('magma')
hist = pg.HistogramLUTItem()
hist.setImageItem(spectrogram_img)
win.addItem(hist, row=2, col=2)

win.show()
sys.exit(app.exec_())
