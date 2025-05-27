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

from PySide6.QtWidgets import QMainWindow, QFileDialog
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Signal

from .graphicsprovider import GraphicsProviderQRhi

import chipped8

class MainWindow(QMainWindow):
    windowFocusChanged = Signal(bool)
    platformChanged = Signal(str, str)
    interpreterChanged = Signal(str, str)
    keyEvent = Signal(int, bool, int)
    loadRom = Signal(str)

    def __init__(self, platform, interpreter):
        super().__init__()

        self.setWindowTitle('Chipped8')
        self.setMinimumSize(128, 64)
        self.resize(640, 320)

        self.gpu_view = GraphicsProviderQRhi()
        self.setCentralWidget(self.gpu_view)

        self._create_menus(platform, interpreter)

    def _create_menus(self, platform, interpreter):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')
        open_action = QAction('Open...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self._open_rom_dialog)
        file_menu.addAction(open_action)

        # Platform menu
        platform_menu = menubar.addMenu('Platform')
        platform_group = QActionGroup(platform_menu)
        platform_group.setExclusive(True)
        for name in chipped8.PlatformTypes:
            a = platform_group.addAction(str(name))
            a.setCheckable(True)
            if name == platform:
                a.setChecked(True)
            platform_menu.addAction(a)
        platform_group.triggered.connect(lambda a: self.platformChanged.emit(a.text(), ''))

        # Interpreter menu
        interpreter_menu = menubar.addMenu('Interpreter')
        interpreter_group = QActionGroup(interpreter_menu)
        interpreter_group.setExclusive(True)
        for name in chipped8.InterpreterTypes:
            a = interpreter_group.addAction(str(name))
            a.setCheckable(True)
            if name == interpreter:
                a.setChecked(True)
            interpreter_menu.addAction(a)
        interpreter_group.triggered.connect(lambda a: self.interpreterChanged.emit('', a.text()))

    def _open_rom_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, 'Open ROM', '', 'Chip-8 (*.ch8);;BIN (*.bin)'
        )
        if fname:
            self.loadRom.emit(fname)

    def focusInEvent(self, event):
        self.windowFocusChanged.emit(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.windowFocusChanged.emit(False)
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        self.keyEvent.emit(event.key(), True, event.modifiers().value)

    def keyReleaseEvent(self, event):
        self.keyEvent.emit(event.key(), False, event.modifiers().value)
