"""
Security tests for all interpreter types.

These tests verify memory bounds checking, stack protection,
and other security-relevant behavior across all CPU implementations.
"""

import pytest

from .test_framework import (
    ProgramTest, run_test_program, load_test_program,
    validate_v, validate_pc, validate_i, validate_stack_len, validate_memory
)
from chipped8.core.memory import MEMORY_SIZE


# =============================================================================
# Memory Bounds Tests - All Interpreters
# =============================================================================

class TestMemoryBoundsAllInterpreters:
    """Memory bounds checking tests that apply to all interpreters."""

    def test_fx55_memory_bounds_exceeded(self, emulator):
        """FX55 (store registers) should raise IndexError when I+X >= MEMORY_SIZE."""
        cpu = emulator._cpu

        # Set I to near end of memory, then try to store 16 registers
        # I = MEMORY_SIZE - 8, storing V0-VF (16 bytes) should fail
        i_value = MEMORY_SIZE - 8
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xFF, 0x55,  # Store V0-VF to memory at I
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError):
            cpu.execute_next_op()  # FX55 - should fail

    def test_fx55_memory_bounds_edge_valid(self, emulator):
        """FX55 exactly at boundary should succeed."""
        cpu = emulator._cpu

        # Set I = MEMORY_SIZE - 16, storing V0-VF (16 bytes) should work
        i_value = MEMORY_SIZE - 16
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xFF, 0x55,  # Store V0-VF to memory at I
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I
        cpu.execute_next_op()  # FX55 - should succeed

    def test_fx65_memory_bounds_exceeded(self, emulator):
        """FX65 (load registers) should raise IndexError when I+X >= MEMORY_SIZE."""
        cpu = emulator._cpu

        # Set I to near end of memory, then try to load 16 registers
        i_value = MEMORY_SIZE - 8
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xFF, 0x65,  # Load V0-VF from memory at I
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError):
            cpu.execute_next_op()  # FX65 - should fail

    def test_fx65_memory_bounds_edge_valid(self, emulator):
        """FX65 exactly at boundary should succeed."""
        cpu = emulator._cpu

        # Set I = MEMORY_SIZE - 16, loading V0-VF (16 bytes) should work
        i_value = MEMORY_SIZE - 16
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xFF, 0x65,  # Load V0-VF from memory at I
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I
        cpu.execute_next_op()  # FX65 - should succeed

    def test_fx33_memory_bounds_exceeded(self, emulator):
        """FX33 (BCD) should raise IndexError when I+2 >= MEMORY_SIZE."""
        cpu = emulator._cpu

        # Set I to MEMORY_SIZE - 1, BCD needs 3 bytes
        i_value = MEMORY_SIZE - 1
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xF0, 0x33,  # Store BCD of V0 at I, I+1, I+2
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError):
            cpu.execute_next_op()  # FX33 - should fail

    def test_fx33_memory_bounds_edge_valid(self, emulator):
        """FX33 exactly at boundary should succeed."""
        cpu = emulator._cpu

        # Set I = MEMORY_SIZE - 3, BCD (3 bytes) should work
        i_value = MEMORY_SIZE - 3
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xF0, 0x33,  # Store BCD of V0 at I, I+1, I+2
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I
        cpu.execute_next_op()  # FX33 - should succeed

    def test_f002_audio_memory_bounds_exceeded(self, emulator):
        """F002 (load audio pattern) should raise IndexError when I+15 >= MEMORY_SIZE."""
        cpu = emulator._cpu

        # Set I to near end of memory (MEMORY_SIZE - 8), audio needs 16 bytes
        i_value = MEMORY_SIZE - 8
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xF0, 0x02,  # Load audio pattern from I
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError):
            cpu.execute_next_op()  # F002 - should fail

    def test_f002_audio_memory_bounds_edge_valid(self, emulator):
        """F002 exactly at boundary should succeed."""
        cpu = emulator._cpu

        # Set I = MEMORY_SIZE - 16, audio pattern (16 bytes) should work
        i_value = MEMORY_SIZE - 16
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0xF0, 0x02,  # Load audio pattern from I
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I
        cpu.execute_next_op()  # F002 - should succeed

    def test_5xy2_memory_bounds_exceeded(self, emulator):
        """5XY2 (store VX..VY) should raise IndexError when memory bounds exceeded."""
        cpu = emulator._cpu

        # Set I to near end of memory, store V0..VF (16 bytes)
        i_value = MEMORY_SIZE - 8
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0x50, 0xF2,  # Store V0..VF to memory at I (5XY2 with X=0, Y=F)
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError):
            cpu.execute_next_op()  # 5XY2 - should fail

    def test_5xy3_memory_bounds_exceeded(self, emulator):
        """5XY3 (load VX..VY) should raise IndexError when memory bounds exceeded."""
        cpu = emulator._cpu

        # Set I to near end of memory, load V0..VF (16 bytes)
        i_value = MEMORY_SIZE - 8
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,
            0x50, 0xF3,  # Load V0..VF from memory at I (5XY3 with X=0, Y=F)
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError):
            cpu.execute_next_op()  # 5XY3 - should fail


