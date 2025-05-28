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

from PySide6.QtWidgets import QMainWindow, QFileDialog, QLabel
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Signal, Slot, QTimer, Qt

from .graphicsprovider import GraphicsProvider

import chipped8

class MainWindow(QMainWindow):
    platformChanged = Signal(str, str)
    interpreterChanged = Signal(str, str)
    keyEvent = Signal(int, bool, int)
    loadRom = Signal(str)

    def __init__(self, platform, interpreter):
        super().__init__()

        self.setWindowTitle('Chipped8')
        self.setMinimumSize(128, 64)
        self.resize(640, 320)

        self.gpu_view = GraphicsProvider()
        self.setCentralWidget(self.gpu_view)

        self._create_menus(platform, interpreter)

        self._status_fps = QLabel()
        self.statusBar().addPermanentWidget(self._status_fps)

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

        # Effects menu
        effects_menu = menubar.addMenu('Effects')
        for name, getter, setter in (
            ('Scanlines', lambda: self.gpu_view.enable_scanlines, self.gpu_view.toggle_effect_scanlines),
            ('Glow', lambda: self.gpu_view.enable_glow, self.gpu_view.toggle_effect_glow),
            ('Barrel', lambda: self.gpu_view.enable_barrel, self.gpu_view.toggle_effect_barrel),
            ('Chromatic', lambda: self.gpu_view.enable_chromatic, self.gpu_view.toggle_effect_chromatic),
            ('Vignette', lambda: self.gpu_view.enable_vignette, self.gpu_view.toggle_effect_vignette),
            ('Noise', lambda: self.gpu_view.enable_noise, self.gpu_view.toggle_effect_noise),
            ('Flicker', lambda: self.gpu_view.enable_flicker, self.gpu_view.toggle_effect_flicker),
            ('Quantize', lambda: self.gpu_view.enable_quantize, self.gpu_view.toggle_effect_quantize),
            ('Interlace', lambda: self.gpu_view.enable_interlace, self.gpu_view.toggle_effect_interlace),
            ('Mask', lambda: self.gpu_view.enable_mask, self.gpu_view.toggle_effect_mask),
            ('Wrap', lambda: self.gpu_view.enable_wrap, self.gpu_view.toggle_effect_wrap),
            ('Scan Delay', lambda: self.gpu_view.enable_scan_delay, self.gpu_view.toggle_effect_scan_delay),
        ):
            a = effects_menu.addAction(name)
            a.setCheckable(True)
            if getter:
                a.setChecked(getter())
            a.toggled.connect(setter)

    def _open_rom_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, 'Open ROM', '', 'Chip-8 (*.ch8);;BIN (*.bin)'
        )
        if fname:
            self.loadRom.emit(fname)

    @Slot(float, float)
    def update_fps(self, frame_sec, fps):
        self._status_fps.setText(f'fps: {round(fps)}')

    def keyPressEvent(self, event):
        self.keyEvent.emit(event.key(), True, event.modifiers().value)

    def keyReleaseEvent(self, event):
        self.keyEvent.emit(event.key(), False, event.modifiers().value)
