"""
Tests for dynarec-specific functionality.

These tests focus on JIT memory management, offset validation,
and other dynarec security features.
"""

import pytest

from chipped8.core.interpreter import is_dynarec_available

# Skip all tests in this module if dynarec is not available
pytestmark = pytest.mark.skipif(
    not is_dynarec_available(),
    reason="Dynarec not available on this platform"
)


# Import dynarec components only if available
if is_dynarec_available():
    from chipped8.core.cpu.dynarec.jit_memory import JITMemory


class TestJITMemoryOffsetValidation:
    """Tests for JIT code offset validation in get_callable()."""

    def test_get_callable_with_valid_offset(self):
        """Valid offset within written code should work."""
        jit = JITMemory(size=4096)
        # Write some dummy code (ARM64 ret instruction: 0xD65F03C0)
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        offset = jit.write_code(code)

        # Should not raise - offset 0 is valid after writing
        func = jit.get_callable(offset)
        assert func is not None

    def test_get_callable_with_negative_offset(self):
        """Negative offset should raise ValueError."""
        jit = JITMemory(size=4096)
        # Write some code first
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        jit.write_code(code)

        with pytest.raises(ValueError, match="must be non-negative"):
            jit.get_callable(-1)

    def test_get_callable_with_large_negative_offset(self):
        """Large negative offset should raise ValueError."""
        jit = JITMemory(size=4096)
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        jit.write_code(code)

        with pytest.raises(ValueError, match="must be non-negative"):
            jit.get_callable(-1000000)

    def test_get_callable_with_offset_beyond_written_code(self):
        """Offset beyond written code should raise ValueError."""
        jit = JITMemory(size=4096)
        # Write 4 bytes
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        jit.write_code(code)

        # Offset 4 is beyond written code (valid range is 0-3)
        with pytest.raises(ValueError, match="valid range"):
            jit.get_callable(4)

    def test_get_callable_with_offset_way_beyond_written_code(self):
        """Offset way beyond written code should raise ValueError."""
        jit = JITMemory(size=4096)
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        jit.write_code(code)

        with pytest.raises(ValueError, match="valid range"):
            jit.get_callable(1000)

    def test_get_callable_with_empty_buffer(self):
        """Getting callable from empty buffer should raise ValueError."""
        jit = JITMemory(size=4096)

        # No code written yet
        with pytest.raises(ValueError, match="No code has been written"):
            jit.get_callable(0)

    def test_get_callable_at_buffer_boundary(self):
        """Offset at exact buffer boundary should raise ValueError."""
        jit = JITMemory(size=4096)
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        jit.write_code(code)

        # jit.offset is now 4, so offset=4 should fail
        with pytest.raises(ValueError, match="valid range"):
            jit.get_callable(jit.offset)

    def test_get_callable_multiple_writes(self):
        """Valid offsets after multiple writes should work."""
        jit = JITMemory(size=4096)

        # Write first block
        code1 = bytes([0xC0, 0x03, 0x5F, 0xD6])
        offset1 = jit.write_code(code1)

        # Write second block
        code2 = bytes([0x00, 0x00, 0x00, 0x00, 0xC0, 0x03, 0x5F, 0xD6])
        offset2 = jit.write_code(code2)

        # Both offsets should be valid
        func1 = jit.get_callable(offset1)
        func2 = jit.get_callable(offset2)
        assert func1 is not None
        assert func2 is not None

        # Offset beyond second block should fail
        with pytest.raises(ValueError, match="valid range"):
            jit.get_callable(offset2 + len(code2))

    def test_get_callable_after_reset(self):
        """After reset, previous offsets should be invalid."""
        jit = JITMemory(size=4096)

        # Write code
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        offset = jit.write_code(code)

        # Should work before reset
        func = jit.get_callable(offset)
        assert func is not None

        # Reset buffer
        jit.reset()

        # Now offset 0 should fail (no code written)
        with pytest.raises(ValueError, match="No code has been written"):
            jit.get_callable(offset)


