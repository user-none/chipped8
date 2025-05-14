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

class InstrFX33(Instr):
    '''
    FX33: Stores the binary-coded decimal representation of VX, with the
          hundreds digit in memory at location in I, the tens digit at location
          I+1, and the ones digit at location I+2
    '''

    def __init__(self, x):
        self._x = x
        self._self_modified = False

    def self_modified(self):
        return self._self_modified

    def execute(self, registers, stack, memory, timers, keys, display, quirks, audio):
        if registers.get_I() < memory.ram_start():
            self._self_modified = True

        n = registers.get_V(self._x)
        memory.set_byte(registers.get_I(), n // 100)
        memory.set_byte(registers.get_I() + 1, (n // 10) % 10)
        memory.set_byte(registers.get_I() + 2, (n % 100) % 10)
