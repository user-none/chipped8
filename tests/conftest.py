import pytest

from chipped8.core.emulator import Emulator
from chipped8.core.platform import PlatformTypes
from chipped8.core.interpreter import InterpreterTypes

# Interpreter types
interpreter_types = [InterpreterTypes.pure, InterpreterTypes.cachedo, InterpreterTypes.cachedlp, InterpreterTypes.cachedlh]

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
