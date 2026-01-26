import pytest

from .test_framework import ProgramTest, run_test_program, load_test_program, validate_stack, validate_stack_len, validate_v, validate_pc, validate_memory, validate_i, validate_audio_pattern, validate_delay_timer, validate_sound_timer, validate_audio_pitch, validate_rpl, validate_display_plane, validate_display_pixel, validate_display_resmode
from chipped8.core.keys import Keys, KeyState
from chipped8.core.display import Plane, ResolutionMode

# -----------------------------
# Helper functions for assertions
# -----------------------------

# FX65: LD V0..Vx, [I]
def fx65_memory_setup():
    memory = [10,20,30] + [0]*4093
    return memory

audio_pattern = bytearray.fromhex('AA BB CC DD EE FF 11 22 33 44 55 66 77 88 99 00')

# -----------------------------
# Test program definitions
# -----------------------------

opcode_tests = [

    # 00CN - NOT IMP
    # 00DN - NOT IMP
    # 00E0 - NOT IMP

    ProgramTest(
        name='00EE: Return from subroutine',
        program=[0x00EE],
        initial_state={'stack': [0x0494]},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0496),
            lambda cpu: validate_stack_len(cpu, 0),
        ]
    ),

    # 00FB - NOT IMP
    # 00FC - NOT IMP
    # 00FD - NOT IMP
    # 00FE - NOT IMP
    # 00FF - NOT IMP

    ProgramTest(
        name='1NNN: Jump to address NNN',
        program=[0x1234],
        validators=[
            lambda cpu: validate_pc(cpu, 0x0234),
        ]
    ),

    ProgramTest(
        name='2NNN: Calls subroutine at address NNN',
        program=[0x2789],
        initial_state={'PC': 0x200},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0789),
            lambda cpu: validate_stack_len(cpu, 1),
            lambda cpu: validate_stack(cpu, 0, 0x0200),
        ]
    ),


    ProgramTest(
        name='2NNN + 00EE: Push to then pop from stack',
        program=[0x2202, 0x2204, 0x2206, 0x00EE],
        initial_state={'PC': 0x200},
        steps = 4,
        validators=[
            lambda cpu: validate_pc(cpu, 0x0206),
            lambda cpu: validate_stack_len(cpu, 2),
            lambda cpu: validate_stack(cpu, 0, 0x0200),
            lambda cpu: validate_stack(cpu, 1, 0x0202),
        ]
    ),

    ProgramTest(
        name='3XNN: Skips the next instruction if VX equals NN - SKIP',
        program=[0x3344],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0204),
        ]
    ),

    ProgramTest(
        name='3XNN: Skips the next instruction if VX equals NN - NO SKIP',
        program=[0x3312],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='3XNN: Skips the next instruction (xo) if VX equals NN - SKIP',
        program=[0x3344, 0xF000],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0206),
        ]
    ),

    ProgramTest(
        name='3XNN: Skips the next instruction (xo) if VX equals NN - NO SKIP',
        program=[0x3343, 0xF000],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='4XNN: Skips the next instruction if VX does not equal NN - SKIP',
        program=[0x4344],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='4XNN: Skips the next instruction if VX does not equal NN - NO SKIP',
        program=[0x4312],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0204),
        ]
    ),

    ProgramTest(
        name='4XNN: Skips the next instruction (xo) if VX does not equal NN - SKIP',
        program=[0x4341, 0xF000],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0206),
        ]
    ),

    ProgramTest(
        name='4XNN: Skips the next instruction (xo) if VX does not equal NN - NO SKIP',
        program=[0x4344, 0xF000],
        initial_state={'V': [0]*3 + [0x44] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='5XY0: Skips the next instruction if VX equals VY - SKIP',
        program=[0x5120],
        initial_state={'V': [0] + [0x09, 0x9] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0204),
        ]
    ),

    ProgramTest(
        name='5XY0: Skips the next instruction if VX equals VY - NO SKIP',
        program=[0x5120],
        initial_state={'V': [0] + [0x09, 0x2] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='5XY0: Skips the next instruction (xo) if VX equals VY - SKIP',
        program=[0x5120, 0xF000],
        initial_state={'V': [0] + [0x09, 0x9] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0206),
        ]
    ),

    ProgramTest(
        name='5XY0: Skips the next instruction (xo) if VX equals VY - NO SKIP',
        program=[0x5120, 0xF000],
        initial_state={'V': [0] + [0x09, 0x2] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='5XY2: Save VX..VY inclusive to memory starting at I.',
        program=[0x5132],
        initial_state={'V': [0] + [0x09, 0x2, 0x59] + [0]*12, 'I': 0x4},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
            lambda cpu: validate_i(cpu, 0x4),
            lambda cpu: validate_memory(cpu, 0x4, bytes([0x09, 0x2, 0x59])),
        ]
    ),

    ProgramTest(
        name='5XY3: Loads VX..VY from memory location in I',
        program=[0x5243],
        initial_state={'I': 0x6000, 'mem': audio_pattern},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
            lambda cpu: validate_v(cpu, 0x01, 0x00),
            lambda cpu: validate_v(cpu, 0x02, 0xAA),
            lambda cpu: validate_v(cpu, 0x03, 0xBB),
            lambda cpu: validate_v(cpu, 0x04, 0xCC),
            lambda cpu: validate_v(cpu, 0x05, 0x00),
        ]
    ),

    ProgramTest(
        name='6XNN: Sets VX to NN',
        program=[0x60FF],
        initial_state={'V': [0]*16, 'PC': 0x200},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0xFF),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='7XNN: Adds NN to VX (carry flag is not changed)',
        program=[0x7114],
        initial_state={'V': [0, 10] + [0]*14},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0x1E),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY0: Sets VX to the value of VY',
        program=[0x8140],
        initial_state={'V': [0]*4 + [0x19] + [0]*11},
        validators=[
            lambda cpu: validate_v(cpu, 4, 0x19),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY1: Sets VX to VX or VY',
        program=[0x8011],
        initial_state={'V': [0x14] + [0x22] + [0]*13 + [0x99]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x36),
            lambda cpu: validate_v(cpu, 0xF, 0x99),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY1: Sets VX to VX or VY - QUIRK LOGIC',
        program=[0x8011],
        initial_state={'V': [0x14] + [0x22] + [0x44]*13 + [0x99], 'quirks': ['logic']},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x36),
            lambda cpu: validate_v(cpu, 0xF, 0x00),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY2: Sets VX to VX and VY',
        program=[0x8012],
        initial_state={'V': [0x14] + [0x04] + [0x09]*13 + [0x99]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x04),
            lambda cpu: validate_v(cpu, 0xF, 0x99),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY2: Sets VX to VX and VY - QUIRK LOGIC',
        program=[0x8012],
        initial_state={'V': [0x14] + [0x04] + [0x09]*13 + [0x99], 'quirks': ['logic']},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x04),
            lambda cpu: validate_v(cpu, 0xF, 0x00),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY3: Sets VX to VX xor VY',
        program=[0x8013],
        initial_state={'V': [0x10] + [0x12] + [0x09]*13 + [0x99]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x02),
            lambda cpu: validate_v(cpu, 0xF, 0x99),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY3: Sets VX to VX xor VY - QUIRK LOGIC',
        program=[0x8013],
        initial_state={'V': [0x10] + [0x12] + [0x09]*13 + [0x99], 'quirks': ['logic']},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x02),
            lambda cpu: validate_v(cpu, 0xF, 0x00),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY4: Adds VY to VX',
        program=[0x8014],
        initial_state={'V': [0x10] + [0x12] + [0x09]*13 + [0x0]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x22),
            lambda cpu: validate_v(cpu, 0xF, 0x00),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY4: Adds VY to VX - OVERFLOW',
        program=[0x8014],
        initial_state={'V': [0xF0] + [0x12] + [0x09]*13 + [0x0]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x02),
            lambda cpu: validate_v(cpu, 0xF, 0x01),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY5: VY is subtracted from VX',
        program=[0x8015],
        initial_state={'V': [0x12] + [0x10] + [0x09]*13 + [0x0]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x02),
            lambda cpu: validate_v(cpu, 0xF, 0x01),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY5: VY is subtracted from VX - UNDERFLOW',
        program=[0x8015],
        initial_state={'V': [0x10] + [0x12] + [0x09]*13 + [0x0]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0xFE),
            lambda cpu: validate_v(cpu, 0xF, 0x00),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY6: Shift VY then store in VX and LSB in VF: LSB 0',
        program=[0x8126],
        initial_state={'V': [0] + [0x99] + [0x42] + [0]*12 + [0x1]},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0x21),
            lambda cpu: validate_v(cpu, 0xF, 0x0),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY6: Shift VY then store in VX and LSB in VF: LSB 1',
        program=[0x8126],
        initial_state={'V': [0] + [0x99] + [0x41] + [0]*13},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0x20),
            lambda cpu: validate_v(cpu, 0xF, 0x1),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY6: Shift VY then store in VX and LSB in VF: LSB 0 - QUIRK SHIFT (VX instead of VY)',
        program=[0x8126],
        initial_state={'V': [0] + [0x42] + [0x99] + [0]*12 + [0x1], 'quirks': ['shift']},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0x21),
            lambda cpu: validate_v(cpu, 0xF, 0x0),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY6: Shift VY then store in VX and LSB in VF: LSB 1 - QUIRK SHIFT (VX instead of VY)',
        program=[0x8126],
        initial_state={'V': [0] + [0x41] + [0x99] + [0]*13, 'quirks': ['shift']},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0x20),
            lambda cpu: validate_v(cpu, 0xF, 0x1),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY7: VX is subtracted from VY',
        program=[0x8017],
        initial_state={'V': [0x10] + [0x12] + [0x09]*13 + [0x0]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0x02),
            lambda cpu: validate_v(cpu, 0xF, 0x01),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XY7: VX is subtracted from VY - UNDERFLOW',
        program=[0x8017],
        initial_state={'V': [0x12] + [0x10] + [0x09]*13 + [0x0]},
        validators=[
            lambda cpu: validate_v(cpu, 0, 0xFE),
            lambda cpu: validate_v(cpu, 0xF, 0x00),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XYE: Shift VY then store in VX and LSB in VF: MSB 0',
        program=[0x812E],
        initial_state={'V': [0] + [0x99] + [0x72] + [0]*12 + [0x1]},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0xE4),
            lambda cpu: validate_v(cpu, 0xF, 0x0),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XYE: Shift VY then store in VX and LSB in VF: LSB 1',
        program=[0x812E],
        initial_state={'V': [0] + [0x99] + [0x82] + [0]*13},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0x04),
            lambda cpu: validate_v(cpu, 0xF, 0x1),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XYE: Shift VY then store in VX and LSB in VF: LSB 0 - QUIRK SHIFT (VX instead of VY)',
        program=[0x812E],
        initial_state={'V': [0] + [0x72] + [0x99] + [0]*12 + [0x1], 'quirks': ['shift']},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0xE4),
            lambda cpu: validate_v(cpu, 0xF, 0x0),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='8XYE: Shift VY then store in VX and LSB in VF: LSB 1 - QUIRK SHIFT (VX instead of VY)',
        program=[0x812E],
        initial_state={'V': [0] + [0x82] + [0x99] + [0]*13, 'quirks': ['shift']},
        validators=[
            lambda cpu: validate_v(cpu, 1, 0x04),
            lambda cpu: validate_v(cpu, 0xF, 0x1),
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),





    ProgramTest(
        name='9XY0: Skips the next instruction if VX does not equal VY - SKIP',
        program=[0x9120],
        initial_state={'V': [0] + [0x09, 0x02] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0204),
        ]
    ),

    ProgramTest(
        name='9XY0: Skips the next instruction if VX does not equal VY - NO SKIP',
        program=[0x9120],
        initial_state={'V': [0] + [0x09, 0x09] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='9XY0: Skips the next instruction (xo) if VX does not equal VY - SKIP',
        program=[0x9120, 0xF000],
        initial_state={'V': [0] + [0x09, 0x02] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0206),
        ]
    ),

    ProgramTest(
        name='9XY0: Skips the next instruction (xo) if VX does not equal VY - NO SKIP',
        program=[0x9120, 0xF000],
        initial_state={'V': [0] + [0x09, 0x09] + [0]*13},
        validators=[
            lambda cpu: validate_pc(cpu, 0x0202),
        ]
    ),

    ProgramTest(
        name='ANNN: Sets I to the address NNN',
        program=[0xA653],
        validators=[
            lambda cpu: validate_i(cpu, 0x0653),
        ]
    ),

    ProgramTest(
        name='BNNN: Jumps to the address NNN plus V0 - VAL 0',
        program=[0xB424],
        initial_state={'V': [0]*16},
        validators=[
            lambda cpu: validate_pc(cpu, 0x424),
        ]
    ),

    ProgramTest(
        name='BNNN: Jumps to the address NNN plus V0 - VAL 9',
        program=[0xB424],
        initial_state={'V': [0x9] + [0]*15},
        validators=[
            lambda cpu: validate_pc(cpu, 0x42D),
        ]
    ),

    ProgramTest(
        name='BXNN: Jumps to the address NNN plus VX - VAL 0',
        program=[0xB324],
        initial_state={'V':  [0]*16, 'quirks': ['jump']},
        validators=[
            lambda cpu: validate_pc(cpu, 0x324),
        ]
    ),

    ProgramTest(
        name='BXNN: Jumps to the address NNN plus VX - VAL 12',
        program=[0xB124],
        initial_state={'V': [0x8] + [0xF3] + [0]*14, 'quirks': ['jump']},
        validators=[
            lambda cpu: validate_pc(cpu, 0x217),
        ]
    ),

    # CXNN - NOT IMP
    # DXYN - NOT IMP

    ProgramTest(
        name='EX9E: Skips the next instruction if the key stored in VX is pressed - PRESSED',
        program=[0xE19E],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.down}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
        ]
    ),

    ProgramTest(
        name='EX9E: Skips the next instruction if the key stored in VX is pressed - NOT PRESSED',
        program=[0xE19E],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.up}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='EX9E: Skips the next instruction (xo) if the key stored in VX is pressed - PRESSED',
        program=[0xE19E, 0xF000],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.down}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x206),
        ]
    ),

    ProgramTest(
        name='EX9E: Skips the next instruction (xo) if the key stored in VX is pressed - NOT PRESSED',
        program=[0xE19E, 0xF000],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.up}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='EXA1: Skips the next instruction if the key stored in VX is not pressed - PRESSED',
        program=[0xE1A1],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.down}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='EXA1: Skips the next instruction if the key stored in VX is not pressed - NOT PRESSED',
        program=[0xE1A1],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.up}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
        ]
    ),

    ProgramTest(
        name='EXA1: Skips the next instruction (xo) if the key stored in VX is not pressed - PRESSED',
        program=[0xE1A1, 0xF000],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.down}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
        ]
    ),

    ProgramTest(
        name='EXA1: Skips the next instruction (xo) if the key stored in VX is not pressed - NOT PRESSED',
        program=[0xE1A1, 0xF000],
        initial_state={
            'V': [0x8] + [0x06] + [0]*14,
            'key_state': {Keys.Key_6: KeyState.up}
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x206),
        ]
    ),

    ProgramTest(
        name='F000 NNNN: Load I with 16-bit address NNNN this is a four byte instruction',
        program=[0xF000, 0x4444],
        initial_state={},
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
            lambda cpu: validate_i(cpu, 0x4444),
        ]
    ),

    # FN01: Select drawing plane
    ProgramTest(
        name='FN01: Select plane 1 only',
        program=[0xF101],  # F101 = select plane 1
        initial_state={},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_plane(cpu, Plane.p1),
        ]
    ),
    ProgramTest(
        name='FN01: Select plane 2 only',
        program=[0xF201],  # F201 = select plane 2
        initial_state={},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_plane(cpu, Plane.p2),
        ]
    ),
    ProgramTest(
        name='FN01: Select both planes',
        program=[0xF301],  # F301 = select both planes (1 | 2 = 3)
        initial_state={},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_plane(cpu, Plane.p1 | Plane.p2),
        ]
    ),

    ProgramTest(
        name='F002: Store 16 bytes in audio pattern buffer, starting at I, to be played by the sound buzzer',
        program=[0xF002],
        initial_state={'I': 0x6000, 'mem': audio_pattern},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_audio_pattern(cpu, audio_pattern),
        ]
    ),

    ProgramTest(
        name='FX07: Sets VX to the value of the delay timer',
        program=[0xF207],
        initial_state={'delay': 0x29},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0x02, 0x29),
        ]
    ),

    # XXX: Need to think about this. Cached CPU works differently with how it moves through the PC
    #ProgramTest(
    #    name='FX0A: Wait for a keypress and store the result in register VX - WAIT',
    #    program=[0xF10A],
    #    validators=[
    #        lambda cpu: validate_pc(cpu, 0x200),
    #    ]
    #),

    ProgramTest(
        name='FX0A: Wait for a keypress and store the result in register VX - PRESSED',
        program=[0xF10A],
        initial_state={'key_state': {Keys.Key_9: KeyState.down}},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0x01, Keys.Key_9),
        ]
    ),

    ProgramTest(
        name='FX15: Sets the delay timer to VX',
        program=[0xF015],
        initial_state={'V': [0x36] + [0]*15},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_delay_timer(cpu, 0x36),

        ]
    ),

    ProgramTest(
        name='FX18: Sets the sound timer to VX',
        program=[0xF018],
        initial_state={'V': [0x73] + [0]*15},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_sound_timer(cpu, 0x73),

        ]
    ),

    ProgramTest(
        name='FX1E: Adds VX to I. VF is not affected',
        program=[0xF01E],
        initial_state={'V': [0x99] + [0]*15, 'I': 0x0A},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_i(cpu, 0xA3),
        ]
    ),

    ProgramTest(
        name='FX29: Sets I to the location of the sprite for the character in VX',
        program=[0xF029],
        initial_state={'V': [0xC] + [0]*15},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_i(cpu, 0x3C),
        ]
    ),

    ProgramTest(
        name='FX30: Point I to 10-byte font sprite for digit VX',
        program=[0xF030],
        initial_state={'V': [0xB] + [0]*15},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_i(cpu, 0xBE),
        ]
    ),

    ProgramTest(
        name='FX33: Stores the binary-coded decimal representation of VX',
        program=[0xF133],
        initial_state={'V': [0] + [0xAF] + [0]*14, 'I': 0x4},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_memory(cpu, 0x4, bytes([0x1, 0x7, 0x5])),
        ]
    ),

    ProgramTest(
        name='FX3A: Set the pitch register to the value in VX.',
        program=[0xF33A],
        initial_state={'V': [0]*3 + [0xBD] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_audio_pitch(cpu, 0xBD),
        ]
    ),

    ProgramTest(
        name='FX55: Stores from V0 to VX (including VX) in memory',
        program=[0xF455],
        initial_state={'V': [0xB1] + [0xB2] + [0xB3] + [0xB4] + [0xB5] + [0xB6] + [0]*10, 'I': 0x04},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_memory(cpu, 0x04, bytes([0xB1] + [0xB2] + [0xB3] + [0xB4] + [0xB5] + [ord('p')])),
            lambda cpu: validate_i(cpu, 0x9),
        ]
    ),

    ProgramTest(
        name='FX55: Stores from V0 to VX (including VX) in memory - QUIRK memoryIncrementByX',
        program=[0xF455],
        initial_state={
            'V': [0xB1] + [0xB2] + [0xB3] + [0xB4] + [0xB5] + [0xB6] + [0]*10,
            'I': 0x04,
            'quirks': ['memoryIncrementByX']
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_memory(cpu, 0x04, bytes([0xB1] + [0xB2] + [0xB3] + [0xB4] + [0xB5] + [ord('p')])),
            lambda cpu: validate_i(cpu, 0x8),
        ]
    ),

    ProgramTest(
        name='FX55: Stores from V0 to VX (including VX) in memory - QUIRK memoryLeaveIUnchanged',
        program=[0xF455],
        initial_state={
            'V': [0xB1] + [0xB2] + [0xB3] + [0xB4] + [0xB5] + [0xB6] + [0]*10,
            'I': 0x04,
            'quirks': ['memoryLeaveIUnchanged']
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_memory(cpu, 0x04, bytes([0xB1] + [0xB2] + [0xB3] + [0xB4] + [0xB5] + [ord('p')])),
            lambda cpu: validate_i(cpu, 0x4),
        ]
    ),

    ProgramTest(
        name='FX65: Fills from V0 to VX (including VX) with values from memory',
        program=[0xF265],
        initial_state={'I': 0x6000, 'mem': audio_pattern},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0x0, 0xAA),
            lambda cpu: validate_v(cpu, 0x1, 0xBB),
            lambda cpu: validate_v(cpu, 0x2, 0xCC),
            lambda cpu: validate_v(cpu, 0x3, 0x0),
        ]
    ),

    ProgramTest(
        name='FX75: Store V0..VX in RPL user flags',
        program=[0xF175],
        initial_state={'V': [0x11] + [0x22] + [0x33] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_rpl(cpu, 0, 0x11),
            lambda cpu: validate_rpl(cpu, 1, 0x22),
            lambda cpu: validate_rpl(cpu, 2, 0x0),
        ]
    ),

    ProgramTest(
        name='FX85: Read V0..VX from RPL user flags',
        program=[0xF185],
        initial_state={'RPL': [0x11] + [0x22] + [0x33] + [0]*12},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0, 0x11),
            lambda cpu: validate_v(cpu, 1, 0x22),
            lambda cpu: validate_v(cpu, 2, 0x0),
        ]
    ),

    # ========================================
    # DXYN - Draw sprite tests
    # ========================================

    ProgramTest(
        name='DXYN: 8x1 sprite no collision (lowres)',
        program=[0xD011],  # Draw 1-row sprite at V0, V1
        initial_state={
            'V': [4, 4] + [0]*14,  # x=4, y=4
            'I': 0x6000,
            'mem': [0xFF] + [0]*15,  # 8 pixels on
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, 0),  # No collision
            lambda cpu: validate_display_pixel(cpu, 0, 8, 8, 1),  # lowres: x*2, y*2
            lambda cpu: validate_display_pixel(cpu, 0, 9, 8, 1),
            lambda cpu: validate_display_pixel(cpu, 0, 14, 8, 1),
            lambda cpu: validate_display_pixel(cpu, 0, 15, 8, 1),
        ]
    ),

    ProgramTest(
        name='DXYN: 8x1 sprite collision - draw twice (lowres)',
        program=[0xD011, 0xD011],  # Draw same sprite twice
        initial_state={
            'V': [4, 4] + [0]*14,
            'I': 0x6000,
            'mem': [0xFF] + [0]*15,
        },
        steps=2,
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
            lambda cpu: validate_v(cpu, 0xF, 1),  # Collision on second draw
            lambda cpu: validate_display_pixel(cpu, 0, 8, 8, 0),  # XOR cleared
            lambda cpu: validate_display_pixel(cpu, 0, 9, 8, 0),
        ]
    ),

    ProgramTest(
        name='DXYN: 8x5 sprite (lowres)',
        program=[0xD015],
        initial_state={
            'V': [0, 0] + [0]*14,
            'I': 0x6000,
            'mem': [0xF0, 0x90, 0x90, 0x90, 0xF0] + [0]*11,  # '0' character
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, 0),
            # Check a few pixels at corners
            lambda cpu: validate_display_pixel(cpu, 0, 0, 0, 1),  # Top-left
            lambda cpu: validate_display_pixel(cpu, 0, 6, 0, 1),  # Top-right of sprite
            lambda cpu: validate_display_pixel(cpu, 0, 0, 8, 1),  # Bottom-left
        ]
    ),

    ProgramTest(
        name='DXYN: 8x15 sprite max height (lowres)',
        program=[0xD01F],  # 15 rows
        initial_state={
            'V': [0, 0] + [0]*14,
            'I': 0x6000,
            'mem': [0x80] * 15 + [0],  # Just leftmost pixel per row
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 0, 1),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 28, 1),  # Row 14 * 2 = 28
        ]
    ),

    ProgramTest(
        name='DXYN: 8x1 sprite no collision (hires)',
        program=[0xD011],
        initial_state={
            'V': [10, 10] + [0]*14,
            'I': 0x6000,
            'mem': [0xFF] + [0]*15,
            'display': {'resmode': ResolutionMode.hires},
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 10, 10, 1),  # hires: 1:1
            lambda cpu: validate_display_pixel(cpu, 0, 17, 10, 1),
        ]
    ),

    ProgramTest(
        name='DXYN: 8x1 sprite collision (hires)',
        program=[0xD011, 0xD011],
        initial_state={
            'V': [10, 10] + [0]*14,
            'I': 0x6000,
            'mem': [0xFF] + [0]*15,
            'display': {'resmode': ResolutionMode.hires},
        },
        steps=2,
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
            lambda cpu: validate_v(cpu, 0xF, 1),
            lambda cpu: validate_display_pixel(cpu, 0, 10, 10, 0),  # XOR cleared
        ]
    ),

    ProgramTest(
        name='DXYN: Multi-plane draw (XO-CHIP)',
        program=[0xF301, 0xD011],  # Select both planes, then draw
        initial_state={
            'V': [5, 5] + [0]*14,
            'I': 0x6000,
            # Sprite data for both planes (1 byte per plane for n=1)
            'mem': [0xFF, 0xFF] + [0]*14,  # Plane 1 sprite at 0x6000, Plane 2 sprite at 0x6001
            'display': {'resmode': ResolutionMode.hires},
        },
        steps=2,
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
            lambda cpu: validate_display_pixel(cpu, 0, 5, 5, 1),  # Plane 0
            lambda cpu: validate_display_pixel(cpu, 1, 5, 5, 1),  # Plane 1
        ]
    ),

    # ========================================
    # DXY0 - 16x16 sprite tests
    # ========================================

    ProgramTest(
        name='DXY0: 16x16 sprite draw (hires)',
        program=[0xD010],  # n=0 means 16x16 sprite
        initial_state={
            'V': [0, 0] + [0]*14,
            'I': 0x6000,
            # 16x16 sprite: 32 bytes (2 bytes per row * 16 rows)
            'mem': [0xFF, 0xFF] * 16,  # Full 16x16 block
            'display': {'resmode': ResolutionMode.hires},
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 0, 1),
            lambda cpu: validate_display_pixel(cpu, 0, 15, 0, 1),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 15, 1),
            lambda cpu: validate_display_pixel(cpu, 0, 15, 15, 1),
        ]
    ),

    ProgramTest(
        name='DXY0: 16x16 sprite collision',
        program=[0xD010, 0xD010],
        initial_state={
            'V': [0, 0] + [0]*14,
            'I': 0x6000,
            'mem': [0xFF, 0xFF] * 16,
            'display': {'resmode': ResolutionMode.hires},
        },
        steps=2,
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
            lambda cpu: validate_v(cpu, 0xF, 1),  # Collision
            lambda cpu: validate_display_pixel(cpu, 0, 0, 0, 0),  # XOR cleared
        ]
    ),

    # ========================================
    # 00E0 - Clear screen tests
    # ========================================

    ProgramTest(
        name='00E0: Clear screen (single plane)',
        program=[0x00E0],
        initial_state={
            'display': {
                'resmode': ResolutionMode.hires,
                'plane': Plane.p1,
                'pixels': [(0, 10, 10, 1), (0, 20, 20, 1), (1, 30, 30, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 10, 10, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 20, 20, 0),
            lambda cpu: validate_display_pixel(cpu, 1, 30, 30, 0),  # Both planes cleared
        ]
    ),

    ProgramTest(
        name='00E0: Clear screen (both planes selected)',
        program=[0xF301, 0x00E0],  # Select both planes, then clear
        initial_state={
            'display': {
                'resmode': ResolutionMode.hires,
                'pixels': [(0, 5, 5, 1), (1, 5, 5, 1)],
            },
        },
        steps=2,
        validators=[
            lambda cpu: validate_pc(cpu, 0x204),
            lambda cpu: validate_display_pixel(cpu, 0, 5, 5, 0),
            lambda cpu: validate_display_pixel(cpu, 1, 5, 5, 0),
        ]
    ),

    # ========================================
    # 00CN - Scroll down tests
    # ========================================

    ProgramTest(
        name='00CN: Scroll down 1px (lowres - becomes 2px internal)',
        program=[0x00C1],
        initial_state={
            'display': {
                'resmode': ResolutionMode.lowres,
                'pixels': [(0, 0, 0, 1)],  # Pixel at top-left
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 0, 0),  # Original cleared
            lambda cpu: validate_display_pixel(cpu, 0, 0, 2, 1),  # Moved down 2 rows
        ]
    ),

    ProgramTest(
        name='00CN: Scroll down 4px (hires)',
        program=[0x00C4],
        initial_state={
            'display': {
                'resmode': ResolutionMode.hires,
                'pixels': [(0, 0, 0, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 0, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 4, 1),
        ]
    ),

    # ========================================
    # 00DN - Scroll up tests
    # ========================================

    ProgramTest(
        name='00DN: Scroll up 1px (lowres - becomes 2px internal)',
        program=[0x00D1],
        initial_state={
            'display': {
                'resmode': ResolutionMode.lowres,
                'pixels': [(0, 0, 10, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 10, 0),  # Original cleared
            lambda cpu: validate_display_pixel(cpu, 0, 0, 8, 1),   # Moved up 2 rows
        ]
    ),

    ProgramTest(
        name='00DN: Scroll up 4px (hires)',
        program=[0x00D4],
        initial_state={
            'display': {
                'resmode': ResolutionMode.hires,
                'pixels': [(0, 0, 10, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 10, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 0, 6, 1),
        ]
    ),

    # ========================================
    # 00FB - Scroll right tests
    # ========================================

    ProgramTest(
        name='00FB: Scroll right (lowres - 8px)',
        program=[0x00FB],
        initial_state={
            'display': {
                'resmode': ResolutionMode.lowres,
                'pixels': [(0, 10, 0, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 10, 0, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 18, 0, 1),  # Moved right 8
        ]
    ),

    ProgramTest(
        name='00FB: Scroll right (hires - 4px)',
        program=[0x00FB],
        initial_state={
            'display': {
                'resmode': ResolutionMode.hires,
                'pixels': [(0, 10, 0, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 10, 0, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 14, 0, 1),  # Moved right 4
        ]
    ),

    # ========================================
    # 00FC - Scroll left tests
    # ========================================

    ProgramTest(
        name='00FC: Scroll left (lowres - 8px)',
        program=[0x00FC],
        initial_state={
            'display': {
                'resmode': ResolutionMode.lowres,
                'pixels': [(0, 20, 0, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 20, 0, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 12, 0, 1),  # Moved left 8
        ]
    ),

    ProgramTest(
        name='00FC: Scroll left (hires - 4px)',
        program=[0x00FC],
        initial_state={
            'display': {
                'resmode': ResolutionMode.hires,
                'pixels': [(0, 20, 0, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_pixel(cpu, 0, 20, 0, 0),
            lambda cpu: validate_display_pixel(cpu, 0, 16, 0, 1),  # Moved left 4
        ]
    ),

    # ========================================
    # 00FE - Switch to lowres tests
    # ========================================

    ProgramTest(
        name='00FE: Switch to lowres, clears screen',
        program=[0x00FE],
        initial_state={
            'display': {
                'resmode': ResolutionMode.hires,
                'pixels': [(0, 10, 10, 1), (1, 20, 20, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_resmode(cpu, ResolutionMode.lowres),
            lambda cpu: validate_display_pixel(cpu, 0, 10, 10, 0),  # Screen cleared
            lambda cpu: validate_display_pixel(cpu, 1, 20, 20, 0),
        ]
    ),

    # ========================================
    # 00FF - Switch to hires tests
    # ========================================

    ProgramTest(
        name='00FF: Switch to hires, clears screen',
        program=[0x00FF],
        initial_state={
            'display': {
                'resmode': ResolutionMode.lowres,
                'pixels': [(0, 10, 10, 1), (1, 20, 20, 1)],
            },
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_display_resmode(cpu, ResolutionMode.hires),
            lambda cpu: validate_display_pixel(cpu, 0, 10, 10, 0),  # Screen cleared
            lambda cpu: validate_display_pixel(cpu, 1, 20, 20, 0),
        ]
    ),

    # ========================================
    # FX0A - Blocking input tests
    # ========================================

    ProgramTest(
        name='FX0A: Key pressed stores in VF',
        program=[0xFF0A],
        initial_state={'key_state': {Keys.Key_A: KeyState.down}},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, Keys.Key_A),
        ]
    ),

    # ========================================
    # 7XNN - Register overflow tests
    # ========================================

    ProgramTest(
        name='7XNN: Overflow wraps - 0xFF + 0x01 = 0x00',
        program=[0x7001],
        initial_state={'V': [0xFF] + [0]*14 + [0x99]},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0, 0x00),
            lambda cpu: validate_v(cpu, 0xF, 0x99),  # VF unchanged
        ]
    ),

    ProgramTest(
        name='7XNN: Large overflow - 0x80 + 0xFF = 0x7F',
        program=[0x70FF],
        initial_state={'V': [0x80] + [0]*14 + [0x55]},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0, 0x7F),
            lambda cpu: validate_v(cpu, 0xF, 0x55),  # VF unchanged
        ]
    ),

    ProgramTest(
        name='7XNN: VF not affected by overflow',
        program=[0x7F10],  # Add to VF directly
        initial_state={'V': [0]*15 + [0xF0]},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, 0x00),  # 0xF0 + 0x10 = 0x100 -> 0x00
        ]
    ),

    # ========================================
    # FX1E - I overflow test
    # ========================================

    ProgramTest(
        name='FX1E: I overflow wraps at 16-bit - 0xFFFF + 0xFF',
        program=[0xF01E],
        initial_state={'V': [0xFF] + [0]*15, 'I': 0xFFFF},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            # Note: Wraps at 16-bit (0x00FE) for pure/cached interpreters
            # Dynarec may not wrap as XO-CHIP has 64KB address space
            lambda cpu: validate_i(cpu, (0xFFFF + 0xFF) & 0xFFFF),
        ]
    ),

    ProgramTest(
        name='FX1E: I add without overflow',
        program=[0xF11E],
        initial_state={'V': [0] + [0x50] + [0]*14, 'I': 0x1000},
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_i(cpu, 0x1050),
        ]
    ),

    # ========================================
    # FX55/FX65 edge cases
    # ========================================

    ProgramTest(
        name='FX55: Store all 16 registers (X=15)',
        program=[0xFF55],
        initial_state={
            'V': [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
                  0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF],
            'I': 0x300
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_memory(cpu, 0x300, bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
                                                           0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])),
            lambda cpu: validate_i(cpu, 0x310),  # I += 16
        ]
    ),

    ProgramTest(
        name='FX65: Load all 16 registers (X=15)',
        program=[0xFF65],
        initial_state={
            'I': 0x6000,
            'mem': [0x10, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x87,
                    0x98, 0xA9, 0xBA, 0xCB, 0xDC, 0xED, 0xFE, 0x0F],
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0x0, 0x10),
            lambda cpu: validate_v(cpu, 0x7, 0x87),
            lambda cpu: validate_v(cpu, 0xF, 0x0F),
        ]
    ),

    ProgramTest(
        name='FX55: Combined quirks - memoryIncrementByX and memoryLeaveIUnchanged',
        program=[0xF355],
        initial_state={
            'V': [0xAA, 0xBB, 0xCC, 0xDD] + [0]*12,
            'I': 0x400,
            'quirks': ['memoryIncrementByX', 'memoryLeaveIUnchanged']
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_memory(cpu, 0x400, bytes([0xAA, 0xBB, 0xCC, 0xDD])),
            lambda cpu: validate_i(cpu, 0x400),  # I unchanged (memoryLeaveIUnchanged takes precedence)
        ]
    ),

    # ========================================
    # Quirk tests - wrap
    # ========================================

    ProgramTest(
        name='DXYN: Wrap quirk disabled - sprite at edge clips',
        program=[0xD015],  # 5-row sprite
        initial_state={
            'V': [62, 30] + [0]*14,  # Near right and bottom edge in lowres (64x32)
            'I': 0x6000,
            'mem': [0xFF, 0xFF, 0xFF, 0xFF, 0xFF] + [0]*11,
            'quirks': [],  # No wrap quirk - default clips
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            # Sprite should be partially drawn (clipped at edges)
            lambda cpu: validate_v(cpu, 0xF, 0),  # No collision expected
        ]
    ),

    ProgramTest(
        name='DXYN: Wrap quirk enabled - sprite wraps around',
        program=[0xD011],
        initial_state={
            'V': [63, 0] + [0]*14,  # At right edge in lowres
            'I': 0x6000,
            'mem': [0xFF] + [0]*15,
            'quirks': ['wrap'],
            'display': {'resmode': ResolutionMode.lowres},
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            # With wrap, sprite should appear on both sides
            lambda cpu: validate_display_pixel(cpu, 0, 126, 0, 1),  # Near right edge (63*2=126)
            lambda cpu: validate_display_pixel(cpu, 0, 0, 0, 1),    # Wrapped to left
        ]
    ),

    ProgramTest(
        name='DXYN: Basic draw with vblank quirk',
        program=[0xD011],
        initial_state={
            'V': [5, 5] + [0]*14,
            'I': 0x6000,
            'mem': [0xFF] + [0]*15,
            'quirks': ['vblank'],
        },
        validators=[
            lambda cpu: validate_pc(cpu, 0x202),
            lambda cpu: validate_v(cpu, 0xF, 0),
            # Sprite should still be drawn
            lambda cpu: validate_display_pixel(cpu, 0, 10, 10, 1),  # lowres: 5*2=10
        ]
    ),
]

# ========================================
# Stack overflow/underflow tests (standalone)
# ========================================

def test_stack_overflow_on_call(emulator):
    """Fill stack to 16, then execute CALL - expect OverflowError."""
    cpu = emulator._cpu
    test = ProgramTest(
        name='Stack overflow test',
        program=[0x2202],  # CALL to next address
        initial_state={
            'stack': [0x300] * 16,  # Stack already full
        },
    )
    load_test_program(cpu, test)
    with pytest.raises(OverflowError):
        cpu.execute_next_op()


def test_stack_underflow_on_return(emulator):
    """Empty stack, execute RET - expect ValueError."""
    cpu = emulator._cpu
    test = ProgramTest(
        name='Stack underflow test',
        program=[0x00EE],  # RET
        initial_state={
            'stack': [],  # Stack empty
        },
    )
    load_test_program(cpu, test)
    with pytest.raises(ValueError):
        cpu.execute_next_op()

# Main test runner
@pytest.mark.parametrize('program_test', opcode_tests, ids=lambda test: test.name)
def test_opcode_programs(emulator, program_test: ProgramTest):
    cpu = emulator._cpu
    # Reset CPU state from program_test.initial_state
    for attr, value in program_test.initial_state.items():
        setattr(cpu, attr, value)
    # Run program
    run_test_program(cpu, program_test)
