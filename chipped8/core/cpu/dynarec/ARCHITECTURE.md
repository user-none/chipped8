# Dynamic Recompiler Architecture Proposal

## Target Platform: ARM64 macOS (Pure Python Implementation)

---

## 1. Overview

This document proposes an architecture for a dynamic recompiler (dynarec) CPU implementation for Chipped8. The dynarec translates Chip-8 bytecode into native ARM64 machine code at runtime, **entirely in Python** using ctypes for memory management and function invocation.

### Goals
- Execute Chip-8 instructions as native ARM64 code for improved performance
- **Pure Python implementation** - no C compiler required
- Implement the `iCPU` interface without modifying other CPU implementations
- Handle all Python object interactions through a well-defined trap mechanism
- Remain self-contained within the `cpu/dynarec/` directory

### Non-Goals
- Modifying audio, video, or other subsystems
- Cross-platform support (ARM64 macOS only)
- 100% native execution (complex ops trap to Python)

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Python Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Emulator   │  │   Display    │  │  Other Components        │  │
│  │              │  │   Audio      │  │  (Keys, Timers, etc.)    │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘  │
│         │                  ▲                      ▲                 │
│         │                  │ trap handlers        │                 │
│         ▼                  │                      │                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      DynarecCPU                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  execute_next_op()                                     │  │  │
│  │  │    1. Lookup/compile block for current PC              │  │  │
│  │  │    2. Call native block via ctypes                     │  │  │
│  │  │    3. Handle trap codes (if any)                       │  │  │
│  │  │    4. Update Python state from SharedState             │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  ARM64Emitter (Pure Python)                            │  │  │
│  │  │    - Encodes ARM64 instructions as bytes               │  │  │
│  │  │    - Writes to executable memory buffer                │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  JITMemory (ctypes)                                    │  │  │
│  │  │    - mmap with MAP_JIT                                 │  │  │
│  │  │    - pthread_jit_write_protect_np                      │  │  │
│  │  │    - sys_icache_invalidate                             │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  BlockCache                                            │  │  │
│  │  │    - Maps PC addresses to compiled code offsets        │  │  │
│  │  │    - Handles invalidation for SMC                      │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Technical Challenge: Executable Memory in Pure Python

### 3.1 macOS ARM64 Memory Protection (W^X)

macOS on ARM64 enforces Write XOR Execute (W^X): memory pages cannot be both writable and executable simultaneously. We handle this entirely via ctypes:

```python
import ctypes
from ctypes import c_void_p, c_size_t, c_int, c_uint8

# Load system libraries
libc = ctypes.CDLL('libc.dylib')
libpthread = ctypes.CDLL('libpthread.dylib')
libsystem = ctypes.CDLL('libsystem_kernel.dylib')

# mmap constants for macOS
MAP_PRIVATE = 0x0002
MAP_ANONYMOUS = 0x1000
MAP_JIT = 0x0800  # Critical for ARM64 JIT
PROT_READ = 0x01
PROT_WRITE = 0x02
PROT_EXEC = 0x04

# Function signatures
libc.mmap.argtypes = [c_void_p, c_size_t, c_int, c_int, c_int, c_size_t]
libc.mmap.restype = c_void_p

libc.munmap.argtypes = [c_void_p, c_size_t]
libc.munmap.restype = c_int

# pthread_jit_write_protect_np(int enabled)
# 0 = writable, 1 = executable
libpthread.pthread_jit_write_protect_np.argtypes = [c_int]
libpthread.pthread_jit_write_protect_np.restype = None

# sys_icache_invalidate(void* start, size_t size)
libsystem.sys_icache_invalidate.argtypes = [c_void_p, c_size_t]
libsystem.sys_icache_invalidate.restype = None
```

### 3.2 JITMemory Class

```python
class JITMemory:
    '''Manages executable memory for JIT code on macOS ARM64.'''

    def __init__(self, size: int = 1024 * 1024):  # 1MB default
        self.size = size
        self.offset = 0  # Current write position

        # Allocate JIT memory
        self.buffer = libc.mmap(
            None, size,
            PROT_READ | PROT_WRITE | PROT_EXEC,
            MAP_PRIVATE | MAP_ANONYMOUS | MAP_JIT,
            -1, 0
        )
        if self.buffer == ctypes.cast(-1, c_void_p).value:
            raise OSError('Failed to allocate JIT memory')

    def write_code(self, code: bytes) -> int:
        '''Write code bytes and return the offset where it was written.'''
        if self.offset + len(code) > self.size:
            raise MemoryError('JIT buffer exhausted')

        start_offset = self.offset

        # Make writable
        libpthread.pthread_jit_write_protect_np(0)

        # Write the bytes
        dst = self.buffer + self.offset
        ctypes.memmove(dst, code, len(code))
        self.offset += len(code)

        # Make executable
        libpthread.pthread_jit_write_protect_np(1)

        # Flush instruction cache
        libsystem.sys_icache_invalidate(
            self.buffer + start_offset, len(code)
        )

        return start_offset

    def get_function(self, offset: int) -> ctypes.CFUNCTYPE:
        '''Get a callable function pointer at the given offset.'''
        # Function signature: int block_entry(shared_state_t* state)
        func_type = ctypes.CFUNCTYPE(c_int, c_void_p)
        return func_type(self.buffer + offset)

    def __del__(self):
        if hasattr(self, 'buffer') and self.buffer:
            libc.munmap(self.buffer, self.size)
```

