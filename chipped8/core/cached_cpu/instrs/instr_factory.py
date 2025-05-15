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

from . import *
from .instr import InstrKind

class InstrFactory:

    def __init__(self):
        self._instruction_cache = {}
        self._pc_instruction_cache = {}
        self._can_cache_pc_instructions = True

    def _pc_instruction(self, opcode):
        if (opcode & 0xF000) in (0x2000, 0x3000, 0x4000, 0x9000, 0xE000) or ((opcode & 0xF00F) == 0x5000 or opcode == 0xF000):
            return True
        return False

    def _load_instruction(self, pc, opcode):
        if self._pc_instruction(opcode):
            return self._pc_instruction_cache.get(pc)
        return self._instruction_cache.get(opcode)

    def _cache_instruction(self, pc, opcode, instr):
        if self._pc_instruction(opcode):
            if self._can_cache_pc_instructions:
                self._pc_instruction_cache[pc] = instr
            else:
                return
        self._instruction_cache[opcode] = instr

    def _get_instruction_0(self, opcode):
        subcode = opcode & 0x00FF
        microcode = opcode & 0x00F0
        n = opcode & 0x000F

        if microcode == 0x00C0:
            return Instr00CN(n)
        elif microcode == 0x00D0:
            return Instr00DN(n)
        elif subcode == 0x00E0:
            return Instr00E0()
        elif subcode == 0x00EE:
            return Instr00EE()
        elif subcode == 0x00FB:
            return Instr00FB()
        elif subcode == 0x00FC:
            return Instr00FC()
        elif subcode == 0x00FD:
            return Instr00FD()
        elif subcode == 0x00FE:
           return Instr00FE()
        elif subcode == 0x00FF:
            return Instr00FF()
        else:
            raise UnknownOpCodeException('Unknown opcode: 00{:02X}'.format(subcode))

    def _get_instruction_5(self, pc, opcode, next_opcode):
        subcode = opcode & 0x000F
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4

        if subcode == 0x0:
            return Instr5XY0(pc, next_opcode, x, y)
        elif subcode == 0x2:
            return Instr5XY2(x, y)
        elif subcode == 0x3:
            return Instr5XY3(x, y)
        else:
            raise UnknownOpCodeException('Unknown opcode: 5XY{:01X}'.format(subcode))

    def _get_instruction_8(self, opcode):
        subcode = opcode & 0x000F
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4

        if subcode == 0x0000:
            return Instr8XY0(x, y)
        elif subcode == 0x0001:
            return Instr8XY1(x, y)
        elif subcode == 0x0002:
            return Instr8XY2(x, y)
        elif subcode == 0x0003:
            return Instr8XY3(x, y)
        elif subcode == 0x0004:
            return Instr8XY4(x, y)
        elif subcode == 0x0005:
            return Instr8XY5(x, y)
        elif subcode == 0x0006:
            return Instr8XY6(x, y)
        elif subcode == 0x0007:
            return Instr8XY7(x, y)
        elif subcode == 0x000E:
            return Instr8XYE(x, y)
        else:
            raise UnknownOpCodeException('Unknown opcode: 8XY{:01X}'.format(subcode))

    def _get_instruction_E(self, pc, opcode, next_opcode):
        subcode = opcode & 0x00FF
        x = (opcode & 0x0F00) >> 8

        if subcode == 0x9E:
            return InstrEX9E(pc, x, next_opcode)
        elif subcode == 0xA1:
            return InstrEXA1(pc, x, next_opcode)
        else:
            raise UnknownOpCodeException('Unknown opcode: EX{:02X}'.format(subcode))

    def _get_instruction_F(self, opcode, next_opcode):
        subcode = opcode & 0x00FF
        x = (opcode & 0x0F00) >> 8

        if subcode == 0x00:
            return InstrF000(next_opcode)
        elif subcode == 0x01:
            return InstrFN01(x)
        elif subcode == 0x02:
            return InstrF002()
        elif subcode == 0x07:
            return InstrFX07(x)
        elif subcode == 0x0A:
            return InstrFX0A(x)
        elif subcode == 0x15:
            return InstrFX15(x)
        elif subcode == 0x18:
            return InstrFX18(x)
        elif subcode == 0x1E:
            return InstrFX1E(x)
        elif subcode == 0x29:
            return InstrFX29(x)
        elif subcode == 0x30:
            return InstrFX30(x)
        elif subcode == 0x33:
            return InstrFX33(x)
        elif subcode == 0x3A:
            return InstrFX3A(x)
        elif subcode == 0x55:
            return InstrFX55(x)
        elif subcode == 0x65:
            return InstrFX65(x)
        elif subcode == 0x75:
            return InstrFX75(x)
        elif subcode == 0x85:
            return InstrFX85(x)
        else:
            raise Exception('Unknown opcode: FX{:02X}'.format(subcode))

    def disable_pc_instruction_cache(self):
        self._pc_instruction_cache = {}
        self._can_cache_pc_instructions = False

    def create(self, pc, opcode, next_opcode):
        code = opcode & 0xF000

        #instr = self._load_instruction(pc, opcode)
        #if instr:
        #    return instr
  
        if code == 0x0000:
            instr = self._get_instruction_0(opcode)
        elif code == 0x1000:
            instr = Instr1NNN(opcode)
        elif code == 0x2000:
            instr = Instr2NNN(pc, opcode)
        elif code == 0x3000:
            instr = Instr3XNN(pc, opcode, next_opcode)
        elif code == 0x4000:
           instr = Instr4XNN(pc, opcode, next_opcode)
        elif code == 0x5000:
            instr = self._get_instruction_5(pc, opcode, next_opcode)
        elif code == 0x6000:
            instr = Instr6XNN(opcode)
        elif code == 0x7000:
            instr = Instr7XNN(opcode)
        elif code == 0x8000:
            instr = self._get_instruction_8(opcode)
        elif code == 0x9000:
            instr = Instr9XY0(pc, opcode, next_opcode)
        elif code == 0xA000:
           instr = InstrANNN(opcode)
        elif code == 0xB000:
            instr = InstrBNNN(opcode)
        elif code == 0xC000:
            instr = InstrCXNN(opcode)
        elif code == 0xD000:
            instr = InstrDXYN(opcode)
        elif code == 0xE000:
            instr = self._get_instruction_E(pc, opcode, next_opcode)
        elif code == 0xF000:
            instr = self._get_instruction_F(opcode, next_opcode)
        else:
            raise UnknownOpCodeException('Unknown opcode: {:04X}'.format(opcode))

        #self._cache_instruction(pc, opcode, instr)
        return instr
