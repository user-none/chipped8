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

from enum import Enum, auto

from .quirks import Quirks

class PlatformTypes(Enum):
    originalChip8 = 'originalChip8'
    hybridVIP = 'hybridVIP'
    modernChip8 = 'modernChip8'
    chip8x = 'chip8x'
    chip48 = 'chip48'
    superchip1 = 'superchip1'
    superchip = 'superchip'
    megachip8 = 'megachip8'
    xochip = 'xochip'

    def __str__(self):
        return self.value

class Platform():

    def __init__(self, platform: PlatformTypes):
        self._platform = platform

    def quirks(self):
        q = Quirks()

        if self._platform == PlatformTypes.originalChip8 or self._platform == PlatformTypes.hybridVIP or self._platform == PlatformTypes.chip8x:
            q.vblank = True
            q.logic = True
        elif self._platform == PlatformTypes.chip48:
            q.shift(True)
            q.memoryIncrementByX = True
            q.jump = True
        elif self._platform == PlatformTypes.superchip1 or self._platform == PlatformTypes.superchip or self._platform == PlatformTypes.megachip8:
            q.shift = True
            q.memoryLeaveIUnchanged = True
            q.jump = True
        elif self._platform == PlatformTypes.xochip:
            q.wrap = True

        return q

    def tickrate(self):
        if self._platform == PlatformTypes.modernChip8:
            return 12
        elif self._platform == PlatformTypes.originalChip8 or self._platform == PlatformTypes.hybridVIP or self._platform == PlatformTypes.chip8x:
            return 15
        elif self._platform == PlatformTypes.chip48 or self._platform == PlatformTypes.superchip1 or self._platform == PlatformTypes.superchip:
            return 30
        elif self._platform == PlatformTypes.xochip:
            return 100
        elif self._platform == PlatformTypes.megachip8:
            return 1000

        return 15