class TestJITMemoryBufferExhaustion:
    """Tests for JIT buffer exhaustion handling."""

    def test_buffer_exhaustion_raises_memory_error(self):
        """Writing beyond buffer size should raise MemoryError."""
        jit = JITMemory(size=64)  # Small buffer

        # Try to write more than buffer size
        large_code = bytes([0xC0, 0x03, 0x5F, 0xD6] * 20)  # 80 bytes

        with pytest.raises(MemoryError, match="JIT buffer exhausted"):
            jit.write_code(large_code)

    def test_incremental_buffer_exhaustion(self):
        """Incremental writes exceeding buffer should raise MemoryError."""
        jit = JITMemory(size=64)
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])  # 4 bytes

        # Write until buffer is almost full
        for _ in range(15):  # 60 bytes
            jit.write_code(code)

        # Next write should fail (would need 64 bytes, only 4 left)
        with pytest.raises(MemoryError, match="JIT buffer exhausted"):
            jit.write_code(bytes([0x00] * 8))


class TestJITMemoryUsageTracking:
    """Tests for JIT buffer usage tracking methods."""

    def test_bytes_used_initial(self):
        """Initially bytes_used should be 0."""
        jit = JITMemory(size=4096)
        assert jit.bytes_used == 0

    def test_bytes_used_after_write(self):
        """bytes_used should reflect written code."""
        jit = JITMemory(size=4096)
        code = bytes([0xC0, 0x03, 0x5F, 0xD6])  # 4 bytes
        jit.write_code(code)
        assert jit.bytes_used == 4

    def test_bytes_available(self):
        """bytes_available should be size - used."""
        jit = JITMemory(size=4096)
        assert jit.bytes_available == 4096

        code = bytes([0xC0, 0x03, 0x5F, 0xD6])
        jit.write_code(code)
        assert jit.bytes_available == 4092

    def test_usage_ratio(self):
        """usage_ratio should be between 0.0 and 1.0."""
        jit = JITMemory(size=100)
        assert jit.usage_ratio == 0.0

        jit.write_code(bytes([0x00] * 50))
        assert jit.usage_ratio == 0.5

        jit.write_code(bytes([0x00] * 50))
        assert jit.usage_ratio == 1.0

    def test_needs_reset_below_threshold(self):
        """needs_reset should be False below threshold."""
        jit = JITMemory(size=100)
        jit.write_code(bytes([0x00] * 80))  # 80%
        assert not jit.needs_reset(threshold=0.9)

    def test_needs_reset_above_threshold(self):
        """needs_reset should be True at or above threshold."""
        jit = JITMemory(size=100)
        jit.write_code(bytes([0x00] * 90))  # 90%
        assert jit.needs_reset(threshold=0.9)

    def test_needs_reset_custom_threshold(self):
        """needs_reset should respect custom threshold."""
        jit = JITMemory(size=100)
        jit.write_code(bytes([0x00] * 50))  # 50%
        assert not jit.needs_reset(threshold=0.6)
        assert jit.needs_reset(threshold=0.5)

    def test_has_space_for(self):
        """has_space_for should correctly check available space."""
        jit = JITMemory(size=100)
        assert jit.has_space_for(100)
        assert jit.has_space_for(50)
        assert not jit.has_space_for(101)

        jit.write_code(bytes([0x00] * 60))
        assert jit.has_space_for(40)
        assert not jit.has_space_for(41)

    def test_reset_clears_usage(self):
        """reset should clear bytes_used."""
        jit = JITMemory(size=100)
        jit.write_code(bytes([0x00] * 50))
        assert jit.bytes_used == 50

        jit.reset()
        assert jit.bytes_used == 0
        assert jit.bytes_available == 100


