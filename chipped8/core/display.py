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

from .constants import *

class Displaly():

    def __init__(self):
        self._screen_buffer = bytearray(SCREEN_PIXEL_COUNT)
        self._update_screen = False

    def __deepcopy__(self, memo):
        d = Displaly()
        d._screen_buffer = deepcopy(self._screen_buffer)
        d._update_screen = self._update_screen
        return d

    def clear_screen(self):
        self._screen_buffer = bytearray(SCREEN_PIXEL_COUNT)
        self._update_screen = True

    def screen_buffer(self):
        return deepcopy(self._screen_buffer)

    def screen_changed(self):
        return self._update_screen

    def screen_updated(self):
        self._update_screen = False

    def get_pixel(self, x, y):
        x = x % SCREEN_WIDTH
        y = y % SCREEN_HEIGHT
        idx = x + (y * SCREEN_WIDTH)
        return self._screen_buffer[idx]

    def set_pixel(self, x, y, v):
        x = x % SCREEN_WIDTH
        y = y % SCREEN_HEIGHT
        idx = x + (y * SCREEN_WIDTH)

        self._screen_buffer[idx] = self._screen_buffer[idx] ^ v
        self._update_screen = True

