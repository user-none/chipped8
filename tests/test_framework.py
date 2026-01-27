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

    # Update ram_start to mark end of ROM region (for SMC detection in dynarec)
    program_end = pc_start + len(test.program) * 2
    cpu._memory._ram_start = program_end + 1

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

    if 'display' in test.initial_state:
        from chipped8.core.display import ResolutionMode, Plane
        display_state = test.initial_state['display']
        if 'resmode' in display_state:
            # Set resmode directly to avoid clearing screen
            cpu._display._res_mode = display_state['resmode']
        if 'plane' in display_state:
            cpu._display._target_plane = display_state['plane']
        if 'pixels' in display_state:
            for plane_idx, x, y, value in display_state['pixels']:
                idx = x + (y * 128)
                cpu._display._screen_planes[plane_idx][idx] = value

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

def validate_display_plane(cpu, expected):
    from chipped8.core.display import Plane
    assert cpu._display.plane == expected, f'Display plane expected {expected}, got {cpu._display.plane}'

def validate_display_pixel(cpu, plane_idx, x, y, expected):
    """Validate a pixel in the display buffer (internal 128x64 coords)."""
    idx = x + (y * 128)
    actual = cpu._display._screen_planes[plane_idx][idx]
    assert actual == expected, f'Pixel ({x},{y}) plane {plane_idx}: expected {expected}, got {actual}'

def validate_display_resmode(cpu, expected):
    """Validate display resolution mode."""
    from chipped8.core.display import ResolutionMode
    assert cpu._display._res_mode == expected, f'Resmode: expected {expected}, got {cpu._display._res_mode}'
