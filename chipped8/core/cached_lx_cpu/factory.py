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

from random import randint

from ..exceptions import UnknownOpCodeException
from ..keys import KeyState
from ..display import Plane, ResolutionMode
from .instr_kind import InstrKind

def _get_opcode(pc, memory):
    return (memory.get_byte(pc) << 8) | memory.get_byte(pc + 1)

def _get_next_opcode(pc, memory):
    return (memory.get_byte(pc + 2) << 8) | memory.get_byte(pc + 3)

# Returns: (advance, self_modified, is_jump)

def _execute_00CN(cpu, n):
    cpu._display.scroll_down(n)
    return (True, False, False)

def _execute_00DN(cpu, n):
    cpu._display.scroll_up(n)
    return (True, False, False)

def _execute_00E0(cpu):
    cpu._display.clear_screen()
    return (True, False, False)

def _execute_00EE(cpu):
    self_modified = False

    pc = cpu._stack.pop()
    if pc < 0x200 or pc >= cpu._memory.ram_start()-2:
        self_modified = True

    cpu._registers.set_PC(pc)
    cpu._registers.advance_PC()

    return (True, self_modified, True)

def _execute_00FB(cpu):
    cpu._display.scroll_right()
    return (True, False, False)

def _execute_00FC(cpu):
    cpu._display.scroll_left()
    return (True, False, False)

def _execute_00FD():
    raise ExitInterpreterException()

def _execute_00FE(cpu):
    cpu._display.resmode = ResolutionMode.lowres
    return (True, False, False)

def _execute_00FF(cpu):
    cpu._display.resmode = ResolutionMode.hires
    return (True, False, False)

def _execute_1NNN(cpu, nnn):
    self_modified = False
    if nnn < 0x200 or nnn >= cpu._memory.ram_start():
        self_modified = True

    cpu._registers.set_PC(nnn)
    return (True, self_modified, True)

def _execute_2NNN(cpu, nnn):
    cpu._stack.push(cpu._registers.get_PC()-2)

    self_modified = False
    if nnn < 0x200 or nnn >= cpu._memory.ram_start():
        self_modified = True

    cpu._registers.set_PC(nnn)
    return (True, self_modified, True)

def _execute_3XNN(cpu, x, nn):
    if cpu._registers.get_V(x) == nn:
        if _get_opcode(cpu._registers.get_PC(), cpu._memory) == 0xF000:
            cpu._registers.advance_PC()
        cpu._registers.advance_PC()

    return (True, False, False)

def _execute_4XNN(cpu, x, nn):
    if cpu._registers.get_V(x) != nn:
        if _get_opcode(cpu._registers.get_PC(), cpu._memory) == 0xF000:
            cpu._registers.advance_PC()
        cpu._registers.advance_PC()

    return (True, False, False)

def _execute_5XY0(cpu, x, y):
    if cpu._registers.get_V(x) == cpu._registers.get_V(y):
        if _get_opcode(cpu._registers.get_PC(), cpu._memory) == 0xF000:
            cpu._registers.advance_PC()
        cpu._registers.advance_PC()

    return (True, False, False)

def _execute_5XY2(cpu, x, y):
    self_modified = False
    if cpu._registers.get_I() < cpu._memory.ram_start():
        self_modified = True

    step = 1 if x <= y else -1
    for i, v in enumerate(range(x, y+step, step)):
        cpu._memory.set_byte(cpu._registers.get_I() + i, cpu._registers.get_V(v))

    return (True, self_modified, False)

def _execute_5XY3(cpu, x, y):
    step = 1 if x <= y else -1
    for i, v in enumerate(range(x, y+step, step)):
        cpu._registers.set_V(v, cpu._memory.get_byte(cpu._registers.get_I() + i))
    return (True, False, False)

def _execute_6XNN(cpu, x, nn):
    cpu._registers.set_V(x, nn)
    return (True, False, False)

def _execute_7XNN(cpu, x, nn):
    cpu._registers.set_V(x, cpu._registers.get_V(x) + nn)
    return (True, False, False)

def _execute_8XY0(cpu, x, y):
    cpu._registers.set_V(x, cpu._registers.get_V(y))
    return (True, False, False)

def _execute_8XY1(cpu, x, y):
    cpu._registers.set_V(x, cpu._registers.get_V(x) | cpu._registers.get_V(y))
    if cpu._quirks.logic:
        cpu._registers.set_V(0xF, 0)
    return (True, False, False)

