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
from enum import Enum, Flag, auto

SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
SCREEN_PIXEL_COUNT = SCREEN_WIDTH * SCREEN_HEIGHT

class Colors(Enum):
    color_1 = auto()
    color_2 = auto()
    color_3 = auto()
    color_4 = auto()

class ResolutionMode(Enum):
    lowres = auto()
    hires = auto()

class Plane(Flag):
    p1 = auto()
    p2 = auto()

class Displaly():

    def __init__(self):
        # There are 2 screen planes that get overlaid when outputting the screen.
        # A screen buffer is a one dimensional array of 0 or 1 denoting if the pixel is set or not.
        # The pixels in the buffer are rows next to each other instead of on top of each other.
        # In the buffer: | row | row | row | row |. Each row is a row of pixels.
        self._screen_buffer = [ self._generate_empty_buffer(), self._generate_empty_buffer() ]
        self._update_screen = False
        self._mode = ResolutionMode.lowres
        self._plane = Plane.p1

    def __deepcopy__(self, memo):
        d = Displaly()
        d._screen_buffer = deepcopy(self._screen_buffer)
        d._update_screen = self._update_screen
        d._mode = self._mode
        d._plane = self._plane
        return d

    def _generate_empty_buffer(self):
        return bytearray(SCREEN_PIXEL_COUNT)

    def set_resmode(self, mode: ResolutionMode):
        self._mode = mode

    def set_plane(self, plane: Plane):
        if self._plane == plane:
            return

        self._plane = plane
        self.clear_screen()

    def _get_plane_buffers(self):
        plane_buffers = []

        if self._plane & Plane.p1:
            plane_buffers.append(self._screen_buffer[0])
        if self._plane & Plane.p2:
            plane_buffers.append(self._screen_buffer[1])

        return plane_buffers

    def clear_screen(self):
        self._screen_buffer = [ self._generate_empty_buffer(), self._generate_empty_buffer() ]
        self._update_screen = True

    def get_pixels(self):
        pixels = []
        for x in range(SCREEN_WIDTH):
            row = []

            for y in range(SCREEN_HEIGHT):
                idx = x + (y * SCREEN_WIDTH)

                color = Colors.color_1
                if self._screen_buffer[0][idx] == 1 and self._screen_buffer[1][idx] == 0:
                    color = Colors.color_2
                elif self._screen_buffer[0][idx] == 0 and self._screen_buffer[1][idx] == 1:
                    color = Colors.color_3
                elif self._screen_buffer[0][idx] == 1 and self._screen_buffer[1][idx] == 1:
                    color = Colors.color_4

                row.append(color)

            pixels.append(row)

        return pixels

    def screen_changed(self):
        return self._update_screen

    def screen_updated(self):
        self._update_screen = False

    def _set_pixel_lowres(self, screen_buffer, x, y, v):
        unset = False
        x = x * 2
        y = y * 2

        for i in range(2):
            col = (x + i) % SCREEN_WIDTH

            for j in range(2):
                row = (y + j) % SCREEN_HEIGHT
                idx = col + (row * SCREEN_WIDTH)

                # XOR can only flip if the current bit is 1
                if screen_buffer[idx] == 1:
                    unset = True
                screen_buffer[idx] = screen_buffer[idx] ^ v

        return unset

    def _set_pixel_hires(self, screen_buffer, x, y, v):
        unset = False
        x = x % SCREEN_WIDTH
        y = y % SCREEN_HEIGHT
        idx = x + (y * SCREEN_WIDTH)

        # XOR can only flip if the current bit is 1
        if screen_buffer[idx] == 1:
            unset = True
        screen_buffer[idx] = screen_buffer[idx] ^ v

        return unset

    def _set_pixel_buffer(self, screen_buffer, x, y, v):
        if self._mode == ResolutionMode.lowres:
            return self._set_pixel_lowres(screen_buffer, x, y, v)
        else:
            return self._set_pixel_hires(screen_buffer, x, y, v)

    def set_pixel(self, x, y, v):
        # XOR with 0 won't change the value
        if v == 0:
            return False

        unset = False
        plane_buffers = self._get_plane_buffers()
        for screen_buffer in plane_buffers:
            u = self._set_pixel_buffer(screen_buffer, x, y, v)
            if u:
                unset = True

        self._update_screen = True
        return unset

    def scroll_down(self, num_pixels):
        plane_buffers = self._get_plane_buffers()
        for screen_buffer in plane_buffers:
            screen_buffer[:] = bytearray(SCREEN_WIDTH * num_pixels) + screen_buffer[ : -1 * SCREEN_WIDTH * num_pixels ]
        self._update_screen = True

    def scroll_up(self, num_pixels):
        plane_buffers = self._get_plane_buffers()
        for screen_buffer in plane_buffers:
            screen_buffer[:] = screen_buffer[ SCREEN_WIDTH * num_pixels : ] + bytearray(SCREEN_WIDTH * num_pixels)
        self._update_screen = True

    def scroll_left(self):
        plane_buffers = self._get_plane_buffers()

        for screen_buffer in plane_buffers:
            buffer = bytearray()

            for x in range(SCREEN_WIDTH):
                row = bytearray(SCREEN_WIDTH)

                for y in range(SCREEN_HEIGHT):
                    row =  screen_buffer[SCREEN_WIDTH * y + 4: SCREEN_WIDTH * y + SCREEN_WIDTH ] + bytearray(4)

                buffer.extend(row)

            screen_buffer[:] = buffer

        self._update_screen = True

    def scroll_right(self):
        plane_buffers = self._get_plane_buffers()

        for screen_buffer in plane_buffers:
            buffer = bytearray()

            for x in range(SCREEN_WIDTH):
                row = bytearray(SCREEN_WIDTH)

                for y in range(SCREEN_HEIGHT):
                    row = bytearray(4) + screen_buffer[SCREEN_WIDTH * y : SCREEN_WIDTH * y + SCREEN_WIDTH - 4 ]

                buffer.extend(row)

            screen_buffer[:] = buffer

        self._update_screen = True

