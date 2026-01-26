#!/usr/bin/env python

# Copyright 2026 John Schember <john@nachtimwald.com>
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

'''
JIT Memory management for macOS ARM64.

Handles allocation of executable memory using mmap with MAP_JIT,
and manages W^X (Write XOR Execute) via pthread_jit_write_protect_np.
'''

import ctypes
from ctypes import c_void_p, c_size_t, c_int

# Load system libraries
# On macOS, most system functions are available through libSystem.B.dylib
# or through the default process library (None)
_libSystem = ctypes.CDLL('/usr/lib/libSystem.B.dylib')

# Aliases for clarity
_libc = _libSystem
_libpthread = _libSystem
_libsystem = _libSystem

# mmap constants for macOS
MAP_PRIVATE = 0x0002
MAP_ANONYMOUS = 0x1000
MAP_JIT = 0x0800  # Critical for ARM64 JIT
PROT_READ = 0x01
PROT_WRITE = 0x02
PROT_EXEC = 0x04

# Configure function signatures
_libc.mmap.argtypes = [c_void_p, c_size_t, c_int, c_int, c_int, c_size_t]
_libc.mmap.restype = c_void_p

_libc.munmap.argtypes = [c_void_p, c_size_t]
_libc.munmap.restype = c_int

# pthread_jit_write_protect_np(int enabled)
# 0 = writable, 1 = executable
_libpthread.pthread_jit_write_protect_np.argtypes = [c_int]
_libpthread.pthread_jit_write_protect_np.restype = None

# sys_icache_invalidate(void* start, size_t size)
_libsystem.sys_icache_invalidate.argtypes = [c_void_p, c_size_t]
_libsystem.sys_icache_invalidate.restype = None

# MAP_FAILED is (void*)-1
MAP_FAILED = ctypes.cast(-1, c_void_p).value


class JITMemory:
    '''Manages executable memory for JIT code on macOS ARM64.'''

    def __init__(self, size: int = 4 * 1024 * 1024):  # 4MB default
        '''
        Allocate a JIT memory buffer.

        Args:
            size: Size of the buffer in bytes (default 4MB)
        '''
        self.size = size
        self.offset = 0  # Current write position

        # Allocate JIT memory with read/write/execute permissions
        self.buffer = _libc.mmap(
            None,
            size,
            PROT_READ | PROT_WRITE | PROT_EXEC,
            MAP_PRIVATE | MAP_ANONYMOUS | MAP_JIT,
            -1,
            0
        )

        if self.buffer == MAP_FAILED:
            raise OSError('Failed to allocate JIT memory. '
                         'Ensure the process has JIT entitlements on macOS.')

    def write_code(self, code: bytes) -> int:
        '''
        Write code bytes to the JIT buffer.

        Args:
            code: The machine code bytes to write

        Returns:
            The offset in the buffer where the code was written

        Raises:
            MemoryError: If the buffer is exhausted
        '''
        if self.offset + len(code) > self.size:
            raise MemoryError('JIT buffer exhausted')

        start_offset = self.offset

        # Make writable (disable execute protection)
        _libpthread.pthread_jit_write_protect_np(0)

        # Write the bytes
        dst = self.buffer + self.offset
        ctypes.memmove(dst, code, len(code))
        self.offset += len(code)

        # Make executable (enable execute protection)
        _libpthread.pthread_jit_write_protect_np(1)

        # Flush instruction cache to ensure CPU sees new code
        _libsystem.sys_icache_invalidate(self.buffer + start_offset, len(code))

        return start_offset

    def get_callable(self, offset: int, restype=c_int, argtypes=None):
        '''
        Get a callable ctypes function at the given offset.

        Args:
            offset: Offset into the buffer where the function starts
            restype: Return type (default c_int)
            argtypes: Argument types (default [c_void_p] for state pointer)

        Returns:
            A callable ctypes function
        '''
        if argtypes is None:
            argtypes = [c_void_p]

        func_type = ctypes.CFUNCTYPE(restype, *argtypes)
        return func_type(self.buffer + offset)

    def reset(self):
        '''Reset the buffer offset, allowing reuse of the entire buffer.'''
        self.offset = 0

    def __del__(self):
        '''Free the allocated memory.'''
        if hasattr(self, 'buffer') and self.buffer and self.buffer != MAP_FAILED:
            _libc.munmap(self.buffer, self.size)