def _execute_8XY2(cpu, x, y):
    cpu._registers.set_V(x, cpu._registers.get_V(x) & cpu._registers.get_V(y))
    if cpu._quirks.logic:
        cpu._registers.set_V(0xF, 0)
    return (True, False, False)

def _execute_8XY3(cpu, x, y):
    cpu._registers.set_V(x, cpu._registers.get_V(x) ^ cpu._registers.get_V(y))
    if cpu._quirks.logic:
        cpu._registers.set_V(0xF, 0)
    return (True, False, False)

def _execute_8XY4(cpu, x, y):
    n = cpu._registers.get_V(x) + cpu._registers.get_V(y)
    cpu._registers.set_V(x, n)
    cpu._registers.set_V(0xF, 1 if n > 0xFF else 0)
    return (True, False, False)

def _execute_8XY5(cpu, x, y):
    vx = cpu._registers.get_V(x)
    vy = cpu._registers.get_V(y)
    n = vx - vy

    cpu._registers.set_V(x, n)
    cpu._registers.set_V(0xF, 1 if vx >= vy else 0)
    return (True, False, False)

def _execute_8XY6(cpu, x, y):
    if cpu._quirks.shift:
        n = cpu._registers.get_V(x)
    else:
        n = cpu._registers.get_V(y)

    cpu._registers.set_V(x, n >> 1)
    cpu._registers.set_V(0xF, n & 0x1)
    return (True, False, False)

def _execute_8XY7(cpu, x, y):
    vx = cpu._registers.get_V(x)
    vy = cpu._registers.get_V(y)
    n = vy - vx

    cpu._registers.set_V(x, n)
    cpu._registers.set_V(0xF, 1 if vy >= vx else 0)
    return (True, False, False)

def _execute_8XYE(cpu, x, y):
    if cpu._quirks.shift:
        n = cpu._registers.get_V(x)
    else:
        n = cpu._registers.get_V(y)

    cpu._registers.set_V(x, n << 1)
    cpu._registers.set_V(0xF, n >> 7)
    return (True, False, False)

def _execute_9XY0(cpu, x, y):
    if cpu._registers.get_V(x) != cpu._registers.get_V(y):
        if _get_opcode(cpu._registers.get_PC(), cpu._memory) == 0xF000:
            cpu._registers.advance_PC()
        cpu._registers.advance_PC()

    return (True, False, False)

def _execute_ANNN(cpu, nnn):
    cpu._registers.set_I(nnn)
    return (True, False, False)

def _execute_BNNN(cpu, x, nnn):
    self_modified = False

    if cpu._quirks.jump:
        n = nnn + cpu._registers.get_V(x)
    else:
        n = nnn + cpu._registers.get_V(0)

    if n >= cpu._memory.ram_start():
        self_modified = True

    cpu._registers.set_PC(n)
    return (True, self_modified, True)

def _execute_CXNN(cpu, x, nn):
    cpu._registers.set_V(x, randint(0, 255) & nn)
    return (True, False, False)

def _execute_DXYN(cpu, x, y, n):
    vx = cpu._registers.get_V(x)
    vy = cpu._registers.get_V(y)

    cpu._display.draw(vx, vy, n, cpu._quirks.wrap, cpu._registers, cpu._memory)
    cpu._vblank_wait = True
    return (True, False, False)

def _execute_EX9E(cpu, x):
    if cpu._keys.get_key_state(cpu._registers.get_V(x)) == KeyState.down:
        if _get_opcode(cpu._registers.get_PC(), cpu._memory) == 0xF000:
            cpu._registers.advance_PC()
        cpu._registers.advance_PC()

    return (True, False, False)

def _execute_EXA1(cpu, x):
    if cpu._keys.get_key_state(cpu._registers.get_V(x)) == KeyState.up:
        if _get_opcode(cpu._registers.get_PC(), cpu._memory) == 0xF000:
            cpu._registers.advance_PC()
        cpu._registers.advance_PC()

    return (True, False, False)

def _execute_F000(cpu):
    addr = _get_next_opcode(cpu._registers.get_PC() - 2, cpu._memory)
    cpu._registers.set_I(addr)
    cpu._registers.advance_PC()
    return (True, False, False)

def _execute_FN01(cpu, n):
    plane = Plane(0)
    if n & 1:
        plane = plane | Plane.p1
    if n & 2:
        plane = plane | Plane.p2
    cpu._display.plane = plane
    return (True, False, False)

def _execute_F002(cpu):
    cpu._audio.pattern = cpu._memory.get_range(cpu._registers.get_I(), 16)
    return (True, False, False)

