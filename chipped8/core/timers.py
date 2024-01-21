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
        t = Timers()
        t._sound = self._sound
        t._delay = self._delay
        return t

    def set_sound(self, val):
        self._sound = maths.reduce_ushort(val)

    def get_sound(self):
        return self._sound

    def update_sound(self):
        if self._sound > 0:
            self._sound = self._sound - 1

    def set_delay(self, val):
        self._delay = maths.reduce_ushort(val)

    def get_delay(self):
        return self._delay

    def update_delay(self):
        if self._delay > 0:
            self._delay = self._delay - 1

