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

from PySide6.QtCore import Qt, QObject, QBuffer, Signal, Slot
from PySide6.QtMultimedia import QAudioSink, QAudioFormat, QMediaDevices

from chipped8 import generate_audio_frame

class AudioPlayer(QObject):

    def __init__(self):
        QObject.__init__(self)
        self._sample_rate = 48000

        aformat = QAudioFormat()
        aformat.setSampleRate(self._sample_rate)
        aformat.setChannelCount(1)
        aformat.setChannelConfig(QAudioFormat.ChannelConfigMono)
        aformat.setSampleFormat(QAudioFormat.UInt8)

        self._sink = QAudioSink(QMediaDevices.defaultAudioOutput(), aformat)
        self._sink_io = self._sink.start()

    @Slot(bytearray, int)
    def play(self, pattern, pitch):
        frame = generate_audio_frame(pattern, pitch, self._sample_rate)
        self._sink_io.write(frame)

