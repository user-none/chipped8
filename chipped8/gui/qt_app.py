#!/usr/bin/env python

# Copyright 2024 John Schember <john@nachtimwald.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import time

from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Slot, QThread, QMetaObject, Q_ARG
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtQml import QQmlApplicationEngine

from .sceneprovider import SceneProvider
from .audio import AudioPlayer
from .c8handler import c8Handler

class QtApp(QObject):
    def __init__(self, args):
        QObject.__init__(self)

        self._args = args

    def run(self):
        scene = SceneProvider()

        app = QApplication(sys.argv)
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty('SceneProvider', scene)
        engine.addImageProvider('SceneProvider', scene)

        qml_file = os.path.join(Path(__file__).parent, 'qml', 'view.qml')
        engine.load(qml_file)

        if not engine.rootObjects():
            return -1

        c8_thread = QThread()
        c8handler = c8Handler(self._args.platform)
        c8handler.moveToThread(c8_thread)
        c8handler.blitReady.connect(scene.blitScreen)
        c8handler.clearScreenReady.connect(scene.clearScreen)

        audio_thread = QThread()
        audio = AudioPlayer()
        audio.moveToThread(audio_thread)
        c8handler.audioReady.connect(audio.play)

        win = engine.rootObjects()[0]
        win.windowFocusChanged.connect(c8handler.process_frames)
        win.platformChanged.connect(c8handler.reload_rom)
        win.keyEvent.connect(c8handler.key_event)
        win.loadRom.connect(c8handler.load_rom)

        c8handler.errorOccurred.connect(self.show_error)

        audio_thread.start()
        c8_thread.start()

        if self._args.in_file:
            QMetaObject.invokeMethod(c8handler, 'load_rom', Qt.QueuedConnection, Q_ARG(str, self._args.in_file))

        # Turn off the splash screen If running a standalone build from PyInstaller
        # Splash screen isn't avaliable on all platforms
        with suppress(Exception):
            import pyi_splash
            pyi_splash.close()

        ret = app.exec()
        QMetaObject.invokeMethod(c8handler, 'process_frames', Qt.BlockingQueuedConnection, Q_ARG(bool, False))
        c8_thread.quit()
        audio_thread.quit()
        sys.exit(ret)

    @Slot(str)
    def show_error(self, message):
        QMessageBox.critical(None, 'Error', message)

