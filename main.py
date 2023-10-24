import shutil
from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QFileDialog, QComboBox, QProgressBar, QLabel, QHBoxLayout
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QKeySequence, QShortcut, QIcon

import sys, os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide' # hide the pygame banner
import pyaudio
import math
import time
import numpy as np
import wave
from pygame import mixer as pymixer

def resourcePath(relativePath):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")

    return os.path.join(basePath, relativePath)

pymixer.init()

GOOD_TAKE_SND = resourcePath("audio/good.mp3")
BAD_TAKE_SND = resourcePath("audio/bad.mp3")
SESS_START_SND = resourcePath("audio/session_start.mp3")

SESS_START_KEY = QtCore.Qt.Key_F10
GOOD_TAKE_KEY = QtCore.Qt.Key_F11
BAD_TAKE_KEY = QtCore.Qt.Key_F12

DISTORTION_THRESHOLD = 0.8

KEEP_DIR = "recorder-keep"
DISCARD_DIR = "recorder-discard"

APP_TITLE = "Edit-as-you-go Sound Recorder"
SESSION_DIR_PATH_TXT = "Session Directory: {0}"
GOOD_TAKE_PATH_TXT = f"    - Good takes: {{0}}/{KEEP_DIR}"
BAD_TAKE_PATH_TXT = f"    - Bad takes: {{0}}/{DISCARD_DIR}"



# style the app, win 10 dark theme
dark_stylesheet = """
    QWidget {
        background-color: #333;
        color: #FFF;
    }

    QPushButton {
        background-color: #0078D7;
        color: #FFF;
        border: 1px solid #0078D7;
        border-radius: 4px;
        padding: 6px 12px;
    }

    QPushButton:hover {
        background-color: #0058A1;
    }

    QPushButton:pressed {
        background-color: #003971;
    }

    QPushButton:disabled {
        background-color: #777777;
        color: #999999;
        border: 1px solid #777777;
    }

    QComboBox {
        background-color: #444;
        color: #FFF;
        border: 1px solid #666;
        border-radius: 4px;
        padding: 2px 10px;
    }

    QProgressBar {
        background-color: #222;
        border: 1px solid #666;
        border-radius: 4px;
        padding: 1px;
        height: 3px;
    }

    QProgressBar::chunk {
        background-color: #00cc00;
        border-radius: 4px;
    }
"""

