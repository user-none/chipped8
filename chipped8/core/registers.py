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

from . import maths

class Registers:
    
    def __init__(self):
        self._V = bytearray(16)
        self._I = 0
        self._PC = 512

    def set_V(self, idx, val):
        if idx < 0 or idx > 15:
            raise Exception('Invalid register V{0}'.format(idx))

        self._V[idx] = maths.reduce_uchar(val)
    
    def get_V(self, idx):
        if idx < 0 or idx > 15: 
            raise Exception('V{0} not a valid register'.format(idx))

        return self._V[idx]

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

