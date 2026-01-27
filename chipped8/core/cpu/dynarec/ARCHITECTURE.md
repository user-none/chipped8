# Dynamic Recompiler Architecture

## Target Platform: ARM64 macOS (Pure Python Implementation)

---

## 1. Overview

This document describes the architecture of the dynamic recompiler (dynarec)
CPU implementation for Chipped8. The dynarec translates Chip-8 bytecode into
native ARM64 machine code at runtime, **entirely in Python** using ctypes for
memory management and function invocation.

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
│  │  │    1. Transfer state from Python to SharedState        │  │  │
│  │  │    2. Lookup/compile block for current PC              │  │  │
│  │  │    3. Call native block via ctypes                     │  │  │
│  │  │    4. Handle trap codes (if any)                       │  │  │
│  │  │    5. Transfer state back to Python                    │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  BlockCompiler (Pure Python)                          │  │  │
│  │  │    - Compiles Chip-8 opcodes to ARM64 instructions    │  │  │
│  │  │    - Uses ARM64Emitter for instruction encoding       │  │  │
│  │  │    - Handles quirk-dependent behavior                 │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  ARM64Emitter (Pure Python)                           │  │  │
│  │  │    - Encodes ARM64 instructions as raw bytes          │  │  │
│  │  │    - Supports arithmetic, logic, memory, branch ops   │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  JITMemory (ctypes)                                   │  │  │
│  │  │    - mmap with MAP_JIT                                │  │  │
│  │  │    - pthread_jit_write_protect_np for W^X             │  │  │
│  │  │    - sys_icache_invalidate                            │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  BlockCache                                           │  │  │
│  │  │    - Maps PC addresses to compiled code offsets       │  │  │
│  │  │    - Only caches blocks within ROM region             │  │  │
│  │  │    - Invalidates on self-modifying code detection     │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Security Considerations

### 3.1 JIT Memory Protection (W^X)

The dynarec enforces Write XOR Execute (W^X) at all times using macOS ARM64 APIs:

```python
# Make writable (disable execute)
pthread_jit_write_protect_np(0)

# ... write code ...

# Make executable (disable write)
pthread_jit_write_protect_np(1)

# Flush instruction cache
sys_icache_invalidate(address, length)
```

This ensures that memory is never simultaneously writable and executable, preventing code injection attacks.

### 3.2 Input Validation

The dynarec validates all inputs to prevent security issues:

| Validation | Location | Purpose |
|------------|----------|---------|
| **PC bounds check** | `compile_block()` | Ensures PC is within valid memory range before compilation |
| **JIT offset validation** | `get_callable()` | Validates offset is non-negative and within written code bounds |
| **Stack bounds check** | Native code (CALL/RET) | Stack overflow (sp >= 16) and underflow (sp == 0) trigger traps |
| **Memory bounds check** | Trap handlers | All memory operations validate I + length <= MEMORY_SIZE |
| **Address masking** | `_handle_jump_bnnn()` | Jump targets masked to 0xFFFF to prevent out-of-bounds access |

### 3.3 Stack Protection

Stack operations include runtime bounds checking in generated native code:

**CALL (2NNN):**
```asm
; Check for stack overflow
ldrb  w0, [x0, #OFFSET_SP]    ; Load stack pointer
cmp   w0, #16                  ; Check against max
b.hs  overflow_trap            ; Branch if SP >= 16
; ... normal call code ...
```

**RET (00EE):**
```asm
; Check for stack underflow
ldrb  w0, [x0, #OFFSET_SP]    ; Load stack pointer
cmp   w0, #0                   ; Check against min
b.eq  underflow_trap           ; Branch if SP == 0
; ... normal return code ...
```

### 3.4 Self-Modifying Code (SMC) Detection

The dynarec detects self-modifying code to prevent execution of stale cached code:

1. **ROM Region Tracking**: Only blocks within ROM region (0x200 to `rom_end`) are cached
2. **Write Detection**: Memory writes to ROM region invalidate the entire cache
3. **Jump Detection**: Jumps outside ROM region invalidate the cache
4. **Conservative Invalidation**: When SMC is detected, both block cache and JIT buffer are cleared

```python
def _write_overlaps_rom(self, start: int, length: int) -> bool:
    '''Check if a write range overlaps ROM region.'''
    write_end = start + length
    rom_start = 0x200
    rom_end = self._shared_state.rom_end
    return start < rom_end and rom_start < write_end
```

