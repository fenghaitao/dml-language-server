# © 2025-2026 Intel Corporation
# Watchdog Timer - Lock Protection Tests

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

def test_lock_protection():
    """Test lock protection mechanism"""
    print("\n=== Test: Lock Protection ===")
    
    # Create device
    reset_device()

    
    # Device should start unlocked
    lock_status = regs.WDOGLOCK.read()
    stest.expect_equal(lock_status, 0x0, "Device should start unlocked (returns 0x0)")
    
    # Write to WDOGLOAD should succeed when unlocked
    regs.WDOGLOCK.write(0x1ACCE551)  # Ensure unlocked
    regs.WDOGLOAD.write(0x12345678)
    stest.expect_equal(regs.WDOGLOAD.read(), 0x12345678, "Write should succeed when unlocked")
    
    # Lock device by writing non-magic value
    regs.WDOGLOCK.write(0xDEADBEEF)
    lock_status = regs.WDOGLOCK.read()
    stest.expect_equal(lock_status, 0x1, "Device should be locked (returns 0x1)")
    
    # Try to write to WDOGLOAD when locked - should be ignored
    regs.WDOGLOAD.write(0x87654321)
    stest.expect_equal(regs.WDOGLOAD.read(), 0x12345678, "Write should be ignored when locked")
    
    # Unlock device again
    regs.WDOGLOCK.write(0x1ACCE551)
    lock_status = regs.WDOGLOCK.read()
    stest.expect_equal(lock_status, 0x0, "Device should be unlocked (returns 0x0)")
    
    # Write should succeed again
    regs.WDOGLOAD.write(0xABCDEF00)
    stest.expect_equal(regs.WDOGLOAD.read(), 0xABCDEF00, "Write should succeed after unlock")
    
    print("✓ Lock protection test passed")

def test_lock_blocks_control_register():
    """Test that lock blocks WDOGCONTROL writes"""
    print("\n=== Test: Lock Blocks WDOGCONTROL ===")
    
    # Create device
    reset_device()

    
    # Unlock and set control register
    regs.WDOGLOCK.write(0x1ACCE551)
    regs.WDOGCONTROL.write(0x5)  # INTEN=1, RESEN=1
    stest.expect_equal(regs.WDOGCONTROL.read(), 0x5, "Control register should be set")
    
    # Lock device
    regs.WDOGLOCK.write(0x0)
    
    # Try to modify control register - should be ignored
    regs.WDOGCONTROL.write(0x0)
    stest.expect_equal(regs.WDOGCONTROL.read(), 0x5, "Control register should not change when locked")
    
    print("✓ Lock blocks control register test passed")

def test_lock_blocks_interrupt_clear():
    """Test that lock blocks WDOGINTCLR writes"""
    print("\n=== Test: Lock Blocks WDOGINTCLR ===")
    
    # Create device
    reset_device()

    
    # Unlock, configure, and generate interrupt
    regs.WDOGLOCK.write(0x1ACCE551)
    regs.WDOGLOAD.write(0x50)
    regs.WDOGCONTROL.write(0x1)  # INTEN=1
    
    # Wait for interrupt
    simics.SIM_continue(0x100)
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x1, "Interrupt should be pending")
    
    # Lock device
    regs.WDOGLOCK.write(0x0)
    
    # Try to clear interrupt - should be ignored
    regs.WDOGINTCLR.write(0xFFFFFFFF)
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x1, "Interrupt should still be pending when locked")
    
    # Unlock and clear interrupt
    regs.WDOGLOCK.write(0x1ACCE551)
    regs.WDOGINTCLR.write(0xFFFFFFFF)
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x0, "Interrupt should be cleared after unlock")
    
    print("✓ Lock blocks interrupt clear test passed")

def test_wdogvalue_readable_when_locked():
    """Test that WDOGVALUE is readable regardless of lock state"""
    print("\n=== Test: WDOGVALUE Readable When Locked ===")
    
    # Create device
    reset_device()

    
    # Start timer
    regs.WDOGLOCK.write(0x1ACCE551)
    regs.WDOGLOAD.write(0x1000)
    regs.WDOGCONTROL.write(0x1)
    
    # Let timer run
    simics.SIM_continue(100)
    
    # Lock device
    regs.WDOGLOCK.write(0x0)
    
    # Read WDOGVALUE - should work even when locked
    value1 = regs.WDOGVALUE.read()
    simics.SIM_continue(50)
    value2 = regs.WDOGVALUE.read()
    
    print(f"WDOGVALUE while locked: {value1:#x} -> {value2:#x}")
    stest.expect_true(value2 < value1, "Counter should decrement even when locked")
    
    print("✓ WDOGVALUE readable when locked test passed")

def test_lock_always_writable():
    """Test that WDOGLOCK itself is always writable"""
    print("\n=== Test: WDOGLOCK Always Writable ===")
    
    # Create device
    reset_device()

    
    # Lock device
    regs.WDOGLOCK.write(0x0)
    stest.expect_equal(regs.WDOGLOCK.read(), 0x1, "Device should be locked")
    
    # WDOGLOCK should still be writable even when locked
    regs.WDOGLOCK.write(0x1ACCE551)
    stest.expect_equal(regs.WDOGLOCK.read(), 0x0, "Device should be unlocked")
    
    print("✓ WDOGLOCK always writable test passed")

# Run all tests
test_lock_protection()
test_lock_blocks_control_register()
test_lock_blocks_interrupt_clear()
test_wdogvalue_readable_when_locked()
test_lock_always_writable()

print("\n=== All Lock Protection Tests Passed ===")
