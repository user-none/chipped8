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
from enum import Enum, IntEnum, auto

class Keys(IntEnum):
    Key_0 = 0x0,
    Key_1 = 0x1,
    Key_2 = 0x2,
    Key_3 = 0x3,
    Key_4 = 0x4,
    Key_5 = 0x5,
    Key_6 = 0x6,
    Key_7 = 0x7,
    Key_8 = 0x8,
    Key_9 = 0x9,
    Key_A = 0xA,
    Key_B = 0xB,
    Key_C = 0xC,
    Key_D = 0xD,
    Key_E = 0xE,
    Key_F = 0xF

class KeyState(Enum):
    up = auto(),
    down = auto()

class KeyInput():

    def __init__(self):
        self._keys = [KeyState.up] * len(Keys)

    def __deepcopy__(self, memo):
        d = KeyInput()
        d._keys = deepcopy(self._keys)
        return d

    def set_key_state(self, key: Keys, state: KeyState):
        self._keys[key] = state

    def get_key_state(self, key):
        if key < 0 or key > 0xF:
            raise Exception('Error: Invalid key {0}'.format(key))
        return self._keys[key]

    def get_keys(self):
        return self._keys