### 3.5 JIT Buffer Management

The JIT buffer uses a safe allocation pattern:

- **Fixed size allocation**: 4MB buffer allocated at initialization
- **Capacity monitoring**: `needs_reset()` checks if buffer is 90% full
- **Safe reset**: `invalidate_cache()` clears both cache and buffer offset
- **No reallocation**: Buffer size is fixed; overflow triggers reset, not growth

---

## 4. Executable Memory Management

### 4.1 macOS ARM64 Memory Protection

macOS on ARM64 enforces W^X: memory pages cannot be both writable and executable simultaneously. The implementation uses ctypes to access system APIs:

```python
import ctypes
from ctypes import c_void_p, c_size_t, c_int

# Load system library
_libSystem = ctypes.CDLL('/usr/lib/libSystem.B.dylib')

# mmap constants for macOS
MAP_PRIVATE = 0x0002
MAP_ANONYMOUS = 0x1000
MAP_JIT = 0x0800  # Critical for ARM64 JIT
PROT_READ = 0x01
PROT_WRITE = 0x02
PROT_EXEC = 0x04

# Function signatures
_libSystem.mmap.argtypes = [c_void_p, c_size_t, c_int, c_int, c_int, c_size_t]
_libSystem.mmap.restype = c_void_p

_libSystem.munmap.argtypes = [c_void_p, c_size_t]
_libSystem.munmap.restype = c_int

# pthread_jit_write_protect_np(int enabled)
# 0 = writable, 1 = executable
_libSystem.pthread_jit_write_protect_np.argtypes = [c_int]
_libSystem.pthread_jit_write_protect_np.restype = None

# sys_icache_invalidate(void* start, size_t size)
_libSystem.sys_icache_invalidate.argtypes = [c_void_p, c_size_t]
_libSystem.sys_icache_invalidate.restype = None
```

### 4.2 JITMemory Class

```python
class JITMemory:
    '''Manages executable memory for JIT code on macOS ARM64.'''

    def __init__(self, size: int = 4 * 1024 * 1024):  # 4MB default
        self.size = size
        self.offset = 0  # Current write position

        # Allocate JIT memory with read/write/execute permissions
        self.buffer = _libSystem.mmap(
            None, size,
            PROT_READ | PROT_WRITE | PROT_EXEC,
            MAP_PRIVATE | MAP_ANONYMOUS | MAP_JIT,
            -1, 0
        )
        if self.buffer == MAP_FAILED:
            raise OSError('Failed to allocate JIT memory')

    def write_code(self, code: bytes) -> int:
        '''Write code bytes and return the offset where written.'''
        if self.offset + len(code) > self.size:
            raise MemoryError('JIT buffer exhausted')

        start_offset = self.offset

        # Make writable
        _libSystem.pthread_jit_write_protect_np(0)

        # Write the bytes
        dst = self.buffer + self.offset
        ctypes.memmove(dst, code, len(code))
        self.offset += len(code)

        # Make executable
        _libSystem.pthread_jit_write_protect_np(1)

        # Flush instruction cache
        _libSystem.sys_icache_invalidate(self.buffer + start_offset, len(code))

        return start_offset

    def get_callable(self, offset: int):
        '''Get a callable function pointer at the given offset.'''
        # Validation
        if offset < 0:
            raise ValueError(f'Invalid JIT code offset: {offset}')
        if offset >= self.offset:
            raise ValueError(f'Invalid JIT code offset: {offset}')

        # Function signature: int block_entry(shared_state_t* state)
        func_type = ctypes.CFUNCTYPE(c_int, c_void_p)
        return func_type(self.buffer + offset)

    def reset(self):
        '''Reset buffer offset for reuse.'''
        self.offset = 0

    def needs_reset(self, threshold: float = 0.9) -> bool:
        '''Check if buffer should be reset (90% full by default).'''
        return (self.offset / self.size) >= threshold

    def __del__(self):
        if hasattr(self, 'buffer') and self.buffer and self.buffer != MAP_FAILED:
            _libSystem.munmap(self.buffer, self.size)
```

---

## 5. SharedState Structure

The shared state is a ctypes Structure that both Python and native code access. **Frequently accessed fields are placed first** to ensure their offsets fit within ARM64 immediate offset limits (max 4095 for byte loads/stores).