# =============================================================================
# Stack Protection Tests - All Interpreters
# =============================================================================

class TestStackProtectionAllInterpreters:
    """Stack overflow/underflow protection tests for all interpreters."""

    def test_stack_overflow_protection(self, emulator):
        """Stack should overflow after 16 nested calls."""
        cpu = emulator._cpu

        # Create a program that makes 17 nested calls
        # Each call instruction is 2NNN
        # We put 17 call instructions, each calling the next address
        program = []
        for i in range(17):
            addr = 0x200 + (i + 1) * 2
            program.extend([0x20 | ((addr >> 8) & 0x0F), addr & 0xFF])
        # Last instruction should be a NOP or something safe
        program.extend([0x00, 0xE0])  # Clear screen

        emulator.load_rom(bytes(program))

        # Execute 16 calls - should succeed
        for i in range(16):
            cpu.execute_next_op()

        # 17th call should fail with stack overflow
        with pytest.raises((OverflowError, ValueError), match="[Ss]tack"):
            cpu.execute_next_op()

    def test_stack_underflow_protection(self, emulator):
        """Returning with empty stack should raise error."""
        cpu = emulator._cpu

        # Just a return instruction with no prior call
        program = bytes([0x00, 0xEE])  # Return
        emulator.load_rom(program)

        with pytest.raises((ValueError, IndexError), match="[Ss]tack"):
            cpu.execute_next_op()

    def test_stack_push_pop_valid(self, emulator):
        """Valid call/return sequence should work correctly."""
        cpu = emulator._cpu

        # Call subroutine at 0x206, then return
        program = bytes([
            0x22, 0x06,  # 0x200: Call 0x206
            0x60, 0xFF,  # 0x202: V0 = 0xFF (after return)
            0x12, 0x08,  # 0x204: Jump to end
            0x61, 0xAA,  # 0x206: V1 = 0xAA (subroutine)
            0x00, 0xEE,  # 0x208: Return
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Call 0x206
        assert cpu._registers._PC == 0x206

        cpu.execute_next_op()  # V1 = 0xAA
        assert cpu._registers._V[1] == 0xAA

        cpu.execute_next_op()  # Return to 0x202
        assert cpu._registers._PC == 0x202

        cpu.execute_next_op()  # V0 = 0xFF
        assert cpu._registers._V[0] == 0xFF

    def test_stack_max_depth_valid(self, emulator):
        """Stack should handle exactly 15 levels of nesting."""
        cpu = emulator._cpu

        # Build a program with 15 nested calls then all returns
        # Each subroutine calls the next, except the last which just returns
        # Structure (4 bytes per subroutine):
        # 0x200: call 0x204, return  (sub0)
        # 0x204: call 0x208, return  (sub1)
        # ...
        # 0x238: call 0x23C, return  (sub14)
        # 0x23C: V0=0, return        (sub15 - deepest, no call)

        program = []
        base = 0x200

        # 16 subroutines (sub0 through sub15)
        for i in range(16):
            next_addr = base + (i + 1) * 4
            if i < 15:
                # Call next subroutine
                program.extend([0x20 | ((next_addr >> 8) & 0x0F), next_addr & 0xFF])
            else:
                # Deepest subroutine: benign instruction (V0 = 0)
                program.extend([0x60, 0x00])
            # Return instruction
            program.extend([0x00, 0xEE])

        emulator.load_rom(bytes(program))

        # Execute 15 calls to reach deepest nesting
        for i in range(15):
            cpu.execute_next_op()

        # Stack should have 15 entries
        assert len(cpu._stack._stack) == 15

        # Execute V0=0 at deepest level
        cpu.execute_next_op()

        # Stack still has 15 entries (V0=0 doesn't change stack)
        assert len(cpu._stack._stack) == 15

        # Execute return at deepest level (sub15 returns to sub14)
        cpu.execute_next_op()
        assert len(cpu._stack._stack) == 14

        # Execute remaining 14 returns
        for i in range(14):
            cpu.execute_next_op()

        # Stack should be empty
        assert len(cpu._stack._stack) == 0


# =============================================================================
# RPL Register Bounds Tests - All Interpreters
# =============================================================================

class TestRPLBoundsAllInterpreters:
    """RPL register bounds validation tests for all interpreters."""

    def test_fx75_stores_to_rpl(self, emulator):
        """FX75 should store V0-VX to RPL registers."""
        cpu = emulator._cpu

        program = bytes([
            0x60, 0xAA,  # V0 = 0xAA
            0x61, 0xBB,  # V1 = 0xBB
            0x62, 0xCC,  # V2 = 0xCC
            0xF2, 0x75,  # Store V0-V2 to RPL
        ])
        emulator.load_rom(program)

        for _ in range(4):
            cpu.execute_next_op()

        assert cpu._registers._RPL[0] == 0xAA
        assert cpu._registers._RPL[1] == 0xBB
        assert cpu._registers._RPL[2] == 0xCC

    def test_fx85_loads_from_rpl(self, emulator):
        """FX85 should load V0-VX from RPL registers."""
        cpu = emulator._cpu

        program = bytes([
            0x60, 0x11,  # V0 = 0x11
            0x61, 0x22,  # V1 = 0x22
            0xF1, 0x75,  # Store V0-V1 to RPL
            0x60, 0x00,  # V0 = 0 (clear)
            0x61, 0x00,  # V1 = 0 (clear)
            0xF1, 0x85,  # Load V0-V1 from RPL
        ])
        emulator.load_rom(program)

        for _ in range(6):
            cpu.execute_next_op()

        assert cpu._registers._V[0] == 0x11
        assert cpu._registers._V[1] == 0x22

    def test_fx75_max_register_index(self, emulator):
        """FX75 with X=F should store all 16 registers without error."""
        cpu = emulator._cpu

        # Initialize V0-VF
        program = bytearray()
        for i in range(16):
            program.extend([0x60 | i, i * 0x10])  # Vi = i * 0x10

        # Add FF75 to store all registers
        program.extend([0xFF, 0x75])

        emulator.load_rom(bytes(program))

        for _ in range(17):
            cpu.execute_next_op()

        # Verify all RPL registers
        for i in range(16):
            assert cpu._registers._RPL[i] == i * 0x10


# =============================================================================
# Malformed Opcode Tests - All Interpreters
# =============================================================================

class TestMalformedOpcodesAllInterpreters:
    """Tests for handling malformed or edge-case opcodes."""

    def test_5xy2_with_x_greater_than_y(self, emulator):
        """5XY2 with X > Y should handle gracefully (swap or reject)."""
        cpu = emulator._cpu

        # 5XY2 with X=5, Y=2 (reversed range)
        # Set I to valid location
        program = bytes([
            0xA6, 0x00,  # I = 0x600
            0x60, 0xAA,  # V0 = 0xAA
            0x62, 0xBB,  # V2 = 0xBB
            0x65, 0xCC,  # V5 = 0xCC
            0x55, 0x22,  # Store V5..V2 (reversed) - should handle gracefully
        ])
        emulator.load_rom(program)

        for _ in range(4):
            cpu.execute_next_op()

        # Should not crash - either swap the range or execute as-is
        cpu.execute_next_op()  # The 5XY2 instruction

        # Verify something reasonable happened (no crash)
        assert cpu._registers._PC > 0x200

    def test_5xy3_with_x_greater_than_y(self, emulator):
        """5XY3 with X > Y should handle gracefully (swap or reject)."""
        cpu = emulator._cpu

        # Pre-populate memory at 0x600
        cpu._memory._memory[0x600:0x604] = bytes([0x11, 0x22, 0x33, 0x44])

        # 5XY3 with X=5, Y=2 (reversed range)
        program = bytes([
            0xA6, 0x00,  # I = 0x600
            0x55, 0x23,  # Load V5..V2 (reversed) - should handle gracefully
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Set I

        # Should not crash
        cpu.execute_next_op()  # The 5XY3 instruction

        # Verify no crash
        assert cpu._registers._PC > 0x200


# =============================================================================
# F000 NNNN 4-byte Instruction Tests - All Interpreters
# =============================================================================

class TestF000NNNNAllInterpreters:
    """Tests for the F000 NNNN 4-byte instruction bounds checking."""

    def test_f000_nnnn_normal_operation(self, emulator):
        """F000 NNNN should load I with 16-bit address."""
        cpu = emulator._cpu

        program = bytes([
            0xF0, 0x00,  # F000
            0xAB, 0xCD,  # NNNN = 0xABCD
            0x00, 0xE0,  # Clear screen (next instruction)
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # F000 NNNN

        assert cpu._registers._I == 0xABCD
        assert cpu._registers._PC == 0x204

    def test_f000_nnnn_at_memory_boundary(self, emulator):
        """F000 NNNN near memory boundary should be handled properly."""
        cpu = emulator._cpu

        # Place F000 NNNN at a normal location - test that it works
        program = bytes([
            0xF0, 0x00,  # F000
            0xFF, 0xFE,  # NNNN = 0xFFFE (near max valid address)
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # Should work

        assert cpu._registers._I == 0xFFFE


# =============================================================================
# Skip Instruction Edge Cases - All Interpreters
# =============================================================================

class TestSkipInstructionEdgeCasesAllInterpreters:
    """Tests for skip instructions with 4-byte instructions."""

    def test_skip_over_f000_nnnn_when_equal(self, emulator):
        """Skip instruction should skip 4 bytes when next instruction is F000 NNNN."""
        cpu = emulator._cpu

        # 3XNN: Skip if VX == NN
        # V0 = 0x42, then skip if V0 == 0x42 (should skip)
        # Next instruction is F000 NNNN (4 bytes), so should skip 4 bytes
        program = bytes([
            0x60, 0x42,  # V0 = 0x42
            0x30, 0x42,  # Skip if V0 == 0x42 (should skip F000 NNNN)
            0xF0, 0x00,  # F000 (should be skipped)
            0x12, 0x34,  # NNNN = 0x1234 (should be skipped)
            0x61, 0xFF,  # V1 = 0xFF (should execute)
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # V0 = 0x42
        cpu.execute_next_op()  # Skip - should land at 0x208

        assert cpu._registers._PC == 0x208

        cpu.execute_next_op()  # V1 = 0xFF
        assert cpu._registers._V[1] == 0xFF

    def test_skip_over_normal_instruction(self, emulator):
        """Skip instruction should skip 2 bytes for normal instructions."""
        cpu = emulator._cpu

        program = bytes([
            0x60, 0x42,  # V0 = 0x42
            0x30, 0x42,  # Skip if V0 == 0x42 (should skip)
            0x61, 0xAA,  # V1 = 0xAA (should be skipped)
            0x62, 0xFF,  # V2 = 0xFF (should execute)
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # V0 = 0x42
        cpu.execute_next_op()  # Skip - should land at 0x206

        assert cpu._registers._PC == 0x206

        cpu.execute_next_op()  # V2 = 0xFF
        assert cpu._registers._V[2] == 0xFF
        assert cpu._registers._V[1] == 0  # V1 was skipped


# =============================================================================
# Address Wrapping Tests - All Interpreters
# =============================================================================

class TestAddressWrappingAllInterpreters:
    """Tests for address space wrapping behavior."""

    def test_fx1e_i_wrapping(self, emulator):
        """FX1E should wrap I to 16-bit address space."""
        cpu = emulator._cpu

        # Set I = 0xFFF0, V0 = 0x20, then I += V0 should give 0x0010 (wrapped)
        program = bytes([
            0xF0, 0x00,  # F000 NNNN
            0xFF, 0xF0,  # I = 0xFFF0
            0x60, 0x20,  # V0 = 0x20
            0xF0, 0x1E,  # I += V0
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # I = 0xFFF0
        cpu.execute_next_op()  # V0 = 0x20
        cpu.execute_next_op()  # I += V0

        # I should wrap: 0xFFF0 + 0x20 = 0x10010 -> 0x0010
        assert cpu._registers._I == 0x0010

    def test_bnnn_address_calculation(self, emulator):
        """BNNN should calculate address correctly."""
        cpu = emulator._cpu

        # V0 = 4, BNNN to 0x300 + V0 = 0x304
        # Write valid instruction at 0x304
        cpu._memory._memory[0x304:0x306] = bytes([0x61, 0xFF])  # V1 = 0xFF

        program = bytes([
            0x60, 0x04,  # V0 = 4
            0xB3, 0x00,  # Jump to 0x300 + V0 = 0x304
        ])
        emulator.load_rom(program)

        cpu.execute_next_op()  # V0 = 4
        cpu.execute_next_op()  # BNNN

        assert cpu._registers._PC == 0x304

        cpu.execute_next_op()  # V1 = 0xFF
        assert cpu._registers._V[1] == 0xFF
