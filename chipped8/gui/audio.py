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

import math

from PySide6.QtCore import Qt, QObject, QBuffer, Signal, Slot
from PySide6.QtMultimedia import QAudioSink, QAudioFormat, QMediaDevices

class AudioPlayer(QObject):

    def __init__(self):
        self._sound_buffer = QBuffer()
        self._sample_rate = 48000
        self._sound_length = 1 / 60

        self._default_pattern = bytes.fromhex('00 00 FF FF 00 00 FF FF 00 00 FF FF 00 00 FF FF')
        self._default_pitch = 127

        aformat = QAudioFormat()
        aformat.setSampleRate(self._sample_rate)
        aformat.setChannelCount(1)
        aformat.setChannelConfig(QAudioFormat.ChannelConfigMono)
        aformat.setSampleFormat(QAudioFormat.UInt8)

        self._sink = QAudioSink(QMediaDevices.defaultAudioOutput(), aformat)
        self._sink_io = self._sink.start()

    def _generate_frame(self, pattern, pitch):
        freq = 4000 * 2 ** ((pitch - 64) / 48)
        num_samples = math.ceil(self._sample_rate * self._sound_length)
        step = freq / self._sample_rate 
        binary_data = ''.join(format(byte, '08b') for byte in pattern)

        pos = 0.0
        samples = []
        for i in range(num_samples):
            p = int(pos) % len(binary_data)
            samples.append(0x40 if binary_data[p] == '1' else 0)
            pos = pos + step

        return bytes(samples)

    @Slot(bytearray, int)
    def play(self, pattern, pitch):
        if not pattern:
            pattern = self._default_pattern
            pitch = self._default_pitch

        frame = self._generate_frame(pattern, pitch)
        self._sink_io.write(frame)

