import PyInstaller.__main__
import os
from PIL import Image

dir_path = os.path.dirname(os.path.realpath(__file__))

# check if ico file exists, if not create it
ICON_IMAGE = Image.open("icon.png")
ICON_ICO = "icon.ico"
if not os.path.isfile(ICON_ICO):
    ICON_IMAGE.resize((32, 32)).save(ICON_ICO)  # Resize and save ico icon

APP_NAME = 'Edit-as-you-go Sound Recorder'

PyInstaller.__main__.run([
    './main.py',
    '--clean', # force a full rebuild
    '--onefile', # contain everything in 1 exe file (will auto extract on run into temp dir)
    '--noconsole', # do not show the terminal console when running
    f'--icon={ICON_ICO}',
    f'--name={APP_NAME}',
    '--add-data',
    'audio/;audio/',
])