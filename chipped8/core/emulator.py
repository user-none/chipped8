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
from threading import Event as ThreadingEvent

from .cpu import CPU
from .registers import Registers
from .timers import Timers
from .stack import Stack
from .memory import Memory
from .keys import KeyInput
from .display import Displaly
from .platform import PlatformTypes, Platform
from .audio import Audio

class Emulator():
    
    def __init__(self, platform=PlatformTypes.originalChip8, tickrate=-1, quirks=None):
        platform = Platform(platform)
        if not quirks:
            self._quirks = platform.quirks()
        else:
            self._quirks = quirks

        if tickrate <= 0:
            self._tickrate = platform.tickrate()
        else:
            self._tickrate = tickrate

        self._registers = Registers()
        self._stack = Stack()
        self._memory = Memory()
        self._timers = Timers()
        self._keys = KeyInput()
        self._display = Displaly()
        self._audio = Audio()
        self._cpu = CPU(
            self._registers,
            self._stack,
            self._memory,
            self._timers,
            self._keys,
            self._display,
            self._quirks,
            self._audio
        )

        self._blit_screen_cb = lambda *args: None
        self._sound_cb = lambda *args: None

        self._halt = ThreadingEvent()
        self._frame_times = []

    def __deepcopy__(self, memo):
        d = Emulator()
        d._registers = deepcopy(self._registers)
        d._stack = deepcopy(self._stack)
        d._memory = deepcopy(self._memory)
        d._timers = deepcopy(self._timers)
        d._keys = deepcopy(self._keys)
        d._display = deepcopy(self._display)
        d.quirks = deepcopy(self._quirks)
        d.audio = deepcopy(self._audio)

        d._cpu = CPU(
            d._registers,
            d._stack,
            d._memory,
            d._timers,
            d._keys,
            d._display,
            d.quirks,
            d.audio
        )

        d._blit_screen_cb = self._blit_screen_cb
        d._sound_cb = self._sound_cb

        d._tickrate = self._tickrate

        return d

    def _blit_screen(self):
        if not self._display.screen_changed():
            return
        self._blit_screen_cb(self._display.get_pixels())
        self._display.screen_updated()

    def set_blit_screen_cb(self, cb):
        self._blit_screen_cb = cb

    def set_sound_cb(self, cb):
        self._sound_cb = cb

    def set_key_state(self, key, state):
        self._keys.set_key_state(key, state)

    def load_rom(self, data):
        self._memory.load_rom(data)

    def screen_buffer(self):
        return self._display.get_pixels()

    def process_frame(self):
        for i in range(self._tickrate):
            self._cpu.execute_next_op()

            # This isn't quite right. We should be running cycles after the
            # draw and only stop when the next op is a draw. But this works
            # well enough, it's easier to check, and you don't notice a difference.
            if self._quirks.get_vblank() and self._cpu.draw_occurred():
                break

        self._timers.update_delay()

        if self._timers.get_sound() != 0:
            self._sound_cb(self._audio.get_pattern(), self._audio.get_pitch())
        self._timers.update_sound()

        self._blit_screen()

    def _update_frame_time(self, ns):
        self._frame_times.append(ns)

        if len(self._frame_times) < 61:
            return

        time_61 = self._frame_times[-1]

        frame_time = self._frame_times[-1] - self._frame_times[0]
        sec = frame_time / 1000000000
        #print('seconds: ', sec, 'fps: ', 60 / sec)

        self._frame_times = []
        self._frame_times.append(time_61)

    def run(self):
        self._halt.clear()

        while True:
            ns = time.perf_counter_ns()
            self._update_frame_time(ns)

            if self._halt.is_set():
                break

            self.process_frame()

            while time.perf_counter_ns() - ns < 1 / 60 * 1000000000:
                pass

        self._frame_times = []

    def stop(self):
        self._halt.set()

