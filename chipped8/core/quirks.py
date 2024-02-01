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

class Quirks():

    def __init__(self):
        self._shift = False
        self._memoryIncrementByX = False
        self._memoryLeaveIUnchanged = False
        self._wrap = False
        self._jump = False
        self._vblank = False
        self._logic = False

    def __deepcopy__(self, memo):
        q = Quirks()
        q._shift = self._shift
        q._memoryIncrementByX = self._memoryIncrementByX
        q._memoryLeaveIUnchanged = self._memoryLeaveIUnchanged
        q._wrap = self._wrap
        q._jump = self._jump
        q._vblank = self._vblank
        q._logic = self._logic
        return q

    def set_shift(self, val: bool):
        self._shift = val

    def get_shift(self):
        return self._shift

    def set_memoryIncrementByX(self, val: bool):
        self._memoryIncrementByX = val

    def get_memoryIncrementByX(self):
        return self._memoryIncrementByX

    def set_memoryLeaveIUnchanged(self, val: bool):
        self._memoryLeaveIUnchanged = val

    def get_memoryLeaveIUnchanged(self):
        return self._memoryLeaveIUnchanged 

    def set_wrap(self, val: bool):
        self._wrap = val

    def get_wrap(self):
        return self._wrap 

    def set_jump(self, val: bool):
        self._jump = val

    def get_jump(self):
        return self._jump

    def set_vblank(self, val: bool):
        self._vblank = val

    def get_vblank(self):
        return self._vblank

    def set_logic(self, val: bool):
        self._logic = val

    def get_logic(self):
        return self._logic