---

## 4. ARM64 Code Generation in Python

### 4.1 ARM64Emitter Class

The emitter generates ARM64 machine code as raw bytes:

```python
import struct

class ARM64Emitter:
    '''Emits ARM64 machine code as bytes.'''

    def __init__(self):
        self.code = bytearray()

    def emit(self, instruction: int):
        '''Emit a 32-bit ARM64 instruction.'''
        self.code.extend(struct.pack('<I', instruction))

    def get_code(self) -> bytes:
        return bytes(self.code)

    def reset(self):
        self.code = bytearray()

    # ─────────────────────────────────────────────────────────────
    # ARM64 Instruction Encoding
    # ─────────────────────────────────────────────────────────────

    def mov_imm(self, rd: int, imm: int):
        '''MOV Wd, #imm (MOVZ for 16-bit immediates)'''
        # MOVZ: 0101_0010_1HWi_iiii_iiii_iiii_iiid_dddd
        # For 32-bit (sf=0), hw=0 for bits 0-15
        assert 0 <= imm <= 0xFFFF, 'Use movz/movk sequence for larger immediates'
        instr = (0b01010010100 << 21) | (imm << 5) | rd
        self.emit(instr)

    def mov_reg(self, rd: int, rm: int):
        '''MOV Wd, Wm (actually ORR Wd, WZR, Wm)'''
        # ORR (shifted register): 0010_1010_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b00101010000 << 21) | (rm << 16) | (0b000000 << 10) | (31 << 5) | rd
        self.emit(instr)

    def add_imm(self, rd: int, rn: int, imm: int):
        '''ADD Wd, Wn, #imm'''
        # ADD (immediate): 0001_0001_00ii_iiii_iiii_iinn_nnnd_dddd
        assert 0 <= imm <= 0xFFF
        instr = (0b00010001 << 24) | (0 << 22) | (imm << 10) | (rn << 5) | rd
        self.emit(instr)

    def sub_imm(self, rd: int, rn: int, imm: int):
        '''SUB Wd, Wn, #imm'''
        # SUB (immediate): 0101_0001_00ii_iiii_iiii_iinn_nnnd_dddd
        assert 0 <= imm <= 0xFFF
        instr = (0b01010001 << 24) | (0 << 22) | (imm << 10) | (rn << 5) | rd
        self.emit(instr)

    def add_reg(self, rd: int, rn: int, rm: int):
        '''ADD Wd, Wn, Wm'''
        # ADD (shifted register): 0000_1011_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b00001011000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def sub_reg(self, rd: int, rn: int, rm: int):
        '''SUB Wd, Wn, Wm'''
        # SUB (shifted register): 0100_1011_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b01001011000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def and_reg(self, rd: int, rn: int, rm: int):
        '''AND Wd, Wn, Wm'''
        # AND (shifted register): 0000_1010_000m_mmmm_0000_00nn_nnnd_dddd
        instr = (0b00001010000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def orr_reg(self, rd: int, rn: int, rm: int):
        '''ORR Wd, Wn, Wm'''
        instr = (0b00101010000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def eor_reg(self, rd: int, rn: int, rm: int):
        '''EOR Wd, Wn, Wm'''
        instr = (0b01001010000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd
        self.emit(instr)

    def lsr_imm(self, rd: int, rn: int, shift: int):
        '''LSR Wd, Wn, #shift (actually UBFM)'''
        # UBFM: 0101_0011_00rr_rrrr_ssss_ssnn_nnnd_dddd
        # LSR is UBFM with immr=shift, imms=31
        imms = 31
        instr = (0b01010011 << 24) | (0 << 22) | (shift << 16) | (imms << 10) | (rn << 5) | rd
        self.emit(instr)

    def lsl_imm(self, rd: int, rn: int, shift: int):
        '''LSL Wd, Wn, #shift (actually UBFM)'''
        # LSL is UBFM with immr=(32-shift)%32, imms=31-shift
        immr = (32 - shift) % 32
        imms = 31 - shift
        instr = (0b01010011 << 24) | (0 << 22) | (immr << 16) | (imms << 10) | (rn << 5) | rd
        self.emit(instr)

    def and_imm(self, rd: int, rn: int, imm: int):
        '''AND Wd, Wn, #imm - only works for certain bitmask patterns'''
        # For 0xFF (8 bits), the encoding is specific
        # This is a simplified version for common masks
        if imm == 0xFF:
            # AND Wd, Wn, #0xFF: N=0, immr=0, imms=0b000111
            instr = (0b00010010 << 24) | (0 << 22) | (0 << 16) | (0b000111 << 10) | (rn << 5) | rd
        elif imm == 0xFFFF:
            # AND Wd, Wn, #0xFFFF: N=0, immr=0, imms=0b001111
            instr = (0b00010010 << 24) | (0 << 22) | (0 << 16) | (0b001111 << 10) | (rn << 5) | rd
        else:
            raise ValueError(f'Unsupported immediate for AND: {imm:#x}')
        self.emit(instr)

    def ldrb(self, rt: int, rn: int, offset: int):
        '''LDRB Wt, [Xn, #offset]'''
        # LDRB (unsigned offset): 0011_1001_01oo_oooo_oooo_oonn_nnnt_tttt
        assert 0 <= offset <= 4095
        instr = (0b0011100101 << 22) | (offset << 10) | (rn << 5) | rt
        self.emit(instr)

    def strb(self, rt: int, rn: int, offset: int):
        '''STRB Wt, [Xn, #offset]'''
        # STRB (unsigned offset): 0011_1001_00oo_oooo_oooo_oonn_nnnt_tttt
        assert 0 <= offset <= 4095
        instr = (0b0011100100 << 22) | (offset << 10) | (rn << 5) | rt
        self.emit(instr)

    def ldrh(self, rt: int, rn: int, offset: int):
        '''LDRH Wt, [Xn, #offset] - offset must be 2-byte aligned'''
        assert offset % 2 == 0 and 0 <= offset <= 8190
        instr = (0b0111100101 << 22) | ((offset // 2) << 10) | (rn << 5) | rt
        self.emit(instr)

    def strh(self, rt: int, rn: int, offset: int):
        '''STRH Wt, [Xn, #offset]'''
        assert offset % 2 == 0 and 0 <= offset <= 8190
        instr = (0b0111100100 << 22) | ((offset // 2) << 10) | (rn << 5) | rt
        self.emit(instr)

    def ldr_w(self, rt: int, rn: int, offset: int):
        '''LDR Wt, [Xn, #offset] - 32-bit load, offset must be 4-byte aligned'''
        assert offset % 4 == 0 and 0 <= offset <= 16380
        instr = (0b1011100101 << 22) | ((offset // 4) << 10) | (rn << 5) | rt
        self.emit(instr)

    def str_w(self, rt: int, rn: int, offset: int):
        '''STR Wt, [Xn, #offset]'''
        assert offset % 4 == 0 and 0 <= offset <= 16380
        instr = (0b1011100100 << 22) | ((offset // 4) << 10) | (rn << 5) | rt
        self.emit(instr)

    def cmp_imm(self, rn: int, imm: int):
        '''CMP Wn, #imm (actually SUBS WZR, Wn, #imm)'''
        assert 0 <= imm <= 0xFFF
        # SUBS (immediate): 0111_0001_00ii_iiii_iiii_iinn_nnnd_dddd
        instr = (0b01110001 << 24) | (0 << 22) | (imm << 10) | (rn << 5) | 31
        self.emit(instr)

    def cmp_reg(self, rn: int, rm: int):
        '''CMP Wn, Wm (actually SUBS WZR, Wn, Wm)'''
        instr = (0b01101011000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | 31
        self.emit(instr)

    def b(self, offset_bytes: int):
        '''B label (unconditional branch, PC-relative)'''
        # B: 0001_01oo_oooo_oooo_oooo_oooo_oooo_oooo
        assert offset_bytes % 4 == 0
        imm26 = (offset_bytes // 4) & 0x3FFFFFF
        instr = (0b000101 << 26) | imm26
        self.emit(instr)

    def b_cond(self, cond: int, offset_bytes: int):
        '''B.cond label (conditional branch)'''
        # B.cond: 0101_0100_oooo_oooo_oooo_oooo_ooo0_cccc
        assert offset_bytes % 4 == 0
        imm19 = (offset_bytes // 4) & 0x7FFFF
        instr = (0b01010100 << 24) | (imm19 << 5) | cond
        self.emit(instr)

    def ret(self):
        '''RET (return to address in X30/LR)'''
        # RET: 1101_0110_0101_1111_0000_00nn_nnn0_0000 (Xn=X30)
        instr = 0xD65F03C0
        self.emit(instr)

    # Condition codes for b_cond
    COND_EQ = 0b0000  # Equal (Z=1)
    COND_NE = 0b0001  # Not equal (Z=0)
    COND_HS = 0b0010  # Unsigned >= (C=1)
    COND_LO = 0b0011  # Unsigned < (C=0)
    COND_HI = 0b1000  # Unsigned > (C=1, Z=0)
    COND_LS = 0b1001  # Unsigned <= (C=0 or Z=1)
    COND_GE = 0b1010  # Signed >=
    COND_LT = 0b1011  # Signed <
    COND_GT = 0b1100  # Signed >
    COND_LE = 0b1101  # Signed <=
```

