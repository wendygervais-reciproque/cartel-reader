from setuptools import setup

APP = ['image-renamer.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['pytesseract','numpy','tkinter','re'], 
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
