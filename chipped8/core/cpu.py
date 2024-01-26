#!/usr/bin/env python

# Copyright 2024 John Schember <john@nachtimwald.com>
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

from copy import deepcopy
from random import randint

from . import maths
from .keys import KeyState
from .display import Plane, ResolutionMode

class ExitInterpreterException(Exception):
    pass

class CPU():

    def __init__(self, registers, stack, memory, timers, keys, display):
        self._registers = registers
        self._stack = stack
        self._memory = memory
        self._timers = timers
        self._keys = keys
        self._display = display

    def _get_opcode(self):
        return (self._memory.get_byte(self._registers.get_PC()) << 8) | self._memory.get_byte(self._registers.get_PC() + 1)

    def _draw(self, x, y, n):
        if n == 0:
            self._draw_s16(x, y)
        else:
            self._draw_s8(x, y, n)

    def _draw_s8(self, x, y, n):
        self._registers.set_V(0xF, 0)
        I = self._registers.get_I()
        for plane in self._display.get_planes():
            for i in range(n):
                sprite = self._memory.get_byte(I + i)

                for j in range(8):
                    # XOR with 0 won't change the value
                    if sprite & (0x80 >> j) == 0:
                        continue

                    row = x + j
                    col = y + i

                    unset = self._display.set_pixel(plane, row, col, 1)
                    if unset:
                        self._registers.set_V(0xF, 1)
            I = I + n

    def _draw_s16(self, x, y):
        self._registers.set_V(0xF, 0)
        I = self._registers.get_I()
        for plane in self._display.get_planes():
            for i in range(16):
                sprite = (self._memory.get_byte(I + (i*2)) << 8) | self._memory.get_byte(I + (i*2) + 1)

                for j in range(16):
                    # XOR with 0 won't change the value
                    if sprite & (0x8000 >> j) == 0:
                        continue

                    row = x + j
                    col = y + i

                    unset = self._display.set_pixel(plane, row, col, 1)
                    if unset:
                        self._registers.set_V(0xF, 1)
            I = I + 32

    def _execute_0(self, opcode):
        subcode = opcode & 0x00FF
        microcode = opcode & 0x00F0
        n = opcode & 0x000F

        if microcode == 0x00C0:
            self._execute_00CN(n)
        elif microcode == 0x00D0:
            self._execute_00DN(n)
        elif subcode == 0x00E0:
            self._execute_00E0()
        elif subcode == 0x00EE:
            self._execute_00EE()
        elif subcode == 0x00FB:
            self._execute_00FB()
        elif subcode == 0x00FC:
            self._execute_00FC()
        elif subcode == 0x00FD:
            self._execute_00FD()
        elif subcode == 0x00FE:
            self._execute_00FE()
        elif subcode == 0x00FF:
            self._execute_00FF()
        else:
            raise Exception('Unknown opcode: 00{:02X}'.format(subcode))

    # 00CN: Scroll down N pixels
    def _execute_00CN(self, n):
        self._display.scroll_down(n)
        self._registers.advance_PC()

    # 00DN: Scroll up N pixels
    def _execute_00DN(self, n):
        self._display.scroll_up(n)
        self._registers.advance_PC()

    # 00E0: Clears the screen
    def _execute_00E0(self):
        self._display.clear_screen()
        self._registers.advance_PC()

    # 00EE: Return from subroutine
    def _execute_00EE(self):
        self._registers.set_PC(self._stack.pop())
        self._registers.advance_PC()

    # Scroll right by 4 pixels; in low resolution mode, 2 pixels
    def _execute_00FB(self):
        self._display.scroll_right()
        self._registers.advance_PC()

    # Scroll left by 4 pixels; in low resolution mode, 2 pixels
    def _execute_00FC(self):
        self._display.scroll_left()
        self._registers.advance_PC()

    # Exit interpreter
    def _execute_00FD(self):
        raise ExitInterpreterException()

    # Switch to low resolution mode
    def _execute_00FE(self):
        self._display.set_resmode(ResolutionMode.lowres)
        self._registers.advance_PC()

    # Switch to high resolution mode
    def _execute_00FF(self):
        self._display.set_resmode(ResolutionMode.hires)
        self._registers.advance_PC()

    # 1NNN: Jump to address NNN
    def _execute_1NNN(self, opcode):
        self._registers.set_PC(opcode & 0x0FFF)

    # 2NNN: Calls subroutine at address NNN
    def _execute_2000(self, opcode):
        self._stack.push(self._registers.get_PC())
        self._registers.set_PC(opcode & 0x0FFF)

    # 3XNN: Skips the next instruction if VX equals NN 
    #       XO-Chip uses 0xF000 with a following 2 byte
    #       address that also needs to be skipped.
    def _execute_3XNN(self, opcode):
        x = (opcode & 0x0F00) >> 8
        n = opcode & 0x00FF

        if self._registers.get_V(x) == n:
            self._registers.advance_PC()
            if self._get_opcode() == 0xF000:
                self._registers.advance_PC()
        self._registers.advance_PC()

    # 4XNN: Skips the next instruction if VX does not equal NN
    #       XO-Chip uses 0xF000 with a following 2 byte
    #       address that also needs to be skipped.
    def _execute_4XNN(self, opcode):
        x = (opcode & 0x0F00) >> 8
        n = opcode & 0x00FF

        if self._registers.get_V(x) != n:
            self._registers.advance_PC()
            if self._get_opcode() == 0xF000:
                self._registers.advance_PC()
        self._registers.advance_PC()

    def _execute_5(self, opcode):
        subcode = opcode & 0x000F
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4

        if subcode == 0x0:
            self._execute_5XY0(x, y)
        elif subcode == 0x2:
            self._execute_5XY2(x, y)
        elif subcode == 0x3:
            self._execute_5XY3(x, y)
        else:
            raise Exception('Unknown opcode: 5XY{:01X}'.format(subcode))

    # 5XY0: Skips the next instruction if VX equals VY
    #       XO-Chip uses 0xF000 with a following 2 byte
    #       address that also needs to be skipped.
    def _execute_5XY0(self, x, y):
        if self._registers.get_V(x) == self._registers.get_V(y):
            self._registers.advance_PC()
            if self._get_opcode() == 0xF000:
                self._registers.advance_PC()
        self._registers.advance_PC()

    # 5XY2: Save VX..VY inclusive to memory starting at I.
    #       order can be ascending or descending. Does not increment I
    def _execute_5XY2(self, x, y):
        step = 1 if x <= y else -1
        for i, v in enumerate(range(x, y+step, step)):
            self._memory.set_byte(self._registers.get_I() + i, self._registers.get_V(v))
        self._registers.advance_PC()

    # 5XY2: Load VX..VY inclusive from memory starting at I.
    #       order can be ascending or descending. Does not increment I
    def _execute_5XY3(self, x, y):
        step = 1 if x <= y else -1
        for i, v in enumerate(range(x, y+step, step)):
            self._registers.set_V(v, self._memory.get_byte(self._registers.get_I() + i))
        self._registers.advance_PC()

    # 6XNN: Sets VX to NN
    def _execute_6XNN(self, opcode):
        x = (opcode & 0x0F00) >> 8
        n = opcode & 0x00FF

        self._registers.set_V(x, n)
        self._registers.advance_PC()

    # 7XNN: Adds NN to VX (carry flag is not changed)
    def _execute_7XNN(self, opcode):
        x = (opcode & 0x0F00) >> 8
        n = opcode & 0x00FF

        self._registers.set_V(x, self._registers.get_V(x) + n)
        self._registers.advance_PC()

    def _execute_8(self, opcode):
        subcode = opcode & 0x000F
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4

        if subcode == 0x0000:
            self._execute_8XY0(x, y)
        elif subcode == 0x0001:
            self._execute_8XY1(x, y)
        elif subcode == 0x0002:
            self._execute_8XY2(x, y)
        elif subcode == 0x0003:
            self._execute_8XY3(x, y)
        elif subcode == 0x0004:
            self._execute_8XY4(x, y)
        elif subcode == 0x0005:
            self._execute_8XY5(x, y)
        elif subcode == 0x0006:
            self._execute_8XY6(x, y)
        elif subcode == 0x0007:
            self._execute_8XY7(x, y)
        elif subcode == 0x000E:
            self._execute_8XYE(x, y)
        else:
            raise Exception('Unknown opcode: 8XY{:01X}'.format(subcode))

    # 8XY0: Sets VX to the value of VY
    def _execute_8XY0(self, x, y):
        self._registers.set_V(x, self._registers.get_V(y))
        self._registers.advance_PC()

    # 8XY1: Sets VX to VX or VY
    def _execute_8XY1(self, x, y):
        self._registers.set_V(x, self._registers.get_V(x) | self._registers.get_V(y))
        self._registers.advance_PC()

    # 8XY2: Sets VX to VX and VY
    def _execute_8XY2(self, x, y):
        self._registers.set_V(x, self._registers.get_V(x) & self._registers.get_V(y))
        self._registers.advance_PC()

    # 8XY3: Sets VX to VX xor VY
    def _execute_8XY3(self, x, y):
        self._registers.set_V(x, self._registers.get_V(x) ^ self._registers.get_V(y))
        self._registers.advance_PC()

    # 8XY4: Adds VY to VX. VF is set to 1 when there's an overflow, and to 0 when there is not
    def _execute_8XY4(self, x, y):
        n = self._registers.get_V(x) + self._registers.get_V(y)
        self._registers.set_V(0xF, 1 if n > 0xFF else 0)
        self._registers.set_V(x, n)
        self._registers.advance_PC()

    # 8XY5: VY is subtracted from VX. VF is set to 0 when there's an underflow, and 1 when there is not
    def _execute_8XY5(self, x, y):
        vx = self._registers.get_V(x)
        vy = self._registers.get_V(y)
        n = vx - vy

        self._registers.set_V(0xF, 1 if vx >= vy else 0)
        self._registers.set_V(x, n)

        self._registers.advance_PC()

    # 8XY6: Stores the least significant bit of VX in VF and then shifts VX to the right by 1
    #       Set register VF to the most significant bit prior to the shift
    def _execute_8XY6(self, x, y):
        n = self._registers.get_V(y)

        self._registers.set_V(0xF, n & 0x1)
        self._registers.set_V(x, n >> 1)

        self._registers.advance_PC()

    # 8XY7: Sets VX to VY minus VX. VF is set to 0 when there's an underflow, and 1 when there is not
    def _execute_8XY7(self, x, y):
        vx = self._registers.get_V(x)
        vy = self._registers.get_V(y)
        n = vy - vx

        self._registers.set_V(x, n)
        self._registers.set_V(0xF, 1 if vy >= vx else 0)

        self._registers.advance_PC()

    # 8XYE: Store the value of register VY shifted left one bit in register VX.
    #       Set register VF to the most significant bit prior to the shift
    def _execute_8XYE(self, x, y):
        n = self._registers.get_V(y)
        self._registers.set_V(0xF, n >> 7)
        self._registers.set_V(x, n << 1)
        self._registers.advance_PC()

    # 9XY0: Skips the next instruction if VX does not equal VY
    #       XO-Chip uses 0xF000 with a following 2 byte
    #       address that also needs to be skipped.
    def _execute_9XY0(self, opcode):
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4

        if self._registers.get_V(x) != self._registers.get_V(y):
            if self._get_opcode() == 0xF000:
                self._registers.advance_PC()
            self._registers.advance_PC()
        self._registers.advance_PC()

    # ANNN: Sets I to the address NNN
    def _execute_ANNN(self, opcode):
        self._registers.set_I(opcode & 0x0FFF)
        self._registers.advance_PC()

    # BNNN: Jumps to the address NNN plus V0
    def _execute_BNNN(self, opcode):
        self._registers.set_PC((opcode & 0x0FFF) + self._registers.get_V(0))

    # CXNN: Sets VX to the result of a bitwise and operation on a random number
    def _execute_CXNN(self, opcode):
        x = (opcode & 0x0F00) >> 8
        mask = (opcode & 0xFF)
        self._registers.set_V(x, randint(0, 255) & mask)
        self._registers.advance_PC()

    # DXYN: Draws a sprite at coordinate (VX, VY) that has a width of 8 pixels
    #       and a height of N pixels. Each row of 8 pixels is read as bit-coded
    #       starting from memory location I; I value does not change after the
    #       execution of this instruction. As described above, VF is set to 1 if any
    #       screen pixels are flipped from set to unset when the sprite is drawn, and
    #       to 0 if that does not happen
    def _execute_DXYN(self, opcode):
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F

        self._draw(self._registers.get_V(x), self._registers.get_V(y), n)
        self._registers.advance_PC()

    def _execute_E(self, opcode):
        subcode = opcode & 0x00FF
        x = (opcode & 0x0F00) >> 8

        if subcode == 0x9E:
            self._execute_EX9E(x)
        elif subcode == 0xA1:
            self._execute_EXA1(x)
        else:
            raise Exception('Unknown opcode: EX{:02X}'.format(subcode))

    # EX9E: Skips the next instruction if the key stored in VX is pressed
    #       XO-Chip uses 0xF000 with a following 2 byte
    #       address that also needs to be skipped.
    def _execute_EX9E(self, x):
        if self._keys.get_key_state(self._registers.get_V(x)) == KeyState.down:
            self._registers.advance_PC()
            if self._get_opcode() == 0xF000:
                self._registers.advance_PC()
        self._registers.advance_PC()

    # EXA1: Skips the next instruction if the key stored in VX is not pressed
    #       XO-Chip uses 0xF000 with a following 2 byte
    #       address that also needs to be skipped.
    def _execute_EXA1(self, x):
        if self._keys.get_key_state(self._registers.get_V(x)) == KeyState.up:
            self._registers.advance_PC()
            if self._get_opcode() == 0xF000:
                self._registers.advance_PC()
        self._registers.advance_PC()

    def _execute_F(self, opcode):
        subcode = opcode & 0x00FF
        x = (opcode & 0x0F00) >> 8

        if subcode == 0x00:
            self._execute_F000()
        elif subcode == 0x01:
            self._execute_FX01(x)
        elif subcode == 0x02:
            self._execute_FX02(x)
        elif subcode == 0x07:
            self._execute_FX07(x)
        elif subcode == 0x0A:
            self._execute_FX0A(x)
        elif subcode == 0x15:
            self._execute_FX15(x)
        elif subcode == 0x18:
            self._execute_FX18(x)
        elif subcode == 0x1E:
            self._execute_FX1E(x)
        elif subcode == 0x29:
            self._execute_FX29(x)
        elif subcode == 0x30:
            self._execute_FX30(x)
        elif subcode == 0x33:
            self._execute_FX33(x)
        elif subcode == 0x3A:
            self._execute_FX3A(x)
        elif subcode == 0x55:
            self._execute_FX55(x)
        elif subcode == 0x65:
            self._execute_FX65(x)
        elif subcode == 0x75:
            self._execute_FX75(x)
        elif subcode == 0x85:
            self._execute_FX85(x)
        else:
            raise Exception('Unknown opcode: FX{:02X}'.format(subcode))

    # F000 NNNN: Load I with 16-bit address NNNN this is a four byte instruction
    def _execute_F000(self):
        # Advance to NNNN address
        self._registers.advance_PC()
        # Get NNNN which is typically an opcode but in this case it's a 16-bit address
        self._registers.set_I(self._get_opcode())
        self._registers.advance_PC()

    # FN01: Select drawing planes by bitmask (0 planes, plane 1, plane 2 or both planes (3))
    def _execute_FX01(self, x):
        plane = Plane(0)
        if x & 1:
            plane = plane | Plane.p1
        if x & 2:
            plane = plane | Plane.p2
        self._display.set_plane(plane)
        self._registers.advance_PC()

    # F002: Store 16 bytes in audio pattern buffer, starting at I, to be played by the sound buzzer
    def _execute_FX02(self, x):
        # TODO
        self._registers.advance_PC()

    # FX07: Sets VX to the value of the delay timer
    def _execute_FX07(self, x):
        self._registers.set_V(x, self._timers.get_delay())
        self._registers.advance_PC()

    # FX0A: Wait for a keypress and store the result in register VX (blocking operation, all instruction halted until next key event)
    def _execute_FX0A(self, x):
        for i, ks in enumerate(self._keys.get_keys()):
            if ks == KeyState.down:
                self._registers.set_V(x, i)
                self._registers.advance_PC()
                break

    # FX15: Sets the delay timer to VX
    def _execute_FX15(self, x):
        self._timers.set_delay(self._registers.get_V(x))
        self._registers.advance_PC()

    # FX18: Sets the sound timer to VX
    def _execute_FX18(self, x):
        self._timers.set_sound(self._registers.get_V(x))
        self._registers.advance_PC()

    # FX1E: Adds VX to I. VF is not affected
    def _execute_FX1E(self, x):
        self._registers.set_I(self._registers.get_I() + self._registers.get_V(x))
        self._registers.advance_PC()

    # FX29: Sets I to the location of the sprite for the character in VX
    def _execute_FX29(self, x):
        n = self._registers.get_V(x)
        self._registers.set_I(n * 5)
        self._registers.advance_PC()

    # FX30: Point I to 10-byte font sprite for digit VX
    def _execute_FX30(self, x):
        n = self._registers.get_V(x)
        self._registers.set_I(self._memory.font_large_offset() + (n * 10))
        self._registers.advance_PC()

    # FX33: Stores the binary-coded decimal representation of VX, with the
    #       hundreds digit in memory at location in I, the tens digit at location
    #       I+1, and the ones digit at location I+2
    def _execute_FX33(self, x):
        n = self._registers.get_V(x)
        self._memory.set_byte(self._registers.get_I(), n // 100)
        self._memory.set_byte(self._registers.get_I() + 1, (n // 10) % 10)
        self._memory.set_byte(self._registers.get_I() + 2, (n % 100) % 10)
        self._registers.advance_PC()

    # Set the pitch register to the value in VX.
    def _execute_FX3A(self, x):
        # TODO
        self._registers.advance_PC()

    # FX55: Stores from V0 to VX (including VX) in memory, starting at address
    #       I. The offset from I is increased by 1 for each value written
    def _execute_FX55(self, x):
        for i in range(x + 1):
            self._memory.set_byte(self._registers.get_I() + i, self._registers.get_V(i))
        self._registers.set_I(self._registers.get_I() + x + 1)
        self._registers.advance_PC()

    # FX65: Fills from V0 to VX (including VX) with values from memory,
    #       starting at address I. The offset from I is increased by 1 for each value
    #       read
    def _execute_FX65(self, x):
        for i in range(x + 1):
            self._registers.set_V(i, self._memory.get_byte(self._registers.get_I() + i))
        self._registers.set_I(self._registers.get_I() + x + 1)
        self._registers.advance_PC()

    # FX75: Store V0..VX in RPL user flags
    def _execute_FX75(self, x):
        n = self._registers.get_V(x)

        for i in range(n+1):
            self._registers.set_RPL(i, self._registers.get_V(i))

        self._registers.advance_PC()

    # FX85: Read V0..VX from RPL user flags
    def _execute_FX85(self, x):
        n = self._registers.get_V(x)

        for i in range(n+1):
            self._registers.set_V(i, self._registers.get_RPL(i))

        self._registers.advance_PC()

    def _execute_op(self, opcode):
        code = opcode & 0xF000

        if code == 0x0000:
            self._execute_0(opcode)
        elif code == 0x1000:
            self._execute_1NNN(opcode)
        elif code == 0x2000:
            self._execute_2000(opcode)
        elif code == 0x3000:
            self._execute_3XNN(opcode)
        elif code == 0x4000:
            self._execute_4XNN(opcode)
        elif code == 0x5000:
            self._execute_5(opcode)
        elif code == 0x6000:
            self._execute_6XNN(opcode)
        elif code == 0x7000:
            self._execute_7XNN(opcode)
        elif code == 0x8000:
            self._execute_8(opcode)
        elif code == 0x9000:
            self._execute_9XY0(opcode)
        elif code == 0xA000:
            self._execute_ANNN(opcode)
        elif code == 0xB000:
            self._execute_BNNN(opcode)
        elif code == 0xC000:
            self._execute_CXNN(opcode)
        elif code == 0xD000:
            self._execute_DXYN(opcode)
        elif code == 0xE000:
            self._execute_E(opcode)
        elif code == 0xF000:
            self._execute_F(opcode)
        else:
            raise Exception('Unknown opcode: {:04X}'.format(opcode))

    def execute_next_op(self):
        opcode = self._get_opcode()
        self._execute_op(opcode)