---

## 5. SharedState Structure

The shared state is a ctypes Structure that the native code reads/writes:

```python
import ctypes

MEMORY_SIZE = 65536

class SharedState(ctypes.Structure):
    _fields_ = [
        # Memory (64KB) - at offset 0 for easy access
        ('memory', ctypes.c_uint8 * MEMORY_SIZE),

        # V registers (V0-VF)
        ('V', ctypes.c_uint8 * 16),

        # RPL registers (XO-Chip)
        ('RPL', ctypes.c_uint8 * 16),

        # Index register (needs 16+ bits for XO-Chip)
        ('I', ctypes.c_uint32),

        # Program counter
        ('pc', ctypes.c_uint32),

        # Stack
        ('stack', ctypes.c_uint16 * 16),
        ('sp', ctypes.c_uint8),

        # Timers
        ('delay_timer', ctypes.c_uint8),
        ('sound_timer', ctypes.c_uint8),

        # Key state
        ('keys', ctypes.c_uint8 * 16),

        # Audio
        ('pattern', ctypes.c_uint8 * 16),
        ('pitch', ctypes.c_uint8),

        # Control fields (set by native code)
        ('trap_code', ctypes.c_uint8),
        ('trap_opcode', ctypes.c_uint16),

        # Quirks (read-only from native perspective)
        ('quirk_shift', ctypes.c_uint8),
        ('quirk_memoryIncrementByX', ctypes.c_uint8),
        ('quirk_memoryLeaveIUnchanged', ctypes.c_uint8),
        ('quirk_wrap', ctypes.c_uint8),
        ('quirk_jump', ctypes.c_uint8),
        ('quirk_logic', ctypes.c_uint8),

        # Execution state
        ('draw_occurred', ctypes.c_uint8),
        ('remaining_instructions', ctypes.c_int32),

        # SMC detection bitmap (64KB / 8 = 8KB)
        ('write_bitmap', ctypes.c_uint8 * 8192),
    ]
```

