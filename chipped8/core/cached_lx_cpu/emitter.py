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

from ..exceptions import UnknownOpCodeException
from .instr_kind import InstrKind
from .factory import get_op_instr

class Emitter:

    def __init__(self):
        self._instr_cache = {}
        self._block_cache = {}

    def _get_opcode(self, pc, memory):
        return (memory.get_byte(pc) << 8) | memory.get_byte(pc + 1)

    def _get_next_opcode(self, pc, memory):
        return (memory.get_byte(pc + 2) << 8) | memory.get_byte(pc + 3)

    def _get_instruction(self, opcode):
        (instr_type, func) = self._instr_cache.get(opcode, (InstrKind.EXIT, None))

        if not func:
            (instr_type, func) = get_op_instr(opcode)
            self._instr_cache[opcode] = (instr_type, func)

        return (instr_type, func)

    def _get_next_instruction(self, registers, memory):
        pc = registers.get_PC()
        opcode = self._get_opcode(pc, memory)

        (instr_type, func) = self._get_instruction(opcode)

        # Advance our position to the next instruction.
        registers.advance_PC()

        # Double wide needs an additional advance because we already read the instruction
        # which was really data.
        if instr_type == InstrKind.DOUBLE_WIDE:
            registers.advance_PC()

        return (pc, instr_type, func)

    def _build_block(self, registers, memory):
        block = []

        while 1:
            try:
                (pc, instr_type, func) = self._get_next_instruction(registers, memory)
            except UnknownOpCodeException:
                # If we're not pulling from the instruction cache we could hit an invalid
                # opcode because of
                # 1. The application could be self modifying and that point could be invalid at this time.
                # 2. We could have read all of the program and be starting to read into RAM. There is
                #    no way to know since we haven't executed anything and we're pre-building the blocks
                #    of instructions instead of building as we execute.
                # When we hit an invalid opcode we stop building the block
                break
            block.append((pc, func))

            # Stop processing on the block when we get to a jump of some kind.
            # The previous advances don't matter because these will change the PC when
            # they execute
            if instr_type in (InstrKind.JUMP, InstrKind.COND_ADVANCE, InstrKind.EXIT, InstrKind.DOUBLE_WIDE):
                break;

        return block

    def clear_block_cache(self):
        self._block_cache = {}

    def get_block(self, registers, memory):
        pc = registers.get_PC()

        block = self._block_cache.get(pc)
        if not block:
            block = self._build_block(registers, memory)
            self._block_cache[pc] = block

        return block
