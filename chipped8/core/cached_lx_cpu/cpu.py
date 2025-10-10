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

from ..icpu import iCPU

from .emitter import Emitter

class CachedLxCPU(iCPU):
    '''
    A caching interpreter.

    Opcodes are cached based on the full operand and added to a lookup table.
    This will reduce the need for decoding of the opcodes to take place. All
    opcodes once decoded are stateless and do not depend on the PC where they
    were first encountered.

    Further, they are cached in blocks based on the PC sequence in the ROM. Each block
    will have the starting PC as the key and will be all ops that come after unless an
    ending op is encountered. An ending opcode is one that changes flow. Such as a
    JUMP, or a conditional advance.


    The PC is set to the last PC + 2 in the current block of opcodes that are being run.
    This simulates the entire block having been run and the PC advancing past. Operations
    are assuming to have already advanced.
    '''

    def __init__(self, registers, stack, memory, timers, keys, display, quirks, audio):
        self._registers = registers
        self._stack = stack
        self._memory = memory
        self._timers = timers
        self._keys = keys
        self._display = display
        self._quirks = quirks
        self._audio = audio

        self._vblank_wait = False

        self._instruction_queue = deque()
        self._emitter = Emitter()

    def copy_state(self, d):
        self._instruction_queue = deque(d._instruction_queue)
        self._emitter = d._emitter

    def execute_next_op(self):
        set_PC = False
        self._vblank_wait = False

        if len(self._instruction_queue) == 0:
            self._instruction_queue.extend(self._emitter.get_block(self._registers, self._memory))
            set_PC = True

        if len(self._instruction_queue) == 0:
            raise NoInstructionsException('No instructions')

        # Set the PC to the last PC of the block if we'll start a new block
        # There are instructions that need to know the PC. They will always be the last item in a given block
        if set_PC:
            (pc, _) = self._instruction_queue[-1]
            self._registers.set_PC(pc)
            self._registers.advance_PC()

        (pc, func) = self._instruction_queue.popleft()
        (advance, self_modified, is_jump) = func(self)

        # Instructions can block advancing and run again. They can also indicate they self modified
        # This could be from jumping out of the ROM space or writing into the ROM space.
        if not advance:
            self._instruction_queue.appendleft((pc, func))
        elif self_modified:
            # Clear the block cache because we don't know the state of the blocks since
            # the program is no longer static in the ROM.
            self._emitter.clear_block_cache()
            self._instruction_queue.clear()

            if not is_jump:
                # If we're not jumping to another address we need to update the
                # PC to the next PC after this current instruction.
                self._registers.set_PC(pc)
                self._registers.advance_PC()

    def draw_occurred(self):
        return self._vblank_wait