### Field Offsets (Important for Code Generation)

```python
# Pre-calculate offsets for use in emitter
OFFSET_MEMORY = SharedState.memory.offset           # 0
OFFSET_V = SharedState.V.offset                     # 65536
OFFSET_RPL = SharedState.RPL.offset                 # 65552
OFFSET_I = SharedState.I.offset                     # 65568
OFFSET_PC = SharedState.pc.offset                   # 65572
OFFSET_STACK = SharedState.stack.offset             # 65576
OFFSET_SP = SharedState.sp.offset                   # 65608
OFFSET_DELAY = SharedState.delay_timer.offset       # 65609
OFFSET_SOUND = SharedState.sound_timer.offset       # 65610
OFFSET_KEYS = SharedState.keys.offset               # 65611
OFFSET_PATTERN = SharedState.pattern.offset         # 65627
OFFSET_PITCH = SharedState.pitch.offset             # 65643
OFFSET_TRAP_CODE = SharedState.trap_code.offset     # 65644
OFFSET_TRAP_OPCODE = SharedState.trap_opcode.offset # 65646
# ... etc
```

---

## 6. Code Generator

### 6.1 Block Compiler

```python
class BlockCompiler:
    '''Compiles Chip-8 basic blocks to ARM64 code.'''

    # ARM64 register assignments
    REG_STATE = 19    # X19 = pointer to SharedState (callee-saved)
    REG_SCRATCH0 = 0  # W0 = scratch
    REG_SCRATCH1 = 1  # W1 = scratch
    REG_SCRATCH2 = 2  # W2 = scratch
    REG_RETVAL = 0    # W0 = return value

    def __init__(self, quirks):
        self.quirks = quirks
        self.emitter = ARM64Emitter()

    def compile_block(self, memory: bytes, start_pc: int) -> bytes:
        '''Compile a basic block starting at start_pc.'''
        self.emitter.reset()

        pc = start_pc
        while True:
            opcode = (memory[pc] << 8) | memory[pc + 1]
            block_ends = self._compile_opcode(opcode, pc)
            pc += 2

            if block_ends:
                break

            # Limit block size
            if pc - start_pc >= 128:
                # Update PC and return
                self._emit_store_pc(pc)
                self.emitter.mov_imm(self.REG_RETVAL, 0)
                self.emitter.ret()
                break

        return self.emitter.get_code()

    def _compile_opcode(self, opcode: int, pc: int) -> bool:
        '''
        Compile a single opcode. Returns True if block should end.
        '''
        nibble = (opcode & 0xF000) >> 12

        if nibble == 0x0:
            return self._compile_0xxx(opcode, pc)
        elif nibble == 0x1:
            return self._compile_1NNN(opcode)
        elif nibble == 0x2:
            return self._compile_2NNN(opcode, pc)
        elif nibble == 0x3:
            return self._compile_3XNN(opcode, pc)
        # ... etc for all opcodes
        elif nibble == 0x6:
            return self._compile_6XNN(opcode, pc)
        elif nibble == 0x7:
            return self._compile_7XNN(opcode, pc)
        elif nibble == 0x8:
            return self._compile_8XYN(opcode, pc)
        elif nibble == 0xD:
            return self._compile_DXYN(opcode, pc)  # Trap for draw
        else:
            # Unknown/complex opcode - trap
            return self._emit_trap(opcode, pc, TrapCode.UNKNOWN)

    def _compile_6XNN(self, opcode: int, pc: int) -> bool:
        '''6XNN: VX = NN'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF

        # Store NN to V[x]
        self.emitter.mov_imm(self.REG_SCRATCH0, nn)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

        # Update PC
        self._emit_store_pc(pc + 2)
        return False  # Block continues

    def _compile_7XNN(self, opcode: int, pc: int) -> bool:
        '''7XNN: VX += NN (no carry)'''
        x = (opcode & 0x0F00) >> 8
        nn = opcode & 0x00FF

        # Load V[x], add NN, mask to 8 bits, store back
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.add_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, nn)
        self.emitter.and_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 0xFF)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

        self._emit_store_pc(pc + 2)
        return False

    def _compile_8XY4(self, opcode: int, pc: int) -> bool:
        '''8XY4: VX += VY with carry'''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4

        # Load VX and VY
        self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)
        self.emitter.ldrb(self.REG_SCRATCH1, self.REG_STATE, OFFSET_V + y)

        # Add
        self.emitter.add_reg(self.REG_SCRATCH0, self.REG_SCRATCH0, self.REG_SCRATCH1)

        # Check carry (result > 255)
        self.emitter.cmp_imm(self.REG_SCRATCH0, 0xFF)

        # Set VF = 1 if carry, 0 otherwise
        # CSET Wd, cond: Wd = 1 if cond, else 0
        # For "unsigned greater than", use COND_HI
        self._emit_cset(self.REG_SCRATCH2, ARM64Emitter.COND_HI)
        self.emitter.strb(self.REG_SCRATCH2, self.REG_STATE, OFFSET_V + 0xF)

        # Mask and store VX
        self.emitter.and_imm(self.REG_SCRATCH0, self.REG_SCRATCH0, 0xFF)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

        self._emit_store_pc(pc + 2)
        return False

    def _compile_1NNN(self, opcode: int) -> bool:
        '''1NNN: Jump to NNN'''
        nnn = opcode & 0x0FFF

        # Store new PC
        self._emit_store_pc(nnn)

        # Return 0 (no trap, but block ends)
        self.emitter.mov_imm(self.REG_RETVAL, 0)
        self.emitter.ret()
        return True  # Block ends

    def _compile_DXYN(self, opcode: int, pc: int) -> bool:
        '''DXYN: Draw sprite - requires trap to Python'''
        # Store the opcode and PC for Python to handle
        self._emit_store_pc(pc)
        self._emit_trap(opcode, pc, TrapCode.DRAW)
        return True  # Block ends

    def _emit_trap(self, opcode: int, pc: int, trap_code: int) -> bool:
        '''Emit code to trap back to Python.'''
        # Store trap code
        self.emitter.mov_imm(self.REG_SCRATCH0, trap_code)
        self.emitter.strb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_TRAP_CODE)

        # Store opcode that caused trap
        self.emitter.mov_imm(self.REG_SCRATCH0, opcode)
        self.emitter.strh(self.REG_SCRATCH0, self.REG_STATE, OFFSET_TRAP_OPCODE)

        # Return trap code
        self.emitter.mov_imm(self.REG_RETVAL, trap_code)
        self.emitter.ret()
        return True

    def _emit_store_pc(self, new_pc: int):
        '''Store a new PC value.'''
        # For values up to 65535, may need MOVZ + MOVK
        if new_pc <= 0xFFFF:
            self.emitter.mov_imm(self.REG_SCRATCH0, new_pc)
        else:
            # Shouldn't happen for Chip-8 (4KB/64KB address space)
            raise ValueError(f'PC out of range: {new_pc}')

        self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

    def _emit_cset(self, rd: int, cond: int):
        '''CSET Wd, cond - Set register to 1 if condition true, else 0'''
        # CSET is actually CSINC Wd, WZR, WZR, invert(cond)
        inv_cond = cond ^ 1  # Invert condition
        # CSINC: 0001_1010_100m_mmmm_cccc_01nn_nnnd_dddd
        instr = (0b00011010100 << 21) | (31 << 16) | (inv_cond << 12) | (0b01 << 10) | (31 << 5) | rd
        self.emitter.emit(instr)
```

