#!/usr/bin/env python

# Copyright 2025 John Schember <john@nachtimwald.com>
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

from PySide6.QtCore import Slot
from PySide6.QtGui import QImage, QColor
from PySide6.QtQuick import QQuickItem, QSGSimpleTextureNode
from PySide6.QtQml import qmlRegisterType

import chipped8

class GraphicsProvider(QQuickItem):
    def __init__(self, color_1='#0f052d', color_2='#203671', color_3='#36868f', color_4='#5fc75d', parent=None):
        super().__init__(parent)

        self.setFlag(QQuickItem.ItemHasContents)

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

        self._rgb_buffer = np.empty((chipped8.SCREEN_HEIGHT, chipped8.SCREEN_WIDTH), dtype=np.uint32)
        self._img = QImage(
            self._rgb_buffer.data,
            chipped8.SCREEN_WIDTH,
            chipped8.SCREEN_HEIGHT,
            self._rgb_buffer.strides[0],
            QImage.Format_RGB32
        )
        self._rgb_buffer.fill(self._rgb_map[0])
        self._dirty = True

        self.update()

    def _qcolor_to_rgb32(self, color: QColor) -> np.uint32:
        return np.uint32((color.alpha() << 24) | (color.red() << 16) | (color.green() << 8) | color.blue())

    @Slot(np.ndarray)
    def blitScreen(self, pixel_indices):
        '''
        pixel_indices: NumPy array of shape (HEIGHT, WIDTH), dtype=np.uint8
        '''

        # Map color indices to 32-bit RGB values
        np.take(self._rgb_map, pixel_indices, out=self._rgb_buffer)
        self._dirty = True
        self.update()

    @Slot()
    def clearScreen(self):
        self._rgb_buffer.fill(self._rgb_map[0])
        self._dirty = True
        self.update()

    def updatePaintNode(self, old_node, _):
        if self._img is None:
            return old_node

        if isinstance(old_node, QSGSimpleTextureNode):
            node = old_node
        else:
            node = QSGSimpleTextureNode()

        # Only update the texture when the image changes.
        # Resize will cause an update to trigger without
        # the image having changed.
        if self._dirty:
            if node.texture():
                node.texture().deleteLater()

            texture = self.window().createTextureFromImage(self._img)
            node.setTexture(texture)

            self._dirty = False

        # Keep aspect ratio by fitting image inside boundingRect
        item_rect = self.boundingRect()
        image_ratio = chipped8.SCREEN_WIDTH / chipped8.SCREEN_HEIGHT
        item_ratio = item_rect.width() / item_rect.height()

        if image_ratio > item_ratio:
            w = item_rect.width()
            h = w / image_ratio
            x = 0
            y = (item_rect.height() - h) / 2
        else:
            h = item_rect.height()
            w = h * image_ratio
            x = (item_rect.width() - w) / 2
            y = 0

        node.setRect(x, y, w, h)
        return node

qmlRegisterType(GraphicsProvider, "GraphicsProvider", 0, 1, "GraphicsProvider")
