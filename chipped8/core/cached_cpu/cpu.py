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

from copy import copy
from random import randint

from ..icpu import iCPU

from ..keys import KeyState
from ..display import Plane, ResolutionMode

from ..exceptions import ExitInterpreterException, NoInstructionsException

from .instrs.instr_factory import InstrFactory
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

        self._instruction_factory = InstrFactory()
        self._block_cache = {}
        self._instruction_queue = []
        self._block_cache_enable = True

    def _get_opcode(self, pc):
        return (self._memory.get_byte(pc) << 8) | self._memory.get_byte(pc + 1)

    def _get_next_opcode(self, pc):
        return (self._memory.get_byte(pc + 2) << 8) | self._memory.get_byte(pc + 3)

    def _get_next_instruction(self):
        pc = self._registers.get_PC()
        instr = self._instruction_factory.create(pc, self._get_opcode(pc), self._get_next_opcode(pc))

        # Advance our position to the next instruction.
        self._registers.advance_PC()

        # Dobule wide needs an additional advance becase we already read the instrcution
        # which was really data.
        if instr.kind() == InstrKind.DOUBLE_WIDE:
            self._registers.advance_PC()

        return (pc, instr)

    def _build_basic_block(self):
        instructions = []

        while 1:
            (pc, instr) = self._get_next_instruction()
            instructions.append((pc, instr))

            # Stop processing on the block when we get to a jump of some kind.
            # The previous advances don't matter because these will change the PC when
            # they exectute
            if instr.kind() in (InstrKind.JUMP, InstrKind.COND_ADVANCE, InstrKind.EXIT):
                break;

        return instructions

    def _load_next_basic_block(self):
        pc = self._registers.get_PC()

        if self._block_cache_enable:
            block = self._block_cache.get(pc)
            if not block:
                block = self._build_basic_block()
                self._block_cache[pc] = block
            self._instruction_queue = copy(block)
        else:
            self._instruction_queue = [self._get_next_instruction()]

    def execute_next_op(self):
        self._draw_occurred = False

        if len(self._instruction_queue) == 0:
            self._load_next_basic_block()

        if len(self._instruction_queue) == 0:
            raise NoInstructionsException('No instructions')

        (pc, instr) = self._instruction_queue.pop(0)
        instr.execute(self._registers, self._stack, self._memory, self._timers, self._keys, self._display, self._quirks, self._audio)

        kind = instr.kind()
        if kind == InstrKind.BLOCKING and not instr.advance():
            self._instruction_queue.insert(0, (pc, instr))
        if kind == InstrKind.DRAW:
            self._draw_occurred = True

        # Check if the instruction self modified. This is either memory within the
        # ROMs address space was modified or we have a jump outside of the ROMs
        # address space indicating instructions were written into RAM.
        if self._block_cache_enable and instr.self_modified():
            print('Self modified')
            # Disable caching of basic blocks because they may no longer be correct
            self._block_cache_enable = False
            # Disable PC location caching of instructions
            self._instruction_factory.disable_pc_instruction_cache()
            # Clear the instruction queue because we can't guarentee the
            # Current basic block is still valid
            self._instruction_queue = []
            # Set the PC to the next instruction because we need to pick up
            # processing from here on the next execution
            self._registers.set_PC(pc)
            self._registers.advance_PC()

    def draw_occurred(self):
        return self._draw_occurred
