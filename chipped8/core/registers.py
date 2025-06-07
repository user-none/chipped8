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

from . import maths

class Registers:
    
    def __init__(self):
        self._V = bytearray(16)
        self._I = 0
        self._PC = 512
        # Flags register. They're supposed to be saved to persist
        # between loading different ROMs.
        self._RPL = bytearray(16)

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]

        d = object.__new__(self.__class__)
        d._V = deepcopy(self._V, memo)
        d._I = self._I
        d._PC = self._PC
        d._RPL = deepcopy(self._RPL, memo)

        memo[id(self)] = d
        return d
        
    def set_V(self, idx: int, val: int) -> None:
        if idx < 0 or idx > 15:
            raise IndexError(f'Invalid register V{idx}')

        self._V[idx] = maths.reduce_uchar(val)
    
    def get_V(self, idx) -> int:
        if idx < 0 or idx > 15: 
            raise IndexError(f'V{idx} not a valid register')

        return self._V[idx]

    def dump_V(self) -> bytearray:
        return self._V[:]

    def set_I(self, val: int) -> None:
        self._I = maths.reduce_ushort(val)

    def get_I(self) -> int:
        return self._I

    def set_PC(self, val: int) -> None:
        val = maths.reduce_ushort(val)
        if val < 512:
            val = 512
        self._PC = val

    def get_PC(self) -> int:
        return self._PC

    def advance_PC(self) -> None:
        self.set_PC(self.get_PC() + 2)

    def set_RPL(self, idx: int, val: int) -> None:
        if idx < 0 or idx > 15:
            raise IndexError(f'Invalid flag slot RPL{idx}')

        self._RPL[idx] = maths.reduce_ushort(val)

    def get_RPL(self, idx: int) -> int:
        if idx < 0 or idx > 15:
            raise IndexError(f'RPL{idx} not a valid flag slot')

        return self._RPL[idx]

    def export_RPL(self) -> bytearray:
        return self._RPL[:]

    def import_RPL(self, rpl: bytes) -> None:
        if len(rpl) != 16:
            raise Exception(f'RPL flags wrong length: need 16 have {len(rpl)}')
        self._RPL = bytearray(rpl)
