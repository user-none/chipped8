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

import platform as pyplat

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QFileDialog, QLabel, QDialog
from PySide6.QtGui import QAction, QActionGroup, QWindowStateChangeEvent
from PySide6.QtCore import QCoreApplication, QStandardPaths, Signal, Slot, QTimer, Qt

from .color_dialog import ColorSelectorDialog
from .graphicsprovider import GraphicsProvider
from .metadata_overlay import MetadataOverlay
from .rom_db import RomDBOpener, RomDatabase
from .settings import AppSettings

import chipped8

class MainWindow(QMainWindow):
    platformChanged = Signal(str, str)
    interpreterChanged = Signal(str, str)
    keyEvent = Signal(int, bool, int)
    loadRom = Signal(str, chipped8.PlatformTypes, int)

    def __init__(self, platform=chipped8.PlatformTypes.originalChip8, interpreter=None):
        super().__init__()

        self._rom_db = RomDatabase()
        self._settings = AppSettings()

        # If a specific interpreter was provided we'll make that the selected one
        if interpreter:
            self._settings['interpreter'] = str(interpreter)
        else:
            interpreter = chipped8.InterpreterTypes(self._settings.get('interpreter', 'cached'))
        self.interpreter = chipped8.InterpreterTypes(interpreter)

        db_opener = RomDBOpener(self)
        db_opener.status_message.connect(lambda msg: self.statusBar().showMessage(msg, 3000))
        db_opener.file_ready.connect(self.db_ready)
        db_opener.start()

        self.setWindowTitle(QCoreApplication.applicationName())
        self.setMinimumSize(128, 64)
        self.resize(640, 345) # 320 if we didn't have the status bar at the bottom

        self.gpu_view = GraphicsProvider()

        colors = self._settings.get('colors')
        if colors and len(colors) == 4:
            self.gpu_view.set_colors(*colors)

        self.setCentralWidget(self.gpu_view)

        self._create_menus(platform, interpreter)

        self._status_fps = QLabel()
        self.statusBar().addPermanentWidget(self._status_fps)

        self._metadata_overlay = MetadataOverlay(self.gpu_view)
        self._metadata_overlay.move(10, 10)

    def _create_menus(self, platform, interpreter):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')
        a = file_menu.addAction('Open...', 'Ctrl+O')
        a.triggered.connect(self._open_rom_dialog)

        self._recent_menu = file_menu.addMenu('Open Recent')
        self._update_recent_menu()

        file_menu.addSeparator()

        a = file_menu.addAction('Colors...')
        a.triggered.connect(self._choose_colors)


        # View menu
        view_menu = menubar.addMenu('View')

        # Status bar toggle
        visible = self._settings.get('statusbar_visible', True)
        self._action_statusbar = view_menu.addAction('')
        if visible:
            self._action_statusbar.setText('Hide Status Bar')
            self.statusBar().show()
        else:
            self._action_statusbar.setText('Show Status Bar')
            self.statusBar().hide()
        self._action_statusbar.triggered.connect(self._toggle_status_bar)

        view_menu.addSeparator()

        # Fullscreen toggle
        if pyplat.system() != 'Darwin':
            # macOS automatically adds a full screen option
            a = view_menu.addAction('View Full Screen', 'F11')
            a.setCheckable(True)
            a.toggled.connect(self._toggle_fullscreen)

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
        interpreter_group.triggered.connect(self._on_interpreter_selected)


        # Effects menu
        effects_menu = menubar.addMenu('Effects')

        effect_presets = {
            'Ultimate CRT': [ 'Scanlines', 'Glow', 'Barrel', 'Noise', 'Flicker', 'Wrap', 'Scan Delay' ],
            'Classic CRT Arcade': [ 'Scanlines', 'Barrel', 'Glow', 'Vignette', 'Pixel Borders' ],
            'Retro Broadcast TV': [ 'Interlace', 'Vignette', 'Noise', 'Signal Tearing', 'Channel Shift' ],
            'Handheld LCD': [ 'Quantize', 'Pixel Borders', 'Temporal Shimmer', 'Flicker' ],
            'Digital Artifacts': [ 'Blocky Artifacts', 'Quantize', 'Channel Shift', 'Temporal Shimmer', 'Flicker' ],
            'Experimental Neon FX': [ 'Glow', 'Chromatic', 'Edge Glow', 'Temporal Shimmer' ],
            'Broken Cabinet': [ 'Scanlines', 'Mask', 'Flicker', 'Scan Delay', 'Signal Tearing' ],
            'Clean': [],
        }

        presets_menu = effects_menu.addMenu('Presets')
        for name, effects in effect_presets.items():
            a = presets_menu.addAction(name)
            a.triggered.connect(lambda checked=False, e=effects: self._apply_shader_preset(e))

        effects_menu.addSeparator()

        self._shader_group = QActionGroup(effects_menu)
        self._shader_group.setExclusive(False)
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
            a = self._shader_group.addAction(name)
            a.setCheckable(True)
            a.setChecked(getter())
            a.toggled.connect(lambda checked, s=setter: (s(checked), self._save_shader_state()))
            effects_menu.addAction(a)

        self._restore_shader_state()

    def _update_recent_menu(self):
        self._recent_menu.clear()
        recent = self._settings.get('recent_files', [])

        if recent:
            for path in recent[:10]:
                action = QAction(Path(path).name, self)
                action.setData(path)
                action.setToolTip(path)
                action.triggered.connect(self._open_recent)
                self._recent_menu.addAction(action)

            self._recent_menu.addSeparator()
            clear_action = QAction('Clear Menu', self)
            clear_action.triggered.connect(self._clear_recent_files)
            self._recent_menu.addAction(clear_action)
        else:
            action = QAction('Clear Menu', self)
            action.setEnabled(False)
            self._recent_menu.addAction(action)

    def _add_to_recent_files(self, path: str):
        recent = self._settings.get('recent_files', [])
        path = str(Path(path))
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._settings['recent_files'] = recent[:10]

    def _clear_recent_files(self):
        self._settings['recent_files'] = []
        self._update_recent_menu()

    def _open_recent(self):
        action = self.sender()
        path = action.data()
        if path:
            self._open_rom(path)

    def _open_rom_dialog(self):
        last_dir = self._settings.get('last_open_dir', QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))

        fname, _ = QFileDialog.getOpenFileName(
            self, 'Open ROM', last_dir, 'Chip-8 (*.ch8);;BIN (*.bin)'
        )

        if fname:
            self._settings['last_open_dir'] = str(Path(fname).parent)
            self._open_rom(fname)

    def _open_rom(self, fname):
        self._add_to_recent_files(fname)
        self._update_recent_menu()

        metadata = self._rom_db.get_metadata_by_path(fname)
        self._metadata_overlay.update_metadata(metadata)
        if metadata.get('title'):
            self.setWindowTitle(f'{QCoreApplication.applicationName()} - {metadata.get("title")}')

        try:
            platform = chipped8.PlatformTypes(metadata.get('best_platform', 'originalChip8'))
        except:
            platform = chipped8.PlatformTypes.originalChip8
        for a in self._platform_group.actions():
            if a.text() == str(platform):
                a.setChecked(True)
                break

        tickrate = metadata.get('tickrate', -1)

        self.loadRom.emit(fname, platform, tickrate)

    def _toggle_fullscreen(self, enabled):
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def _toggle_status_bar(self):
        visible = self._settings.get('statusbar_visible', True)
        if visible:
            self._action_statusbar.setText('Show Status Bar')
            self.statusBar().hide()
        else:
            self._action_statusbar.setText('Hide Status Bar')
            self.statusBar().show()
        self._settings['statusbar_visible'] = not visible

    def _choose_colors(self):
        colors = self.gpu_view.get_colors()
        d = ColorSelectorDialog(*colors)
        if d.exec() == QDialog.Accepted:
            colors = d.get_colors()
            self._settings['colors'] = colors
            self.gpu_view.set_colors(*colors)

    def _apply_shader_preset(self, enabled_effects: set[str]):
        for action in self._shader_group.actions():
            name = action.text()
            enable = True if name in enabled_effects else False
            if action.isChecked() != enable:
                action.setChecked(enable)

    def _restore_shader_state(self):
        enabled = set(self._settings.get('enabled_shaders', []))
        for action in self._shader_group.actions():
            name = action.text()
            if name in enabled:
                action.setChecked(True)

    def _save_shader_state(self):
        enabled = [
            action.text() for action in self._shader_group.actions() if action.isChecked()
        ]
        self._settings.set('enabled_shaders', enabled)

    @Slot(object)
    def db_ready(self, data):
        if not data:
            return
        self._rom_db.load_data(data)
        self.statusBar().showMessage('Ready', 3000)

    def _on_interpreter_selected(self, action):
        self._settings['interpreter'] = action.text()
        self.interpreterChanged.emit('', action.text())
        self.interpreter = chipped8.InterpreterTypes(action.text())

    @Slot(float, float)
    def update_fps(self, frame_sec, fps):
        self._status_fps.setText(f'fps: {round(fps)}')

    def changeEvent(self, event):
        super().changeEvent(event)
        if isinstance(event, QWindowStateChangeEvent):
            if self.isFullScreen():
                self._action_statusbar.setEnabled(False)
                self.statusBar().hide()
            else:
                visible = self._settings.get('statusbar_visible', True)
                if visible:
                    self.statusBar().show()
                else:
                    self.statusBar().hide()
                self._action_statusbar.setEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_AsciiTilde:
            if self._metadata_overlay.isVisible():
                self._metadata_overlay.hide()
            else:
                self._metadata_overlay.show()
        else:
            self.keyEvent.emit(event.key(), True, event.modifiers().value)

    def keyReleaseEvent(self, event):
        self.keyEvent.emit(event.key(), False, event.modifiers().value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._metadata_overlay.move(10, 10)
