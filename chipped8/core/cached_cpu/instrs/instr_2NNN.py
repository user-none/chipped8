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

class Instr2NNN(Instr):
    '''
    2NNN: Calls subroutine at address NNN
    '''

    def __init__(self, pc, opcode):
        self._call_pc = opcode & 0x0FFF
        self._pc = pc
        self._self_modified = False

    def self_modified(self):
        return self._self_modified

    def kind(self):
        return InstrKind.JUMP

    def execute(self, registers, stack, memory, timers, keys, display, quirks, audio):
        stack.push(self._pc)

        if self._call_pc >= memory.ram_start():
            self._self_modified = True

        registers.set_PC(self._call_pc)