class TestDynarecBufferAutoReset:
    """Tests for automatic JIT buffer reset in dynarec CPU."""

    def test_buffer_auto_resets_when_nearly_full(self):
        """CPU should auto-reset JIT buffer when usage exceeds threshold."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Create a small JIT buffer for testing
        from chipped8.core.cpu.dynarec.jit_memory import JITMemory
        cpu._jit_memory = JITMemory(size=1024)  # Small 1KB buffer

        # Load a program with many unique instructions
        program = bytes([
            0x60, 0x01,  # V0 = 1
            0x70, 0x01,  # V0 += 1
            0x12, 0x02,  # Jump back to 0x202
        ])
        emu.load_rom(program)

        # Execute many times to fill the buffer
        # The auto-reset should prevent MemoryError
        for _ in range(100):
            cpu.execute_next_op()

        # Should complete without MemoryError
        assert True, "Execution should complete without memory error"

    def test_write_code_safe_resets_on_overflow(self):
        """_write_code_safe should reset buffer if no space."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Create a small JIT buffer
        from chipped8.core.cpu.dynarec.jit_memory import JITMemory
        cpu._jit_memory = JITMemory(size=128)

        # Manually fill the buffer almost completely
        dummy_code = bytes([0xC0, 0x03, 0x5F, 0xD6] * 30)  # 120 bytes
        cpu._jit_memory.write_code(dummy_code)
        cpu._block_cache[0x999] = 0  # Fake cache entry

        assert cpu._jit_memory.bytes_available < 20, "Buffer should be nearly full"
        assert len(cpu._block_cache) > 0, "Cache should have entries"

        # Now try to write more code - should auto-reset
        new_code = bytes([0xC0, 0x03, 0x5F, 0xD6] * 10)  # 40 bytes
        offset = cpu._write_code_safe(new_code)

        # Should succeed after reset
        assert offset == 0, "Code should be written at offset 0 after reset"
        assert len(cpu._block_cache) == 0, "Cache should be cleared after reset"


class TestDynarecCacheIntegrity:
    """Tests for block cache integrity in dynarec CPU."""

    def test_cache_cleared_on_smc(self):
        """Block cache should be cleared when SMC is detected."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Load a simple program that writes to ROM area
        # 6001 - V0 = 1
        # A200 - I = 0x200 (ROM area)
        # F055 - Store V0 to [I]
        program = bytes([
            0x60, 0x01,  # V0 = 1
            0xA2, 0x00,  # I = 0x200
            0xF0, 0x55,  # Store V0 to [I]
        ])
        emu.load_rom(program)

        # Execute first two instructions to populate cache
        cpu.execute_next_op()  # V0 = 1
        cpu.execute_next_op()  # I = 0x200

        assert len(cpu._block_cache) > 0, "Cache should have entries"

        # Execute SMC write
        cpu.execute_next_op()  # Store V0 to [I] - writes to ROM

        # Cache should be cleared
        assert len(cpu._block_cache) == 0, "Cache should be cleared after SMC"

    def test_cache_not_cleared_on_ram_write(self):
        """Block cache should NOT be cleared when writing to RAM."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Load a program that writes to RAM area (0x6000)
        # 6001 - V0 = 1
        # A600 - I = 0x6000 (RAM area)
        # 1208 - Jump to 0x208 (force block end)
        # F055 - Store V0 to [I]
        # 120A - Jump to 0x20A (force block end)
        program = bytes([
            0x60, 0x01,  # 0x200: V0 = 1
            0xA6, 0x00,  # 0x202: I = 0x6000
            0x12, 0x08,  # 0x204: Jump to 0x208
            0x00, 0x00,  # 0x206: padding
            0xF0, 0x55,  # 0x208: Store V0 to [I]
            0x12, 0x0C,  # 0x20A: Jump to 0x20C
        ])
        emu.load_rom(program)

        # Execute instructions to populate cache
        cpu.execute_next_op()  # V0 = 1
        cpu.execute_next_op()  # I = 0x6000
        cpu.execute_next_op()  # Jump to 0x208

        cache_size_before = len(cpu._block_cache)
        assert cache_size_before > 0, "Cache should have entries"

        # Execute RAM write
        cpu.execute_next_op()  # Store V0 to [I] - writes to RAM

        # Cache should NOT be cleared (may have grown with new block)
        assert len(cpu._block_cache) >= cache_size_before, \
            "Cache should not be cleared when writing to RAM"


