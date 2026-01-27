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
Trap and state codes for dynarec execution.

These codes are used to communicate between JIT-compiled code and Python.
'''

from enum import IntEnum


class TrapCode(IntEnum):
    '''
    Trap codes returned by JIT code to indicate why execution stopped.

    The JIT code stores the trap code in SharedState.trap_code and returns
    it as the function return value.
    '''
    NONE = 0             # No trap; continue execution

    # Display operations - require Python display object
    DRAW = 1             # DXYN: Draw sprite
    DISPLAY = 2          # 00E0, 00CN, 00DN, 00FB, 00FC, 00FE, 00FF

    # Input operations
    WAIT_KEY = 3         # FX0A: Wait for keypress
    CHECK_KEY = 4        # EX9E, EXA1: Skip based on key state

    # Random number
    RANDOM = 5           # CXNN: Random number

    # Memory operations (complex quirk handling)
    STORE_REGS = 6       # FX55: Store V0-VX to memory
    LOAD_REGS = 7        # FX65: Load V0-VX from memory

    # Audio
    AUDIO = 8            # F002, FX3A: Audio pattern/pitch

    # Special/complex operations
    SPECIAL = 9          # F000, FX30, FX33, FX75, FX85, etc.

    # Jump operations (need address validation)
    JUMP_BNNN = 10       # BNNN/BXNN: Jump with offset (needs SMC check)

    # Stack errors
    STACK_OVERFLOW = 253   # CALL with full stack
    STACK_UNDERFLOW = 254  # RET with empty stack

    # Exit
    EXIT = 255           # 00FD: Exit interpreter
