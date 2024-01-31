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
        d = Displaly()
        d._screen_planes = deepcopy(self._screen_planes)
        d._update_screen = self._update_screen
        d._res_mode = self._res_mode
        d._target_plane = self._target_plane
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
        Convert the flat array of on / off bytes that represent pixels to a
        multi dimensional array of colors based on what pixels are set in each
        plane.
        '''
        pixels = []
        for x in range(SCREEN_WIDTH):
            row = []

            for y in range(SCREEN_HEIGHT):
                idx = x + (y * SCREEN_WIDTH)

                color = Colors.color_1
                if self._screen_planes[0][idx] == 1 and self._screen_planes[1][idx] == 0:
                    color = Colors.color_2
                elif self._screen_planes[0][idx] == 0 and self._screen_planes[1][idx] == 1:
                    color = Colors.color_3
                elif self._screen_planes[0][idx] == 1 and self._screen_planes[1][idx] == 1:
                    color = Colors.color_4

                row.append(color)

            pixels.append(row)

        return pixels

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

