"""
Script for building the example.

Usage:
    python setup.py py2app
"""
from distutils.core import setup
import py2app

setup(
    app=["Main.py"],
    data_files=["English.lproj", "Preferences.png", "beholder.png", "butter.png", "ODBEditors.plist"],
    options=dict(py2app=dict(
        iconfile="Butterfly.icns",
        plist=dict(CFBundleName='99eyeballs'),
    )),
)
