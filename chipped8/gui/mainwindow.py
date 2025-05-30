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

from PySide6.QtWidgets import QMainWindow, QFileDialog, QLabel, QDialog
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import QCoreApplication, Signal, Slot, QTimer, Qt

from .color_dialog import ColorSelectorDialog
from .graphicsprovider import GraphicsProvider
from .rom_db import RomDBOpener, RomDatabase

import chipped8

class MainWindow(QMainWindow):
    platformChanged = Signal(str, str)
    interpreterChanged = Signal(str, str)
    keyEvent = Signal(int, bool, int)
    loadRom = Signal(str, chipped8.PlatformTypes, int)

    def __init__(self, platform, interpreter):
        super().__init__()

        self._rom_db = RomDatabase()

        db_opener = RomDBOpener(self)
        db_opener.status_message.connect(lambda msg: self.statusBar().showMessage(msg, 3000))
        db_opener.file_ready.connect(self.db_ready)
        db_opener.start()

        self.setWindowTitle(QCoreApplication.applicationName())
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
        a = file_menu.addAction('Open...', 'Ctrl+O')
        a.triggered.connect(self._open_rom_dialog)

        a = file_menu.addAction('Colors...')
        a.triggered.connect(self._choose_colors)


        # Platform menu
        platform_menu = menubar.addMenu('Platform')
        self._platform_group = QActionGroup(platform_menu)
        self._platform_group.setExclusive(True)
        for name in chipped8.PlatformTypes:
            a = self._platform_group.addAction(str(name))
            a.setCheckable(True)
            if name == platform:
                a.setChecked(True)
            platform_menu.addAction(a)
        self._platform_group.triggered.connect(lambda a: self.platformChanged.emit(a.text(), ''))

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
            ('Pixel Borders', lambda: self.gpu_view.enable_pixel_borders, self.gpu_view.toggle_effect_pixel_borders),
            ('Edge Glow', lambda: self.gpu_view.enable_edge_glow, self.gpu_view.toggle_effect_edge_glow),
            ('Signal Tearing', lambda: self.gpu_view.enable_signal_tearing, self.gpu_view.toggle_effect_signal_tearing),
            ('Channel Shift', lambda: self.gpu_view.enable_channel_shift, self.gpu_view.toggle_effect_channel_shift),
            ('Blocky Artifacts', lambda: self.gpu_view.enable_blocky_artifacts, self.gpu_view.toggle_effect_blocky_artifacts),
            ('Temporal Shimmer', lambda: self.gpu_view.enable_temporal_shimmer, self.gpu_view.toggle_effect_temporal_shimmer),
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
            metadata = self._rom_db.get_metadata_by_path(fname)

            if metadata.get('title'):
                self.setWindowTitle(f'{QCoreApplication.applicationName()} - {metadata.get("title")}')

            try:
                platform = chipped8.PlatformTypes(metadata.get('platform', 'originalChip8'))
            except:
                platform = chipped8.PlatformTypes.originalChip8
            for a in self._platform_group.actions():
                if a.text() == str(platform):
                    a.setChecked(True)
                    break

            tickrate = metadata.get('tickrate', -1)

            self.loadRom.emit(fname, platform, tickrate)

    def _choose_colors(self):
        colors = self.gpu_view.get_colors()
        d = ColorSelectorDialog(colors[0], colors[1], colors[2], colors[3])
        if d.exec() == QDialog.Accepted:
            colors = d.get_colors()
            self.gpu_view.set_colors(colors[0], colors[1], colors[2], colors[3])

    @Slot(object)
    def db_ready(self, data):
        if not data:
            return
        self._rom_db.load_data(data)
        self.statusBar().showMessage('Ready', 3000)

    @Slot(float, float)
    def update_fps(self, frame_sec, fps):
        self._status_fps.setText(f'fps: {round(fps)}')

    def keyPressEvent(self, event):
        self.keyEvent.emit(event.key(), True, event.modifiers().value)

    def keyReleaseEvent(self, event):
        self.keyEvent.emit(event.key(), False, event.modifiers().value)
