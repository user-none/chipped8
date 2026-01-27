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
Dynamic recompiler CPU implementation.

Translates Chip-8 bytecode to ARM64 machine code at runtime for
native execution on Apple Silicon Macs.
'''

import ctypes
from random import randint

from ..icpu import iCPU
from .shared_state import SharedState, transfer_state_to_dynarec, transfer_state_to_python
from .state_codes import TrapCode
from .jit_memory import JITMemory
from .arm64 import BlockCompiler

from ...display import Plane, ResolutionMode
from ...exceptions import ExitInterpreterException
from ...memory import MEMORY_SIZE


class DynarecCPU(iCPU):
    '''
    Dynamic recompiler CPU for Chip-8.

    Compiles Chip-8 bytecode to native ARM64 code and executes it directly.
    Complex operations (display, input, audio) trap back to Python.
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

        # Initialize JIT infrastructure
        self._shared_state = SharedState()
        self._jit_memory = JITMemory(size=4 * 1024 * 1024)  # 4MB
        self._compiler = BlockCompiler(quirks)
        self._block_cache = {}  # pc -> code_offset

        # Copy quirks to shared state
        self._shared_state.quirk_shift = 1 if quirks.shift else 0
        self._shared_state.quirk_memoryIncrementByX = 1 if quirks.memoryIncrementByX else 0
        self._shared_state.quirk_memoryLeaveIUnchanged = 1 if quirks.memoryLeaveIUnchanged else 0
        self._shared_state.quirk_wrap = 1 if quirks.wrap else 0
        self._shared_state.quirk_jump = 1 if quirks.jump else 0
        self._shared_state.quirk_logic = 1 if quirks.logic else 0

    def copy_state(self, d):
        '''Copy state from another CPU instance.'''
        if isinstance(d, DynarecCPU):
            # Copy block cache if same type
            self._block_cache = d._block_cache.copy()

    def _is_in_rom_region(self, addr: int) -> bool:
        '''Check if address is within ROM region (0x200 to rom_end-1).'''
        return 0x200 <= addr < self._shared_state.rom_end

    def _write_overlaps_rom(self, start: int, length: int) -> bool:
        '''Check if a write range [start, start+length) overlaps ROM region.'''
        write_end = start + length
        rom_start = 0x200
        rom_end = self._shared_state.rom_end
        # Two ranges overlap if: start < rom_end AND rom_start < write_end
        return start < rom_end and rom_start < write_end

    def _write_code_safe(self, code: bytes) -> int:
        '''
        Write code to JIT buffer, resetting if necessary.

        If the buffer doesn't have space for the code, resets the buffer
        and clears the block cache, then writes the code.

        Args:
            code: The machine code bytes to write

        Returns:
            The offset in the buffer where the code was written
        '''
        if not self._jit_memory.has_space_for(len(code)):
            # Buffer full - reset and clear cache
            self.invalidate_cache()

        return self._jit_memory.write_code(code)

    def execute_next_op(self):
        '''Execute the next Chip-8 instruction.'''
        self._draw_occurred = False

        # Sync quirks (may have been changed by test framework)
        self._compiler.quirks = self._quirks
        self._shared_state.quirk_shift = 1 if self._quirks.shift else 0
        self._shared_state.quirk_memoryIncrementByX = 1 if self._quirks.memoryIncrementByX else 0
        self._shared_state.quirk_memoryLeaveIUnchanged = 1 if self._quirks.memoryLeaveIUnchanged else 0
        self._shared_state.quirk_wrap = 1 if self._quirks.wrap else 0
        self._shared_state.quirk_jump = 1 if self._quirks.jump else 0
        self._shared_state.quirk_logic = 1 if self._quirks.logic else 0

        # Transfer Python state to SharedState
        transfer_state_to_dynarec(
            self._shared_state,
            self._memory,
            self._registers,
            self._stack,
            self._timers,
            self._keys,
            self._audio
        )

        pc = self._shared_state.pc

        # Check if JIT buffer needs reset (approaching capacity)
        if self._jit_memory.needs_reset():
            self.invalidate_cache()

        # Only cache blocks within ROM region
        if self._is_in_rom_region(pc):
            if pc not in self._block_cache:
                code = self._compiler.compile_block(
                    bytes(self._shared_state.memory),
                    pc
                )
                offset = self._write_code_safe(code)
                self._block_cache[pc] = offset
            offset = self._block_cache[pc]
            block_func = self._jit_memory.get_callable(offset)
        else:
            # Outside ROM - compile but don't cache (dynamic code)
            code = self._compiler.compile_block(
                bytes(self._shared_state.memory),
                pc
            )
            offset = self._write_code_safe(code)
            block_func = self._jit_memory.get_callable(offset)
        trap_code = block_func(ctypes.byref(self._shared_state))

        # Handle trap if needed
        if trap_code != TrapCode.NONE:
            self._handle_trap(trap_code)

        # Transfer state back to Python
        transfer_state_to_python(
            self._shared_state,
            self._memory,
            self._registers,
            self._stack,
            self._timers,
            self._keys,
            self._audio
        )

        self._draw_occurred = bool(self._shared_state.draw_occurred)

    def _handle_trap(self, trap_code: int):
        '''Handle a trap from native code.'''
        opcode = self._shared_state.trap_opcode

        if trap_code == TrapCode.DRAW:
            self._handle_draw(opcode)
        elif trap_code == TrapCode.DISPLAY:
            self._handle_display(opcode)
        elif trap_code == TrapCode.RANDOM:
            self._handle_random(opcode)
        elif trap_code == TrapCode.WAIT_KEY:
            self._handle_wait_key(opcode)
        elif trap_code == TrapCode.CHECK_KEY:
            self._handle_check_key(opcode)
        elif trap_code == TrapCode.STORE_REGS:
            self._handle_store_regs(opcode)
        elif trap_code == TrapCode.LOAD_REGS:
            self._handle_load_regs(opcode)
        elif trap_code == TrapCode.AUDIO:
            self._handle_audio(opcode)
        elif trap_code == TrapCode.SPECIAL:
            self._handle_special(opcode)
        elif trap_code == TrapCode.JUMP_BNNN:
            self._handle_jump_bnnn(opcode)
        elif trap_code == TrapCode.STACK_OVERFLOW:
            raise OverflowError('Stack limit exceeded')
        elif trap_code == TrapCode.STACK_UNDERFLOW:
            raise ValueError('Stack is empty')
        elif trap_code == TrapCode.EXIT:
            raise ExitInterpreterException()

    def _handle_draw(self, opcode: int):
        '''Handle DXYN draw instruction.'''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F

        vx = self._shared_state.V[x]
        vy = self._shared_state.V[y]

        # Need to sync memory and registers for draw
        self._memory._memory[:] = bytes(self._shared_state.memory)
        for i in range(16):
            self._registers._V[i] = self._shared_state.V[i]
        self._registers._I = self._shared_state.I

        self._display.draw(vx, vy, n, self._quirks.wrap, self._registers, self._memory)

        # Copy VF back (collision flag)
        self._shared_state.V[0xF] = self._registers._V[0xF]

        self._shared_state.draw_occurred = 1
        self._shared_state.pc += 2

    def _handle_display(self, opcode: int):
        '''Handle display control instructions (00E0, 00CN, etc.).'''
        if opcode == 0x00E0:
            self._display.clear_screen()
        elif opcode == 0x00FE:
            self._display.resmode = ResolutionMode.lowres
        elif opcode == 0x00FF:
            self._display.resmode = ResolutionMode.hires
        elif opcode == 0x00FB:
            self._display.scroll_right()
        elif opcode == 0x00FC:
            self._display.scroll_left()
        elif (opcode & 0xFFF0) == 0x00C0:
            n = opcode & 0x000F
            self._display.scroll_down(n)
        elif (opcode & 0xFFF0) == 0x00D0:
            n = opcode & 0x000F
            self._display.scroll_up(n)
        elif (opcode & 0xF0FF) == 0xF001:
            # FN01: Select plane
            n = (opcode & 0x0F00) >> 8
            plane = Plane(0)
            if n & 1:
                plane = plane | Plane.p1
            if n & 2:
                plane = plane | Plane.p2
            self._display.plane = plane

        self._shared_state.draw_occurred = 1
        self._shared_state.pc += 2

    def _handle_random(self, opcode: int):
        '''Handle CXNN random instruction.'''
        x = (opcode & 0x0F00) >> 8
        mask = opcode & 0x00FF
        self._shared_state.V[x] = randint(0, 255) & mask
        self._shared_state.pc += 2

    def _handle_wait_key(self, opcode: int):
        '''Handle FX0A wait for key instruction.'''
        x = (opcode & 0x0F00) >> 8

        # Check if any key is pressed
        for i in range(16):
            if self._shared_state.keys[i] == 1:
                self._shared_state.V[x] = i
                self._shared_state.pc += 2
                return

        # No key pressed - don't advance PC (will retry next frame)

    def _handle_check_key(self, opcode: int):
        '''Handle EX9E and EXA1 key skip instructions.'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF
        key = self._shared_state.V[x] & 0x0F

        key_pressed = self._shared_state.keys[key] == 1

        # Calculate skip amount - check if next instruction is F000 NNNN (4 bytes)
        pc = self._shared_state.pc
        # Bounds check for reading next opcode
        if pc + 4 > MEMORY_SIZE:
            # Near end of memory, can't have 4-byte instruction
            skip_amount = 2
        else:
            next_opcode = (self._shared_state.memory[pc + 2] << 8) | self._shared_state.memory[pc + 3]
            skip_amount = 4 if next_opcode == 0xF000 else 2

        if nn == 0x9E:
            # EX9E: Skip if key pressed
            if key_pressed:
                self._shared_state.pc += 2 + skip_amount
            else:
                self._shared_state.pc += 2
        elif nn == 0xA1:
            # EXA1: Skip if key not pressed
            if not key_pressed:
                self._shared_state.pc += 2 + skip_amount
            else:
                self._shared_state.pc += 2

    def _handle_store_regs(self, opcode: int):
        '''Handle FX55 or 5XY2 store registers instruction.'''
        I = self._shared_state.I
        top_nibble = (opcode & 0xF000) >> 12

        if top_nibble == 0x5:
            # 5XY2: Store VX..VY to memory at I
            x = (opcode & 0x0F00) >> 8
            y = (opcode & 0x00F0) >> 4
            # Ensure x <= y to prevent negative range
            if x > y:
                x, y = y, x
            num_bytes = y - x + 1
        else:
            # FX55: Store V0..VX to memory at I
            x = (opcode & 0x0F00) >> 8
            num_bytes = x + 1

        # Bounds check: ensure write doesn't exceed memory
        if I + num_bytes > MEMORY_SIZE:
            raise IndexError(f'Memory write out of bounds: I={I:#x}, bytes={num_bytes}')

        # SMC detection: check if write range overlaps ROM
        if self._write_overlaps_rom(I, num_bytes):
            self.invalidate_cache()

        if top_nibble == 0x5:
            # 5XY2: Store VX..VY to memory at I
            for i in range(x, y + 1):
                self._shared_state.memory[I + (i - x)] = self._shared_state.V[i]
            # I is not modified for 5XY2
        else:
            # FX55: Store V0..VX to memory at I
            for i in range(x + 1):
                self._shared_state.memory[I + i] = self._shared_state.V[i]

            if not self._quirks.memoryLeaveIUnchanged:
                if self._quirks.memoryIncrementByX:
                    self._shared_state.I = I + x
                else:
                    self._shared_state.I = I + x + 1

        self._shared_state.pc += 2

    def _handle_load_regs(self, opcode: int):
        '''Handle FX65 or 5XY3 load registers instruction.'''
        top_nibble = (opcode & 0xF000) >> 12

        if top_nibble == 0x5:
            # 5XY3: Load VX..VY from memory at I
            x = (opcode & 0x0F00) >> 8
            y = (opcode & 0x00F0) >> 4
            # Ensure x <= y to prevent negative range
            if x > y:
                x, y = y, x
            I = self._shared_state.I
            num_bytes = y - x + 1
            # Bounds check: ensure I + num_bytes - 1 < MEMORY_SIZE
            if I + num_bytes > MEMORY_SIZE:
                raise IndexError(f'Memory read out of bounds: I={I:#x}, bytes={num_bytes}')
            for i in range(x, y + 1):
                self._shared_state.V[i] = self._shared_state.memory[I + (i - x)]
            # I is not modified for 5XY3
        else:
            # FX65: Load V0..VX from memory at I
            x = (opcode & 0x0F00) >> 8
            I = self._shared_state.I
            num_bytes = x + 1
            # Bounds check: ensure I + num_bytes - 1 < MEMORY_SIZE
            if I + num_bytes > MEMORY_SIZE:
                raise IndexError(f'Memory read out of bounds: I={I:#x}, bytes={num_bytes}')

            for i in range(x + 1):
                self._shared_state.V[i] = self._shared_state.memory[I + i]

            if not self._quirks.memoryLeaveIUnchanged:
                if self._quirks.memoryIncrementByX:
                    self._shared_state.I = I + x
                else:
                    self._shared_state.I = I + x + 1

        self._shared_state.pc += 2

    def _handle_audio(self, opcode: int):
        '''Handle audio instructions (F002, FX3A).'''
        nn = opcode & 0x00FF

        if nn == 0x02:
            # F002: Load audio pattern from I (16 bytes)
            I = self._shared_state.I
            # Bounds check: ensure I + 16 <= MEMORY_SIZE
            if I + 16 > MEMORY_SIZE:
                raise IndexError(f'Memory read out of bounds: I={I:#x}, bytes=16')
            for i in range(16):
                self._shared_state.pattern[i] = self._shared_state.memory[I + i]
        elif nn == 0x3A:
            # FX3A: Set pitch
            x = (opcode & 0x0F00) >> 8
            self._shared_state.pitch = self._shared_state.V[x]

        self._shared_state.pc += 2

    def _handle_special(self, opcode: int):
        '''Handle special/complex instructions.'''
        nn = opcode & 0x00FF
        x = (opcode & 0x0F00) >> 8

        if nn == 0x00 and (opcode & 0xF000) == 0xF000:
            # F000 NNNN: Load I with 16-bit address (4-byte instruction)
            self._shared_state.pc += 2
            pc = self._shared_state.pc
            # Bounds check: ensure pc + 1 < MEMORY_SIZE
            if pc + 2 > MEMORY_SIZE:
                raise IndexError(f'Memory read out of bounds: pc={pc:#x}, bytes=2')
            addr = (self._shared_state.memory[pc] << 8) | \
                   self._shared_state.memory[pc + 1]
            self._shared_state.I = addr
            self._shared_state.pc += 2
        elif nn == 0x30:
            # FX30: Point I to large font
            digit = self._shared_state.V[x]
            # Large font starts at offset 80 (after 16 small fonts * 5 bytes)
            self._shared_state.I = 80 + (digit * 10)
            self._shared_state.pc += 2
        elif nn == 0x33:
            # FX33: BCD (writes 3 bytes at I, I+1, I+2)
            I = self._shared_state.I

            # Bounds check: ensure I + 3 <= MEMORY_SIZE
            if I + 3 > MEMORY_SIZE:
                raise IndexError(f'Memory write out of bounds: I={I:#x}, bytes=3')

            # SMC detection: check if write range overlaps ROM
            if self._write_overlaps_rom(I, 3):
                self.invalidate_cache()

            n = self._shared_state.V[x]
            self._shared_state.memory[I] = n // 100
            self._shared_state.memory[I + 1] = (n // 10) % 10
            self._shared_state.memory[I + 2] = n % 10
            self._shared_state.pc += 2
        elif nn == 0x75:
            # FX75: Store V0-VX in RPL
            if x > 15:
                raise IndexError(f'RPL register index out of bounds: {x}')
            for i in range(x + 1):
                self._shared_state.RPL[i] = self._shared_state.V[i]
            self._shared_state.pc += 2
        elif nn == 0x85:
            # FX85: Load V0-VX from RPL
            if x > 15:
                raise IndexError(f'RPL register index out of bounds: {x}')
            for i in range(x + 1):
                self._shared_state.V[i] = self._shared_state.RPL[i]
            self._shared_state.pc += 2
        else:
            # Unknown - just advance PC
            self._shared_state.pc += 2

    def _handle_jump_bnnn(self, opcode: int):
        '''Handle BNNN: Jump to V0 + NNN (or VX + XNN with quirk).

        Validates and masks the jump address, and invalidates cache if
        jumping outside ROM (possible self-modifying code).
        '''
        nnn = opcode & 0x0FFF

        if self._quirks.jump:
            # BXNN: Jump to VX + XNN
            x = (opcode & 0x0F00) >> 8
            target = nnn + self._shared_state.V[x]
        else:
            # BNNN: Jump to V0 + NNN
            target = nnn + self._shared_state.V[0]

        # Mask to 16-bit address space for safety
        target = target & 0xFFFF

        # SMC detection: if jumping outside ROM, invalidate cache
        # This matches behavior of other interpreters
        if target >= self._shared_state.rom_end:
            self.invalidate_cache()

        self._shared_state.pc = target

    def draw_occurred(self) -> bool:
        '''Return whether a draw operation occurred in the last instruction.'''
        return self._draw_occurred

    def invalidate_cache(self):
        '''Invalidate the entire block cache (e.g., after SMC detected).'''
        self._block_cache.clear()
        self._jit_memory.reset()
