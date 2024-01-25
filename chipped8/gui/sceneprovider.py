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

        self._img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        self._img.fill(self._color_1)

    @Slot(list)
    def blitScreen(self, pixels):
        img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        img.fill(self._color_1)

        for i in range(chipped8.SCREEN_WIDTH):
            for j in range(chipped8.SCREEN_HEIGHT):
                if pixels[i][j] == chipped8.Colors.color_2:
                    img.setPixelColor(i, j, self._color_2)
                elif pixels[i][j] == chipped8.Colors.color_3:
                    img.setPixelColor(i, j, self._color_3)
                elif pixels[i][j] == chipped8.Colors.color_4:
                    img.setPixelColor(i, j, self._color_4)

        self._img = img
        self.blitReady.emit()

    def requestImage(self, id, size, requestedSize):
        size.setWidth(chipped8.SCREEN_WIDTH * UPSCALE_FACTOR)
        size.setHeight(chipped8.SCREEN_HEIGHT * UPSCALE_FACTOR)

        return self._img.scaled(size, Qt.KeepAspectRatio)

