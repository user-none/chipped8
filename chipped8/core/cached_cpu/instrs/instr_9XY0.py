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

from .instr import Instr, InstrKind

class Instr9XY0(Instr):
    '''
    9XY0: Skips the next instruction if VX does not equal VY
          XO-Chip uses 0xF000 with a following 2 byte
          address that also needs to be skipped.
    '''

    def __init__(self, pc, opcode, next_opcode):
        self._pc = pc
        self._next_opcode = next_opcode
        self._x = (opcode & 0x0F00) >> 8
        self._y = (opcode & 0x00F0) >> 4

    def kind(self):
        return InstrKind.COND_ADVANCE

    def is_pic(self):
        return False

    def execute(self, registers, stack, memory, timers, keys, display, quirks, audio):
        registers.set_PC(self._pc)

        if registers.get_V(self._x) != registers.get_V(self._y):
            registers.advance_PC()
            if self._next_opcode == 0xF000:
                registers.advance_PC()

        registers.advance_PC()
