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

from PySide6.QtCore import Qt, Signal
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtGui import QImage, QColor

import chipped8

class SceneProvider(QQuickImageProvider):
    blit_ready = Signal(list)
    blitImage = Signal()

    def __init__(self):
        QQuickImageProvider.__init__(self, QQuickImageProvider.Image)

        self.blit_ready.connect(self.blit_screen)

        self._img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        self._img.fill(QColor(Qt.black))

    def _fill_screen_buffer(self, pixels):
        self.blit_ready.emit(pixels)

    def blit_screen(self, pixels):
        img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        img.fill(QColor(Qt.black))

        for i in range(chipped8.SCREEN_HEIGHT):
            for j in range(chipped8.SCREEN_WIDTH):
                idx = i * chipped8.SCREEN_WIDTH + j
                if pixels[idx]:
                    img.setPixelColor(j, i, Qt.white)

        self._img = img
        self.blitImage.emit()

    def requestImage(self, id, size, requestedSize):
        size.width = chipped8.SCREEN_WIDTH
        size.height = chipped8.SCREEN_HEIGHT
        requestedSize.width = chipped8.SCREEN_WIDTH
        requestedSize.height = chipped8.SCREEN_HEIGHT
        return self._img