---

## 7. Instruction Classification

### 7.1 Fully JIT-able (Pure Native Execution)

| Opcode | Description | Complexity |
|--------|-------------|------------|
| `1NNN` | Jump | Simple - ends block |
| `2NNN` | Call subroutine | Medium - stack push |
| `00EE` | Return | Medium - stack pop |
| `3XNN` | Skip if VX == NN | Medium - conditional |
| `4XNN` | Skip if VX != NN | Medium - conditional |
| `5XY0` | Skip if VX == VY | Medium - conditional |
| `9XY0` | Skip if VX != VY | Medium - conditional |
| `6XNN` | VX = NN | Simple |
| `7XNN` | VX += NN | Simple |
| `8XY0-E` | ALU ops | Simple to medium |
| `ANNN` | I = NNN | Simple |
| `BNNN` | Jump V0+NNN | Medium (quirk-dependent) |
| `FX07` | VX = delay | Simple |
| `FX15` | delay = VX | Simple |
| `FX18` | sound = VX | Simple |
| `FX1E` | I += VX | Simple |
| `FX29` | I = font[VX] | Simple calculation |
| `FX33` | BCD store | Medium - 3 memory writes |
| `FX55` | Store V0-VX | Medium - loop, quirk-dependent |
| `FX65` | Load V0-VX | Medium - loop, quirk-dependent |
| `FX75` | Store RPL | Simple loop |
| `FX85` | Load RPL | Simple loop |

