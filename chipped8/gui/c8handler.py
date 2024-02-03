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

import chipped8

max_rewind_frames = 60*30 # 60 frame per sec, 30 seconds

class c8Handler(QObject):
    blitReady = Signal(list)
    audioReady = Signal(bytearray, int)
    clearScreenReady = Signal()
    errorOccurred = Signal(str)

    def __init__(self, platform=chipped8.PlatformTypes.originalChip8):
        QObject.__init__(self)

        self._emulator = None
        self._platform = platform

        self._process_timer = QTimer(self)
        self._process_timer.setTimerType(Qt.PreciseTimer)
        self._process_timer.setInterval(1 / 60 * 1000) # Note: timer interval is only ms accuracy so this comes out to 16 ms timeout not 16.666666.
        self._process_timer.timeout.connect(self._process_frame)

        self._frame_times = []
        self._rewind_stack = []

    def _fill_screen_buffer(self, pixels):
        self.blitReady.emit(pixels)

    def _audio(self, pattern, pitch):
        self.audioReady.emit(pattern, pitch)

    @Slot(bool)
    def process_frames(self, run):
        if not self._emulator:
            return

        if run:
            self._process_timer.start()
        else:
            self._process_timer.stop()
            self._frame_times = []

    @Slot(int, bool, int)
    def key_event(self, key, pressed, modifiers):
        if not self._emulator:
            return

        state = chipped8.KeyState.down if pressed else chipped8.KeyState.up
        if key == Qt.Key_1:
            self._emulator.set_key_state(chipped8.Keys.Key_1, state)
        elif key == Qt.Key_2:
            self._emulator.set_key_state(chipped8.Keys.Key_2, state)
        elif key == Qt.Key_3:
            self._emulator.set_key_state(chipped8.Keys.Key_3, state)
        elif key == Qt.Key_4:
            self._emulator.set_key_state(chipped8.Keys.Key_C, state)
        elif key == Qt.Key_Q:
            self._emulator.set_key_state(chipped8.Keys.Key_4, state)
        elif key == Qt.Key_W:
            self._emulator.set_key_state(chipped8.Keys.Key_5, state)
        elif key == Qt.Key_E:
            self._emulator.set_key_state(chipped8.Keys.Key_6, state)
        elif key == Qt.Key_R:
            self._emulator.set_key_state(chipped8.Keys.Key_D, state)
        elif key == Qt.Key_A:
            self._emulator.set_key_state(chipped8.Keys.Key_7, state)
        elif key == Qt.Key_S:
            self._emulator.set_key_state(chipped8.Keys.Key_8, state)
        elif key == Qt.Key_D:
            self._emulator.set_key_state(chipped8.Keys.Key_9, state)
        elif key == Qt.Key_F:
            self._emulator.set_key_state(chipped8.Keys.Key_E, state)
        elif key == Qt.Key_Z:
            self._emulator.set_key_state(chipped8.Keys.Key_A, state)
        elif key == Qt.Key_X:
            self._emulator.set_key_state(chipped8.Keys.Key_0, state)
        elif key == Qt.Key_C:
            self._emulator.set_key_state(chipped8.Keys.Key_B, state)
        elif key == Qt.Key_V:
            self._emulator.set_key_state(chipped8.Keys.Key_F, state)
        elif key == Qt.Key_P and pressed:
            if self._process_timer.isActive():
                self._process_timer.stop()
                self._frame_times = []
            else:
                self._process_timer.start()
        elif key == Qt.Key_Left and pressed:
            self._process_timer.stop()
            self._frame_times = []

            if len(self._rewind_stack) == 0:
                return

            frames = 1
            if modifiers & Qt.ShiftModifier.value:
                frames = 60
            if frames > len(self._rewind_stack):
                frames = len(self._rewind_stack)

            for i in range(frames):
                self._emulator = self._rewind_stack.pop()

            if len(self._rewind_stack) == 0:
                self._record_frame()

            self.blitReady.emit(self._emulator.screen_buffer())

    @Slot(QUrl)
    @Slot(str)
    def load_rom(self, fname):
        self._emulator = chipped8.Emulator(self._platform)

        self._rewind_stack = []

        if isinstance(fname, QUrl):
            fname = fname.path()

        try:
            with open(fname, 'rb') as f:
                self._emulator.load_rom(f.read())
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self._emulator = None
            return

        self._emulator.set_blit_screen_cb(self._fill_screen_buffer)
        self._emulator.set_sound_cb(self._audio)
        self._record_frame()
        self._process_timer.start()

    def _record_frame(self):
        if self._emulator == None:
            return

        if len(self._rewind_stack) > max_rewind_frames:
            self._rewind_stack = self._rewind_stack[1:]
        self._rewind_stack.append(deepcopy(self._emulator))

    def _update_frame_time(self, ns):
        self._frame_times.append(ns)

        if len(self._frame_times) < 61:
            return

        time_61 = self._frame_times[-1]

        frame_time = self._frame_times[-1] - self._frame_times[0]
        sec = frame_time / 1000000000
        # TODO: Do something with this info
        print('seconds: ', sec, 'fps: ', 60 / sec)

        self._frame_times = []
        self._frame_times.append(time_61)

    @Slot()
    def _process_frame(self):
        ns_start = time.perf_counter_ns()
        self._update_frame_time(ns_start)

        if not self._emulator:
            self._process_timer.stop()
            self._frame_times = []
            return

        try:
            self._emulator.process_frame()
        except chipped8.ExitInterpreterException:
            self._emulator = None
            self._rewind_stack = []
            self._process_timer.stop()
            self._frame_times = []
            self.clearScreenReady.emit()
            return
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self._emulator = None
            self._rewind_stack = []
            self._process_timer.stop()
            self._frame_times = []
            return

        self._record_frame()

