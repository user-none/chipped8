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

class Timers:

    def __init__(self):
        self._sound = 0
        self._delay = 0

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]

        d = object.__new__(self.__class__)
        d._sound = self._sound
        d._delay = self._delay

        memo[id(self)] = d
        return d

    @property
    def sound(self) -> int:
        return self._sound

    @sound.setter
    def sound(self, val: int) -> None:
        self._sound = val
        if self._sound < 0:
            self._sound = 0
        else:
            self._sound = maths.reduce_ushort(self._sound)

    @property
    def delay(self) -> int:
        return self._delay

    @delay.setter
    def delay(self, val: int) -> None:
        self._delay = val
        if self._delay < 0:
            self._delay = 0
        else:
            self._delay = maths.reduce_ushort(val)
