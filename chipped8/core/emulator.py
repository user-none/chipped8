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

from .cpu import CPU
from .registers import Registers
from .timers import Timers
from .stack import Stack
from .memory import Memory
from .keys import KeyInput
from .display import Displaly

class Emulator():
    
    def __init__(self, hz=1200):
        self._registers = Registers()
        self._stack = Stack()
        self._memory = Memory()
        self._timers = Timers()
        self._keys = KeyInput()
        self._display = Displaly()
        self._cpu = CPU(
            self._registers,
            self._stack,
            self._memory,
            self._timers,
            self._keys,
            self._display
        )

        self._blit_screen_cb = lambda *args: None
        self._sound_cb = lambda *args: None

        self._hz = hz
        self._cycles_per_frame = self._hz // 60
        if self._cycles_per_frame <= 0:
            self._cycles_per_frame = 1

    def __deepcopy__(self, memo):
        d = Emulator(self._hz)
        d._registers = deepcopy(self._registers)
        d._stack = deepcopy(self._stack)
        d._memory = deepcopy(self._memory)
        d._timers = deepcopy(self._timers)
        d._keys = deepcopy(self._keys)
        d._display = deepcopy(self._display)

        d._cpu = CPU(
            d._registers,
            d._stack,
            d._memory,
            d._timers,
            d._keys,
            d._display
        )

        d._blit_screen_cb = self._blit_screen_cb
        d._sound_cb = self._sound_cb

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
        for i in range(self._cycles_per_frame):
            self._cpu.execute_next_op()

        self._timers.update_delay()

        if self._timers.get_sound() != 0:
            self._sound_cb()
        self._timers.update_sound()

        self._blit_screen()

    def run(self):
        self._process = True

        while True:
            if not self._process:
                break

            ns = time.perf_counter_ns()
            self.process_frame()

            wait_sec = (16666666 - (time.perf_counter_ns() - ns)) / 1000000000
            if wait_sec > 0:
                time.sleep(wait_sec)

    def stop(self):
        self._process = False