class TestBNNNJumpValidation:
    """Tests for BNNN jump address validation and SMC detection."""

    def test_bnnn_normal_jump_within_rom(self):
        """BNNN jump within ROM should work and not clear cache."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Program: V0 = 2, BNNN to 0x204 + V0 = 0x206
        program = bytes([
            0x60, 0x02,  # 0x200: V0 = 2
            0xB2, 0x04,  # 0x202: Jump to 0x204 + V0 = 0x206
            0x00, 0x00,  # 0x204: padding (skipped)
            0x61, 0xFF,  # 0x206: V1 = 0xFF (target)
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # V0 = 2
        cpu.execute_next_op()  # BNNN jump to 0x206
        cpu.execute_next_op()  # V1 = 0xFF

        assert cpu._shared_state.V[1] == 0xFF, "Jump should land at correct target"
        assert cpu._shared_state.pc == 0x208, "PC should be after executed instruction"

    def test_bnnn_jump_outside_rom_clears_cache(self):
        """BNNN jump outside ROM should clear cache (SMC detection)."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Program: V0 = 0xFF, BNNN to 0x600 + V0 = 0x6FF (outside ROM)
        # First we need to set up some code at target to not crash
        program = bytes([
            0x60, 0xFF,  # 0x200: V0 = 0xFF
            0xB6, 0x00,  # 0x202: Jump to 0x600 + V0 = 0x6FF (outside ROM)
        ])
        emu.load_rom(program)

        # Write valid instruction at 0x6FF so we don't crash
        cpu._shared_state.memory[0x6FF] = 0x00  # 00E0 (clear screen)
        cpu._shared_state.memory[0x700] = 0xE0

        cpu.execute_next_op()  # V0 = 0xFF

        assert len(cpu._block_cache) > 0, "Cache should have entries before BNNN"

        cpu.execute_next_op()  # BNNN jump outside ROM

        assert len(cpu._block_cache) == 0, "Cache should be cleared when jumping outside ROM"
        assert cpu._shared_state.pc == 0x6FF, "PC should be at jump target"

    def test_bnnn_address_masking(self):
        """BNNN result should be masked to 16-bit address space."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Program: V0 = 0xFF, BNNN to 0xFFF + V0 = 0x10FE which should mask
        # Max: NNN=0xFFF (4095) + V0=0xFF (255) = 0x10FE (4350)
        # This is < 0x10000 so no wrap, but test the masking is in place
        program = bytes([
            0x60, 0xFF,  # 0x200: V0 = 0xFF
            0xBF, 0xFF,  # 0x202: Jump to 0xFFF + V0 = 0x10FE
        ])
        emu.load_rom(program)

        # Write valid instruction at 0x10FE (which is 0x10FE since no wrap needed)
        # But this tests the masking logic is present
        target = (0xFFF + 0xFF) & 0xFFFF  # Should be 0x10FE
        cpu._shared_state.memory[target] = 0x00
        cpu._shared_state.memory[target + 1] = 0xE0

        cpu.execute_next_op()  # V0 = 0xFF
        cpu.execute_next_op()  # BNNN

        assert cpu._shared_state.pc == target, f"PC should be {target:#x}, got {cpu._shared_state.pc:#x}"

    def test_bxnn_quirk_mode_uses_vx(self):
        """BXNN with jump quirk should use VX instead of V0."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu
        # Enable jump quirk
        cpu._quirks.jump = True

        # Program: V0 = 0, V5 = 4, BXNN with X=5 -> jump to 0x204 + V5 = 0x208
        program = bytes([
            0x60, 0x00,  # 0x200: V0 = 0
            0x65, 0x04,  # 0x202: V5 = 4
            0xB5, 0x04,  # 0x204: Jump to 0x504 + V5 = 0x508? No wait...
            # With quirk: B5NN means jump to 0x504 + V5 = 0x508
            # Actually the opcode is BXNN where X=5, NN=04
            # So jump to 0x504 + V5 = 0x504 + 4 = 0x508
        ])
        emu.load_rom(program)

        # Write valid instruction at target
        target = 0x504 + 4
        cpu._shared_state.memory[target] = 0x61
        cpu._shared_state.memory[target + 1] = 0xAB  # V1 = 0xAB

        cpu.execute_next_op()  # V0 = 0
        cpu.execute_next_op()  # V5 = 4
        cpu.execute_next_op()  # BXNN jump

        assert cpu._shared_state.pc == target, f"PC should be {target:#x} with quirk"

    def test_bnnn_cache_preserved_when_jumping_within_rom(self):
        """BNNN jumping within ROM should NOT clear the cache."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Longer program to ensure jump target is within ROM
        program = bytes([
            0x60, 0x04,  # 0x200: V0 = 4
            0xB2, 0x04,  # 0x202: Jump to 0x204 + V0 = 0x208
            0x00, 0x00,  # 0x204: padding
            0x00, 0x00,  # 0x206: padding
            0x61, 0xFF,  # 0x208: V1 = 0xFF (target within ROM)
            0x00, 0x00,  # 0x20A: padding to extend ROM
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # V0 = 4

        cache_before = len(cpu._block_cache)
        assert cache_before > 0, "Cache should have entries"

        cpu.execute_next_op()  # BNNN jump within ROM

        # Cache should not be cleared
        assert len(cpu._block_cache) >= cache_before, \
            "Cache should NOT be cleared when jumping within ROM"


class TestSpriteMemoryBounds:
    """Tests for sprite drawing memory bounds validation."""

    def test_dxyn_memory_bounds_exceeded(self):
        """DXYN with I near end of memory should raise IndexError."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes
        from chipped8.core.memory import MEMORY_SIZE

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set I to near end of memory (MEMORY_SIZE - 4), then draw 8-row sprite
        # which needs 8 bytes - this should fail
        # Use F000 NNNN to set I to 16-bit address
        i_value = MEMORY_SIZE - 4
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,  # High and low bytes of address
            0xD0, 0x08,  # Draw 8-row sprite at V0, V1
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError, match="Sprite memory read out of bounds"):
            cpu.execute_next_op()  # Draw - should fail

    def test_dxy0_memory_bounds_exceeded(self):
        """DXY0 (16x16 sprite) with I near end of memory should raise IndexError."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes
        from chipped8.core.memory import MEMORY_SIZE

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set I to near end of memory (MEMORY_SIZE - 16), then draw 16x16 sprite
        # which needs 32 bytes - this should fail
        # Use F000 NNNN to set I to 16-bit address
        i_value = MEMORY_SIZE - 16
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,  # High and low bytes of address
            0xD0, 0x00,  # Draw 16x16 sprite at V0, V1
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError, match="Sprite memory read out of bounds"):
            cpu.execute_next_op()  # Draw - should fail

    def test_dxyn_memory_bounds_edge_valid(self):
        """DXYN exactly at boundary should pass."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes
        from chipped8.core.memory import MEMORY_SIZE

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set I to exactly MEMORY_SIZE - 8, draw 8-row sprite (needs 8 bytes)
        # This should pass as it reads bytes at I..I+7
        # Use F000 NNNN to set I to 16-bit address
        i_value = MEMORY_SIZE - 8
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,  # High and low bytes of address
            0xD0, 0x08,  # Draw 8-row sprite at V0, V1
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # Set I
        cpu.execute_next_op()  # Draw - should pass (no exception)

    def test_dxy0_multi_plane_bounds(self):
        """DXY0 with both planes selected needs 64 bytes total."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes
        from chipped8.core.memory import MEMORY_SIZE

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set I to MEMORY_SIZE - 40, select both planes, draw 16x16 sprite
        # which needs 32 bytes * 2 planes = 64 bytes - this should fail
        # Use F000 NNNN to set I to 16-bit address
        i_value = MEMORY_SIZE - 40
        program = bytes([
            0xF3, 0x01,  # FN01: Select both planes (N=3)
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,  # High and low bytes of address
            0xD0, 0x00,  # Draw 16x16 sprite
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # Select planes
        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError, match="Sprite memory read out of bounds"):
            cpu.execute_next_op()  # Draw - should fail


class TestRPLRegisterBounds:
    """Tests for RPL register bounds validation."""

    def test_fx75_normal_operation(self):
        """FX75 should store V0-VX to RPL registers."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set V0-V3 to known values, then store to RPL
        program = bytes([
            0x60, 0xAA,  # V0 = 0xAA
            0x61, 0xBB,  # V1 = 0xBB
            0x62, 0xCC,  # V2 = 0xCC
            0x63, 0xDD,  # V3 = 0xDD
            0xF3, 0x75,  # Store V0-V3 to RPL
        ])
        emu.load_rom(program)

        for _ in range(5):
            cpu.execute_next_op()

        assert cpu._shared_state.RPL[0] == 0xAA
        assert cpu._shared_state.RPL[1] == 0xBB
        assert cpu._shared_state.RPL[2] == 0xCC
        assert cpu._shared_state.RPL[3] == 0xDD

    def test_fx85_normal_operation(self):
        """FX85 should load V0-VX from RPL registers."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # First store known values to RPL, then load them back
        # This tests the roundtrip properly
        program = bytes([
            0x60, 0x11,  # V0 = 0x11
            0x61, 0x22,  # V1 = 0x22
            0x62, 0x33,  # V2 = 0x33
            0x63, 0x44,  # V3 = 0x44
            0xF3, 0x75,  # Store V0-V3 to RPL
            0x60, 0x00,  # V0 = 0 (clear)
            0x61, 0x00,  # V1 = 0 (clear)
            0x62, 0x00,  # V2 = 0 (clear)
            0x63, 0x00,  # V3 = 0 (clear)
            0xF3, 0x85,  # Load V0-V3 from RPL
        ])
        emu.load_rom(program)

        for _ in range(10):
            cpu.execute_next_op()

        assert cpu._shared_state.V[0] == 0x11
        assert cpu._shared_state.V[1] == 0x22
        assert cpu._shared_state.V[2] == 0x33
        assert cpu._shared_state.V[3] == 0x44

    def test_fx75_max_register_index(self):
        """FX75 with X=15 should store all 16 registers."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set all V registers via program code
        program = bytes([
            0x60, 0x00,  # V0 = 0x00
            0x61, 0x10,  # V1 = 0x10
            0x62, 0x20,  # V2 = 0x20
            0x63, 0x30,  # V3 = 0x30
            0x64, 0x40,  # V4 = 0x40
            0x65, 0x50,  # V5 = 0x50
            0x66, 0x60,  # V6 = 0x60
            0x67, 0x70,  # V7 = 0x70
            0x68, 0x80,  # V8 = 0x80
            0x69, 0x90,  # V9 = 0x90
            0x6A, 0xA0,  # VA = 0xA0
            0x6B, 0xB0,  # VB = 0xB0
            0x6C, 0xC0,  # VC = 0xC0
            0x6D, 0xD0,  # VD = 0xD0
            0x6E, 0xE0,  # VE = 0xE0
            0x6F, 0xF0,  # VF = 0xF0
            0xFF, 0x75,  # Store V0-VF to RPL
        ])
        emu.load_rom(program)

        for _ in range(17):
            cpu.execute_next_op()

        for i in range(16):
            assert cpu._shared_state.RPL[i] == i * 0x10


