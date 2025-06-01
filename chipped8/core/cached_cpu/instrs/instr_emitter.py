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

from ...exceptions import UnknownOpCodeException

from .instr import InstrKind
from .instr_factory import InstrFactory

class InstrBlockEmitter:

    def __init__(self):
        self._instr_cache = {}
        self._pc_instr_cache = {}
        self._block_cache = {}

        self._instr_factory = InstrFactory()

    def clear_pc_cache(self):
        self._pc_instr_cache = {}
        self._block_cache = {}

    def _get_opcode(self, pc, memory):
        return (memory.get_byte(pc) << 8) | memory.get_byte(pc + 1)

    def _get_next_opcode(self, pc, memory):
        return (memory.get_byte(pc + 2) << 8) | memory.get_byte(pc + 3)

    def _get_instruction(self, pc, opcode, next_opcode, quirks):
        instr = None

        instr = self._pc_instr_cache.get(pc)
        if not instr:
            instr = self._instr_cache.get(opcode)

        if not instr:
            instr = self._instr_factory.create(pc, opcode, next_opcode, quirks)
            self._save_instruction(pc, opcode, instr)

        return instr

    def _save_instruction(self, pc, opcode, instr):
        if instr.pic:
            self._instr_cache[opcode] = instr
        else:
            self._pc_instr_cache[pc] = instr

    def _get_next_instruction(self, registers, memory, quirks):
        pc = registers.get_PC()
        opcode = self._get_opcode(pc, memory)
        next_opcode = self._get_next_opcode(pc, memory)

        instr = self._get_instruction(pc, opcode, next_opcode, quirks)

        # Advance our position to the next instruction.
        registers.advance_PC()

        # Double wide needs an additional advance because we already read the instruction
        # which was really data.
        if instr.kind == InstrKind.DOUBLE_WIDE:
            registers.advance_PC()

        return (pc, instr)

    def _build_block(self, registers, memory, quirks):
        block = []

        while 1:
            (pc, instr) = self._get_next_instruction(registers, memory, quirks)
            block.append((pc, instr))

            # Stop processing on the block when we get to a jump of some kind.
            # The previous advances don't matter because these will change the PC when
            # they execute
            if instr.kind in (InstrKind.JUMP, InstrKind.COND_ADVANCE, InstrKind.EXIT):
                break;

        return block

    def get_block(self, registers, memory, quirks):
        pc = registers.get_PC()

        block = self._block_cache.get(pc)
        if not block:
            # Build block loops and if it's self modifying we might
            # not know until we run. In which case we could try
            # reading an invlaid opcode while building the block.
            # We'll catch the exception and disable caching. Then
            # try to get the next instruction in non-cached mode.
            # It could raise an exception but that's fine, it just
            # means it really is an invalid opcode because it's only
            # going to read the next opcode which has to be valid
            # in order to continue emulation.
            try:
                block = self._build_block(registers, memory, quirks)
                self._save_block(pc, block)
            except UnknownOpCodeException:
                self.clear_pc_cache()
                registers.set_PC(pc)
                block = [self._get_next_instruction(registers, memory, quirks)]

        return block

    def _save_block(self, pc, block):
        self._block_cache[pc] = block
