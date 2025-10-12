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

from .registers import Registers
from .timers import Timers
from .stack import Stack
from .memory import Memory
from .keys import KeyInput
from .display import Displaly
from .platform import PlatformTypes, Platform
from .interpreter import InterpreterTypes, get_interperter
from .audio import Audio

class Emulator():

    def __init__(self, platform=PlatformTypes.originalChip8, interpreter_type=InterpreterTypes.pure, tickrate=-1, quirks=None):
        platform = Platform(platform)
        if not quirks:
            self._quirks = platform.quirks()
        else:
            self._quirks = quirks

        self._interpreter_type = interpreter_type

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

        CPU = get_interperter(self._interpreter_type)
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

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]

        d = object.__new__(self.__class__)
        d._quirks = self._quirks
        d._interpreter_type = self._interpreter_type
        d._tickrate = self._tickrate
        d._registers = deepcopy(self._registers, memo)
        d._stack = deepcopy(self._stack, memo)
        d._memory = deepcopy(self._memory, memo)
        d._timers = deepcopy(self._timers, memo)
        d._keys = self._keys
        d._display = deepcopy(self._display, memo)
        d._audio = deepcopy(self._audio, memo)


        CPU = get_interperter(self._interpreter_type)
        d._cpu = CPU(
            d._registers,
            d._stack,
            d._memory,
            d._timers,
            d._keys,
            d._display,
            d._quirks,
            d._audio
        )
        d._cpu.copy_state(self._cpu)

        d._blit_screen_cb = self._blit_screen_cb
        d._sound_cb = self._sound_cb

        memo[id(self)] = d
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
            if self._quirks.vblank and self._cpu.draw_occurred():
                break

        if self._timers.delay > 0:
            self._timers.delay -= 1

        if self._timers.sound != 0:
            self._sound_cb(self._audio.pattern, self._audio.pitch)
            self._timers.sound -= 1

        self._blit_screen()

    def clear_keys(self):
        self._keys.clear_key_states()
