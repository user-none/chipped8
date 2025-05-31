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

import os
import hashlib
import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QStandardPaths

FILE_URL = 'https://raw.githubusercontent.com/chip-8/chip-8-database/refs/heads/master/database/programs.json'
FILE_NAME = 'programs.json'
MAX_AGE_DAYS = 180

def get_app_data_path():
    base_path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    full_path = os.path.join(base_path, "rom_db")
    os.makedirs(full_path, exist_ok=True)
    return os.path.join(full_path, FILE_NAME)

class RomDBOpener(QThread):
    status_message = Signal(str)
    file_ready = Signal(object)  # data: dict or list

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = get_app_data_path()

    def run(self):
        needs_download = False
        file_exists = os.path.exists(self._file_path)

        if not file_exists:
            self.status_message.emit('Downloading ROM DB...')
            needs_download = True
        else:
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self._file_path))
            if file_age > timedelta(days=MAX_AGE_DAYS):
                self.status_message.emit('Updating ROM DB...')
                needs_download = True

        if needs_download:
            try:
                urllib.request.urlretrieve(FILE_URL, self._file_path)
                self.status_message.emit('ROM DB downloaded')
            except:
                if not file_exists:
                    self.status_message.emit('ROM DB download failed')
                    return

        try:
            self.status_message.emit('Opening ROM DB...')
            with open(self._file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                self.file_ready.emit(json_data)
        except Exception as e:
            self.status_message.emit(f'Failed to open ROM DB {e}')

class RomDatabase:
    def __init__(self, data: list = None):
        self._hash_to_entry = {}
        self._loaded = False

        if data:
            self.load_data(data)

    def load_data(self, data: list):
        self._hash_to_entry.clear()
        for entry in data:
            roms = entry.get('roms', {})
            for sha1, rom_info in roms.items():
                self._hash_to_entry[sha1] = {
                    'entry': entry,
                    'rom_info': rom_info,
                }
        self._loaded = True

    def is_ready(self) -> bool:
        return self._loaded

    def compute_sha1(self, filepath: str) -> str:
        h = hashlib.sha1()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def get_metadata_by_path(self, filepath: str):
        sha1 = self.compute_sha1(filepath)
        return self.get_metadata_by_hash(sha1)

    def get_metadata_by_hash(self, sha1: str) -> dict:
        if not self._loaded:
            return {} # or raise RuntimeError('Database not loaded yet')

        entry = self._hash_to_entry.get(sha1)
        if not entry:
            return {}

        rom_info = entry['rom_info']
        platforms = rom_info.get('platforms', [])
        best_platform = platforms[0] if platforms else 'originalChip8'

        d = {
            'sha1': sha1,
            'title': entry['entry'].get('title', 'Unknown Title'),
            'tickrate': rom_info.get('tickrate', None),
            'best_platform': best_platform,
            'platforms': platforms,
            'authors': entry['entry'].get('authors'),
            'description': entry['entry'].get('description', rom_info.get('description', '')),
            'release': entry['entry'].get('release')
            }

        if not d.get('tickrate'):
            del d['tickrate']

        return d