### 7.2 Trap-Required (Return to Python)

| Opcode | Description | Trap Code | Reason |
|--------|-------------|-----------|--------|
| `DXYN` | Draw sprite | `DRAW` | Complex display logic |
| `00E0` | Clear screen | `DISPLAY` | Display object |
| `00CN/DN` | Scroll up/down | `DISPLAY` | Display object |
| `00FB/FC` | Scroll left/right | `DISPLAY` | Display object |
| `00FE/FF` | Lo/Hi res mode | `DISPLAY` | Display mode change |
| `CXNN` | Random | `RANDOM` | Need Python random |
| `FX0A` | Wait for key | `WAIT_KEY` | Blocking input |
| `EX9E` | Skip if key pressed | `CHECK_KEY` | Key state in Python |
| `EXA1` | Skip if key not pressed | `CHECK_KEY` | Key state in Python |
| `00FD` | Exit | `EXIT` | Halt emulator |
| `FX01` | Plane select | `DISPLAY` | Display plane |
| `F002` | Audio pattern | `AUDIO` | Audio object |
| `FX3A` | Pitch | `AUDIO` | Audio object |
| `F000` | Load I (16-bit) | `SPECIAL` | 4-byte instruction |

---

## 8. DynarecCPU Implementation

```python
from ..icpu import iCPU
from .shared_state import SharedState, transfer_to_dynarec, transfer_to_python
from .state_codes import TrapCode
from .jit_memory import JITMemory
from .arm64 import BlockCompiler

class DynarecCPU(iCPU):

    def __init__(self, registers, stack, memory, timers, keys, display, quirks, audio):
        self._registers = registers
        self._stack = stack
        self._memory = memory
        self._timers = timers
        self._keys = keys
        self._display = display
        self._quirks = quirks
        self._audio = audio

        self._draw_occurred = False

        # Initialize JIT infrastructure
        self._shared_state = SharedState()
        self._jit_memory = JITMemory(size=4 * 1024 * 1024)  # 4MB
        self._compiler = BlockCompiler(quirks)
        self._block_cache = {}  # pc -> (code_offset, checksum)

        # Copy quirks to shared state
        self._shared_state.quirk_shift = quirks.shift
        self._shared_state.quirk_memoryIncrementByX = quirks.memoryIncrementByX
        self._shared_state.quirk_memoryLeaveIUnchanged = quirks.memoryLeaveIUnchanged
        self._shared_state.quirk_wrap = quirks.wrap
        self._shared_state.quirk_jump = quirks.jump
        self._shared_state.quirk_logic = quirks.logic

    def copy_state(self, d):
        '''Copy state from another CPU instance.'''
        # Copy block cache if same type
        if isinstance(d, DynarecCPU):
            self._block_cache = d._block_cache.copy()

    def execute_next_op(self):
        self._draw_occurred = False

        # Transfer Python state to SharedState
        transfer_to_dynarec(
            self._shared_state,
            self._memory,
            self._registers,
            self._stack,
            self._timers,
            self._keys,
            self._audio
        )

        pc = self._shared_state.pc

        # Lookup or compile block
        if pc not in self._block_cache:
            code = self._compiler.compile_block(
                bytes(self._shared_state.memory),
                pc
            )
            offset = self._jit_memory.write_code(code)
            checksum = self._compute_checksum(pc, len(code) // 4)  # Rough estimate
            self._block_cache[pc] = (offset, checksum)

        offset, _ = self._block_cache[pc]

        # Get callable function and execute
        block_func = self._jit_memory.get_function(offset)
        trap_code = block_func(ctypes.byref(self._shared_state))

        # Handle trap if needed
        if trap_code != 0:
            self._handle_trap(trap_code)

        # Transfer state back to Python
        transfer_to_python(
            self._shared_state,
            self._memory,
            self._registers,
            self._stack,
            self._timers,
            self._keys,
            self._audio
        )

    def _handle_trap(self, trap_code: int):
        '''Handle a trap from native code.'''
        opcode = self._shared_state.trap_opcode

        if trap_code == TrapCode.DRAW:
            self._handle_draw(opcode)
        elif trap_code == TrapCode.RANDOM:
            self._handle_random(opcode)
        elif trap_code == TrapCode.WAIT_KEY:
            self._handle_wait_key(opcode)
        elif trap_code == TrapCode.CHECK_KEY:
            self._handle_check_key(opcode)
        elif trap_code == TrapCode.DISPLAY:
            self._handle_display(opcode)
        elif trap_code == TrapCode.AUDIO:
            self._handle_audio(opcode)
        elif trap_code == TrapCode.EXIT:
            from ...exceptions import ExitInterpreterException
            raise ExitInterpreterException()

    def _handle_draw(self, opcode: int):
        '''Handle DXYN draw instruction.'''
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F

        vx = self._shared_state.V[x]
        vy = self._shared_state.V[y]

        self._display.draw(vx, vy, n, self._quirks.wrap,
                          self._registers, self._memory)
        self._draw_occurred = True
        self._shared_state.pc += 2

    def _handle_random(self, opcode: int):
        '''Handle CXNN random instruction.'''
        from random import randint
        x = (opcode & 0x0F00) >> 8
        mask = opcode & 0x00FF
        self._shared_state.V[x] = randint(0, 255) & mask
        self._shared_state.pc += 2

    # ... other trap handlers ...

    def draw_occurred(self) -> bool:
        return self._draw_occurred

    def _compute_checksum(self, pc: int, num_instructions: int) -> int:
        '''Compute a simple checksum of memory for SMC detection.'''
        data = bytes(self._shared_state.memory[pc:pc + num_instructions * 2])
        return hash(data)
```

