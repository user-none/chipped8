from dataclasses import dataclass, field
from typing import List, Callable

from chipped8.core.quirks import Quirks

# -----------------------------
# Test program data structure
# -----------------------------

@dataclass
class ProgramTest:
    name: str
    program: List[int] = field(default_factory=list)
    initial_state: dict = field(default_factory=dict)
    steps: int = 1
    validators: List[Callable] = field(default_factory=list)

    def __repr__(self):
        return f'{self.name}'

# -----------------------------
# Loader and executor
# -----------------------------

def load_test_program(cpu, test: ProgramTest):
    pc_start = test.initial_state.get('PC', 0x200)
    cpu._registers._PC = pc_start
    for i, opcode in enumerate(test.program):
        cpu._memory._memory[pc_start + i*2: pc_start + i*2 + 2] = opcode.to_bytes(2, 'big')

    if 'V' in test.initial_state:
        cpu._registers._V[:] = test.initial_state['V'][:]

    if 'I' in test.initial_state:
        cpu._registers._I = test.initial_state['I']

    if 'RPL' in test.initial_state:
        cpu._registers._RPL[:] = test.initial_state['RPL'][:]

    if 'stack' in test.initial_state:
        cpu._stack._stack[:] = test.initial_state['stack'][:]

    if 'mem' in test.initial_state:
        data = test.initial_state['mem']
        cpu._memory._memory[0x6000:0x6000 + len(data)] = data

    if 'delay' in test.initial_state:
        cpu._timers.delay = test.initial_state['delay']

    if 'key_state' in test.initial_state:
        states = test.initial_state['key_state']
        for k, s in states.items():
            cpu._keys.set_key_state(k, s)

    if 'quirks' in test.initial_state:
        quirk_list = test.initial_state['quirks']
        quirks = Quirks()
        if 'shift' in quirk_list:
            quirks.shift = True
        if 'memoryIncrementByX' in quirk_list:
            quirks.memoryIncrementByX = True
        if 'memoryLeaveIUnchanged' in quirk_list:
            quirks.memoryLeaveIUnchanged = True
        if 'wrap' in quirk_list:
            quirks.wrap = True
        if 'jump' in quirk_list:
            quirks.jump = True
        if 'vblank' in quirk_list:
            quirks.vblank = True
        if 'logic' in quirk_list:
            quirks.logic = True
        cpu._quirks = quirks

def run_test_program(cpu, test: ProgramTest):
    load_test_program(cpu, test)
    for _ in range(test.steps):
        cpu.execute_next_op()
    for validator in test.validators:
        validator(cpu)

# -----------------------------
# Common validators
# -----------------------------

def validate_v(cpu, reg, expected):
    assert cpu._registers._V[reg] == expected, f'V{reg} expected {expected}, got {cpu._registers._V[reg]}, {cpu._registers._V}'

def validate_pc(cpu, expected):
    assert cpu._registers._PC == expected, f'PC expected {expected:04X}, got {cpu._registers._PC:04X}'

def validate_memory(cpu, addr, expected_bytes):
    actual = cpu._memory._memory[addr:addr+len(expected_bytes)]
    assert actual == expected_bytes, f'Memory at {addr:04X} expected {expected_bytes}, got {actual}'

def validate_stack(cpu, idx, expected):
    assert cpu._stack._stack[idx] == expected, f'stack[{idx}] expected {expected}, got {cpu._stack._stack[idx]}, {cpu._stack._stack}'

def validate_stack_len(cpu, expected):
    assert len(cpu._stack._stack) == expected, f'Stack length expected {expected}, got {len(cpu._stack._stack)}: {cpu._stack._stack}'

def validate_i(cpu, expected):
    assert cpu._registers._I == expected, f'I expected {expected:04X}, got {cpu._registers._I:04X}'

def validate_audio_pattern(cpu, expected):
    assert cpu._audio.pattern == expected, f'Audio pattern expected {expected}, got {cpu._audio.pattern}'

def validate_audio_pitch(cpu, expected):
    assert cpu._audio.pitch == expected, f'Audio pitch expected {expected}, got {cpu._audio.pitch}'

def validate_delay_timer(cpu, expected):
    assert cpu._timers.delay == expected, f'Delay timer expected {expected}, got {cpu._timers.delay}'

def validate_sound_timer(cpu, expected):
    assert cpu._timers.sound == expected, f'Sound timer expected {expected}, got {cpu._timers.sound}'

def validate_rpl(cpu, idx, expected):
    assert cpu._registers._RPL[idx] == expected, f'RPL[{idx}] expected {expected}, got {cpu._registers._RPL[idx]}: {cpu._registers._RPL}'
