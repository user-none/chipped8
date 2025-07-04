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

from collections import deque
from copy import deepcopy
from random import randint

from ..icpu import iCPU

from ..keys import KeyState
from ..display import Plane, ResolutionMode

from .instrs.instr_emitter import InstrBlockEmitter
from .instrs.instr import InstrKind

class CachedCPU(iCPU):

    def __init__(self, registers, stack, memory, timers, keys, display, quirks, audio):
        self._registers = registers
        self._stack = stack
        self._memory = memory
        self._timers = timers
        self._keys = keys
        self._display = display
        self._quirks = quirks
        self._audio = audio

        self._draw_occurred = False

        self._instruction_queue = deque()
        self._block_emitter = InstrBlockEmitter()

    def copy_state(self, d):
        self._instruction_queue = deque(d._instruction_queue)
        self._block_emitter = d._block_emitter

    def execute_next_op(self):
        self._draw_occurred = False

        if len(self._instruction_queue) == 0:
            self._instruction_queue.extend(self._block_emitter.get_block(self._registers, self._memory, self._quirks))

        if len(self._instruction_queue) == 0:
            raise NoInstructionsException('No instructions')

        (pc, instr) = self._instruction_queue.popleft()
        instr.execute(self._registers, self._stack, self._memory, self._timers, self._keys, self._display, self._audio)

        if not instr.advance:
            self._instruction_queue.appendleft((pc, instr))
        if instr.draw_occurred:
            self._draw_occurred = True

        # Check if the instruction self modified. This is either memory within the
        # ROMs address space was modified or we have a jump outside of the ROMs
        # address space indicating instructions were written into RAM.
        #if not self._self_modified and instr.self_modified():
        if instr.self_modified:
            # Disable caching of basic blocks because they may no longer be correct
            self._block_emitter.clear_pc_cache()

            # Clear the instruction queue because we can't guarantee the
            # Current basic block is still valid
            self._instruction_queue.clear()

            # Jump will set the PC address for us so we only need to update it
            # for other operations
            if instr.kind is not InstrKind.JUMP:
                # Set the PC to the next instruction because we need to pick up
                # processing from here on the next execution
                self._registers.set_PC(pc)
                self._registers.advance_PC()

    def draw_occurred(self):
        return self._draw_occurred