def _execute_FX07(cpu, x):
    cpu._registers.set_V(x, cpu._timers.delay)
    return (True, False, False)

def _execute_FX0A(cpu, x):
    advance = False

    for i, ks in enumerate(cpu._keys.get_keys()):
        if ks == KeyState.down:
            cpu._registers.set_V(x, i)
            advance = True
            break
    return (advance, False, False)

def _execute_FX15(cpu, x):
    cpu._timers.delay = cpu._registers.get_V(x)
    return (True, False, False)

def _execute_FX18(cpu, x):
    cpu._timers.sound = cpu._registers.get_V(x)
    return (True, False, False)

def _execute_FX1E(cpu, x):
    cpu._registers.set_I(cpu._registers.get_I() + cpu._registers.get_V(x))
    return (True, False, False)

def _execute_FX29(cpu, x):
    n = cpu._registers.get_V(x)
    cpu._registers.set_I(n * 5)
    return (True, False, False)

def _execute_FX30(cpu, x):
    n = cpu._registers.get_V(x)
    cpu._registers.set_I(cpu._memory.font_large_offset() + (n * 10))
    return (True, False, False)

def _execute_FX33(cpu, x):
    self_modified = False
    if cpu._registers.get_I() < cpu._memory.ram_start():
        self_modified = True

    n = cpu._registers.get_V(x)
    cpu._memory.set_byte(cpu._registers.get_I(), n // 100)
    cpu._memory.set_byte(cpu._registers.get_I() + 1, (n // 10) % 10)
    cpu._memory.set_byte(cpu._registers.get_I() + 2, (n % 100) % 10)
    return (True, self_modified, False)

def _execute_FX3A(cpu, x):
    cpu._audio.pitch = cpu._registers.get_V(x)
    return (True, False, False)

def _execute_FX55(cpu, x):
    self_modified = False
    if cpu._registers.get_I() < cpu._memory.ram_start():
        self_modified = True

    for i in range(x + 1):
        cpu._memory.set_byte(cpu._registers.get_I() + i, cpu._registers.get_V(i))

    if not cpu._quirks.memoryLeaveIUnchanged:
        if cpu._quirks.memoryIncrementByX:
            cpu._registers.set_I(cpu._registers.get_I() + x)
        else:
            cpu._registers.set_I(cpu._registers.get_I() + x + 1)
    return (True, self_modified, False)

def _execute_FX65(cpu, x):
    for i in range(x + 1):
        cpu._registers.set_V(i, cpu._memory.get_byte(cpu._registers.get_I() + i))

    if not cpu._quirks.memoryLeaveIUnchanged:
        if cpu._quirks.memoryIncrementByX:
            cpu._registers.set_I(cpu._registers.get_I() + x)
        else:
            cpu._registers.set_I(cpu._registers.get_I() + x + 1)
    return (True, False, False)

def _execute_FX75(cpu, x):
    for i in range(x+1):
        cpu._registers.set_RPL(i, cpu._registers.get_V(i))
    return (True, False, False)

def _execute_FX85(cpu, x):
    for i in range(x+1):
        cpu._registers.set_V(i, cpu._registers.get_RPL(i))
    return (True, False, False)

def get_op_instr(opcode):
    code = (opcode & 0xF000)
    x = (opcode & 0x0F00) >> 8
    y = (opcode & 0x00F0) >> 4
    n = opcode & 0x000F
    nn = opcode & 0x00FF
    nnn = opcode & 0x0FFF

    match code:
        case 0x0000 if (opcode & 0x0FFF) == 0x00C0:
            return (InstrKind.OPERATION, lambda cpu, n=n: _execute_00CN(cpu, n))
        case 0x0000 if (opcode & 0x0FFF) == 0x00D0:
            return (InstrKind.OPERATION, lambda cpu, n=n: _execute_00DN(cpu, n))
        case 0x0000 if (opcode & 0x0FFF) == 0x00E0:
            return (InstrKind.OPERATION, lambda cpu: _execute_00E0(cpu))
        case 0x0000 if (opcode & 0x0FFF) == 0x00EE:
            return (InstrKind.JUMP, lambda cpu: _execute_00EE(cpu))
        case 0x0000 if (opcode & 0x0FFF) == 0x00FB:
            return (InstrKind.OPERATION, lambda cpu: _execute_00FB(cpu))
        case 0x0000 if (opcode & 0x0FFF) == 0x00FC:
            return (InstrKind.OPERATION, lambda cpu: _execute_00FC(cpu))
        case 0x0000 if (opcode & 0x0FFF) == 0x00FD:
            return (InstrKind.EXIT, lambda cpu: _execute_00FD())
        case 0x0000 if (opcode & 0x0FFF) == 0x00FE:
            return (InstrKind.OPERATION, lambda cpu: _execute_00FE(cpu))
        case 0x0000 if (opcode & 0x0FFF) == 0x00FF:
            return (InstrKind.OPERATION, lambda cpu: _execute_00FF(cpu))

        case 0x1000:
            return (InstrKind.JUMP, lambda cpu, nnn=nnn: _execute_1NNN(cpu, nnn))

        case 0x2000:
            return (InstrKind.JUMP, lambda cpu, nnn=nnn: _execute_2NNN(cpu, nnn))

        case 0x3000:
            return (InstrKind.COND_ADVANCE, lambda cpu, x=x, nn=nn: _execute_3XNN(cpu, x, nn))

        case 0x4000:
            return (InstrKind.COND_ADVANCE, lambda cpu, x=x, nn=nn: _execute_4XNN(cpu, x, nn))

        case 0x5000 if (opcode & 0x000F) == 0x0000:
            return (InstrKind.COND_ADVANCE, lambda cpu, x=x, y=y: _execute_5XY0(cpu, x, y))
        case 0x5000 if (opcode & 0x000F) == 0x0002:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_5XY2(cpu, x, y))
        case 0x5000 if (opcode & 0x000F) == 0x0003:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_5XY3(cpu, x, y))

        case 0x6000:
            return (InstrKind.OPERATION, lambda cpu, x=x, nn=nn: _execute_6XNN(cpu, x, nn))

        case 0x7000:
            return (InstrKind.OPERATION, lambda cpu, x=x, nn=nn: _execute_7XNN(cpu, x, nn))

        case 0x8000 if (opcode & 0x000F) == 0x0000:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY0(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x0001:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY1(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x0002:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY2(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x0003:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY3(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x0004:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY4(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x0005:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY5(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x0006:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY6(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x0007:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XY7(cpu, x, y))
        case 0x8000 if (opcode & 0x000F) == 0x000E:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y: _execute_8XYE(cpu, x, y))

        case 0x9000:
            return (InstrKind.COND_ADVANCE, lambda cpu, x=x, y=y: _execute_9XY0(cpu, x, y))

        case 0xA000:
            return (InstrKind.OPERATION, lambda cpu, nnn=nnn: _execute_ANNN(cpu, nnn))

        case 0xB000:
            return (InstrKind.JUMP, lambda cpu, x=x, nnn=nnn: _execute_BNNN(cpu, x, nnn))

        case 0xC000:
            return (InstrKind.OPERATION, lambda cpu, x=x, nn=nn: _execute_CXNN(cpu, x, nn))

        case 0xD000:
            return (InstrKind.OPERATION, lambda cpu, x=x, y=y, n=n: _execute_DXYN(cpu, x, y, n))

        case 0xE000 if (opcode & 0x00FF) == 0x009E:
            return (InstrKind.COND_ADVANCE, lambda cpu, x=x: _execute_EX9E(cpu, x))

        case 0xE000 if (opcode & 0x00FF) == 0x00A1:
            return (InstrKind.COND_ADVANCE, lambda cpu, x=x: _execute_EXA1(cpu, x))

        case 0xF000 if (opcode & 0x00FF) == 0x0000:
            return (InstrKind.DOUBLE_WIDE, lambda cpu: _execute_F000(cpu))
        case 0xF000 if (opcode & 0x00FF) == 0x0001:
            return (InstrKind.OPERATION, lambda cpu, n=x: _execute_FN01(cpu, n))
        case 0xF000 if (opcode & 0x00FF) == 0x0002:
            return (InstrKind.OPERATION, lambda cpu: _execute_F002(cpu))
        case 0xF000 if (opcode & 0x00FF) == 0x0007:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX07(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x000A:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX0A(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0015:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX15(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0018:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX18(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x001E:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX1E(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0029:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX29(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0030:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX30(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0033:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX33(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x003A:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX3A(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0055:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX55(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0065:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX65(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0075:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX75(cpu, x))
        case 0xF000 if (opcode & 0x00FF) == 0x0085:
            return (InstrKind.OPERATION, lambda cpu, x=x: _execute_FX85(cpu, x))

        case _:
            raise UnknownOpCodeException(f'Unknown opcode: {opcode:04X}')
