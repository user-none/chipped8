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

class Instr8XYE(Instr):
    '''
    8XYE: Store the value of register VY shifted left one bit in register VX.
          Set register VF to the most significant bit prior to the shift
    '''

    def __init__(self, x, y, quirks):
        self._x = x
        self._y = y
        self._quirk_shift = quirks.get_shift()
        super().__init__()

    def execute(self, registers, stack, memory, timers, keys, display, audio):
        if self._quirk_shift:
            n = registers.get_V(self._x)
        else:
            n = registers.get_V(self._y)

        registers.set_V(self._x, n << 1)
        registers.set_V(0xF, n >> 7)
        return self._result
