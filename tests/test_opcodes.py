import pytest

from .test_framework import ProgramTest, run_test_program, validate_stack, validate_stack_len, validate_v, validate_pc, validate_memory, validate_i, validate_audio_pattern, validate_delay_timer, validate_sound_timer, validate_audio_pitch, validate_rpl
from chipped8.core.keys import Keys, KeyState

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

    # FN01 - NOT IMP

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
]

# Main test runner
@pytest.mark.parametrize('program_test', opcode_tests, ids=lambda test: test.name)
def test_opcode_programs(emulator, program_test: ProgramTest):
    cpu = emulator._cpu
    # Reset CPU state from program_test.initial_state
    for attr, value in program_test.initial_state.items():
        setattr(cpu, attr, value)
    # Run program
    run_test_program(cpu, program_test)
