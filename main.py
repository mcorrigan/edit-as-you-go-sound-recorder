import shutil
from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QFileDialog, QComboBox, QProgressBar, QLabel, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QKeySequence, QShortcut, QIcon
from PySide6.QtCore import QTimer, QTime

import sys, os, ctypes
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide' # hide the pygame banner
import pyaudio
import math
import time
import numpy as np
import wave
from pygame import mixer as pymixer

VERSION = '0.2.1'

def resourcePath(relativePath):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")

    return os.path.join(basePath, relativePath)

pymixer.init()
ui_channel = pymixer.Channel(0)
replay_channel = pymixer.Channel(1)
record_start_channel = pymixer.Channel(2)

GOOD_TAKE_SND = pymixer.Sound(resourcePath("audio/good.mp3"))
BAD_TAKE_SND = pymixer.Sound(resourcePath("audio/bad.mp3"))
SESS_START_SND = pymixer.Sound(resourcePath("audio/session_start.mp3"))
SESS_END_SND = pymixer.Sound(resourcePath("audio/session_end.mp3"))

SESS_START_KEY = QtCore.Qt.Key_F10
GOOD_TAKE_KEY = QtCore.Qt.Key_F11
BAD_TAKE_KEY = QtCore.Qt.Key_F12
REPLAY_TAKE_KEY = QtCore.Qt.Key_F13

DISTORTION_THRESHOLD = 0.8

KEEP_DIR = "recorder-keep"
DISCARD_DIR = "recorder-discard"

APP_TITLE = "Edit-as-you-go Sound Recorder"
SESSION_DIR_PATH_TXT = "Session Directory: {0}"
GOOD_TAKE_PATH_TXT = f"    - Good takes: {{0}}/{KEEP_DIR}"
BAD_TAKE_PATH_TXT = f"    - Bad takes: {{0}}/{DISCARD_DIR}"

