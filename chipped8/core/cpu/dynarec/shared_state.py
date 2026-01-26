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
Shared state structure for communication between Python and JIT code.

This ctypes Structure defines the memory layout that both Python and
the generated ARM64 code can access.
'''

import ctypes

from ...memory import MEMORY_SIZE
from ...keys import KeyState


class SharedState(ctypes.Structure):
    '''
    Shared state between Python and JIT-compiled code.

    This structure is passed to generated ARM64 code, which reads and
    writes fields directly. The layout must remain stable.

    IMPORTANT: Frequently accessed fields (V registers, PC, I, etc.) are
    placed first to ensure their offsets fit within ARM64 immediate
    offset limits (max 4095 for byte loads/stores).
    '''
    _fields_ = [
        # --- Frequently accessed fields first (offset < 4096) ---

        # V registers (V0-VF, 16 bytes) - offset 0
        ('V', ctypes.c_uint8 * 16),

        # RPL registers (XO-Chip, 16 bytes) - offset 16
        ('RPL', ctypes.c_uint8 * 16),

        # Program counter - offset 32
        ('pc', ctypes.c_uint32),

        # Index register I (needs 16+ bits for XO-Chip) - offset 36
        ('I', ctypes.c_uint32),

        # Stack (16 entries of 16-bit addresses) - offset 40
        ('stack', ctypes.c_uint16 * 16),

        # Stack pointer - offset 72
        ('sp', ctypes.c_uint8),

        # Timers - offset 73, 74
        ('delay_timer', ctypes.c_uint8),
        ('sound_timer', ctypes.c_uint8),

        # Key state (16 keys, 0=up, 1=down) - offset 75
        ('keys', ctypes.c_uint8 * 16),

        # Audio pattern (16 bytes) and pitch - offset 91, 107
        ('pattern', ctypes.c_uint8 * 16),
        ('pitch', ctypes.c_uint8),

        # Control fields - set by native code to communicate with Python
        ('trap_code', ctypes.c_uint8),
        ('trap_opcode', ctypes.c_uint16),

        # Quirks (copied at init, read-only from JIT perspective)
        ('quirk_shift', ctypes.c_uint8),
        ('quirk_memoryIncrementByX', ctypes.c_uint8),
        ('quirk_memoryLeaveIUnchanged', ctypes.c_uint8),
        ('quirk_wrap', ctypes.c_uint8),
        ('quirk_jump', ctypes.c_uint8),
        ('quirk_logic', ctypes.c_uint8),

        # Execution state
        ('draw_occurred', ctypes.c_uint8),

        # ROM boundary (address where ROM ends, typically ram_start)
        ('rom_end', ctypes.c_uint16),

        # --- Large fields at end (accessed via pointer arithmetic) ---

        # Memory (64KB) - offset ~120, accessed via separate pointer
        ('memory', ctypes.c_uint8 * MEMORY_SIZE),
    ]


# Pre-calculate field offsets for use in code generation
OFFSET_MEMORY = SharedState.memory.offset
OFFSET_V = SharedState.V.offset
OFFSET_RPL = SharedState.RPL.offset
OFFSET_I = SharedState.I.offset
OFFSET_PC = SharedState.pc.offset
OFFSET_STACK = SharedState.stack.offset
OFFSET_SP = SharedState.sp.offset
OFFSET_DELAY = SharedState.delay_timer.offset
OFFSET_SOUND = SharedState.sound_timer.offset
OFFSET_KEYS = SharedState.keys.offset
OFFSET_PATTERN = SharedState.pattern.offset
OFFSET_PITCH = SharedState.pitch.offset
OFFSET_TRAP_CODE = SharedState.trap_code.offset
OFFSET_TRAP_OPCODE = SharedState.trap_opcode.offset
OFFSET_QUIRK_SHIFT = SharedState.quirk_shift.offset
OFFSET_QUIRK_MEMORY_INCREMENT_BY_X = SharedState.quirk_memoryIncrementByX.offset
OFFSET_QUIRK_MEMORY_LEAVE_I_UNCHANGED = SharedState.quirk_memoryLeaveIUnchanged.offset
OFFSET_QUIRK_WRAP = SharedState.quirk_wrap.offset
OFFSET_QUIRK_JUMP = SharedState.quirk_jump.offset
OFFSET_QUIRK_LOGIC = SharedState.quirk_logic.offset
OFFSET_DRAW_OCCURRED = SharedState.draw_occurred.offset


def transfer_state_to_python(shared_state: SharedState, memory, registers, stack, timers, keys, audio):
    '''
    Transfer state from SharedState back to Python objects.

    Called after JIT code execution to sync state back to Python.
    '''
    # Memory
    memory._memory[:] = bytes(shared_state.memory)

    # Registers
    v_len = min(16, len(registers._V))
    for i in range(v_len):
        registers._V[i] = shared_state.V[i]
    registers._I = shared_state.I
    registers._PC = shared_state.pc
    rpl_len = min(16, len(registers._RPL))
    for i in range(rpl_len):
        registers._RPL[i] = shared_state.RPL[i]

    # Stack
    stack._stack = []
    for i in range(shared_state.sp):
        stack._stack.append(shared_state.stack[i])

    # Timers
    timers._sound = shared_state.sound_timer
    timers._delay = shared_state.delay_timer

    # Keys - convert back to KeyState enum
    for i in range(16):
        keys._keys[i] = KeyState.down if shared_state.keys[i] == 1 else KeyState.up

    # Audio
    audio._pattern = bytearray(shared_state.pattern)
    audio.pitch = shared_state.pitch


def transfer_state_to_dynarec(shared_state: SharedState, memory, registers, stack, timers, keys, audio):
    '''
    Transfer state from Python objects to SharedState.

    Called before JIT code execution to sync state from Python.
    '''
    # Memory
    ctypes.memmove(
        ctypes.addressof(shared_state.memory),
        bytes(memory._memory),
        len(memory._memory)
    )

    # Registers
    v_len = min(16, len(registers._V))
    for i in range(v_len):
        shared_state.V[i] = registers._V[i]
    shared_state.I = registers._I
    shared_state.pc = registers._PC
    rpl_len = min(16, len(registers._RPL))
    for i in range(rpl_len):
        shared_state.RPL[i] = registers._RPL[i]

    # Stack
    for i in range(len(stack._stack)):
        shared_state.stack[i] = stack._stack[i]
    shared_state.sp = len(stack._stack)

    # Timers
    shared_state.sound_timer = timers._sound
    shared_state.delay_timer = timers._delay

    # Keys - convert KeyState enum to 0/1
    for i in range(16):
        shared_state.keys[i] = 1 if keys._keys[i] == KeyState.down else 0

    # Audio
    for i in range(16):
        shared_state.pattern[i] = audio._pattern[i]
    shared_state.pitch = audio.pitch

    # ROM boundary
    shared_state.rom_end = memory.ram_start()

    # Reset control fields
    shared_state.trap_code = 0
    shared_state.trap_opcode = 0
    shared_state.draw_occurred = 0
