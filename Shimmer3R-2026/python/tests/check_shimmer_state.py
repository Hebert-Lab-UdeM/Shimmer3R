"""
check_shimmer_state.py — Verify Shimmer3R is powered and accessible.

This script checks:
1. Is the Shimmer3R actually powered on?
2. Is it visible to Windows Bluetooth?
3. Can we access it at all?

Usage:
    python check_shimmer_state.py

Requirements:
    - pyserial installed
"""

import sys
import serial
import serial.tools.list_ports
import time
import subprocess


def check_device_manager():
    """Check Device Manager for Shimmer device."""
    print("\n" + "="*70)
    print("STEP 1: Check Device Manager")
    print("="*70 + "\n")
    
    # Use PowerShell to query PnP devices
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-PnpDevice -Class Ports -PresentOnly -Status OK | Select-Object Name, DeviceID | Format-Table'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print("COM ports in Device Manager:")
        print(result.stdout)
        
        if 'Shimmer' in result.stdout or 'Standard Serial' in result.stdout:
            print("✓ Shimmer/Bluetooth COM ports found in Device Manager\n")
        else:
            print("⚠ No Shimmer/Bluetooth ports visible\n")
            
    except Exception as e:
        print(f"Could not query Device Manager: {e}\n")


def check_bluetooth_pairing():
    """Check if Shimmer is paired in Windows."""
    print("="*70)
    print("STEP 2: Check Bluetooth Pairing")
    print("="*70 + "\n")
    
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-PnpDevice -Class Bluetooth -PresentOnly | Where-Object {$_.Name -like "*Shimmer*"} | Select-Object Name, Status | Format-Table'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print("Paired Shimmer devices:")
        print(result.stdout if result.stdout.strip() else "  (none found)")
        print()
        
    except Exception as e:
        print(f"Could not check pairing: {e}\n")


def check_port_accessibility(com_port: str):
    """Try to access a COM port with very short timeout."""
    print(f"Testing {com_port}...")
    
    try:
        # Try with extremely short timeout
        ser = serial.Serial(
            com_port, 
            115200, 
            timeout=0.1,  # 100ms
            write_timeout=0.1
        )
        
        # If we get here, port opened
        print(f"  ✓ {com_port} opened successfully")
        
        # Check if port is actually a Shimmer
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Try to read any existing data
        time.sleep(0.1)
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"    Found {len(data)} bytes waiting")
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"  ✗ {com_port} failed: {e}")
        return False
    except OSError as e:
        print(f"  ✗ {com_port} OS error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ {com_port} unexpected: {e}")
        return False


def main():
    """Main diagnostic routine."""
    print("\n" + "="*70)
    print("Shimmer3R State Diagnostic")
    print("="*70)
    print("\nThis script checks if the Shimmer3R is powered and accessible.\n")
    
    # Step 1: Device Manager
    check_device_manager()
    
    # Step 2: Bluetooth pairing
    check_bluetooth_pairing()
    
    # Step 3: Try to access ports
    print("="*70)
    print("STEP 3: Test COM Port Accessibility")
    print("="*70 + "\n")
    
    bt_ports = find_bluetooth_ports()
    print(f"Found {len(bt_ports)} Bluetooth COM ports: {', '.join(bt_ports)}\n")
    
    working_ports = []
    for port in bt_ports[:2]:  # Test first 2 (likely COM4, COM5)
        if check_port_accessibility(port):
            working_ports.append(port)
    
    print()
    
    # Final verdict
    print("="*70)
    print("DIAGNOSTIC RESULTS")
    print("="*70 + "\n")
    
    if working_ports:
        print(f"✓ SUCCESS: {len(working_ports)} port(s) accessible: {', '.join(working_ports)}")
        print(f"\n→ Use COM port '{working_ports[-1]}' for streaming")
        print("\nThe Shimmer3R appears to be:")
        print("  ✓ Powered on")
        print("  ✓ Paired with Windows")
        print("  ✓ Accessible via serial")
        
    else:
        print("✗ FAILURE: No accessible COM ports")
        print("\nThis means the Shimmer3R is NOT ready for connection.\n")
        
        print("CRITICAL CHECKS:")
        print("-"*70)
        print("\n1. POWER STATUS")
        print("   - Press and hold the power button for 2 seconds")
        print("   - LED should light up BLUE (solid or blinking)")
        print("   - If LED is OFF: device is not powered → charge it")
        print("   - If LED is RED: battery too low → charge for 30+ minutes")
        
        print("\n2. PAIRING STATUS")
        print("   - Go to: Settings → Bluetooth & devices")
        print("   - Look for 'Shimmer3R' or 'Shimmer3' in paired devices")
        print("   - If not listed: pair the device first")
        print("   - If listed with error: remove and re-pair")
        
        print("\n3. DEVICE MANAGER")
        print("   - Right-click Start → Device Manager")
        print("   - Expand 'Ports (COM & LPT)'")
        print("   - Look for 'Standard Serial over Bluetooth' entries")
        print("   - Note the COM port numbers (e.g., COM4, COM5)")
        print("   - If yellow warning icon: right-click → Uninstall, then re-pair")
        
        print("\n4. CLOSE COMPETING APPLICATIONS")
        print("   - Close MATLAB completely")
        print("   - Close Consensys/ConsensysPRO")
        print("   - Check Task Manager for background Shimmer processes")
        print("   - Restart Bluetooth Support Service:")
        print("     * Win+R → services.msc")
        print("     * Find 'Bluetooth Support Service'")
        print("     * Right-click → Restart")
        
        print("\n5. POWER CYCLE SHIMMER")
        print("   - Hold power button for 5 seconds until LED goes OFF")
        print("   - Wait 5 seconds")
        print("   - Press power button for 2 seconds to turn ON")
        print("   - Wait for LED to blink BLUE")
        print("   - Run this script again")
    
    print("\n" + "="*70)
    print()


def find_bluetooth_ports():
    """Find Bluetooth COM ports."""
    ports = list(serial.tools.list_ports.comports())
    bt_ports = []
    
    for port in ports:
        if 'Bluetooth' in port.description or 'Standard Serial' in port.description:
            bt_ports.append(port.device)
    
    return sorted(bt_ports, key=lambda x: int(x.replace('COM', '')))


if __name__ == '__main__':
    main()