TEMP_AUDIOFILE_NAME = '__eaygsr_recording_temp.wav'


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
        self.bit_depth = pyaudio.paInt32
        self.sample_rate = 96000
        self.channels = 1
        self.recording = False
        self.replaying = False
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
        
        # Create a QComboBox for audio input devices
        self.audio_input_combo = QComboBox()
        self.audio_input_combo.addItem("None", -1)  # Default item
        self.audio_input_combo.setCurrentIndex(0)  # Set "None" as the initial selection
        self.audio_input_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        
        # Create a QProgressBar for the audio meter
        self.audio_meter = QProgressBar()
        self.audio_meter.setValue(0)
        self.audio_meter.setRange(49, 85)
        self.audio_meter.setSizeIncrement(1, 1)
        self.audio_meter.setTextVisible(False)
        self.audio_meter.setOrientation(QtCore.Qt.Vertical)
        self.audio_meter.setFixedSize(20, 60)
        
        # simple quality label
        quality_label = QLabel("Quality: 96 kHz | 32 Bit")
        quality_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        
        # Create a label to display the session time
        self.session_time_label = QLabel("Take Duration: 00:00")
        self.session_time_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        
        # Create a QTimer to update the session time label
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.update_session_time)
        
        inputs_left_layout = QVBoxLayout()
        inputs_left_layout.addWidget(self.audio_input_combo)
        inputs_left_layout.addWidget(quality_label)
        inputs_left_layout.addWidget(self.session_time_label)
        
        inputs_layout = QHBoxLayout()
        inputs_layout.addLayout(inputs_left_layout, 1)
        inputs_layout.addWidget(self.audio_meter)
        
        # connect signal to function
        self.audio_level_updated.connect(self.update_audio_meter)
        
        # start session button
        self.start_button = QPushButton("Start Session (F10)")
        self.start_button.pressed.connect(self.toggle_recording)
        
        self.finish_good_take_button = QPushButton("Finish Good Take (F11)")
        self.finish_good_take_button.pressed.connect(self.finish_good_take)
        self.finish_bad_take_button = QPushButton("Finish Bad Take (F12)")
        self.finish_bad_take_button.pressed.connect(self.finish_bad_take)
        self.replay_last_take_button = QPushButton("Replay Last Take (F13)")
        self.replay_last_take_button.pressed.connect(self.replay_last_take)
        
         # Add the buttons to the layout
         # Create a layout for the buttons at the bottom
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.finish_good_take_button)
        button_layout.addWidget(self.finish_bad_take_button)
        button_layout.addWidget(self.replay_last_take_button)
        
        # version label
        version_label = QLabel(f"Version: {VERSION}")
        version_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        
        version_layout = QHBoxLayout()
        version_layout.addStretch(1)  # Add a stretchable space on the left
        version_layout.addWidget(version_label)
        
        # layout all UI
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.select_dir_btn)
        layout.addWidget(self.target_dir_lbl)
        layout.addWidget(self.good_take_lbl)
        layout.addWidget(self.bad_take_lbl)
        layout.addItem(spacer) 
        layout.addLayout(inputs_layout)
        layout.addWidget(self.start_button)
        layout.addLayout(button_layout)
        layout.addLayout(version_layout)
        
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Apply styles and show
        self.setStyleSheet(dark_stylesheet)
        self.show()
        
        # Initialize audio processing
        self.start_audio_stream()
        
        # keyboard shortcuts
        session_start_key_shortcut = QShortcut(QKeySequence(SESS_START_KEY), self)
        session_start_key_shortcut.activated.connect(self.start_button.click)
        
        goodtake_key_shortcut = QShortcut(QKeySequence(GOOD_TAKE_KEY), self)
        goodtake_key_shortcut.activated.connect(self.finish_good_take_button.click)
        
        badtake_key_shortcut = QShortcut(QKeySequence(BAD_TAKE_KEY), self)
        badtake_key_shortcut.activated.connect(self.finish_bad_take_button.click)
        
        replay_key_shortcut = QShortcut(QKeySequence(REPLAY_TAKE_KEY), self)
        replay_key_shortcut.activated.connect(self.replay_last_take_button.click)
        
        self.populate_audio_input_devices()
        self.update_controls()
        self.handle_any_file_leftovers()
    
    def update_session_time(self):
        # Update the session time label with the elapsed time
        current_time = QTime.currentTime()
        elapsed_time = self.start_time.msecsTo(current_time)
        self.session_time_label.setText(f"Take Duration: {elapsed_time // 60000:02d}:{(elapsed_time // 1000) % 60:02d}")
    
    def handle_any_file_leftovers(self):
        file_path = f"{self.selected_directory}/{TEMP_AUDIOFILE_NAME}"
        if os.path.exists(file_path):
            # The temporary audio file exists, which could be due to a program crash.
            # check if file length is zero, if so just delete it
            if os.path.getsize(file_path) == 0:
                print("Temporary audio file is empty. Deleting it.")
                os.remove(file_path)
            else:
                # Prompt the user to keep or discard it.
                response = self.prompt_for_keep_or_discard()

                if response == "keep":
                    # Move the file to the "keep" directory
                    self.save_recording(True)
                elif response == "discard":
                    # Move the file to the "discard" directory
                    self.save_recording(False)
                elif response == 'delete':
                    # Delete the file completely
                    os.remove(file_path)
                else:
                    # we should not get here...
                    pass
    
    def prompt_for_keep_or_discard(self):
        # Create a custom QMessageBox with customized button labels.
        msg_box = QMessageBox()
        
        msg_box.setWindowTitle("Temporary Recording File Found")
        message = f"A temporary audio file was found in '{self.selected_directory}'. Do you want to place it in the keep folder, discard folder, or delete it entirely?"
        msg_box.setText(message)

        # Create custom buttons with desired labels.
        keep_button = msg_box.addButton("Keep Folder", QMessageBox.AcceptRole)
        discard_button = msg_box.addButton("Discard Folder", QMessageBox.DestructiveRole)
        delete_button = msg_box.addButton("Delete", QMessageBox.ActionRole)
        
        msg_box.exec()

        if msg_box.clickedButton() == keep_button:
            return "keep"
        elif msg_box.clickedButton() == discard_button:
            return "discard"
        elif msg_box.clickedButton() == delete_button:
            return "delete"
        else:
            return "skip"
    
    def display_message(self, title, msg):
        message_box = QMessageBox()
        message_box.setWindowTitle(title)
        message_box.setText(msg)
        message_box.setIcon(QMessageBox.Information)
        message_box.setStandardButtons(QMessageBox.Ok)
        message_box.exec()
    
    def update_controls(self):
        has_device = self.selected_device_index is not None and self.selected_device_index > -1
        self.start_button.setEnabled(has_device)
        self.audio_input_combo.setEnabled(not self.recording and not self.replaying)
        self.select_dir_btn.setEnabled(not self.recording and not self.replaying)
        self.finish_good_take_button.setEnabled(self.recording or self.replaying)
        self.finish_bad_take_button.setEnabled(self.recording or self.replaying)
        self.replay_last_take_button.setEnabled(self.recording)
    
    def update_audio_meter(self, audio_level):
        self.audio_meter.setValue(audio_level)
    
    def select_directory(self):
        temp_selected_dir = QFileDialog.getExistingDirectory(self, "Select Directory", self.selected_directory, QFileDialog.ShowDirsOnly)
        if temp_selected_dir == '':
            return
        
        if os.access(temp_selected_dir, os.W_OK):
            self.selected_directory = temp_selected_dir
            self.handle_any_file_leftovers()
        else:
            print(f"Write permission error for directory {temp_selected_dir}")
            self.display_message("Permission Error", f"The application does not have permission to save files in: {temp_selected_dir}. \nPlease choose a new location.")
            return 
        
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
            self.display_message("No Input Devices Found", "This application requires one or more input devices be available on the machine.")
        
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

    def replay_last_take(self):
        self.stop_recording()
        self.replay_take()
        self.update_controls()

    def finish_good_take(self):
        if self.replaying:
            self.stop_replaying()
        if self.recording:
            self.stop_recording()
        self.save_recording(True)
        ui_channel.play(GOOD_TAKE_SND)
        while ui_channel.get_busy():
            pass
        self.start_recording()
        self.update_controls()

    def finish_bad_take(self):
        if self.replaying:
            self.stop_replaying()
        if self.recording:
            self.stop_recording()
        self.save_recording(False)
        ui_channel.play(BAD_TAKE_SND)
        while ui_channel.get_busy():
            pass
        self.start_recording()
        self.update_controls()

    def replay_take(self):
        self.replaying = True
        replay_channel.stop()
        snd = pymixer.Sound(f"{self.selected_directory}/{TEMP_AUDIOFILE_NAME}")
        replay_channel.play(snd, 99)        

    def stop_replaying(self):
        replay_channel.stop()
        self.replaying = False

    def end_session(self):
        self.stop_recording()
        self.stop_replaying()
        os.unlink(f"{self.selected_directory}/{TEMP_AUDIOFILE_NAME}") # delete scraps
        ui_channel.play(SESS_END_SND)
        self.session_time_label.setText(f"Take Duration: 00:00")

    def toggle_recording(self):
        if self.recording or self.replaying:
            # end the session
            self.start_button.setText("Start Session")
            self.start_button.setStyleSheet("QPushButton { background-color: #0078D7; border: 1px solid #0078D7; }")
            self.end_session()
            print('Session Ended')
        else:
            # start the session
            self.start_button.setText("End Session")
            self.start_button.setStyleSheet("QPushButton { background-color: #D32F2F; border: 1px solid red; }")
            self.start_recording()
            print('Session Started')
        
        self.update_controls()
    
    def start_recording(self):
        if not self.selected_directory:
            print("No directory selected for saving recordings.")
            return

        record_start_channel.play(SESS_START_SND)

        file_path = f"{self.selected_directory}/{TEMP_AUDIOFILE_NAME}"
        self.recording_file = wave.open(file_path, "wb")
        self.recording_file.setnchannels(self.channels)
        self.recording_file.setsampwidth(4) # 4 for 32 bit audio
        self.recording_file.setframerate(self.sample_rate)
        self.recording_buffer = []
        self.recording = True
        
        self.set_hidden_attribute(file_path)
        
        self.session_timer.start(100)  # Update every 1 second
        self.start_time = QTime.currentTime()

    def stop_recording(self):
        if self.recording and hasattr(self, "recording_file"):
            self.recording_file.writeframes(b''.join(self.recording_buffer))
            self.recording_file.close()
        
        self.session_timer.stop()
        self.recording = False

    def save_recording(self, wasGoodTake):
        # move file to keep or discard based on how we stopped the recording
        if wasGoodTake:
            directory_path = f"{self.selected_directory}/{KEEP_DIR}"
        else:
            directory_path = f"{self.selected_directory}/{DISCARD_DIR}"
            
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        
        try:
            current_time_seconds = int(time.time())
            src_path = f"{self.selected_directory}/{TEMP_AUDIOFILE_NAME}"
            dest_path = os.path.join(directory_path, f"track_{current_time_seconds}.wav")
            shutil.move(src_path, dest_path)
            self.unset_hidden_attribute(dest_path) # make file visible again to the user
            print(f"Moved '{self.selected_directory}/{TEMP_AUDIOFILE_NAME}' to '{directory_path}'")
        except FileNotFoundError:
            print(f"Source file '{self.selected_directory}/{TEMP_AUDIOFILE_NAME}' not found.")
        except shutil.Error as e:
            print(f"Error while moving the file: {e}")
        

    def audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            print("Audio input underflow!") 

        audio_data = np.frombuffer(in_data, dtype=np.int32)
        rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float64)) / (2 ** 31)))
        audio_level_dB = 20 * math.log10(rms) # Convert to dB

        peak_amplitude = np.max(np.abs(audio_data)) / (2 ** 31)  # Normalize to the range [-1.0, 1.0]
        if peak_amplitude > DISTORTION_THRESHOLD:
            print("Audio distortion detected!")

        if self.recording:
            self.recording_buffer.append(in_data)
            
            # every 10 MB, flush the buffer to the temp file so we don't lose everything if we crash
            if len(self.recording_buffer) * len(in_data) >= 10 * 1024 * 1024:
                print('Flush audio to temp file')
                self.recording_file.writeframes(b''.join(self.recording_buffer))
                self.recording_buffer = []

        # Update the audio meter
        # print(audio_level_dB)
        self.audio_level_updated.emit(audio_level_dB)
        
        return None, pyaudio.paContinue

    def set_hidden_attribute(self, file_path):
        if os.name == 'nt':
            # On Windows, set the hidden attribute
            try:
                # FILE_ATTRIBUTE_HIDDEN = 2
                ctypes.windll.kernel32.SetFileAttributesW(file_path, 2)
            except Exception as e:
                print(f"Error setting hidden attribute: {e}")
        else:
            print("Setting file attributes is not supported on this platform.")

    def unset_hidden_attribute(self, file_path):
        if os.name == 'nt':
            # On Windows, remove the hidden attribute
            try:
                # FILE_ATTRIBUTE_NORMAL = 128
                ctypes.windll.kernel32.SetFileAttributesW(file_path, 128)
            except Exception as e:
                print(f"Error unsetting hidden attribute: {e}")
        else:
            print("Setting file attributes is not supported on this platform.")
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    app.exec()