class MainWindow(QMainWindow):
    audio_level_updated = QtCore.Signal(int)
    
    def __init__(self):
        super().__init__()

        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.bit_depth = pyaudio.paInt16 # might have to update audio_callback if not 16 bit
        self.sample_rate = 96000
        self.channels = 1
        self.recording = False
        self.selected_directory = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation)
        self.selected_device_index = None

        self.setWindowTitle(APP_TITLE)
        self.setFixedSize(650, 350)
        icon = QIcon("icon.png")
        self.setWindowIcon(icon)

        # Create a QPushButton and connect it to the select_directory method
        self.select_dir_btn = QPushButton("Select Directory")
        self.select_dir_btn.pressed.connect(self.select_directory)
        
        self.target_dir_lbl = QLabel(SESSION_DIR_PATH_TXT.format(self.selected_directory))
        self.target_dir_lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.good_take_lbl = QLabel(GOOD_TAKE_PATH_TXT.format(self.selected_directory))
        self.good_take_lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.good_take_lbl.setFixedHeight(14)
        self.bad_take_lbl = QLabel(BAD_TAKE_PATH_TXT.format(self.selected_directory))
        self.bad_take_lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.bad_take_lbl.setFixedHeight(14)
        
        # Create a QSpacerItem for vertical spacing
        spacer = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        # simple quality label
        label = QLabel("Quality: 48 kHz / 128 kbps | 24 Bits")
        label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        
        # Create a QComboBox for audio input devices
        self.audio_input_combo = QComboBox()
        self.audio_input_combo.addItem("None", -1)  # Default item
        self.audio_input_combo.setCurrentIndex(0)  # Set "None" as the initial selection
        
        # Create a QProgressBar for the audio meter
        self.audio_meter = QProgressBar()
        self.audio_meter.setValue(0)
        self.audio_meter.setRange(49, 85)
        self.audio_meter.setSizeIncrement(1, 1)
        self.audio_meter.setTextVisible(False)
        self.audio_meter.setOrientation(QtCore.Qt.Horizontal)
        
        # connect signal to function
        self.audio_level_updated.connect(self.update_audio_meter)
        
        # start session button
        self.start_button = QPushButton("Start Session (F10)")
        self.start_button.pressed.connect(self.toggle_recording)
        
        # Create a layout for the buttons at the bottom
        button_layout = QHBoxLayout()
        
        self.finish_good_take_button = QPushButton("Finish Good Take (F11)")
        self.finish_good_take_button.pressed.connect(self.finish_good_take)
        self.finish_bad_take_button = QPushButton("Finish Bad Take (F12)")
        self.finish_bad_take_button.pressed.connect(self.finish_bad_take)
        
         # Add the buttons to the layout
        button_layout.addWidget(self.finish_good_take_button)
        button_layout.addWidget(self.finish_bad_take_button)
        
        # layout all UI
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.select_dir_btn)
        layout.addWidget(self.target_dir_lbl)
        layout.addWidget(self.good_take_lbl)
        layout.addWidget(self.bad_take_lbl)
        layout.addItem(spacer) 
        layout.addWidget(self.audio_input_combo)
        layout.addWidget(label)
        layout.addWidget(self.audio_meter)
        layout.addWidget(self.start_button)
        layout.addLayout(button_layout)
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Apply styles and show
        self.setStyleSheet(dark_stylesheet)
        self.show()
        
        # Initialize audio processing
        self.start_audio_stream()
        
        # keyboard shortcuts (connect f18 = start, f19 = good take, f20 = bad take)
        f10_shortcut = QShortcut(QKeySequence(SESS_START_KEY), self)
        f10_shortcut.activated.connect(self.start_button.click)
        
        f11_shortcut = QShortcut(QKeySequence(GOOD_TAKE_KEY), self)
        f11_shortcut.activated.connect(self.finish_good_take_button.click) # update this
        
        f12_shortcut = QShortcut(QKeySequence(BAD_TAKE_KEY), self)
        f12_shortcut.activated.connect(self.finish_bad_take_button.click) # update this
        
        self.populate_audio_input_devices()
        self.update_controls()
    
    def update_controls(self):
        self.start_button.setEnabled(self.selected_device_index is not None and self.select_audio_device != 0)
        self.audio_input_combo.setEnabled(not self.recording)
        self.select_dir_btn.setEnabled(not self.recording)
        self.finish_good_take_button.setEnabled(self.recording)
        self.finish_bad_take_button.setEnabled(self.recording)
    
    def update_audio_meter(self, audio_level):
        self.audio_meter.setValue(audio_level)
    
    def select_directory(self):
        self.selected_directory = QFileDialog.getExistingDirectory(self, "Select Directory", self.selected_directory, QFileDialog.ShowDirsOnly)
        if self.selected_directory:
            print(f"Selected directory: {self.selected_directory}")
            self.target_dir_lbl.setText(SESSION_DIR_PATH_TXT.format(self.selected_directory))
            self.good_take_lbl.setText(GOOD_TAKE_PATH_TXT.format(self.selected_directory))
            self.bad_take_lbl.setText(BAD_TAKE_PATH_TXT.format(self.selected_directory))
        else:
            print("No directory selected.")
        
        self.update_controls()
    
    def populate_audio_input_devices(self):
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        input_devices = []

        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                input_devices.append({
                    'index': device_info.get('index'),
                    'name': device_info.get('name'),
                    'details': f"Index: {i}, Name: {device_info.get('name')}",
                })

        if input_devices:
            for device in input_devices:
                self.audio_input_combo.addItem(device['name'], device['index'])
            self.audio_input_combo.currentIndexChanged.connect(self.select_audio_device)
        else:
            self.audio_input_combo.addItem("No audio input devices found", -1)
        
        self.update_controls()
    
    def select_audio_device(self):
        self.selected_device_index = self.audio_input_combo.currentData()
        if self.selected_device_index < 0:
            print('No audio input device selected')
        else:
            print(f"Selected audio input device: {self.audio_input_combo.currentText()}")
            self.start_audio_stream()
        
        self.update_controls()
            
    def start_audio_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()

        if self.selected_device_index is not None and self.selected_device_index >= 0:
            self.stream = self.audio.open(
                format=self.bit_depth,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.selected_device_index,
                frames_per_buffer=1024,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()

    def finish_good_take(self):
        self.stop_recording(True)
        pymixer.music.load(GOOD_TAKE_SND)
        pymixer.music.play()
        self.start_recording()

    def finish_bad_take(self):
        self.stop_recording(False)
        pymixer.music.load(BAD_TAKE_SND)
        pymixer.music.play()
        self.start_recording()

    def toggle_recording(self):
        if self.recording:
            self.recording = False
            self.start_button.setText("Start Session")
            if hasattr(self, "recording_file"):
                self.recording_file.close() # close the recording file
                os.unlink(f"{self.selected_directory}/recording_temp.wav") # delete scraps
            print('Session Ended')
        else:
            self.recording = True
            self.start_button.setText("End Session")
            pymixer.music.load(SESS_START_SND)
            pymixer.music.play()
            self.start_recording()
            print('Session Started')
        
        self.update_controls()
    
    def start_recording(self):
        if not self.selected_directory:
            print("No directory selected for saving recordings.")
            return

        self.recording_file = wave.open(f"{self.selected_directory}/recording_temp.wav", "wb")
        self.recording_file.setnchannels(self.channels)
        self.recording_file.setsampwidth(2)
        self.recording_file.setframerate(self.sample_rate)
        self.recording_buffer = []

    def stop_recording(self, wasGoodTake):
        if hasattr(self, "recording_file"):
            self.recording_file.writeframes(b''.join(self.recording_buffer))
            self.recording_file.close()
            
            # move file to keep or discard based on how we stopped the recording
            if wasGoodTake:
                directory_path = f"{self.selected_directory}/{KEEP_DIR}"
            else:
                directory_path = f"{self.selected_directory}/{DISCARD_DIR}"
                
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            
            try:
                current_time_seconds = int(time.time())
                shutil.move(f"{self.selected_directory}/recording_temp.wav", os.path.join(directory_path, f"track_{current_time_seconds}.wav"))
                print(f"Moved '{self.selected_directory}/recording_temp.wav' to '{directory_path}'")
            except FileNotFoundError:
                print(f"Source file '{self.selected_directory}/recording_temp.wav' not found.")
            except shutil.Error as e:
                print(f"Error while moving the file: {e}")

    def audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            print("Audio input underflow!") 

        audio_data = np.frombuffer(in_data, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))  # Calculate RMS
        audio_level_dB = 20 * math.log10(rms)  # Convert to dB
        # audio_level = np.max(np.abs(audio_data))  # Calculate the audio level

        peak_amplitude = np.max(np.abs(audio_data)) / 32767.0  # Normalize to the range [-1.0, 1.0]
        if peak_amplitude > DISTORTION_THRESHOLD:
            print("Audio distortion detected!")

        if self.recording:
            self.recording_buffer.append(in_data)

        # Update the audio meter
        # print(audio_level_dB)
        self.audio_level_updated.emit(audio_level_dB)
        
        return None, pyaudio.paContinue


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    app.exec()