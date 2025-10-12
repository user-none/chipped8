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
from ...instr_kind import InstrKind

class InstrDXYN(Instr):
    '''
    DXYN: Draws a sprite at coordinate (VX, VY) that has a width of 8 pixels
          and a height of N pixels. Each row of 8 pixels is read as bit-coded
          starting from memory location I; I value does not change after the
          execution of this instruction. As described above, VF is set to 1 if any
          screen pixels are flipped from set to unset when the sprite is drawn, and
          to 0 if that does not happen
    '''

    def __init__(self, opcode, quirks):
        self._x = (opcode & 0x0F00) >> 8
        self._y = (opcode & 0x00F0) >> 4
        self._n = opcode & 0x000F
        self._quirk_wrap = quirks.wrap

        super().__init__()
        self.kind = InstrKind.DRAW
        self.draw_occurred = True

    def execute(self, registers, stack, memory, timers, keys, display, audio):
        vx = registers.get_V(self._x)
        vy = registers.get_V(self._y)

        display.draw(vx, vy, self._n, self._quirk_wrap, registers, memory)
