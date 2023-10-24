from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QFileDialog, QComboBox, QProgressBar, QLabel, QHBoxLayout
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QKeySequence, QShortcut

import sys, os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide' # hide the pygame banner
import pyaudio
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
        background-color: #444;
        border: 1px solid #666;
        border-radius: 4px;
        padding: 1px;
    }

    QProgressBar::chunk {
        background-color: #0078D7;
        border-radius: 4px;
    }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.audio = pyaudio.PyAudio()
        self.selected_device_index = None
        self.stream = None
        self.bit_depth = pyaudio.paInt16 # might have to update audio_callback if not 16 bit
        self.sample_rate = 96000
        self.channels = 1
        self.recording = False
        self.selected_directory = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DesktopLocation)

        self.setWindowTitle("Simple Edit-as-you-go Sound Recorder")
        self.setFixedSize(650, 350)

        # Create a QPushButton and connect it to the select_directory method
        button = QPushButton("Select Directory")
        button.pressed.connect(self.select_directory)
        
        self.target_dir_lbl = QLabel(f"Session Directory: {self.selected_directory}")
        self.target_dir_lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        
        # Create a QSpacerItem for vertical spacing
        spacer = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        # simple quality label
        label = QLabel("Quality: 48 kHz / 128 kbps | 24 Bits")
        label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        
        # Create a QComboBox for audio input devices
        self.audio_input_combo = QComboBox()
        self.audio_input_combo.addItem("None")  # Default item
        self.populate_audio_input_devices()
        self.audio_input_combo.setCurrentIndex(0)  # Set "None" as the initial selection
        
        # Create a QProgressBar for the audio meter
        self.audio_meter = QProgressBar()
        self.audio_meter.setValue(0)
        self.audio_meter.setOrientation(QtCore.Qt.Horizontal)
        
        # start session button
        self.start_button = QPushButton("Start Recording Session")
        self.start_button.pressed.connect(self.toggle_recording)
        self.start_button.setEnabled(False)
        
        # Create a layout for the buttons at the bottom
        button_layout = QHBoxLayout()
        
        finish_good_take_button = QPushButton("Finish Good Take")
        finish_bad_take_button = QPushButton("Finish Bad Take")
        
         # Add the buttons to the layout
        button_layout.addWidget(finish_good_take_button)
        button_layout.addWidget(finish_bad_take_button)
        
        # layout all UI
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(button)
        layout.addWidget(self.target_dir_lbl)
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
        self.f10_shortcut = QShortcut(QKeySequence(SESS_START_KEY), self)
        self.f10_shortcut.activated.connect(self.handle_f10_key_press)
        
        self.f11_shortcut = QShortcut(QKeySequence(GOOD_TAKE_KEY), self)
        self.f11_shortcut.activated.connect(self.handle_f10_key_press) # update this
        
        self.f12_shortcut = QShortcut(QKeySequence(BAD_TAKE_KEY), self)
        self.f12_shortcut.activated.connect(self.handle_f10_key_press) # update this
    
    def handle_f10_key_press(self):
        print("F10 (or F11 or F12) key pressed")
        pymixer.music.load(BAD_TAKE_SND)
        pymixer.music.play()
    
    def select_directory(self):
        self.selected_directory = QFileDialog.getExistingDirectory(self, "Select Directory", self.selected_directory, QFileDialog.ShowDirsOnly)
        if self.selected_directory:
            print(f"Selected directory: {self.selected_directory}")
            self.target_dir_lbl.setText(f"Session Directory: {self.selected_directory}")
        else:
            print("No directory selected.")
    
    def populate_audio_input_devices(self):
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        input_devices = []

        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                input_devices.append({
                    'index': i,
                    'name': device_info.get('name'),
                    'details': f"Index: {i}, Name: {device_info.get('name')}",
                })

        if input_devices:
            for device in input_devices:
                self.audio_input_combo.addItem(device['details'])
            self.audio_input_combo.currentIndexChanged.connect(self.select_audio_device)
        else:
            self.audio_input_combo.addItem("No audio input devices found")
    
    def select_audio_device(self):
        self.selected_device_index = self.audio_input_combo.currentIndex()
        if self.selected_device_index >= 0:
            self.start_audio_stream()
            print(f"Selected audio input device: {self.audio_input_combo.currentText()}")
        else:
            print("No audio input device selected")
            
    def start_audio_stream(self):
        print('start audio stream')
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()

        if self.selected_device_index is not None:
            self.stream = self.audio.open(
                format=self.bit_depth,
                channels=self.channels,
                rate=self.sample_rate,  # Set the sample rate
                input=True,
                input_device_index=self.selected_device_index - 1,  # Adjust the index for "None" item
                frames_per_buffer=1024,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()

    def toggle_recording(self):
        if self.recording:
            self.recording = False
            self.start_button.setText("Start Recording")
            self.stop_recording()
        else:
            self.recording = True
            self.start_button.setText("Stop Recording")
            self.start_recording()
    
    def start_recording(self):
        if not self.selected_directory:
            print("No directory selected for saving recordings.")
            return

        self.recording_file = wave.open(f"{self.selected_directory}/recording.wav", "wb")
        self.recording_file.setnchannels(self.channels)
        self.recording_file.setsampwidth(2)
        self.recording_file.setframerate(self.sample_rate)
        self.recording_buffer = []

    def stop_recording(self):
        if hasattr(self, "recording_file"):
            self.recording_file.writeframes(b''.join(self.recording_buffer))
            self.recording_file.close()

    def audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            print("Audio input underflow!")

        audio_data = np.frombuffer(in_data, dtype=np.int16)
        audio_level = np.max(np.abs(audio_data))  # Calculate the audio level

        # Update the audio meter
        self.audio_meter.setValue(audio_level)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    app.exec()