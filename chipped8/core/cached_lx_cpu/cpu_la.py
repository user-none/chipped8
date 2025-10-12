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

from .factory import get_op_instr
from .instr_kind import InstrKind

def _get_opcode(pc, memory):
    return (memory.get_byte(pc) << 8) | memory.get_byte(pc + 1)

class CachedLaCPU(iCPU):
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

    Blocks are built as instructions are run. The instruction chain is prebuilt before
    execution starts. As instructions executer they are added to the current block.
    Once a control instruction that changes flow is encountered the block is closed
    and a new one is started.

    The advantage of post building instruction block is for self modifying ROMs. Prebuilding
    blocks can result in blocks that have instructions that computed never executed. This
    ensures only executed instructions are put into blocks.

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

        self._draw_occurred = False

        self._instruction_queue = deque()
        self._instr_cache = {}
        self._block_cache = {}
        self._block_pc = -1
        self._block = deque()

    def copy_state(self, d):
        self._instruction_queue = deque(d._instruction_queue)
        self._instr_cache = d._instr_cache
        self._block_cache = deepcopy(d._block_cache)
        self._block = deque(d._block)
        self._block_pc = d._block_pc

    def _clear_blocks(self):
        self._block_cache = {}
        self._instruction_queue.clear()
        self._block_pc = -1
        self._block = deque()

    def _record_block(self):
        if len(self._block) != 0:
            self._block_cache[self._block_pc] = self._block
        self._block_pc = -1
        self._block = deque()

    def _execute_next_op_queue(self):
        (pc, func) = self._instruction_queue.popleft()
        (advance, self_modified, is_jump) = func(self)

        if not advance:
            self._registers.set_PC(pc)
            return
        elif self_modified:
            self._clear_blocks()
            if not is_jump:
                self._registers.set_PC(pc+2)

    def _execute_next_op_pc(self):
        pc = self._registers.get_PC()
        opcode = _get_opcode(pc, self._memory)
        (instr_type, func) = self._instr_cache.get(opcode, (None, None))

        if not func:
            instr_type, func = get_op_instr(opcode)
            self._instr_cache[opcode] = (instr_type, func)

        self._registers.advance_PC()
        (advance, self_modified, is_jump) = func(self)

        if not advance:
            self._registers.set_PC(pc)
            return
        elif self_modified:
            self._clear_blocks()
            return

        # Record the PC of the start of the block is this is the start
        if self._block_pc == -1:
            self._block_pc = pc

        self._block.append((pc, func))

        # All of these end the block because some kind of flow control is happening. Or double wide which
        # is a bit weird to handle since it skips an instruction (the operand data). So it's kinda like
        # A conditional advance that always skips.
        if instr_type in (InstrKind.JUMP, InstrKind.COND_ADVANCE, InstrKind.EXIT, InstrKind.DOUBLE_WIDE):
            self._record_block()

    def execute_next_op(self):
        self._draw_occurred = False
        pc = self._registers.get_PC()

        if len(self._instruction_queue) == 0:
            pc = self._registers.get_PC()
            block = self._block_cache.get(pc, [])
            self._instruction_queue.extend(block)

            if len(self._instruction_queue) != 0:
                # If we've loaded a block from the queue we want
                # to close the current block we're working on so
                # following instruction that aren't in queue don't
                # try to add to it.
                self._record_block()

                (pc, _) = self._instruction_queue[-1]
                self._registers.set_PC(pc+2)

        if len(self._instruction_queue) != 0:
            self._execute_next_op_queue()
            return

        self._execute_next_op_pc()

    def draw_occurred(self):
        return self._draw_occurred
