# © 2025-2026 Intel Corporation
# Watchdog Timer - Timer and Interrupt Tests

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

def test_basic_timer_countdown():
    """Test basic timer countdown functionality"""
    print("\n=== Test: Basic Timer Countdown ===")
    reset_device()
    
    # Verify initial state (device starts unlocked)
    lock_val = regs.WDOGLOCK.read()
    stest.expect_equal(lock_val, 0x0, "Device should start unlocked")
    
    # Unlock device
    regs.WDOGLOCK.write(0x1ACCE551)
    
    # Set small load value for quick test
    load_value = 0x100
    regs.WDOGLOAD.write(load_value)
    
    # Verify load value
    stest.expect_equal(regs.WDOGLOAD.read(), load_value, "WDOGLOAD should store value")
    
    # Enable timer (INTEN=1)
    regs.WDOGCONTROL.write(0x1)  # INTEN=1, RESEN=0, STEP_VALUE=0 (÷1)
    
    # Counter should have reloaded
    counter_val = regs.WDOGVALUE.read()
    stest.expect_equal(counter_val, load_value, "Counter should reload on enable")
    
    # Advance time and check counter decrements
    simics.SIM_continue(100)
    counter_after = regs.WDOGVALUE.read()
    print(f"Counter after 100 cycles: {counter_after:#x}")
    stest.expect_true(counter_after < counter_val, "Counter should decrement")
    
    # Wait for interrupt
    simics.SIM_continue(load_value + 100)
    
    # Check interrupt was generated
    ris = regs.WDOGRIS.read()
    mis = regs.WDOGMIS.read()
    stest.expect_equal(ris & 0x1, 0x1, "WDOGRIS should show interrupt pending")
    stest.expect_equal(mis & 0x1, 0x1, "WDOGMIS should show masked interrupt")
    stest.expect_equal(pic_int.raised, 1, "Interrupt signal should be asserted")
    
    print("✓ Basic timer countdown test passed")

def test_interrupt_and_reset_sequence():
    """Test interrupt and reset generation sequence"""
    print("\n=== Test: Interrupt and Reset Sequence ===")
    
    # Create device
    reset_device()

    
    # Unlock device
    regs.WDOGLOCK.write(0x1ACCE551)
    
    # Set small load value
    load_value = 0x80
    regs.WDOGLOAD.write(load_value)
    
    # Enable timer with interrupt and reset enabled
    regs.WDOGCONTROL.write(0x3)  # INTEN=1, RESEN=1, STEP_VALUE=0
    
    # Wait for first timeout (interrupt)
    simics.SIM_continue(load_value + 50)
    
    # Check first timeout generated interrupt
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x1, "First timeout should generate interrupt")
    stest.expect_equal(pic_int.raised, 1, "Interrupt should be asserted")
    stest.expect_equal(pic_res.raised, 0, "Reset should NOT be asserted yet")
    
    # Wait for second timeout (reset) without clearing interrupt
    simics.SIM_continue(load_value + 50)
    
    # Check second timeout generated reset
    stest.expect_equal(pic_res.raised, 1, "Second timeout should generate reset")
    stest.expect_equal(pic_int.raised, 1, "Interrupt should still be asserted")
    
    print("✓ Interrupt and reset sequence test passed")

def test_interrupt_clear():
    """Test interrupt clearing and counter reload"""
    print("\n=== Test: Interrupt Clear and Reload ===")
    
    # Create device
    reset_device()

    
    # Unlock and configure
    regs.WDOGLOCK.write(0x1ACCE551)
    load_value = 0x100
    regs.WDOGLOAD.write(load_value)
    regs.WDOGCONTROL.write(0x1)  # INTEN=1
    
    # Wait for interrupt
    simics.SIM_continue(load_value + 50)
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x1, "Interrupt should be pending")
    stest.expect_equal(pic_int.raised, 1, "Interrupt signal should be asserted")
    
    # Clear interrupt
    regs.WDOGINTCLR.write(0xFFFFFFFF)
    
    # Check interrupt cleared
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x0, "Interrupt should be cleared")
    stest.expect_equal(regs.WDOGMIS.read() & 0x1, 0x0, "Masked interrupt should be cleared")
    stest.expect_equal(pic_int.raised, 0, "Interrupt signal should be lowered")
    
    # Check counter reloaded
    counter_val = regs.WDOGVALUE.read()
    print(f"Counter after clear: {counter_val:#x}")
    stest.expect_true(counter_val >= load_value - 10, "Counter should be reloaded near load value")
    
    print("✓ Interrupt clear test passed")

def test_clock_divider():
    """Test clock divider settings"""
    print("\n=== Test: Clock Divider ===")
    
    # Create device
    reset_device()

    
    # Unlock device
    regs.WDOGLOCK.write(0x1ACCE551)
    
    # Test divider = 1 (fastest)
    load_value = 0x200
    regs.WDOGLOAD.write(load_value)
    regs.WDOGCONTROL.write(0x1)  # INTEN=1, STEP_VALUE=000 (÷1)
    
    cycles_div1 = 300
    simics.SIM_continue(cycles_div1)
    counter_div1 = regs.WDOGVALUE.read()
    print(f"Divider ÷1 - Counter after {cycles_div1} cycles: {counter_div1:#x}")
    
    # Disable timer
    regs.WDOGCONTROL.write(0x0)
    
    # Test divider = 16 (slowest)
    regs.WDOGLOAD.write(load_value)
    regs.WDOGCONTROL.write(0x11)  # INTEN=1, STEP_VALUE=100 (÷16)
    
    cycles_div16 = 300
    simics.SIM_continue(cycles_div16)
    counter_div16 = regs.WDOGVALUE.read()
    print(f"Divider ÷16 - Counter after {cycles_div16} cycles: {counter_div16:#x}")
    
    # Calculate decrements
    decrement_div1 = load_value - counter_div1
    decrement_div16 = load_value - counter_div16
    
    print(f"Decrements: ÷1={decrement_div1}, ÷16={decrement_div16}")
    
    # Divider ÷16 should decrement ~16x slower
    # Allow for some tolerance due to timing
    ratio = decrement_div1 / max(decrement_div16, 1)
    print(f"Ratio: {ratio:.2f}")
    stest.expect_true(ratio > 10, f"Divider ÷16 should be much slower than ÷1 (ratio={ratio:.2f})")
    
    print("✓ Clock divider test passed")

def test_timer_disable():
    """Test timer can be disabled"""
    print("\n=== Test: Timer Disable ===")
    
    # Create device
    reset_device()

    
    # Unlock and start timer
    regs.WDOGLOCK.write(0x1ACCE551)
    regs.WDOGLOAD.write(0x500)
    regs.WDOGCONTROL.write(0x1)  # INTEN=1
    
    # Let it count for a bit
    simics.SIM_continue(100)
    counter_running = regs.WDOGVALUE.read()
    
    # Disable timer (INTEN=0)
    regs.WDOGCONTROL.write(0x0)
    
    # Wait and check counter doesn't change
    simics.SIM_continue(200)
    counter_stopped = regs.WDOGVALUE.read()
    
    stest.expect_equal(counter_stopped, counter_running, "Counter should not change when disabled")
    
    # No interrupt should be generated
    stest.expect_equal(regs.WDOGRIS.read() & 0x1, 0x0, "No interrupt when disabled")
    
    print("✓ Timer disable test passed")

# Run all tests
test_basic_timer_countdown()
test_interrupt_and_reset_sequence()
test_interrupt_clear()
test_clock_divider()
test_timer_disable()

print("\n=== All Timer Tests Passed ===")
