#!/usr/bin/env python

# Copyright 2025 John Schember <john@nachtimwald.com>
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

from .instr import Instr

class InstrFX55(Instr):
    '''
    FX55: Stores from V0 to VX (including VX) in memory, starting at address
          I. The offset from I is increased by 1 for each value written
    '''

    def __init__(self, x, quirks):
        self._x = x
        self._self_modified = False
        self._quirk_memoryLeaveIUnchanged = quirks.get_memoryLeaveIUnchanged()
        self._quirk_memoryIncrementByX = quirks.get_memoryIncrementByX()

    def self_modified(self):
        return self._self_modified

    def execute(self, registers, stack, memory, timers, keys, display, audio):
        if registers.get_I() < memory.ram_start():
            self._self_modified = True

        for i in range(self._x + 1):
            memory.set_byte(registers.get_I() + i, registers.get_V(i))

        if not self._quirk_memoryLeaveIUnchanged:
            if self._quirk_memoryIncrementByX:
                registers.set_I(registers.get_I() + self._x)
            else:
                registers.set_I(registers.get_I() + self._x + 1)
