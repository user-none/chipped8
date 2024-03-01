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

    def _setup_engine(self, scene):
        engine = QQmlApplicationEngine()

        engine.rootContext().setContextProperty('SceneProvider', scene)
        engine.addImageProvider('SceneProvider', scene)

        qml_file = Path(__file__).parent / 'view.qml'
        engine.load(qml_file)

        if not engine.rootObjects():
            None
        return engine

    def _setup_c8(self, scene):
        self._c8_thread = QThread()

        c8_handler = c8Handler(self._args.platform)
        c8_handler.moveToThread(self._c8_thread)
        c8_handler.blitReady.connect(scene.blitScreen)
        c8_handler.clearScreenReady.connect(scene.clearScreen)

        return c8_handler

    def _setup_audio(self, c8_handler):
        self._audio_thread = QThread()

        audio = AudioPlayer()
        audio.moveToThread(self._audio_thread)

        c8_handler.audioReady.connect(audio.play)

    def _setup_win(self, engine, c8_handler):
        win = engine.rootObjects()[0]

        win.windowFocusChanged.connect(c8_handler.process_frames)
        win.platformChanged.connect(c8_handler.reload_rom)
        win.keyEvent.connect(c8_handler.key_event)
        win.loadRom.connect(c8_handler.load_rom)

    def run(self):
        app = QApplication(sys.argv)

        scene = SceneProvider()
        engine = self._setup_engine(scene)
        if not engine:
            return -1

        c8_handler = self._setup_c8(scene)
        c8_handler.errorOccurred.connect(self.show_error)
        self._setup_audio(c8_handler)
        self._setup_win(engine, c8_handler)

        self._audio_thread.start()
        self._c8_thread.start()

        if self._args.in_file:
            QMetaObject.invokeMethod(c8_handler, 'load_rom', Qt.QueuedConnection, Q_ARG(str, self._args.in_file))

        ret = app.exec()
        QMetaObject.invokeMethod(c8_handler, 'process_frames', Qt.BlockingQueuedConnection, Q_ARG(bool, False))
        self._c8_thread.quit()
        self._audio_thread.quit()
        sys.exit(ret)

    @Slot(str)
    def show_error(self, message):
        QMessageBox.critical(None, 'Error', message)