---

## 9. File Structure

```
chipped8/core/cpu/dynarec/
├── __init__.py              # Public exports (DynarecCPU, TrapCode)
├── cpu.py                   # DynarecCPU class (iCPU implementation)
├── shared_state.py          # SharedState ctypes structure + transfer functions
├── state_codes.py           # TrapCode enum
├── jit_memory.py            # JITMemory class (mmap, write protection)
├── ARCHITECTURE.md          # This document
└── arm64/                   # ARM64 backend
    ├── __init__.py          # Exports BlockCompiler
    ├── compiler.py          # BlockCompiler class (opcode -> ARM64)
    └── emitter.py           # ARM64Emitter class (instruction encoding)
```

The architecture separates shared components (JIT memory, shared state, trap codes) from
architecture-specific code generation (ARM64 emitter, compiler). This allows for potential
future backends while keeping the macOS-only constraint.

---

## 10. Caveats and Considerations

### 10.1 Platform Limitations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| **ARM64 macOS only** | No Windows/Linux/Intel Mac support | Document clearly; other CPUs work everywhere |
| **JIT entitlement may be needed** | App Store / hardened runtime issues | Document signing requirements |
| **Python ctypes overhead** | Each block call has FFI overhead | Batch multiple instructions per block |

### 10.2 Self-Modifying Code (SMC)

Chip-8 programs can modify their own code. Detection strategies:

