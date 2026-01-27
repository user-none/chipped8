import pytest

from chipped8.core.emulator import Emulator
from chipped8.core.platform import PlatformTypes
from chipped8.core.interpreter import InterpreterTypes, is_dynarec_available

# Interpreter types - include dynarec if available on this platform
interpreter_types = [
    InterpreterTypes.pure,
    InterpreterTypes.cachedo,
    InterpreterTypes.cachedlp,
    InterpreterTypes.cachedlh,
]

if is_dynarec_available():
    interpreter_types.append(InterpreterTypes.dynarec)

# Platform types
@pytest.fixture(params=interpreter_types)
def interpreter_type(request):
    return request.param

@pytest.fixture
def emulator(interpreter_type):
    # Initialize Emulator with selected interpreter and platform
    emu = Emulator(
        platform=PlatformTypes.xochip,
        interpreter_type=interpreter_type
    )
    return emu


@pytest.fixture
def dynarec_emulator():
    """Fixture that provides only a dynarec emulator (for dynarec-specific tests)."""
    if not is_dynarec_available():
        pytest.skip("Dynarec not available on this platform")
    emu = Emulator(
        platform=PlatformTypes.xochip,
        interpreter_type=InterpreterTypes.dynarec
    )
    return emu


# Cached interpreter types (have block caches, excludes pure)
cached_interpreter_types = [
    InterpreterTypes.cachedo,
    InterpreterTypes.cachedlp,
    InterpreterTypes.cachedlh,
]

if is_dynarec_available():
    cached_interpreter_types.append(InterpreterTypes.dynarec)


@pytest.fixture(params=cached_interpreter_types)
def cached_emulator(request):
    """Fixture that provides emulators with block caching (excludes pure interpreter)."""
    emu = Emulator(
        platform=PlatformTypes.xochip,
        interpreter_type=request.param
    )
    return emu


def get_block_cache(cpu):
    """Get the block cache dict from any cached interpreter type."""
    # dynarec
    if hasattr(cpu, '_block_cache') and isinstance(cpu._block_cache, dict):
        return cpu._block_cache
    # cachedo
    if hasattr(cpu, '_block_emitter') and hasattr(cpu._block_emitter, '_block_cache'):
        return cpu._block_emitter._block_cache
    # cachedlp
    if hasattr(cpu, '_emitter') and hasattr(cpu._emitter, '_block_cache'):
        return cpu._emitter._block_cache
    # cachedlh - also has _block_cache at top level
    if hasattr(cpu, '_block_cache'):
        return cpu._block_cache
    return None


def is_cache_empty(cpu):
    """Check if the block cache is empty for any cached interpreter type."""
    cache = get_block_cache(cpu)
    if cache is not None:
        return len(cache) == 0
    # Also check pc_instr_cache for cachedo
    if hasattr(cpu, '_block_emitter') and hasattr(cpu._block_emitter, '_pc_instr_cache'):
        return len(cpu._block_emitter._pc_instr_cache) == 0
    return True
