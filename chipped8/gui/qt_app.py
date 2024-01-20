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
import chipped8

class QtApp(QObject):
    def __init__(self, args):
        QObject.__init__(self)

        self._args = args
        self._cpu = None

    @Slot(bool)
    def cpu_process(self, run):
        if not self._cpu:
            return

        if run:
            Thread(target=self._cpu.run).start()
        else:
            self._cpu.stop()

    @Slot(int, bool)
    def key_event(self, key, pressed):
        state = chipped8.KeyState.down if pressed else chipped8.KeyState.up
        if key == Qt.Key_1:
            self._cpu.set_key_state(chipped8.Keys.Key_1, state)
        elif key == Qt.Key_2:
            self._cpu.set_key_state(chipped8.Keys.Key_2, state)
        elif key == Qt.Key_3:
            self._cpu.set_key_state(chipped8.Keys.Key_3, state)
        elif key == Qt.Key_4:
            self._cpu.set_key_state(chipped8.Keys.Key_C, state)
        elif key == Qt.Key_Q:
            self._cpu.set_key_state(chipped8.Keys.Key_4, state)
        elif key == Qt.Key_W:
            self._cpu.set_key_state(chipped8.Keys.Key_5, state)
        elif key == Qt.Key_E:
            self._cpu.set_key_state(chipped8.Keys.Key_6, state)
        elif key == Qt.Key_R:
            self._cpu.set_key_state(chipped8.Keys.Key_D, state)
        elif key == Qt.Key_A:
            self._cpu.set_key_state(chipped8.Keys.Key_7, state)
        elif key == Qt.Key_S:
            self._cpu.set_key_state(chipped8.Keys.Key_8, state)
        elif key == Qt.Key_D:
            self._cpu.set_key_state(chipped8.Keys.Key_9, state)
        elif key == Qt.Key_F:
            self._cpu.set_key_state(chipped8.Keys.Key_E, state)
        elif key == Qt.Key_Z:
            self._cpu.set_key_state(chipped8.Keys.Key_A, state)
        elif key == Qt.Key_X:
            self._cpu.set_key_state(chipped8.Keys.Key_0, state)
        elif key == Qt.Key_C:
            self._cpu.set_key_state(chipped8.Keys.Key_B, state)
        elif key == Qt.Key_V:
            self._cpu.set_key_state(chipped8.Keys.Key_F, state)

    def _beep(self):
        #os.system("echo -ne '\007'")
        pass

    def run(self):
        self._cpu = chipped8.cpu.CPU(self._args.hz)
        self._cpu.set_sound_cb(self._beep)

        with open(self._args.in_file, 'rb') as f:
            self._cpu.load_rom(f.read())

        scene = SceneProvider(self._args.back_color, self._args.fore_color)
        self._cpu.set_blit_screen_cb(scene._fill_screen_buffer)

        app = QApplication(sys.argv)
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty('SceneProvider', scene)
        engine.addImageProvider('SceneProvider', scene)

        qml_file = Path(__file__).parent / 'view.qml'
        engine.load(qml_file)

        if not engine.rootObjects():
            return -1

        win = engine.rootObjects()[0]
        win.windowFocusChanged.connect(self.cpu_process)
        win.keyEvent.connect(self.key_event)


        ret = app.exec()
        self._cpu.stop()
        sys.exit(ret)

