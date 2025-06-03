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

import time

from collections import deque
from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtMultimedia import QAudioSink, QAudioFormat, QMediaDevices

import numpy as np

from chipped8 import generate_audio_frame

class AudioPlayer(QObject):
    def __init__(self):
        super().__init__()

        self._sample_rate = 48000
        self._frame_samples = self._sample_rate // 60  # 800 samples at 60Hz
        max_buffer_size = self._frame_samples * 4 # Only allow 4 frames to be buffered
        self._buffer = deque(maxlen=max_buffer_size)
        self._phase = 0.0

        # Setup audio format
        aformat = QAudioFormat()
        aformat.setSampleRate(self._sample_rate)
        aformat.setChannelCount(1)
        aformat.setSampleFormat(QAudioFormat.UInt8)

        # Create and start audio sink
        self._sink = QAudioSink(QMediaDevices.defaultAudioOutput(), aformat)
        self._sink.setBufferSize(max_buffer_size)
        self._sink_io = self._sink.start()

        # Clock-based pacing
        self._last_write_ns = time.perf_counter_ns()
        self._frame_interval_ns = 1_000_000_000 // 60  # 16666666 ns which is ~16.666ms which is 1 frame

        self._last_pattern = bytes(16)
        self._last_pitch = None

    @Slot()
    def start(self):
        # Drain the audio buffer multilpe times a frame
        # We need to keep the audio sink full even if
        # were writing silence to prevent popping when
        # the DAC powers up to write audio.
        self._timer = QTimer(self)
        self._timer.setInterval(5)
        self._timer.timeout.connect(self._feed_audio)
        self._timer.start()

    @Slot()
    def stop(self):
        self._timer.stop()

    def _feed_audio(self):
        now_ns = time.perf_counter_ns()

        # Keep writing until we're caught up (in case we fell behind)
        while now_ns - self._last_write_ns >= self._frame_interval_ns:
            to_write = min(self._frame_samples, self._sink.bytesFree())
            if to_write < 1:
                return  # truly nothing can be written

            output = bytearray()
            real_audio = min(len(self._buffer), to_write)
            output.extend([self._buffer.popleft() for _ in range(real_audio)])
            # Pad / write silence if there isn't enough data
            output.extend([0x80] * (to_write - real_audio))

            self._sink_io.write(bytes(output))
            self._last_write_ns += self._frame_interval_ns

    def _pitch_changed_enough(self, current: int, previous: int | None, threshold: int = 2) -> bool:
        if previous is None:
            return False
        return abs(current - previous) >= threshold

    def _pattern_changed_enough(self, current: bytes, previous: bytes, threshold: int = 16) -> bool:
        a = np.frombuffer(current, dtype=np.uint8)
        b = np.frombuffer(previous, dtype=np.uint8)

        xor = np.bitwise_xor(a, b)
        bits = np.unpackbits(xor)
        return np.count_nonzero(bits) >= threshold

    def play(self, pattern: bytes, pitch: int):
        pattern_changed = self._pattern_changed_enough(pattern, self._last_pattern)
        pitch_changed = self._pitch_changed_enough(pitch, self._last_pitch)

        self._last_pattern = pattern
        self._last_pitch = pitch

        if pattern_changed or pitch_changed:
            self._phase = 0.0

        frame, self._phase = generate_audio_frame(
            pattern,
            pitch,
            self._sample_rate,
            self._frame_samples,
            self._phase,
            amplitude=0.05
        )
        self._buffer.extend(frame)