1. **Write Tracking**: When `FX55` writes to memory, mark those addresses in a bitmap. Before executing a cached block, check if any writes occurred in its range.

2. **Checksums**: Store a hash of the original bytes. Re-verify periodically.

3. **Conservative Invalidation**: Any write to memory below 0x1000 invalidates all blocks (most ROMs live in low memory).

**Recommendation**: Start with conservative invalidation (clear entire cache on memory write). Optimize later if needed.

### 10.3 Debugging

- Add a `DEBUG` flag that prints disassembly of generated code
- Use LLDB to debug crashes in generated code
- Consider a "validation mode" that runs both PureCPU and DynarecCPU, comparing state after each instruction

### 10.4 Testing Strategy

1. Run existing pytest test suite with `interpreter_type=dynarec`
2. Compare output with PureCPU for many ROMs
3. Test edge cases: SMC, all quirk combinations, boundary conditions

### 10.5 Performance Expectations

| Factor | Impact |
|--------|--------|
| **JIT compilation overhead** | First execution of a block is slower |
| **ctypes FFI overhead** | ~1-2μs per call |
| **Block execution** | Much faster than Python interpretation |
| **Net effect** | Likely 2-10x faster for hot loops, may be slower for straight-line code |

**Reality check**: The cached lambda interpreter is already quite fast. Dynarec is primarily valuable for:
- Learning JIT techniques
- Handling very high tickrate requirements
- Future extensibility

### 10.6 Code Signing for Development

```bash
# Create entitlements file
cat > entitlements.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
EOF

# Sign the Python interpreter (if using hardened runtime)
codesign --sign - --entitlements entitlements.plist --force /path/to/python
```

For development, running unsigned Python typically works without special signing.

---

## 11. Implementation Phases

### Phase 1: Infrastructure
1. Implement `JITMemory` class with mmap/write protection
2. Implement `ARM64Emitter` with basic instructions
3. Test: allocate memory, emit simple function, call it

### Phase 2: Minimal JIT
1. Implement `SharedState` structure
2. Implement state transfer functions
3. Compile only `6XNN` (set register) - everything else traps
4. Verify with simple test program

### Phase 3: Arithmetic Operations
1. Add `7XNN`, `8XY0-8XYE` compilation
2. Add `ANNN`, `FX1E`
3. Run arithmetic-heavy tests

### Phase 4: Control Flow
1. Add `1NNN` (jump), `2NNN` (call), `00EE` (return)
2. Add conditional skips (`3XNN`, `4XNN`, `5XY0`, `9XY0`)
3. Test with actual ROMs

### Phase 5: Full Implementation
1. Add all remaining JIT-able opcodes
2. Implement all trap handlers
3. Add SMC detection
4. Full test suite pass

### Phase 6: Optimization (Optional)
1. Multi-instruction blocks
2. Register caching
3. Block linking (jump directly between blocks)
4. Profile and optimize hot paths

---

## 12. Example: Complete Block Compilation

Given this Chip-8 code at address 0x200:
```
0x200: 6000    ; V0 = 0
0x202: 6100    ; V1 = 0
0x204: 8014    ; V0 += V1
0x206: 1200    ; Jump to 0x200
```

Generated ARM64 (conceptual):
```asm
block_0x200:
    ; V0 = 0
    mov     w0, #0
    strb    w0, [x19, #OFFSET_V+0]

    ; V1 = 0
    mov     w0, #0
    strb    w0, [x19, #OFFSET_V+1]

    ; V0 += V1
    ldrb    w0, [x19, #OFFSET_V+0]
    ldrb    w1, [x19, #OFFSET_V+1]
    add     w0, w0, w1
    cmp     w0, #255
    cset    w2, hi
    and     w0, w0, #0xFF
    strb    w0, [x19, #OFFSET_V+0]
    strb    w2, [x19, #OFFSET_V+15]

    ; Jump to 0x200 (store PC, return)
    mov     w0, #0x200
    str     w0, [x19, #OFFSET_PC]
    mov     w0, #0              ; return 0 (no trap)
    ret
```

---

## 13. Summary

This architecture enables a pure Python dynamic recompiler for Chip-8 on ARM64 macOS by:

1. Using **ctypes** to allocate executable memory via `mmap` with `MAP_JIT`
2. Managing W^X via **`pthread_jit_write_protect_np`**
3. Encoding ARM64 instructions as **raw bytes** in Python
4. Using a **SharedState** structure for Python/native communication
5. **Trapping** to Python for complex operations (display, input, audio)
6. Implementing the standard **`iCPU` interface** for seamless integration

The implementation is self-contained in `cpu/dynarec/` and requires no modifications to other CPU implementations or subsystems.
