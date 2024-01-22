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

import time

from copy import deepcopy

from PySide6.QtCore import Qt, QObject, Slot, Signal, QTimer, QUrl
from PySide6.QtWidgets import QApplication, QMessageBox

import chipped8

max_rewind_frames = 60*60*2 # 60 frame per sec, 60 secs in a minute, 2 minutes

class c8Handler(QObject):
    blitReady = Signal(list)

    def __init__(self, hz=400):
        QObject.__init__(self)

        self._cpu = None
        self._hz = hz
        self._process = False
        self._process_timer = QTimer(self)
        self._process_timer.setTimerType(Qt.PreciseTimer)
        self._process_timer.timeout.connect(self._process_frame)
        self._last_process_ns = 0

        self._rewind_stack = []

    def _fill_screen_buffer(self, pixels):
        self.blitReady.emit(pixels)

    def _beep(self):
        QApplication.beep()

    @Slot(bool)
    def process_frames(self, run):
        if not self._cpu:
            return

        if run:
            self._process_timer.start(0)
        else:
            self._process_timer.stop()

    @Slot(int, bool, int)
    def key_event(self, key, pressed, modifiers):
        if not self._cpu:
            return

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
        elif key == Qt.Key_P and pressed:
            if self._process_timer.isActive():
                self._process_timer.stop()
            else:
                self._process_timer.start(0)
        elif key == Qt.Key_Left and pressed:
            self._process_timer.stop()

            if len(self._rewind_stack) == 0:
                return

            frames = 1
            if modifiers & Qt.ShiftModifier.value:
                frames = 60
            if frames > len(self._rewind_stack):
                frames = len(self._rewind_stack)

            for i in range(frames):
                self._cpu = self._rewind_stack.pop()

            if len(self._rewind_stack) == 0:
                self._record_frame()

            self.blitReady.emit(self._cpu.screen_buffer())

    @Slot(QUrl)
    @Slot(str)
    def load_rom(self, fname):
        self._cpu = chipped8.cpu.CPU(self._hz)

        self._rewind_stack = []

        if isinstance(fname, QUrl):
            fname = fname.path()

        try:
            with open(fname, 'rb') as f:
                self._cpu.load_rom(f.read())
        except Exception as e:
            QMessageBox.critical(None, 'Load Error', str(e))
            self._cpu = None
            return

        self._cpu.set_blit_screen_cb(self._fill_screen_buffer)
        self._cpu.set_sound_cb(self._beep)
        self._record_frame()
        self._process_timer.start(0)

    def _record_frame(self):
        if self._cpu == None:
            return

        if len(self._rewind_stack) > max_rewind_frames:
            self._rewind_stack = self._rewind_stack[1:]
        self._rewind_stack.append(deepcopy(self._cpu))

    @Slot()
    def _process_frame(self):
        if not self._cpu:
            self._process_timer.stop()
            return

        try:
            self._cpu.process_frame()
        except Exception as e:
            QMessageBox.critical(None, 'Run Error', str(e))
            self._cpu = None
            self._rewind_stack = []
            self._process_timer.stop()
            return

        self._record_frame()

        ns = time.perf_counter_ns()
        wait_ms = 16.666666 - ((ns - self._last_process_ns) / 1000000)
        self._last_process_ns = ns
        if wait_ms < 0:
            wait_ms = 0
        self._process_timer.setInterval(wait_ms)