```python
class SharedState(ctypes.Structure):
    _fields_ = [
        # --- Frequently accessed fields first (offset < 4096) ---

        # V registers (V0-VF, 16 bytes) - offset 0
        ('V', ctypes.c_uint8 * 16),

        # RPL registers (XO-Chip, 16 bytes) - offset 16
        ('RPL', ctypes.c_uint8 * 16),

        # Program counter - offset 32
        ('pc', ctypes.c_uint32),

        # Index register I (needs 16+ bits for XO-Chip) - offset 36
        ('I', ctypes.c_uint32),

        # Stack (16 entries of 16-bit addresses) - offset 40
        ('stack', ctypes.c_uint16 * 16),

        # Stack pointer - offset 72
        ('sp', ctypes.c_uint8),

        # Timers - offset 73, 74
        ('delay_timer', ctypes.c_uint8),
        ('sound_timer', ctypes.c_uint8),

        # Key state (16 keys, 0=up, 1=down) - offset 75
        ('keys', ctypes.c_uint8 * 16),

        # Audio pattern (16 bytes) and pitch - offset 91, 107
        ('pattern', ctypes.c_uint8 * 16),
        ('pitch', ctypes.c_uint8),

        # Control fields - set by native code
        ('trap_code', ctypes.c_uint8),
        ('trap_opcode', ctypes.c_uint16),

        # Quirks (read-only from JIT perspective)
        ('quirk_shift', ctypes.c_uint8),
        ('quirk_memoryIncrementByX', ctypes.c_uint8),
        ('quirk_memoryLeaveIUnchanged', ctypes.c_uint8),
        ('quirk_wrap', ctypes.c_uint8),
        ('quirk_jump', ctypes.c_uint8),
        ('quirk_logic', ctypes.c_uint8),

        # Execution state
        ('draw_occurred', ctypes.c_uint8),

        # ROM boundary (address where ROM ends)
        ('rom_end', ctypes.c_uint16),

        # --- Large fields at end ---

        # Memory (64KB) - accessed via computed addresses
        ('memory', ctypes.c_uint8 * 65536),
    ]
```

### Field Offsets

```python
OFFSET_V = 0              # V registers
OFFSET_RPL = 16           # RPL registers
OFFSET_PC = 32            # Program counter
OFFSET_I = 36             # Index register
OFFSET_STACK = 40         # Stack array
OFFSET_SP = 72            # Stack pointer
OFFSET_DELAY = 73         # Delay timer
OFFSET_SOUND = 74         # Sound timer
OFFSET_KEYS = 75          # Key state array
OFFSET_PATTERN = 91       # Audio pattern
OFFSET_PITCH = 107        # Audio pitch
OFFSET_TRAP_CODE = 108    # Trap code
OFFSET_TRAP_OPCODE = 109  # Trap opcode
# ... quirks and flags ...
OFFSET_MEMORY = ~120      # Memory array (at end)
```

---

## 6. ARM64 Code Generation

### 6.1 Register Allocation

| Register | Purpose | Notes |
|----------|---------|-------|
| X0 | SharedState pointer | Passed as first argument, never modified |
| W1 | Scratch register 0 | Volatile |
| W2 | Scratch register 1 | Volatile |
| W3 | Scratch register 2 | Volatile |
| W4 | Scratch register 3 | Volatile |
| W0 | Return value | Set just before RET |

### 6.2 Block Compilation

The compiler generates basic blocks of up to 64 instructions:

```python
def compile_block(self, memory: bytes, start_pc: int) -> bytes:
    '''Compile a basic block starting at the given PC.'''
    self.emitter.reset()
    self._memory = memory

    # Validate start_pc
    if start_pc < 0 or start_pc + 1 >= len(memory):
        raise ValueError(f'PC out of bounds: {start_pc:#x}')

    pc = start_pc
    instruction_count = 0

    while instruction_count < self.MAX_BLOCK_INSTRUCTIONS:
        # Bounds check
        if pc + 1 >= len(memory):
            self._emit_store_pc(pc)
            self.emitter.mov_imm(self.REG_RETVAL, 0)
            self.emitter.ret()
            break

        # Fetch opcode (big-endian)
        opcode = (memory[pc] << 8) | memory[pc + 1]

        # Compile the opcode
        block_ends = self._compile_opcode(opcode, pc)

        pc += 2
        instruction_count += 1

        if block_ends:
            break

    return self.emitter.get_code()
```

