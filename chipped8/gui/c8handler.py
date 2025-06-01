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
import numpy as np

max_rewind_frames = 60*30 # 60 frame per sec, 30 seconds

class c8Handler(QObject):
    blitReady = Signal(np.ndarray)
    audioReady = Signal(bytearray, int)
    clearScreenReady = Signal()
    errorOccurred = Signal(str)
    fps = Signal(float, float)
    updateScreen = Signal()

    def __init__(self, platform=chipped8.PlatformTypes.originalChip8, interpreter=chipped8.InterpreterTypes.cached):
        QObject.__init__(self)

        self._emulator = None
        self._platform = platform
        self._tickrate = -1
        if not interpreter:
            interpreter = chipped8.InterpreterTypes.cached
        self._interpreter = interpreter

        self._process_timer = QTimer(self)
        self._process_timer.setTimerType(Qt.PreciseTimer)
        self._process_timer.timeout.connect(self._process_frame)
        self._process_timer.timeout.connect(lambda: self.updateScreen.emit())

        self._frame_times = []
        self._rewind_stack = []

        self._rom_fname = None

    def _fill_screen_buffer(self, pixels):
        self.blitReady.emit(pixels)

    def _audio(self, pattern, pitch):
        self.audioReady.emit(bytes(pattern), pitch)

    @Slot(bool)
    def process_frames(self, run):
        if not self._emulator:
            return

        if run:
            self._process_timer.start(0)
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
                self.fps.emit(0, 0)
                self._frame_times = []
            else:
                self._process_timer.start(0)
        elif key == Qt.Key_Left and pressed:
            self._process_timer.stop()
            self.fps.emit(0, 0)
            self._frame_times = []

            if len(self._rewind_stack) == 0:
                return

            frames = 1
            if modifiers & Qt.ShiftModifier.value:
                frames = 60
            if frames > len(self._rewind_stack):
                frames = len(self._rewind_stack)

            if frames > 1:
                self._rewind_stack[:] = self._rewind_stack[:-(frames-1)]
            self._emulator = self._rewind_stack.pop()

            if len(self._rewind_stack) == 0:
                self._record_frame()
            self._emulator.clear_keys()

            self.blitReady.emit(self._emulator.screen_buffer())

    @Slot(QUrl)
    @Slot(str)
    @Slot(str, chipped8.PlatformTypes, int)
    def load_rom(self, fname, platform=None, tickrate=-1):
        if not fname:
            return

        if platform and platform != self._platform:
            self._platform = platform
        if self._tickrate != tickrate:
            self._tickrate = tickrate

        self._emulator = chipped8.Emulator(platform=self._platform, interpreter_type=self._interpreter, tickrate=self._tickrate)
        self._rewind_stack = []

        if isinstance(fname, QUrl):
            fname = fname.path()

        try:
            with open(fname, 'rb') as f:
                self._emulator.load_rom(f.read())
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self._emulator = None
            self._rom_fname = None
            raise e
            return

        self.clearScreenReady.emit()
        self._rom_fname = fname

        self._emulator.set_blit_screen_cb(self._fill_screen_buffer)
        self._emulator.set_sound_cb(self._audio)
        self._record_frame()
        self._process_timer.start(0)

    @Slot(str, str)
    def reload_rom(self, platform=None, interpreter=None):
        if not platform:
            platform = self._platform
        if isinstance(platform, str):
            platform = chipped8.PlatformTypes(platform)

        if not interpreter:
            interpreter = self._interpreter
        if isinstance(interpreter, str):
            interpreter = chipped8.InterpreterTypes(interpreter)

        self._platform = platform
        self._interpreter = interpreter

        if not self._rom_fname:
            return

        self.load_rom(self._rom_fname, self._platform, self._tickrate)

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
        self.fps.emit(sec, 60 / sec)
        #print('seconds: ', sec, 'fps: ', 60 / sec, round(60 / sec))

        self._frame_times = []
        self._frame_times.append(time_61)

    def _adjust_frame_interval(self, ns_start, ns_previous_frame):
        '''
        Adjust frame time because we only have ms timing with the timer but
        need sub-ms frame times. We're going to vary the frame times by 1 ms in
        order to average out to 60 fps. A 40/20 split of 17 and 16 ms frames
        will give us 60 fps.

        We're using `start(<number>)` but even if we used `setInterval()`, the
        timer will reset. Either way it will start timing for the full interval
        so we need to account for:

        - The time it took to process this frame
        - Any time longer than expected to start this frame.

        The interval we need to set could be 0-17 ms. If we get a negative from
        our calculation we are behind. But we can't set a negative timer so 0
        is used to fire immediately.

        Formula:

        - Frame time we're targeting: (interval)
        - Time already spent processing this frame: ((time.perf_counter_ns() - ns_start) / 1000000)
        - Any time longer than we expected to wait. E.g. we waited for 18 ms between frames. This is a catch up.
          - Processing time of last frame: ((ns_start - ns_previous_frame) / 1000000)
          - The minimum amount of time we should spend processing a frame: (16)
        '''

        interval = 17
        if len(self._frame_times) % 3 == 0:
            interval = 16

        interval = max(interval - ((time.perf_counter_ns() - ns_start) / 1000000) - max(((ns_start - ns_previous_frame) / 1000000) - 16, 0), 0)
        self._process_timer.start(interval)

    @Slot()
    def _process_frame(self):
        ns_start = time.perf_counter_ns()
        self._update_frame_time(ns_start)

        if not self._emulator:
            self._process_timer.stop()
            self.fps.emit(0, 0)
            self._frame_times = []
            return

        try:
            self._emulator.process_frame()
        except chipped8.ExitInterpreterException:
            self._emulator = None
            self._rewind_stack = []
            self._process_timer.stop()
            self.fps.emit(0, 0)
            self._frame_times = []
            self.clearScreenReady.emit()
            return
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self._emulator = None
            self._rewind_stack = []
            self._process_timer.stop()
            self.fps.emit(0, 0)
            self._frame_times = []
            return

        self._record_frame()

        # len == 1 means we only have this frame but we want the previous frame
        ns_previous_frame = ns_start if len(self._frame_times) <= 1 else self._frame_times[-2]
        self._adjust_frame_interval(ns_start, ns_previous_frame)

