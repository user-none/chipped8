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
        
    def set_V(self, idx, val):
        if idx < 0 or idx > 15:
            raise Exception('Invalid register V{0}'.format(idx))

        self._V[idx] = maths.reduce_uchar(val)
    
    def get_V(self, idx):
        if idx < 0 or idx > 15: 
            raise Exception('V{0} not a valid register'.format(idx))

        return self._V[idx]

    def dump_V(self):
        return [ x for x in self._V ]

    def set_I(self, val):
        self._I = maths.reduce_ushort(val)

    def get_I(self):
        return self._I

    def set_PC(self, val):
        val = maths.reduce_ushort(val)
        if val < 512:
            val = 512
        self._PC = val

    def get_PC(self):
        return self._PC

    def advance_PC(self):
        self.set_PC(self.get_PC() + 2)

    def set_RPL(self, idx, val):
        if idx < 0 or idx > 15:
            raise Exception('Invalid flag slot RPL{0}'.format(idx))

        self._RPL[idx] = maths.reduce_ushort(val)

    def get_RPL(self, idx):
        if idx < 0 or idx > 15:
            raise Exception('RPL{0} not a valid flag slot'.format(idx))

        return self._RPL[idx]

    def export_RPL(self):
        return deepcopy(self._RPL)

    def import_RPL(self, rpl=bytearray(0)):
        if len(rpl) != 16:
            raise Exception('RPL flags wrong length: need 16 have {0}', len(rpl))
        self._RPL = deepcopy(rpl)