### 6.3 Example: Skip Instruction (3XNN)

```python
def _compile_3XNN(self, opcode: int, pc: int) -> bool:
    '''3XNN: Skip next instruction if VX == NN'''
    x = (opcode & 0x0F00) >> 8
    nn = opcode & 0x00FF
    skip_amount = self._get_skip_amount(pc)  # 2 or 4 bytes

    # Load V[x]
    self.emitter.ldrb(self.REG_SCRATCH0, self.REG_STATE, OFFSET_V + x)

    # Compare with NN
    self.emitter.cmp_imm(self.REG_SCRATCH0, nn)

    # Conditional select: if equal, skip; else, no skip
    self.emitter.mov_imm(self.REG_SCRATCH0, pc + 2)              # no skip
    self.emitter.mov_imm(self.REG_SCRATCH1, pc + 2 + skip_amount) # skip
    self.emitter.csel(self.REG_SCRATCH0, self.REG_SCRATCH1, self.REG_SCRATCH0,
                     ARM64Emitter.COND_EQ)

    self.emitter.str_w(self.REG_SCRATCH0, self.REG_STATE, OFFSET_PC)

    # End block - PC was conditionally modified
    self.emitter.mov_imm(self.REG_RETVAL, 0)
    self.emitter.ret()
    return True
```

Generated ARM64:
```asm
    ldrb    w1, [x0, #OFFSET_V+x]    ; Load V[x]
    cmp     w1, #nn                   ; Compare with NN
    mov     w1, #(pc+2)               ; Default: no skip
    mov     w2, #(pc+2+skip)          ; Skip target
    csel    w1, w2, w1, eq            ; Select based on comparison
    str     w1, [x0, #OFFSET_PC]      ; Store new PC
    mov     w0, #0                    ; Return 0 (no trap)
    ret
```

---

## 7. Trap Mechanism

### 7.1 Trap Codes

```python
class TrapCode(IntEnum):
    NONE = 0             # No trap; continue execution

    # Display operations
    DRAW = 1             # DXYN: Draw sprite
    DISPLAY = 2          # 00E0, 00CN, 00DN, 00FB, 00FC, 00FE, 00FF, FN01

    # Input operations
    WAIT_KEY = 3         # FX0A: Wait for keypress
    CHECK_KEY = 4        # EX9E, EXA1: Skip based on key state

    # Random number
    RANDOM = 5           # CXNN: Random number

    # Memory operations (quirk handling)
    STORE_REGS = 6       # FX55, 5XY2: Store registers to memory
    LOAD_REGS = 7        # FX65, 5XY3: Load registers from memory

    # Audio
    AUDIO = 8            # F002, FX3A: Audio pattern/pitch

    # Special/complex operations
    SPECIAL = 9          # F000, FX30, FX33, FX75, FX85

    # Jump with offset
    JUMP_BNNN = 10       # BNNN/BXNN: Jump with offset (SMC check)

    # Stack errors
    STACK_OVERFLOW = 253
    STACK_UNDERFLOW = 254

    # Exit
    EXIT = 255           # 00FD: Exit interpreter
```

### 7.2 Instruction Classification

**Fully JIT-compiled (Native Execution):**

| Opcode | Description |
|--------|-------------|
| `1NNN` | Jump |
| `2NNN` | Call subroutine (with stack overflow check) |
| `00EE` | Return (with stack underflow check) |
| `3XNN` | Skip if VX == NN |
| `4XNN` | Skip if VX != NN |
| `5XY0` | Skip if VX == VY |
| `9XY0` | Skip if VX != VY |
| `6XNN` | VX = NN |
| `7XNN` | VX += NN |
| `8XY0-E` | ALU operations (with quirk support) |
| `ANNN` | I = NNN |
| `FX07` | VX = delay |
| `FX15` | delay = VX |
| `FX18` | sound = VX |
| `FX1E` | I += VX |
| `FX29` | I = font[VX] |

**Trap to Python:**

