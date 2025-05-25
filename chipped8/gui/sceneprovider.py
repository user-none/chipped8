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

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtGui import QImage, QColor

import chipped8

UPSCALE_FACTOR = 5

class SceneProvider(QQuickImageProvider):
    blitReady = Signal()

    def __init__(self, color_1='#0f052d', color_2='#203671', color_3='#36868f', color_4='#5fc75d'):
        QQuickImageProvider.__init__(self, QQuickImageProvider.Image)

        self._color_1 = QColor(color_1)
        self._color_2 = QColor(color_2)
        self._color_3 = QColor(color_3)
        self._color_4 = QColor(color_4)

        # Precompute RGB values
        self._rgb_map = np.array([
            self._qcolor_to_rgb32(self._color_1),
            self._qcolor_to_rgb32(self._color_2),
            self._qcolor_to_rgb32(self._color_3),
            self._qcolor_to_rgb32(self._color_4),
        ], dtype=np.uint32)

        self._img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        self._img.fill(self._color_1)

    def _qcolor_to_rgb32(self, color: QColor) -> np.uint32:
        return np.uint32((color.alpha() << 24) | (color.red() << 16) | (color.green() << 8) | color.blue())

    @Slot(np.ndarray)
    def blitScreen(self, pixel_indices):
        '''
        pixel_indices: NumPy array of shape (HEIGHT, WIDTH), dtype=np.uint8
        '''

        # Map color indices to 32-bit RGB values
        rgb_pixels = self._rgb_map[pixel_indices]

        # Create a QImage that shares memory with the NumPy array
        img = QImage(
            rgb_pixels.data,
            chipped8.SCREEN_WIDTH,
            chipped8.SCREEN_HEIGHT,
            rgb_pixels.strides[0],
            QImage.Format_RGB32
        )
        img = img.copy()  # Detach QImage from NumPy memory

        self._img = img
        self.blitReady.emit()

    @Slot()
    def clearScreen(self):
        img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        img.fill(self._color_1)
        self._img = img
        self.blitReady.emit()

    def requestImage(self, id, size, requestedSize):
        size.setWidth(chipped8.SCREEN_WIDTH * UPSCALE_FACTOR)
        size.setHeight(chipped8.SCREEN_HEIGHT * UPSCALE_FACTOR)

        return self._img.scaled(size, Qt.KeepAspectRatio)

