#!/usr/bin/env python

# Copyright 2026 John Schember <john@nachtimwald.com>
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

'''
Chip-8 to ARM64 compiler.

Translates Chip-8 opcodes into ARM64 machine code for JIT execution.
'''

from .emitter import ARM64Emitter
from ..state_codes import TrapCode
from ..shared_state import (
    OFFSET_V,
    OFFSET_I,
    OFFSET_PC,
    OFFSET_STACK,
    OFFSET_SP,
    OFFSET_DELAY,
    OFFSET_SOUND,
    OFFSET_TRAP_CODE,
    OFFSET_TRAP_OPCODE,
)


class BlockCompiler:
    '''
    Compiles Chip-8 basic blocks to ARM64 machine code.

    A basic block ends when:
    - A jump/call/return instruction is encountered
    - A trap-required instruction is encountered
    - Maximum block size is reached
    '''

    # ARM64 register assignments
    # We use X0 directly as the state pointer since we don't make any calls
    # X0 is passed as the first argument and remains valid throughout
    REG_STATE = 0     # X0 = pointer to SharedState (argument register)
    REG_SCRATCH0 = 1  # W1 = scratch
    REG_SCRATCH1 = 2  # W2 = scratch
    REG_SCRATCH2 = 3  # W3 = scratch
    REG_SCRATCH3 = 4  # W4 = scratch
    REG_RETVAL = 0    # W0 = return value (same as STATE, set just before ret)

    # Maximum instructions per block
    MAX_BLOCK_INSTRUCTIONS = 64

    def __init__(self, quirks):
        '''
        Initialize the compiler with platform quirks.

        Args:
            quirks: Quirks object defining platform-specific behavior
        '''
        self.quirks = quirks
        self.emitter = ARM64Emitter()
        self._memory = None  # Set during compilation

    def _get_skip_amount(self, pc: int) -> int:
        '''
        Get the number of bytes to skip when a skip instruction is executed.

        Normally 2, but 4 if the next instruction is F000 NNNN (a 4-byte instruction).
        '''
        if self._memory is None:
            return 2

        # Check if next opcode at pc+2 is F000 (start of 4-byte instruction)
        next_pc = pc + 2
        if next_pc + 1 < len(self._memory):
            next_opcode = (self._memory[next_pc] << 8) | self._memory[next_pc + 1]
            if next_opcode == 0xF000:
                return 4  # Skip the 4-byte F000 NNNN instruction

        return 2

    def compile_block(self, memory: bytes, start_pc: int) -> bytes:
        '''
        Compile a basic block starting at the given PC.

        Args:
            memory: The full Chip-8 memory (64KB)
            start_pc: Starting program counter

        Returns:
            Compiled ARM64 machine code as bytes
        '''
        self.emitter.reset()
        self._memory = memory  # Store for skip calculations

        # No prologue needed - we use X0 directly as state pointer
        # since we don't make any function calls

        pc = start_pc
        instruction_count = 0

        while instruction_count < self.MAX_BLOCK_INSTRUCTIONS:
            # Fetch opcode (big-endian)
            opcode = (memory[pc] << 8) | memory[pc + 1]

            # Compile the opcode
            block_ends = self._compile_opcode(opcode, pc)

            pc += 2
            instruction_count += 1

            if block_ends:
                break

        # If we hit max instructions without a block-ending opcode,
        # store PC and return 0 (no trap)
        if instruction_count >= self.MAX_BLOCK_INSTRUCTIONS:
            self._emit_store_pc(pc)
            self.emitter.mov_imm(self.REG_RETVAL, 0)
            self.emitter.ret()

        return self.emitter.get_code()

    def _compile_opcode(self, opcode: int, pc: int) -> bool:
        '''
        Compile a single Chip-8 opcode.

        Args:
            opcode: The 16-bit opcode
            pc: Current program counter

        Returns:
            True if the block should end after this opcode
        '''
        nibble = (opcode & 0xF000) >> 12

        if nibble == 0x0:
            return self._compile_0xxx(opcode, pc)
        elif nibble == 0x1:
            return self._compile_1NNN(opcode)
        elif nibble == 0x2:
            return self._compile_2NNN(opcode, pc)
        elif nibble == 0x3:
            return self._compile_3XNN(opcode, pc)
        elif nibble == 0x4:
            return self._compile_4XNN(opcode, pc)
        elif nibble == 0x5:
            return self._compile_5XY0(opcode, pc)
        elif nibble == 0x6:
            return self._compile_6XNN(opcode, pc)
        elif nibble == 0x7:
            return self._compile_7XNN(opcode, pc)
        elif nibble == 0x8:
            return self._compile_8XYN(opcode, pc)
        elif nibble == 0x9:
            return self._compile_9XY0(opcode, pc)
        elif nibble == 0xA:
            return self._compile_ANNN(opcode, pc)
        elif nibble == 0xB:
            return self._compile_BNNN(opcode, pc)
        elif nibble == 0xC:
            return self._emit_trap(opcode, pc, TrapCode.RANDOM)
        elif nibble == 0xD:
            return self._emit_trap(opcode, pc, TrapCode.DRAW)
        elif nibble == 0xE:
            return self._compile_EXXX(opcode, pc)
        elif nibble == 0xF:
            return self._compile_FXXX(opcode, pc)
        else:
            # Unknown opcode - trap
            return self._emit_trap(opcode, pc, TrapCode.EXIT)

    # -------------------------------------------------------------------------
    # 0xxx opcodes
    # -------------------------------------------------------------------------

    def _compile_0xxx(self, opcode: int, pc: int) -> bool:
        '''Compile 0xxx opcodes (clear, return, scroll, etc.)'''
        if opcode == 0x00E0:
            # 00E0: Clear screen - trap to Python
            return self._emit_trap(opcode, pc, TrapCode.DISPLAY)
        elif opcode == 0x00EE:
            # 00EE: Return from subroutine
            return self._compile_00EE(pc)
        elif opcode == 0x00FD:
            # 00FD: Exit
            return self._emit_trap(opcode, pc, TrapCode.EXIT)
        elif opcode == 0x00FE or opcode == 0x00FF:
            # 00FE/00FF: Low/high res mode - trap
            return self._emit_trap(opcode, pc, TrapCode.DISPLAY)
        elif opcode == 0x00FB or opcode == 0x00FC:
            # 00FB/00FC: Scroll left/right - trap
            return self._emit_trap(opcode, pc, TrapCode.DISPLAY)
        elif (opcode & 0xFFF0) == 0x00C0 or (opcode & 0xFFF0) == 0x00D0:
            # 00CN/00DN: Scroll down/up - trap
            return self._emit_trap(opcode, pc, TrapCode.DISPLAY)
        else:
            # Unknown 0xxx - trap
            return self._emit_trap(opcode, pc, TrapCode.EXIT)

    def _compile_00EE(self, pc: int) -> bool:
        '''00EE: Return from subroutine'''
        # Decrement SP
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_SP)
        self.emitter.sub_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 1)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_SP)

        # Load return address from stack[sp]
        # stack is at OFFSET_STACK, each entry is 2 bytes
        # Address = state + OFFSET_STACK + sp * 2

        # Compute sp * 2 (W1 = sp * 2)
        self.emitter.lsl_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 1)

        # Get base address of stack (X2 = state + OFFSET_STACK)
        self.emitter.add_x_imm(self.REG_SCRATCH1, self.REG_STATE, OFFSET_STACK)

        # Add offset to base - MUST use 64-bit add for pointer arithmetic
        self.emitter.add_x_reg(self.REG_SCRATCH1, self.REG_SCRATCH1, self.REG_SCRATCH0)

        # Load halfword from [scratch1]
        self.emitter.ldrh(self.REG_SCRATCH0, self.REG_SCRATCH1, 0)

        # Add 2 to get past the return instruction
        self.emitter.add_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 2)

        # Store as new PC
        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

        # Return 0 (no trap)
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # 1NNN: Jump
    # -------------------------------------------------------------------------

    def _compile_1NNN(self, opcode: int) -> bool:
        '''1NNN: Jump to address NNN'''
        nnn = opcode & 0x0FFF
        self._emit_store_pc(nnn)
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # 2NNN: Call subroutine
    # -------------------------------------------------------------------------

    def _compile_2NNN(self, opcode: int, pc: int) -> bool:
        '''2NNN: Call subroutine at NNN'''
        nnn = opcode & 0x0FFF

        # Push current PC onto stack
        # stack[sp] = pc
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_SP)

        # Compute stack address: state + OFFSET_STACK + sp * 2
        self.emitter.lsl_imm(self.REG_SCRATCH1, self.REG_SCRATCH0, 1)
        self.emitter.add_x_imm(self.REG_SCRATCH2, self.REG_STATE, OFFSET_STACK)
        self.emitter.add_x_reg(self.REG_SCRATCH2, self.REG_SCRATCH2, self.REG_SCRATCH1)

        # Store current PC
        self.emitter.mov_imm(self.REG_SCRATCH1, pc)
        self.emitter.strh(self.REG_SCRATCH1, self.REG_SCRATCH2, 0)

        # Increment SP
        self.emitter.add_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 1)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_SP)

        # Jump to NNN
        self._emit_store_pc(nnn)
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # 3XNN: Skip if VX == NN
    # -------------------------------------------------------------------------

    def _compile_3XNN(self, opcode: int, pc: int) -> bool:
        '''3XNN: Skip next instruction if VX == NN'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF
        skip_amount = self._get_skip_amount(pc)

        # Load V[x]
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

        # Compare with NN
        self.emitter.cmp_imm(self.REG_SCRATCH0, nn)

        # If equal, skip (pc + 2 + skip_amount), else no skip (pc + 2)
        self.emitter.mov_imm(self.REG_SCRATCH0, pc + 2)  # Default: no skip
        self.emitter.mov_imm(self.REG_SCRATCH1, pc + 2 + skip_amount)  # Skip
        self.emitter.csel(self.REG_SCRATCH0, self.REG_SCRATCH1, self.REG_SCRATCH0,
                         ARM64Emitter.COND_EQ)

        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

        # End block - PC was conditionally modified
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # 4XNN: Skip if VX != NN
    # -------------------------------------------------------------------------

    def _compile_4XNN(self, opcode: int, pc: int) -> bool:
        '''4XNN: Skip next instruction if VX != NN'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF
        skip_amount = self._get_skip_amount(pc)

        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.cmp_imm(self.REG_SCRATCH0, nn)

        self.emitter.mov_imm(self.REG_SCRATCH0, pc + 2)
        self.emitter.mov_imm(self.REG_SCRATCH1, pc + 2 + skip_amount)
        self.emitter.csel(self.REG_SCRATCH0, self.REG_SCRATCH1, self.REG_SCRATCH0,
                         ARM64Emitter.COND_NE)

        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

        # End block - PC was conditionally modified
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # 5XYN: Skip/Memory operations
    # -------------------------------------------------------------------------

    def _compile_5XY0(self, opcode: int, pc: int) -> bool:
        '''Handle 5XY* opcodes'''
        n = opcode & 0x000F

        if n == 0x0:
            return self._compile_5XY0_skip(opcode, pc)
        elif n == 0x2:
            # 5XY2: Save VX..VY to memory at I - trap to Python
            return self._emit_trap(opcode, pc, TrapCode.STORE_REGS)
        elif n == 0x3:
            # 5XY3: Load VX..VY from memory at I - trap to Python
            return self._emit_trap(opcode, pc, TrapCode.LOAD_REGS)
        else:
            return self._emit_trap(opcode, pc, TrapCode.EXIT)

    def _compile_5XY0_skip(self, opcode: int, pc: int) -> bool:
        '''5XY0: Skip next instruction if VX == VY'''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        skip_amount = self._get_skip_amount(pc)

        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)
        self.emitter.cmp_reg(self.REG_SCRATCH0, self.REG_SCRATCH1)

        self.emitter.mov_imm(self.REG_SCRATCH0, pc + 2)
        self.emitter.mov_imm(self.REG_SCRATCH1, pc + 2 + skip_amount)
        self.emitter.csel(self.REG_SCRATCH0, self.REG_SCRATCH1, self.REG_SCRATCH0,
                         ARM64Emitter.COND_EQ)

        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

        # End block - PC was conditionally modified
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # 6XNN: VX = NN
    # -------------------------------------------------------------------------

    def _compile_6XNN(self, opcode: int, pc: int) -> bool:
        '''6XNN: Set VX = NN'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF

        self.emitter.mov_imm(self.REG_SCRATCH0, nn)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    # -------------------------------------------------------------------------
    # 7XNN: VX += NN
    # -------------------------------------------------------------------------

    def _compile_7XNN(self, opcode: int, pc: int) -> bool:
        '''7XNN: Add NN to VX (no carry flag change)'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF

        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.add_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, nn)
        self.emitter.and_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 0xFF)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    # -------------------------------------------------------------------------
    # 8XYN: ALU operations
    # -------------------------------------------------------------------------

    def _compile_8XYN(self, opcode: int, pc: int) -> bool:
        '''Compile 8XYN ALU operations'''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F

        if n == 0x0:
            return self._compile_8XY0(x, y, pc)
        elif n == 0x1:
            return self._compile_8XY1(x, y, pc)
        elif n == 0x2:
            return self._compile_8XY2(x, y, pc)
        elif n == 0x3:
            return self._compile_8XY3(x, y, pc)
        elif n == 0x4:
            return self._compile_8XY4(x, y, pc)
        elif n == 0x5:
            return self._compile_8XY5(x, y, pc)
        elif n == 0x6:
            return self._compile_8XY6(x, y, pc)
        elif n == 0x7:
            return self._compile_8XY7(x, y, pc)
        elif n == 0xE:
            return self._compile_8XYE(x, y, pc)
        else:
            return self._emit_trap(opcode, pc, TrapCode.EXIT)

    def _compile_8XY0(self, x: int, y: int, pc: int) -> bool:
        '''8XY0: VX = VY'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + y)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XY1(self, x: int, y: int, pc: int) -> bool:
        '''8XY1: VX |= VY'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)
        self.emitter.orr_reg(self.REG_SCRATCH0, self.REG_SCRATCH0, self.REG_SCRATCH1)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

        # Quirk: reset VF
        if self.quirks.logic:
            self.emitter.mov_imm(self.REG_SCRATCH0, 0)
            self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XY2(self, x: int, y: int, pc: int) -> bool:
        '''8XY2: VX &= VY'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)
        self.emitter.and_reg(self.REG_SCRATCH0, self.REG_SCRATCH0, self.REG_SCRATCH1)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

        if self.quirks.logic:
            self.emitter.mov_imm(self.REG_SCRATCH0, 0)
            self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XY3(self, x: int, y: int, pc: int) -> bool:
        '''8XY3: VX ^= VY'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)
        self.emitter.eor_reg(self.REG_SCRATCH0, self.REG_SCRATCH0, self.REG_SCRATCH1)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

        if self.quirks.logic:
            self.emitter.mov_imm(self.REG_SCRATCH0, 0)
            self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XY4(self, x: int, y: int, pc: int) -> bool:
        '''8XY4: VX += VY with carry'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)
        self.emitter.add_reg(self.REG_SCRATCH2, self.REG_SCRATCH0, self.REG_SCRATCH1)

        # VF = 1 if result > 255
        self.emitter.cmp_imm(self.REG_SCRATCH2, 0xFF)
        self.emitter.cset(self.REG_SCRATCH3, ARM64Emitter.COND_HI)

        # Mask result and store
        self.emitter.and_imm(self.REG_SCRATCH2, self.REG_SCRATCH2, 0xFF)
        self.emitter.strb(self.REG_SCRATCH2, self.REG_STATE, OFFSET_V + x)
        self.emitter.strb(self.REG_SCRATCH3, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XY5(self, x: int, y: int, pc: int) -> bool:
        '''8XY5: VX -= VY (VF = NOT borrow)'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)

        # VF = 1 if VX >= VY (no borrow)
        self.emitter.cmp_reg(self.REG_SCRATCH0, self.REG_SCRATCH1)
        self.emitter.cset(self.REG_SCRATCH3, ARM64Emitter.COND_HS)

        # VX = VX - VY (wrapping)
        self.emitter.sub_reg(self.REG_SCRATCH0, self.REG_SCRATCH0, self.REG_SCRATCH1)
        self.emitter.and_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 0xFF)

        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.strb(self.REG_SCRATCH3, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XY6(self, x: int, y: int, pc: int) -> bool:
        '''8XY6: VX >>= 1 (or VX = VY >> 1 depending on quirk)'''
        if self.quirks.shift:
            # Modern: shift VX
            self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        else:
            # Original: shift VY into VX
            self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + y)

        # VF = LSB before shift
        self.emitter.and_imm(self.REG_SCRATCH1, self.REG_SCRATCH0, 0x1)

        # Shift right
        self.emitter.lsr_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 1)

        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.strb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XY7(self, x: int, y: int, pc: int) -> bool:
        '''8XY7: VX = VY - VX (VF = NOT borrow)'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)

        # VF = 1 if VY >= VX
        self.emitter.cmp_reg(self.REG_SCRATCH1, self.REG_SCRATCH0)
        self.emitter.cset(self.REG_SCRATCH3, ARM64Emitter.COND_HS)

        # VX = VY - VX
        self.emitter.sub_reg(self.REG_SCRATCH0, self.REG_SCRATCH1, self.REG_SCRATCH0)
        self.emitter.and_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 0xFF)

        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.strb(self.REG_SCRATCH3, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_8XYE(self, x: int, y: int, pc: int) -> bool:
        '''8XYE: VX <<= 1 (or VX = VY << 1 depending on quirk)'''
        if self.quirks.shift:
            self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        else:
            self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + y)

        # VF = MSB before shift
        self.emitter.lsr_imm(self.REG_SCRATCH1, self.REG_SCRATCH0, 7)

        # Shift left
        self.emitter.lsl_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 1)
        self.emitter.and_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 0xFF)

        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.strb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + 0xF)

        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    # -------------------------------------------------------------------------
    # 9XY0: Skip if VX != VY
    # -------------------------------------------------------------------------

    def _compile_9XY0(self, opcode: int, pc: int) -> bool:
        '''9XY0: Skip next instruction if VX != VY'''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        skip_amount = self._get_skip_amount(pc)

        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)
        self.emitter.cmp_reg(self.REG_SCRATCH0, self.REG_SCRATCH1)

        self.emitter.mov_imm(self.REG_SCRATCH0, pc + 2)
        self.emitter.mov_imm(self.REG_SCRATCH1, pc + 2 + skip_amount)
        self.emitter.csel(self.REG_SCRATCH0, self.REG_SCRATCH1, self.REG_SCRATCH0,
                         ARM64Emitter.COND_NE)

        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

        # End block - PC was conditionally modified
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # ANNN: I = NNN
    # -------------------------------------------------------------------------

    def _compile_ANNN(self, opcode: int, pc: int) -> bool:
        '''ANNN: Set I = NNN'''
        nnn = opcode & 0x0FFF
        self.emitter.mov_imm(self.REG_SCRATCH0, nnn)
        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_I)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    # -------------------------------------------------------------------------
    # BNNN: Jump to V0 + NNN
    # -------------------------------------------------------------------------

    def _compile_BNNN(self, opcode: int, pc: int) -> bool:
        '''BNNN: Jump to V0 + NNN (or VX + XNN with quirk)'''
        nnn = opcode & 0x0FFF

        if self.quirks.jump:
            # BXNN: Jump to VX + XNN
            x = (opcode & 0x0F00) >> 8
            self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        else:
            # BNNN: Jump to V0 + NNN
            self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V)

        self.emitter.add_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, nnn & 0xFFF)
        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True

    # -------------------------------------------------------------------------
    # EXXX: Key operations
    # -------------------------------------------------------------------------

    def _compile_EXXX(self, opcode: int, pc: int) -> bool:
        '''Compile EX9E and EXA1 (key skip instructions) - trap to Python'''
        return self._emit_trap(opcode, pc, TrapCode.CHECK_KEY)

    # -------------------------------------------------------------------------
    # FXXX: Misc operations
    # -------------------------------------------------------------------------

    def _compile_FXXX(self, opcode: int, pc: int) -> bool:
        '''Compile FX** instructions'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF

        if nn == 0x07:
            return self._compile_FX07(x, pc)
        elif nn == 0x0A:
            return self._emit_trap(opcode, pc, TrapCode.WAIT_KEY)
        elif nn == 0x15:
            return self._compile_FX15(x, pc)
        elif nn == 0x18:
            return self._compile_FX18(x, pc)
        elif nn == 0x1E:
            return self._compile_FX1E(x, pc)
        elif nn == 0x29:
            return self._compile_FX29(x, pc)
        elif nn == 0x33:
            return self._compile_FX33(x, pc, opcode)
        elif nn == 0x55:
            return self._emit_trap(opcode, pc, TrapCode.STORE_REGS)
        elif nn == 0x65:
            return self._emit_trap(opcode, pc, TrapCode.LOAD_REGS)
        elif nn == 0x01:
            # FN01: Select drawing plane(s) - trap to Python for display handling
            return self._emit_trap(opcode, pc, TrapCode.DISPLAY)
        elif nn == 0x02:
            # F002: Load audio pattern from I
            return self._emit_trap(opcode, pc, TrapCode.AUDIO)
        elif nn == 0x3A:
            # FX3A: Set pitch
            return self._emit_trap(opcode, pc, TrapCode.AUDIO)
        else:
            # Unknown or complex FX instruction - trap
            return self._emit_trap(opcode, pc, TrapCode.SPECIAL)

    def _compile_FX07(self, x: int, pc: int) -> bool:
        '''FX07: VX = delay timer'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_DELAY)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_FX15(self, x: int, pc: int) -> bool:
        '''FX15: delay timer = VX'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_DELAY)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_FX18(self, x: int, pc: int) -> bool:
        '''FX18: sound timer = VX'''
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_SOUND)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_FX1E(self, x: int, pc: int) -> bool:
        '''FX1E: I += VX'''
        self.emitter.ldr_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_I)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + x)
        self.emitter.add_reg(self.REG_SCRATCH0, self.REG_SCRATCH0, self.REG_SCRATCH1)
        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_I)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_FX29(self, x: int, pc: int) -> bool:
        '''FX29: I = font address for digit VX'''
        # Font is at address 0, each digit is 5 bytes
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        # I = VX * 5
        self.emitter.mov_imm(self.REG_SCRATCH1, 5)
        # Use add to multiply by 5: x*5 = x*4 + x = (x<<2) + x
        self.emitter.lsl_imm(self.REG_SCRATCH1, self.REG_SCRATCH0, 2)
        self.emitter.add_reg(self.REG_SCRATCH0, self.REG_SCRATCH1, self.REG_SCRATCH0)
        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_I)
        self._emit_store_pc(pc + 2)
        self._emit_block_end()
        return True

    def _compile_FX33(self, x: int, pc: int, opcode: int) -> bool:
        '''FX33: Store BCD of VX at I, I+1, I+2 - trap due to complexity'''
        return self._emit_trap(opcode, pc, TrapCode.SPECIAL)

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _emit_store_pc(self, new_pc: int):
        '''Store a new PC value.'''
        self.emitter.mov_imm(self.REG_SCRATCH0, new_pc)
        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

    def _emit_block_end(self):
        '''Emit code to end the block and return to Python.'''
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()

    def _emit_trap(self, opcode: int, pc: int, trap_code: int) -> bool:
        '''
        Emit code to trap back to Python.

        Stores the trap code and opcode, updates PC, and returns.
        '''
        # Store PC first (before the current instruction)
        self._emit_store_pc(pc)

        # Store trap code
        self.emitter.mov_imm(self.REG_SCRATCH0, trap_code)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_TRAP_CODE)

        # Store opcode that caused the trap
        self.emitter.mov_imm(self.REG_SCRATCH0, opcode)
        self.emitter.strh(self.REG_SCRATCH0, self.REG_STATE, OFFSET_TRAP_OPCODE)

        # Return trap code
        self.emitter.mov_imm(self.REG_RETVAL, trap_code)
        self.emitter.ret()
        return True
