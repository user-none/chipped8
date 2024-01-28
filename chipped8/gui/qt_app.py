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
from threading import Thread

from PySide6.QtCore import Qt, QObject, Slot
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

from .sceneprovider import SceneProvider
from .c8handler import c8Handler

from chipped8 import Platform

class QtApp(QObject):
    def __init__(self, args):
        QObject.__init__(self)

        self._args = args
        self._c8handler = c8Handler(self._args.hz, self._args.platform)

    def run(self):
        scene = SceneProvider()
        self._c8handler.blitReady.connect(scene.blitScreen)
        self._c8handler.clearScreenReady.connect(scene.clearScreen)

        app = QApplication(sys.argv)
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty('SceneProvider', scene)
        engine.addImageProvider('SceneProvider', scene)

        qml_file = Path(__file__).parent / 'view.qml'
        engine.load(qml_file)

        if not engine.rootObjects():
            return -1

        win = engine.rootObjects()[0]
        win.windowFocusChanged.connect(self._c8handler.process_frames)
        win.keyEvent.connect(self._c8handler.key_event)
        win.loadRom.connect(self._c8handler.load_rom)

        if self._args.in_file:
            self._c8handler.load_rom(self._args.in_file)

        ret = app.exec()
        sys.exit(ret)

