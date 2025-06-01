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

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QObject, Slot, QThread, QMetaObject, Q_ARG
import sys
from contextlib import suppress

from .mainwindow import MainWindow
from .audio import AudioPlayer
from .c8handler import c8Handler

class QtApp(QObject):
    def __init__(self, args):
        super().__init__()
        self._args = args

    def run(self):
        QApplication.setApplicationName('Chipped8')

        app = QApplication(sys.argv)
        win = MainWindow(self._args.platform, self._args.interpreter)

        # Put the emulator on a thread
        c8_thread = QThread()
        c8_thread.setObjectName('c8_thread')
        c8handler = c8Handler(self._args.platform, self._args.interpreter)
        c8handler.moveToThread(c8_thread)

        c8handler.blitReady.connect(win.gpu_view.blitScreen)
        c8handler.fps.connect(win.update_fps)
        c8handler.clearScreenReady.connect(win.gpu_view.clearScreen)
        c8handler.updateScreen.connect(win.gpu_view.update)

        # Put the audio playback on a thread
        audio_thread = QThread()
        audio_thread.setObjectName('audio_thread')
        audio = AudioPlayer()
        audio.moveToThread(audio_thread)
        audio_thread.started.connect(audio.start)
        c8handler.audioReady.connect(audio.play)

        win.gpu_view.focusChanged.connect(c8handler.process_frames)
        win.platformChanged.connect(c8handler.reload_rom)
        win.interpreterChanged.connect(c8handler.reload_rom)
        win.keyEvent.connect(c8handler.key_event)
        win.loadRom.connect(c8handler.load_rom)
        c8handler.errorOccurred.connect(self.show_error)

        # Start the processing threads
        audio_thread.start()
        c8_thread.start()

        if self._args.in_file:
            QMetaObject.invokeMethod(c8handler, 'load_rom', Qt.QueuedConnection, Q_ARG(str, self._args.in_file))

        win.show()
        # Start execution of the GUI
        ret = app.exec()

        # Stop the timer for processing frames
        # This is so the process frame timer stops.
        # We can't call it directly because we're on a different thread. Hence a blocking queued conenction.
        QMetaObject.invokeMethod(c8handler, 'process_frames', Qt.BlockingQueuedConnection, Q_ARG(bool, False))

        # Stop the audio. The audio buffer is filled using an internal timer that keeps it full.
        QMetaObject.invokeMethod(audio, "stop", Qt.BlockingQueuedConnection)

        # Stop our threads
        c8_thread.quit()
        audio_thread.quit()

        # Wait for them to fully exit
        c8_thread.wait()
        audio_thread.wait()

        # Exit
        sys.exit(ret)

    @Slot(str)
    def show_error(self, message):
        QMessageBox.critical(None, 'Error', message)
