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

class InstrBNNN(Instr):
    '''
    BXNN / BNNN: Jumps to the address NNN plus V0
    '''

    def __init__(self, opcode, quirks):
        self._x = (opcode & 0x0F00) >> 8
        self._nn  = (opcode & 0x00FF)
        self._nnn  = (opcode & 0x0FFF)
        self._quirk_jump = quirks.get_jump()

        super().__init__()
        self.kind = InstrKind.JUMP

    def execute(self, registers, stack, memory, timers, keys, display, audio):
        self.self_modified = False

        if self._quirk_jump:
            n = self._nn + registers.get_V(self._x)
        else:
            n = self._nnn + registers.get_V(0)

        if n >= memory.ram_start():
            self.self_modified = True

        registers.set_PC(n)
