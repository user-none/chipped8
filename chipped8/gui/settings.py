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

import json
from pathlib import Path

from PySide6.QtCore import QStandardPaths

class AppSettings:

    def __init__(self, filename='config.json'):
        self._path = self._get_config_path(filename)
        self._data = self._load()

    def _get_config_path(self, filename):
        config_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / filename

    def _load(self):
        try:
            with self._path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
        return {}

    def _save(self):
        with self._path.open('w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=4)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def remove(self, key):
        if key in self._data:
            del self._data[key]
            self._save()

    def clear(self):
        self._data.clear()
        self._save()

    def keys(self):
        return list(self._data.keys())

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.remove(key)

    def __contains__(self, key):
        return key in self._data