| Opcode | Trap Code | Reason |
|--------|-----------|--------|
| `DXYN` | DRAW | Display object interaction |
| `00E0` | DISPLAY | Clear screen |
| `00CN/DN` | DISPLAY | Scroll up/down |
| `00FB/FC` | DISPLAY | Scroll left/right |
| `00FE/FF` | DISPLAY | Lo/hi res mode |
| `FN01` | DISPLAY | Plane select |
| `CXNN` | RANDOM | Python random number |
| `FX0A` | WAIT_KEY | Blocking input |
| `EX9E/A1` | CHECK_KEY | Key state + F000 skip handling |
| `FX55` | STORE_REGS | Quirk handling + SMC detection |
| `FX65` | LOAD_REGS | Quirk handling |
| `5XY2` | STORE_REGS | Register range store |
| `5XY3` | LOAD_REGS | Register range load |
| `BNNN` | JUMP_BNNN | SMC detection for dynamic jumps |
| `F002` | AUDIO | Audio pattern |
| `FX3A` | AUDIO | Pitch |
| `FX33` | SPECIAL | BCD + SMC detection |
| `FX30` | SPECIAL | Large font |
| `FX75/85` | SPECIAL | RPL registers |
| `F000` | SPECIAL | 16-bit I load |
| `00FD` | EXIT | Halt emulator |

---

## 8. Execution Flow

```python
def execute_next_op(self):
    '''Execute the next Chip-8 instruction.'''
    self._draw_occurred = False

    # Transfer Python state to SharedState
    transfer_state_to_dynarec(
        self._shared_state,
        self._memory,
        self._registers,
        self._stack,
        self._timers,
        self._keys,
        self._audio
    )

    pc = self._shared_state.pc

    # Check if JIT buffer needs reset
    if self._jit_memory.needs_reset():
        self.invalidate_cache()

    # Only cache blocks within ROM region
    if self._is_in_rom_region(pc):
        if pc not in self._block_cache:
            code = self._compiler.compile_block(
                bytes(self._shared_state.memory), pc
            )
            offset = self._write_code_safe(code)
            self._block_cache[pc] = offset
        offset = self._block_cache[pc]
    else:
        # Outside ROM - compile but don't cache
        code = self._compiler.compile_block(
            bytes(self._shared_state.memory), pc
        )
        offset = self._write_code_safe(code)

    # Execute native code
    block_func = self._jit_memory.get_callable(offset)
    trap_code = block_func(ctypes.byref(self._shared_state))

    # Handle trap if needed
    if trap_code != TrapCode.NONE:
        self._handle_trap(trap_code)

    # Transfer state back to Python
    transfer_state_to_python(
        self._shared_state,
        self._memory,
        self._registers,
        self._stack,
        self._timers,
        self._keys,
        self._audio
    )
```

---

## 9. File Structure

```
chipped8/core/cpu/dynarec/
├── __init__.py              # Public exports (DynarecCPU)
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

---

## 10. Platform Considerations

### 10.1 Limitations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| **ARM64 macOS only** | No Windows/Linux/Intel Mac support | Other CPU implementations work everywhere |
| **JIT entitlement may be needed** | App Store / hardened runtime issues | Works without signing in development |
| **Python ctypes overhead** | Each block call has FFI overhead | Blocks execute multiple instructions |

### 10.2 Code Signing (If Required)

For hardened runtime or App Store distribution:

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

# Sign the Python interpreter
codesign --sign - --entitlements entitlements.plist --force /path/to/python
```

For development, running unsigned Python typically works without special signing.

---

## 11. Performance Characteristics

| Factor | Impact |
|--------|--------|
| **JIT compilation overhead** | First execution of a block is slower |
| **ctypes FFI overhead** | ~1-2μs per call |
| **Block execution** | Much faster than Python interpretation |
| **Block size** | Up to 64 instructions per block |
| **Cache behavior** | ROM blocks cached; RAM blocks compiled on-demand |

**Estimated speedup**: 5-15x faster than pure interpreter for most programs.

---

## 12. Summary

The dynarec enables native ARM64 execution for Chip-8 on Apple Silicon Macs by:

1. Using **ctypes** to allocate executable memory via `mmap` with `MAP_JIT`
2. Managing W^X via **`pthread_jit_write_protect_np`**
3. Encoding ARM64 instructions as **raw bytes** in Python
4. Using a **SharedState** structure for Python/native communication
5. **Trapping** to Python for complex operations (display, input, audio)
6. Implementing **security validations** for bounds checking and SMC detection
7. Implementing the standard **`iCPU` interface** for seamless integration

The implementation is self-contained in `cpu/dynarec/` and requires no modifications to other CPU implementations or subsystems.
