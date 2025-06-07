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

import numpy as np

from copy import deepcopy
from enum import Enum, Flag, auto

SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
SCREEN_PIXEL_COUNT = SCREEN_WIDTH * SCREEN_HEIGHT

class ResolutionMode(Enum):
    lowres = auto()
    hires = auto()

class Plane(Flag):
    p1 = auto()
    p2 = auto()

class Displaly():
    '''
    Chip-8 uses a 64x32 pixel screen. Super Chip 1.0/1 and XO-Chip adds a high resolution
    mode which doubles the resolutions to 128x64 pixels. To allow more code reuse a 128x64
    screen is always used. When in low resolution mode, the pixels will be doubled to effectively
    look 64x32.

    This allows us to only need to know which mode is being used when writing to the screen.
    In order to know if we need to write one or a 2x2 pixel square (for low res mode). Otherwise,
    all other display operations are the same.

    A screen buffer is a one dimensional array of 0 or 1 denoting if the pixel is set or not.
    The pixels in the buffer are rows next to each other instead of on top of each other.
    In the buffer: | row | row | row | row |. Each row is a row of pixels.

    XO-Chip uses 2 screen planes (layers) that get overlaid when rendering the screen.
    This allows for 4 colors. Pixel off, plane 1 pixel on, plane 2 pixel on, and plane
    1 and 2 overlapping pixel on.

    Chip-8 and Super Chip 1.0/1 only use plane 1 which is the default. They retain their
    two color support.

    Multiple planes can be selected and written to at the same time.
    '''

    def __init__(self):
        self._screen_planes = [ self._generate_empty_plane(), self._generate_empty_plane() ]
        self._update_screen = False
        self._res_mode = ResolutionMode.lowres
        self._target_plane = Plane.p1

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]

        d = object.__new__(self.__class__)
        d._screen_planes = deepcopy(self._screen_planes, memo)
        d._update_screen = self._update_screen
        d._res_mode = self._res_mode
        d._target_plane = self._target_plane

        memo[id(self)] = d
        return d

    def _generate_empty_plane(self):
        return bytearray(SCREEN_PIXEL_COUNT)

    def set_resmode(self, mode: ResolutionMode):
        self._res_mode = mode
        self.clear_screen()

    def get_planes(self):
        return self._target_plane

    def set_plane(self, plane: Plane):
        if plane == self._target_plane or plane == Plane(0):
            return
        self._target_plane = plane

    def _get_plane_buffers(self):
        buffers = []

        if self._target_plane & Plane.p1:
            buffers.append(self._screen_planes[0])
        if self._target_plane & Plane.p2:
            buffers.append(self._screen_planes[1])

        return buffers

    def clear_screen(self):
        self._screen_planes = [ self._generate_empty_plane(), self._generate_empty_plane() ]
        self._update_screen = True

    def get_pixels(self):
        '''
        Return a 2D NumPy array of pixel indices (0–3) for fast rendering.
        Each index maps to a color via.
        '''
        plane0 = np.array(self._screen_planes[0], dtype=np.uint8)
        plane1 = np.array(self._screen_planes[1], dtype=np.uint8)

        # Mapping:
        #   0b00 = 0 -> color_1
        #   0b01 = 1 -> color_2
        #   0b10 = 2 -> color_3
        #   0b11 = 3 -> color_4
        keys = (plane1 << 1) | plane0

        # Remap keys to match color index order: [color_1, color_2, color_3, color_4]
        remap = np.array([0, 1, 2, 3], dtype=np.uint8)
        pixel_indices = remap[keys].reshape((SCREEN_HEIGHT, SCREEN_WIDTH))

        return pixel_indices

    def screen_changed(self):
        return self._update_screen

    def screen_updated(self):
        self._update_screen = False

    def _set_pixel_lowres(self, plane_buffer, x, y, v):
        unset = False
        x = x * 2
        y = y * 2

        for i in range(2):
            col = (x + i) % SCREEN_WIDTH

            for j in range(2):
                row = (y + j) % SCREEN_HEIGHT
                idx = col + (row * SCREEN_WIDTH)

                # XOR can only flip if the current bit is 1
                if plane_buffer[idx] == 1:
                    unset = True
                plane_buffer[idx] = plane_buffer[idx] ^ v

        return unset

    def _set_pixel_hires(self, plane_buffer, x, y, v):
        unset = False

        x = x % SCREEN_WIDTH
        y = y % SCREEN_HEIGHT
        idx = x + (y * SCREEN_WIDTH)

        # XOR can only flip if the current bit is 1
        if plane_buffer[idx] == 1:
            unset = True
        plane_buffer[idx] = plane_buffer[idx] ^ v

        return unset

    def set_pixel(self, plane, x, y, v):
        # XOR with 0 won't change the value
        if v == 0:
            return False

        if not (plane & self._target_plane):
            return False

        unset = False
        plane_buffer = self._screen_planes[0] if plane == Plane.p1 else self._screen_planes[1]
        if self._res_mode == ResolutionMode.lowres:
            u = self._set_pixel_lowres(plane_buffer, x, y, v)
        else:
            u = self._set_pixel_hires(plane_buffer, x, y, v)

        if u:
            unset = True

        self._update_screen = True
        return unset

    def scroll_down(self, num_pixels):
        if self._res_mode == ResolutionMode.lowres:
            num_pixels = num_pixels * 2

        plane_buffers = self._get_plane_buffers()

        for plane_buffer in plane_buffers:
            plane_buffer[:] = bytearray(SCREEN_WIDTH * num_pixels) + plane_buffer[ : -1 * SCREEN_WIDTH * num_pixels ]
        self._update_screen = True

    def scroll_up(self, num_pixels):
        if self._res_mode == ResolutionMode.lowres:
            num_pixels = num_pixels * 2

        plane_buffers = self._get_plane_buffers()

        for plane_buffer in plane_buffers:
            plane_buffer[:] = plane_buffer[ SCREEN_WIDTH * num_pixels : ] + bytearray(SCREEN_WIDTH * num_pixels)
        self._update_screen = True

    def scroll_left(self):
        num_pixels = 4
        if self._res_mode == ResolutionMode.lowres:
            num_pixels = 8

        plane_buffers = self._get_plane_buffers()

        for plane_buffer in plane_buffers:
            buffer = bytearray()

            for x in range(SCREEN_HEIGHT):
                row =  plane_buffer[SCREEN_WIDTH * x + num_pixels: SCREEN_WIDTH * x + SCREEN_WIDTH ] + bytearray(num_pixels)
                buffer.extend(row)

            plane_buffer[:] = buffer

        self._update_screen = True

    def scroll_right(self):
        num_pixels = 4
        if self._res_mode == ResolutionMode.lowres:
            num_pixels = 8

        plane_buffers = self._get_plane_buffers()

        for plane_buffer in plane_buffers:
            buffer = bytearray()

            for x in range(SCREEN_HEIGHT):
                row = bytearray(num_pixels) + plane_buffer[SCREEN_WIDTH * x : SCREEN_WIDTH * x + SCREEN_WIDTH - num_pixels ]
                buffer.extend(row)

            plane_buffer[:] = buffer

        self._update_screen = True

    def sprite_will_wrap(self, x1, y1, x2, y2):
        if self._res_mode == ResolutionMode.lowres:
            x1 = x1 * 2
            y1 = y1 * 2
            x2 = x2 * 2
            y2 = y2 * 2

        x1 = x1 % SCREEN_WIDTH
        y1 = y1 % SCREEN_HEIGHT
        x2 = x2 % SCREEN_WIDTH
        y2 = y2 % SCREEN_HEIGHT

        if x1 > x2 or y1 > y2:
            return True
        return False

    def _draw_s8(self, x, y, n, wrap, registers, memory):
        registers.set_V(0xF, 0)
        I = registers.get_I()
        for plane in self.get_planes():
            for i in range(n):
                sprite = memory.get_byte(I + i)

                for j in range(8):
                    # XOR with 0 won't change the value
                    if sprite & (0x80 >> j) == 0:
                        continue

                    row = x + j
                    col = y + i

                    if not wrap and self.sprite_will_wrap(x, y, x+j, y+i):
                        continue

                    unset = self.set_pixel(plane, row, col, 1)
                    if unset:
                        registers.set_V(0xF, 1)
            I = I + n

    def _draw_s16(self, x, y, registers, memory):
        registers.set_V(0xF, 0)
        I = registers.get_I()
        for plane in self.get_planes():
            for i in range(16):
                sprite = (memory.get_byte(I + (i*2)) << 8) | memory.get_byte(I + (i*2) + 1)

                for j in range(16):
                    # XOR with 0 won't change the value
                    if sprite & (0x8000 >> j) == 0:
                        continue

                    row = x + j
                    col = y + i

                    unset = self.set_pixel(plane, row, col, 1)
                    if unset:
                        registers.set_V(0xF, 1)
            I = I + 32

    def draw(self, x, y, n, wrap, registers, memory):
        if n == 0:
            self._draw_s16(x, y, registers, memory)
        else:
            self._draw_s8(x, y, n, wrap, registers, memory)
