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

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

class MetadataOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Widget)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._label = QLabel()
        self._label.setStyleSheet('''
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 160);
                padding: 8px;
                font-family: 'Courier New', Consolas, Menlo, Monaco, 'DejaVu Sans Mono', 'Liberation Mono', monospace;
            }
        ''')
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._label.setText('No metadata available.')
        self.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # margin from the parent edge
        layout.addWidget(self._label)
        self.setLayout(layout)

    def update_metadata(self, metadata: dict):
        if not metadata:
            self._label.setText('No metadata available.')
        else:
            text = '\n'.join([
                f'Title: {metadata.get("title", "-")}',
                f'Tickrate: {metadata.get("tickrate", "-")}',
                f'Platforms: {metadata.get("platforms", "-")}',
                f'Authors: {", ".join(metadata.get("authors", []))}',
                f'Released: {metadata.get("release", "-")}',
                '',
                metadata.get('description', ''),
            ])
            self._label.setText(text)
        self.adjustSize()
