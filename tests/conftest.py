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
