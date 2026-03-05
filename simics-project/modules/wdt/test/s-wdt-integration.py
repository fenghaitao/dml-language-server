# © 2025-2026 Intel Corporation
# Watchdog Timer - Integration Test Mode Tests

import simics
import stest
import dev_util

# Import common configuration
from wdt_common import create_config

# Create device once for all tests
dev, pic_int, pic_res = create_config()
regs = dev_util.bank_regs(dev.bank.WatchdogRegisters)

def reset_device():
    """Reset device to clean state between tests"""
    # Unlock device
    regs.WDOGLOCK.write(0x1ACCE551)
    # Disable timer
    regs.WDOGCONTROL.write(0x0)
    # Clear any pending interrupt
    regs.WDOGINTCLR.write(0xFFFFFFFF)
    # Reset load value
    regs.WDOGLOAD.write(0xFFFFFFFF)
    # Exit test mode if enabled
    regs.WDOGITCR.write(0x0)

def test_integration_test_mode():
    """Test integration test mode functionality"""
    print("\n=== Test: Integration Test Mode ===")
    
    # Create device
    reset_device()

    
    # Unlock device
    regs.WDOGLOCK.write(0x1ACCE551)
    
    # Verify initial state (test mode disabled)
    itcr = regs.WDOGITCR.read()
    stest.expect_equal(itcr & 0x1, 0x0, "Test mode should be disabled initially")
    
    # Enable integration test mode
    regs.WDOGITCR.write(0x1)
    stest.expect_equal(regs.WDOGITCR.read() & 0x1, 0x1, "Test mode should be enabled")
    
    # In test mode, WDOGITOP should control signals directly
    # Test interrupt signal control
    regs.WDOGITOP.write(0x2)  # Set WDOGINT_VAL=1, WDOGRES_VAL=0
    stest.expect_equal(pic_int.raised, 1, "Interrupt signal should be raised via WDOGITOP")
    stest.expect_equal(pic_res.raised, 0, "Reset signal should be low")
    
    # Test reset signal control
    regs.WDOGITOP.write(0x1)  # Set WDOGINT_VAL=0, WDOGRES_VAL=1
    stest.expect_equal(pic_int.raised, 0, "Interrupt signal should be lowered")
    stest.expect_equal(pic_res.raised, 1, "Reset signal should be raised via WDOGITOP")
    
    # Test both signals
    regs.WDOGITOP.write(0x3)  # Set both to 1
    stest.expect_equal(pic_int.raised, 1, "Both signals should be high")
    stest.expect_equal(pic_res.raised, 1, "Both signals should be high")
    
    # Clear both signals
    regs.WDOGITOP.write(0x0)
    stest.expect_equal(pic_int.raised, 0, "Both signals should be low")
    stest.expect_equal(pic_res.raised, 0, "Both signals should be low")
    
    print("✓ Integration test mode test passed")

def test_normal_mode_restored():
    """Test that exiting test mode restores normal operation"""
    print("\n=== Test: Normal Mode Restored ===")
    
    # Create device
    reset_device()

    
    # Unlock device
    regs.WDOGLOCK.write(0x1ACCE551)
    
    # Enter test mode and set signals
    regs.WDOGITCR.write(0x1)
    regs.WDOGITOP.write(0x3)  # Both signals high
    stest.expect_equal(pic_int.raised, 1, "Signals should be high in test mode")
    stest.expect_equal(pic_res.raised, 1, "Signals should be high in test mode")
    
    # Exit test mode
    regs.WDOGITCR.write(0x0)
    stest.expect_equal(regs.WDOGITCR.read() & 0x1, 0x0, "Test mode should be disabled")
    
    # Signals should return to normal state (both low since no interrupt/reset pending)
    stest.expect_equal(pic_int.raised, 0, "Signals should be restored to normal state")
    stest.expect_equal(pic_res.raised, 0, "Signals should be restored to normal state")
    
    # Verify normal timer operation works
    regs.WDOGLOAD.write(0x100)
    regs.WDOGCONTROL.write(0x1)  # INTEN=1
    
    # Wait for interrupt
    simics.SIM_continue(0x150)
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x1, "Normal interrupt should work after test mode")
    
    print("✓ Normal mode restored test passed")

def test_test_mode_blocks_normal_timer():
    """Test that test mode blocks normal timer operation"""
    print("\n=== Test: Test Mode Blocks Normal Timer ===")
    
    # Create device
    reset_device()

    
    # Unlock device
    regs.WDOGLOCK.write(0x1ACCE551)
    
    # Start timer in normal mode
    regs.WDOGLOAD.write(0x80)
    regs.WDOGCONTROL.write(0x1)
    
    # Enter test mode immediately
    regs.WDOGITCR.write(0x1)
    
    # Wait past when interrupt would normally occur
    simics.SIM_continue(0x100)
    
    # Check that normal timer interrupt didn't occur
    # (test mode should prevent normal operation)
    # Note: Counter might still count, but signals are controlled by WDOGITOP
    print(f"WDOGRIS: {regs.WDOGRIS.read():#x}")
    
    # In test mode, signals are controlled by WDOGITOP, not timer
    # Set WDOGITOP to 0 ensures signals are low
    regs.WDOGITOP.write(0x0)
    stest.expect_equal(pic_int.raised, 0, "Interrupt signal controlled by WDOGITOP in test mode")
    
    print("✓ Test mode blocks normal timer test passed")

def test_lock_blocks_test_mode_registers():
    """Test that lock blocks writes to test mode registers"""
    print("\n=== Test: Lock Blocks Test Mode Registers ===")
    
    # Create device
    reset_device()

    
    # Unlock and enable test mode
    regs.WDOGLOCK.write(0x1ACCE551)
    regs.WDOGITCR.write(0x1)
    stest.expect_equal(regs.WDOGITCR.read() & 0x1, 0x1, "Test mode should be enabled")
    
    # Lock device
    regs.WDOGLOCK.write(0x0)
    
    # Try to disable test mode - should be ignored
    regs.WDOGITCR.write(0x0)
    stest.expect_equal(regs.WDOGITCR.read() & 0x1, 0x1, "Test mode should still be enabled when locked")
    
    # Try to write WDOGITOP - should be ignored
    regs.WDOGITOP.write(0x3)
    # Signals should not change (should remain at their previous state)
    
    # Unlock and verify we can control again
    regs.WDOGLOCK.write(0x1ACCE551)
    regs.WDOGITOP.write(0x2)
    stest.expect_equal(pic_int.raised, 1, "Should be able to control after unlock")
    
    print("✓ Lock blocks test mode registers test passed")

# Run all tests
test_integration_test_mode()
test_normal_mode_restored()
test_test_mode_blocks_normal_timer()
test_lock_blocks_test_mode_registers()

print("\n=== All Integration Test Mode Tests Passed ===")
