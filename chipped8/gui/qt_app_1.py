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

import os
import sys
import time

from threading import Thread

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QApplication, QLabel, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PySide6.QtGui import QImage, QColor, QPixmap

import chipped8

class QtApp(QObject):
    _blit_ready = Signal(list)

    def __init__(self, args):
        QObject.__init__(self)

        self._args = args
        self._pitem = None
        self._view = None

        self._blit_ready.connect(self._blit_screen)

    def _fill_screen_buffer(self, pixels):
        self._blit_ready.emit(pixels)

    def _blit_screen(self, pixels):
        if not pixels or not self._pitem:
            return

        img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        img.fill(QColor(Qt.black))
        for i in range(chipped8.SCREEN_HEIGHT):
            for j in range(chipped8.SCREEN_WIDTH):
                idx = i * chipped8.SCREEN_WIDTH + j
                if pixels[idx]:
                    img.setPixelColor(j, i, Qt.white)

        self._pitem.setPixmap(QPixmap(img).scaled(self._view.width(), self._view.height()))

    def _beep(self):
        #os.system("echo -ne '\007'")
        pass

    def run(self):
        cpu = chipped8.cpu.CPU(self._args.hz)
        cpu.set_blit_screen_cb(self._fill_screen_buffer)
        cpu.set_sound_cb(self._beep)

        with open(self._args.in_file, 'rb') as f:
            cpu.load_rom(f.read())

        Thread(target=cpu.run).start()

        app = QApplication(sys.argv)

        scene = QGraphicsScene()
        self._view = QGraphicsView(scene)
        self._pitem = QGraphicsPixmapItem()

        img = QImage(chipped8.SCREEN_WIDTH, chipped8.SCREEN_HEIGHT, QImage.Format_RGB32)
        img.fill(QColor(Qt.yellow))
        self._pitem.setPixmap(QPixmap(img).scaled(self._view.width(), self._view.height()))

        scene.addItem(self._pitem)
        self._view.show()

        ret = app.exec_()
        cpu.stop()
        sys.exit(ret)


