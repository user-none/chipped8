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

from copy import deepcopy

class Audio():

    def __init__(self):
        self._pattern = list(bytes.fromhex('00 00 FF FF 00 00 FF FF 00 00 FF FF 00 00 FF FF'))
        self._pitch = 127
        self._sound_length = 1 / 60

    def __deepcopy__(self, memo):
        c = Audio()
        if self._pattern:
            c._pattern = deepcopy(self._pattern)
        c._pitch = self._pitch
        return c

    def set_pattern(self, pattern):
        self._pattern[:] = pattern[:]

    def get_pattern(self):
        return self._pattern

    def set_pitch(self, pitch):
        self._pitch = pitch

    def get_pitch(self):
        return self._pitch


def generate_audio_frame(pattern, pitch, sample_rate=48000, sound_length=1/60):
    freq = 4000 * 2 ** ((pitch - 64) / 48)
    num_samples = math.ceil(sample_rate * sound_length)
    step = freq / sample_rate
    binary_data = ''.join(format(byte, '08b') for byte in pattern)

    pos = 0.0
    samples = []
    for i in range(num_samples):
        p = int(pos) % len(binary_data)
        samples.append(0x15 if binary_data[p] == '1' else 0)
        pos = pos + step

    # IIR filter to smooth square into sine wave
    for i in range(1, num_samples):
        samples[i] = int(samples[i-1] * 0.4 + samples[i]) % 0xFF

    return bytes(samples)

