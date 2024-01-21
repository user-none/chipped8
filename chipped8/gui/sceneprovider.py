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

class SceneProvider(QQuickImageProvider):
    blitReady = Signal()

    def __init__(self, back_color, fore_color):
        QQuickImageProvider.__init__(self, QQuickImageProvider.Image)

        self._back_color = QColor(back_color)
        self._fore_color = QColor(fore_color)
        self._img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        self._img.fill(self._back_color)

    @Slot(list)
    def blitScreen(self, pixels):
        img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        img.fill(self._back_color)

        for i in range(chipped8.SCREEN_HEIGHT):
            for j in range(chipped8.SCREEN_WIDTH):
                idx = i * chipped8.SCREEN_WIDTH + j
                if pixels[idx]:
                    img.setPixelColor(j, i, self._fore_color)

        self._img = img
        self.blitReady.emit()

    def requestImage(self, id, size, requestedSize):
        size.setWidth(chipped8.SCREEN_WIDTH*10)
        size.setHeight(chipped8.SCREEN_HEIGHT*10)

        return self._img.scaled(size, Qt.KeepAspectRatio)