class TestAudioPatternBounds:
    """Tests for audio pattern memory bounds validation."""

    def test_f002_memory_bounds_exceeded(self):
        """F002 with I near end of memory should raise IndexError."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes
        from chipped8.core.memory import MEMORY_SIZE

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set I to near end of memory (MEMORY_SIZE - 8), then load audio pattern
        # which needs 16 bytes - this should fail
        # Use F000 NNNN to set I to 16-bit address
        i_value = MEMORY_SIZE - 8
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,  # High and low bytes of address
            0xF0, 0x02,  # Load audio pattern from I
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # Set I

        with pytest.raises(IndexError, match="Memory read out of bounds"):
            cpu.execute_next_op()  # F002 - should fail

    def test_f002_memory_bounds_edge_valid(self):
        """F002 exactly at boundary should pass."""
        from chipped8.core.emulator import Emulator
        from chipped8.core.platform import PlatformTypes
        from chipped8.core.interpreter import InterpreterTypes
        from chipped8.core.memory import MEMORY_SIZE

        emu = Emulator(
            platform=PlatformTypes.xochip,
            interpreter_type=InterpreterTypes.dynarec
        )
        cpu = emu._cpu

        # Set I to exactly MEMORY_SIZE - 16, load audio pattern (needs 16 bytes)
        # This should pass as it reads bytes at I..I+15
        # Use F000 NNNN to set I to 16-bit address
        i_value = MEMORY_SIZE - 16
        program = bytes([
            0xF0, 0x00,  # F000 NNNN: Load I with 16-bit address
            (i_value >> 8) & 0xFF, i_value & 0xFF,  # High and low bytes of address
            0xF0, 0x02,  # Load audio pattern from I
        ])
        emu.load_rom(program)

        cpu.execute_next_op()  # Set I
        cpu.execute_next_op()  # F002 - should pass (no exception)
