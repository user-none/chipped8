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

import argparse
import os
import sys

from .gui.qt_app import QtApp
import chipped8

def parse_args():
    parser = argparse.ArgumentParser(
            prog = os.path.basename(sys.argv[0]),
            description = 'Chip8 Emulator')
    parser.add_argument('in_file', help='Input ROM file', nargs='?')
    parser.add_argument('-p', '--platform', type=chipped8.PlatformTypes, choices=chipped8.PlatformTypes, default=chipped8.PlatformTypes.originalChip8, help='Set the Chip-8 instruction set to use')
    parser.add_argument('-i', '--interpreter', type=chipped8.InterpreterTypes, choices=chipped8.InterpreterTypes, help='Set the type of interpreter to use')
    parser.add_argument('--version', action='version', version='%(prog)s {v}'.format(v=chipped8.__version__))
    return parser.parse_args()

def main():
    args = parse_args()
    app = QtApp(args)

    try:
        app.run()
    except Exception as e:
        print('Error: {0}'.format(e))
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())

