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
ARM64 instruction emitter.

Encodes ARM64 machine instructions as raw bytes for JIT compilation.
All instructions are encoded in little-endian format.
'''

import struct


class ARM64Emitter:
    '''Emits ARM64 machine code as bytes.'''

    # Condition codes for conditional branches
    COND_EQ = 0b0000  # Equal (Z=1)
    COND_NE = 0b0001  # Not equal (Z=0)
    COND_HS = 0b0010  # Unsigned >= (C=1), also CS
    COND_HI = 0b1000  # Unsigned > (C=1, Z=0)

    # Common register aliases
    REG_WZR = 31  # Zero register (32-bit)

    def __init__(self):
        self.code = bytearray()

    def emit(self, instruction: int):
        '''Emit a 32-bit ARM64 instruction in little-endian format.'''
        self.code.extend(struct.pack('<I', instruction))

    def get_code(self) -> bytes:
        '''Return the emitted code as bytes.'''
        return bytes(self.code)

    def reset(self):
        '''Clear the code buffer.'''
        self.code = bytearray()

    # -------------------------------------------------------------------------
    # Move Instructions
    # -------------------------------------------------------------------------

    def movz_w(self, rd: int, imm: int, shift: int = 0):
        '''
        MOVZ Wd, #imm{, LSL #shift}
        Move wide with zero. Sets register to imm << shift, zeroing other bits.
        shift must be 0 or 16 for 32-bit.
        '''
        assert 0 <= imm <= 0xFFFF, 'Immediate must be 16-bit'
        assert shift in (0, 16), 'Shift must be 0 or 16 for 32-bit'
        hw = shift // 16
        # MOVZ: sf=0, opc=10, hw, imm16, rd
        # 0101_0010_1HWi_iiii_iiii_iiii_iiid_dddd
        instr = (0b01010010100 << 21) | (hw << 21) | (imm << 5) | rd
        self.emit(instr)

    def movk_w(self, rd: int, imm: int, shift: int = 0):
        '''
        MOVK Wd, #imm{, LSL #shift}
        Move wide with keep. Inserts imm at shift position, keeping other bits.
        '''
        assert 0 <= imm <= 0xFFFF, 'Immediate must be 16-bit'
        assert shift in (0, 16), 'Shift must be 0 or 16 for 32-bit'
        hw = shift // 16
        # MOVK: sf=0, opc=11, hw, imm16, rd
        # 0111_0010_1HWi_iiii_iiii_iiii_iiid_dddd
        instr = (0b01110010100 << 21) | (hw << 21) | (imm << 5) | rd
        self.emit(instr)

    def mov_imm(self, rd: int, imm: int):
        '''
        MOV Wd, #imm
        Move immediate to register. Handles values up to 32 bits.
        '''
        if imm == 0:
            # MOV Wd, WZR
            self.mov_reg(rd, self.REG_WZR)
        elif imm <= 0xFFFF:
            self.movz_w(rd, imm, 0)
        elif imm <= 0xFFFFFFFF:
            # Need MOVZ + MOVK for larger values
            self.movz_w(rd, imm & 0xFFFF, 0)
            if imm > 0xFFFF:
                self.movk_w(rd, (imm >> 16) & 0xFFFF, 16)
        else:
            raise ValueError(f'Immediate {imm} too large for 32-bit register')

    def mov_reg(self, rd: int, rm: int):
        '''
        MOV Wd, Wm
        Move register to register (actually ORR Wd, WZR, Wm).
        '''
        # ORR (shifted register): 0010_1010_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b00101010000 << 21) | (rm << 16) | (0 << 10) | (31 << 5) | rd
        self.emit(instr)

    # -------------------------------------------------------------------------
    # Arithmetic Instructions
    # -------------------------------------------------------------------------

    def add_imm(self, rd: int, rn: int, imm: int):
        '''ADD Wd, Wn, #imm'''
        assert 0 <= imm <= 0xFFF, 'Immediate must be 12-bit'
        # ADD (immediate): 0001_0001_00ii_iiii_iiii_iinn_nnnd_dddd
        instr = (0b00010001 << 24) | (0 << 22) | (imm << 10) | (rn << 5) | rd
        self.emit(instr)

    def add_reg(self, rd: int, rn: int, rm: int):
        '''ADD Wd, Wn, Wm'''
        # ADD (shifted register): 0000_1011_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b00001011000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def add_x_reg(self, rd: int, rn: int, rm: int):
        '''ADD Xd, Xn, Xm - 64-bit register add'''
        # ADD (shifted register) 64-bit: 1000_1011_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b10001011000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def sub_imm(self, rd: int, rn: int, imm: int):
        '''SUB Wd, Wn, #imm'''
        assert 0 <= imm <= 0xFFF, 'Immediate must be 12-bit'
        # SUB (immediate): 0101_0001_00ii_iiii_iiii_iinn_nnnd_dddd
        instr = (0b01010001 << 24) | (0 << 22) | (imm << 10) | (rn << 5) | rd
        self.emit(instr)

    def sub_reg(self, rd: int, rn: int, rm: int):
        '''SUB Wd, Wn, Wm'''
        # SUB (shifted register): 0100_1011_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b01001011000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    # -------------------------------------------------------------------------
    # Logical Instructions
    # -------------------------------------------------------------------------

    def and_reg(self, rd: int, rn: int, rm: int):
        '''AND Wd, Wn, Wm'''
        # AND (shifted register): 0000_1010_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b00001010000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def orr_reg(self, rd: int, rn: int, rm: int):
        '''ORR Wd, Wn, Wm'''
        # ORR (shifted register): 0010_1010_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b00101010000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def eor_reg(self, rd: int, rn: int, rm: int):
        '''EOR Wd, Wn, Wm (XOR)'''
        # EOR (shifted register): 0100_1010_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b01001010000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def and_imm(self, rd: int, rn: int, imm: int):
        '''
        AND Wd, Wn, #imm
        Only works for certain bitmask patterns. Common masks supported.
        '''
        # AND (immediate) uses a complex bitmask encoding
        # For common masks we can hardcode the encoding
        if imm == 0xFF:
            # N=0, immr=0, imms=0b000111 (8 consecutive 1s)
            n, immr, imms = 0, 0, 0b000111
        elif imm == 0xFFFF:
            # N=0, immr=0, imms=0b001111 (16 consecutive 1s)
            n, immr, imms = 0, 0, 0b001111
        elif imm == 0x1:
            # N=0, immr=0, imms=0b000000 (1 bit)
            n, immr, imms = 0, 0, 0b000000
        elif imm == 0xFFF:
            # N=0, immr=0, imms=0b001011 (12 consecutive 1s)
            n, immr, imms = 0, 0, 0b001011
        else:
            raise ValueError(f'Unsupported immediate for AND: {imm:#x}')

        # AND (immediate): 0001_0010_0Nrr_rrrr_ssss_ssnn_nnnd_dddd
        instr = (0b00010010 << 24) | (n << 22) | (immr << 16) | (imms << 10) | (rn << 5) | rd
        self.emit(instr)

    # -------------------------------------------------------------------------
    # Shift Instructions
    # -------------------------------------------------------------------------

    def lsr_imm(self, rd: int, rn: int, shift: int):
        '''LSR Wd, Wn, #shift (logical shift right)'''
        assert 0 <= shift <= 31, 'Shift must be 0-31'
        # LSR is UBFM with immr=shift, imms=31
        immr = shift
        imms = 31
        # UBFM: 0101_0011_00rr_rrrr_ssss_ssnn_nnnd_dddd
        instr = (0b01010011 << 24) | (0 << 22) | (immr << 16) | (imms << 10) | (rn << 5) | rd
        self.emit(instr)

    def lsl_imm(self, rd: int, rn: int, shift: int):
        '''LSL Wd, Wn, #shift (logical shift left)'''
        assert 0 <= shift <= 31, 'Shift must be 0-31'
        # LSL is UBFM with immr=(32-shift)%32, imms=31-shift
        immr = (32 - shift) % 32
        imms = 31 - shift
        # UBFM: 0101_0011_00rr_rrrr_ssss_ssnn_nnnd_dddd
        instr = (0b01010011 << 24) | (0 << 22) | (immr << 16) | (imms << 10) | (rn << 5) | rd
        self.emit(instr)

    # -------------------------------------------------------------------------
    # Load/Store Instructions
    # -------------------------------------------------------------------------

    def ldrb(self, rt: int, rn: int, offset: int):
        '''LDRB Wt, [Xn, #offset] - load byte (zero-extend)'''
        assert 0 <= offset <= 4095, 'Offset must be 0-4095'
        # LDRB (unsigned offset): 0011_1001_01oo_oooo_oooo_oonn_nnnt_tttt
        instr = (0b0011100101 << 22) | (offset << 10) | (rn << 5) | rt
        self.emit(instr)

    def strb(self, rt: int, rn: int, offset: int):
        '''STRB Wt, [Xn, #offset] - store byte'''
        assert 0 <= offset <= 4095, 'Offset must be 0-4095'
        # STRB (unsigned offset): 0011_1001_00oo_oooo_oooo_oonn_nnnt_tttt
        instr = (0b0011100100 << 22) | (offset << 10) | (rn << 5) | rt
        self.emit(instr)

    def ldrh(self, rt: int, rn: int, offset: int):
        '''LDRH Wt, [Xn, #offset] - load halfword, offset must be 2-byte aligned'''
        assert offset % 2 == 0 and 0 <= offset <= 8190, 'Offset must be 2-aligned, 0-8190'
        # LDRH (unsigned offset): 0111_1001_01oo_oooo_oooo_oonn_nnnt_tttt
        instr = (0b0111100101 << 22) | ((offset // 2) << 10) | (rn << 5) | rt
        self.emit(instr)

    def strh(self, rt: int, rn: int, offset: int):
        '''STRH Wt, [Xn, #offset] - store halfword'''
        assert offset % 2 == 0 and 0 <= offset <= 8190, 'Offset must be 2-aligned, 0-8190'
        # STRH (unsigned offset): 0111_1001_00oo_oooo_oooo_oonn_nnnt_tttt
        instr = (0b0111100100 << 22) | ((offset // 2) << 10) | (rn << 5) | rt
        self.emit(instr)

    def ldr_w(self, rt: int, rn: int, offset: int):
        '''LDR Wt, [Xn, #offset] - load 32-bit word, offset must be 4-byte aligned'''
        assert offset % 4 == 0 and 0 <= offset <= 16380, 'Offset must be 4-aligned, 0-16380'
        # LDR (unsigned offset) 32-bit: 1011_1001_01oo_oooo_oooo_oonn_nnnt_tttt
        instr = (0b1011100101 << 22) | ((offset // 4) << 10) | (rn << 5) | rt
        self.emit(instr)

    def str_w(self, rt: int, rn: int, offset: int):
        '''STR Wt, [Xn, #offset] - store 32-bit word'''
        assert offset % 4 == 0 and 0 <= offset <= 16380, 'Offset must be 4-aligned, 0-16380'
        # STR (unsigned offset) 32-bit: 1011_1001_00oo_oooo_oooo_oonn_nnnt_tttt
        instr = (0b1011100100 << 22) | ((offset // 4) << 10) | (rn << 5) | rt
        self.emit(instr)

    # -------------------------------------------------------------------------
    # Compare Instructions
    # -------------------------------------------------------------------------

    def cmp_imm(self, rn: int, imm: int):
        '''CMP Wn, #imm (actually SUBS WZR, Wn, #imm)'''
        assert 0 <= imm <= 0xFFF, 'Immediate must be 12-bit'
        # SUBS (immediate): 0111_0001_00ii_iiii_iiii_iinn_nnnd_dddd (rd=31=WZR)
        instr = (0b01110001 << 24) | (0 << 22) | (imm << 10) | (rn << 5) | 31
        self.emit(instr)

    def cmp_reg(self, rn: int, rm: int):
        '''CMP Wn, Wm (actually SUBS WZR, Wn, Wm)'''
        # SUBS (shifted register): 0110_1011_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b01101011000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | 31
        self.emit(instr)

    # -------------------------------------------------------------------------
    # Conditional Instructions
    # -------------------------------------------------------------------------

    def cset(self, rd: int, cond: int):
        '''
        CSET Wd, cond
        Set register to 1 if condition is true, else 0.
        '''
        # CSET is CSINC Wd, WZR, WZR, invert(cond)
        inv_cond = cond ^ 1  # Invert condition
        # CSINC: 0001_1010_100m_mmmm_cccc_01nn_nnnd_dddd
        instr = (0b00011010100 << 21) | (31 << 16) | (inv_cond << 12) | (0b01 << 10) | (31 << 5) | rd
        self.emit(instr)

    def csel(self, rd: int, rn: int, rm: int, cond: int):
        '''
        CSEL Wd, Wn, Wm, cond
        Conditional select: Wd = cond ? Wn : Wm
        '''
        # CSEL: 0001_1010_100m_mmmm_cccc_00nn_nnnd_dddd
        instr = (0b00011010100 << 21) | (rm << 16) | (cond << 12) | (0b00 << 10) | (rn << 5) | rd
        self.emit(instr)

    # -------------------------------------------------------------------------
    # Branch Instructions
    # -------------------------------------------------------------------------

    def ret(self, rn: int = 30):
        '''
        RET {Xn}
        Return to address in register (default X30/LR).
        '''
        # RET: 1101_0110_0101_1111_0000_00nn_nnn0_0000
        instr = (0b1101011001011111000000 << 10) | (rn << 5) | 0
        self.emit(instr)

    def b_cond(self, cond: int, offset_bytes: int):
        '''
        B.cond label
        Conditional branch with PC-relative offset.
        offset_bytes must be within ±1MB range and 4-byte aligned.
        '''
        assert offset_bytes % 4 == 0, 'Offset must be 4-byte aligned'
        imm19 = (offset_bytes >> 2) & 0x7FFFF
        # B.cond: 0101_0100_iiii_iiii_iiii_iiii_iii0_cccc
        instr = (0b01010100 << 24) | (imm19 << 5) | cond
        self.emit(instr)

    def add_x_imm(self, rd: int, rn: int, imm: int):
        '''ADD Xd, Xn, #imm - 64-bit add immediate'''
        assert 0 <= imm <= 0xFFF, 'Immediate must be 12-bit'
        # ADD (immediate) 64-bit: 1001_0001_00ii_iiii_iiii_iinn_nnnd_dddd
        instr = (0b10010001 << 24) | (0 << 22) | (imm << 10) | (rn << 5) | rd
        self.emit(instr)

