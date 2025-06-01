#!/usr/bin/env python

# Copyright 2024-2025 John Schember <john@nachtimwald.com>
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

import numpy as np

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

def generate_audio_frame(pattern: bytes, pitch: int, sample_rate: int,
                         num_samples: int, start_phase: float, amplitude: float) -> tuple[bytes, float]:
    '''
    pattern: 16 bytes (128 bits) repeating waveform pattern
    pitch: controls frequency via spec formula
    sample_rate: audio sample rate (48000)
    num_samples: number of output samples to generate (~800)
    start_phase: phase position in bits for continuity
    amplitude: float between 0..1 to scale waveform amplitude
    '''
    freq = 4000.0 * (2 ** ((pitch - 64) / 48.0))
    total_bits = 128  # 16 bytes * 8 bits
    step = freq / sample_rate  # bits to advance per sample

    # Vector of phases for each sample
    phases = (start_phase + step * np.arange(num_samples)) % total_bits
    bit_indices = phases.astype(np.uint8)

    # Compute byte indices and bit positions
    byte_indices = bit_indices // 8
    bit_offsets = 7 - (bit_indices % 8)

    # Convert pattern to NumPy array for vectorized indexing
    pattern_arr = np.frombuffer(pattern, dtype=np.uint8)
    selected_bytes = pattern_arr[byte_indices]
    bit_vals = (selected_bytes >> bit_offsets) & 1

    # Convert bits to audio values
    waveform = np.where(bit_vals, amplitude, -amplitude)
    samples = np.clip(128 + waveform * 127, 0, 255).astype(np.uint8)

    return samples.tobytes(), float(phases[-1])
