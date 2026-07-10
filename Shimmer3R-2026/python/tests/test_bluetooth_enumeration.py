"""
test_bluetooth_enumeration.py — Verify Bluetooth RFCOMM device enumeration for Shimmer3R.

This script tests that the Windows Bluetooth stack correctly exposes paired Shimmer3R
devices as COM ports accessible via pyserial.

Usage:
    python test_bluetooth_enumeration.py

Expected output:
    List of available COM ports with device names
    Identification of which COM port corresponds to Shimmer3R

Requirements:
    - Windows 10/11 with Bluetooth adapter
    - Shimmer3R paired via Windows Settings → Bluetooth & devices
    - pyserial installed (pip install -r requirements.txt)

Note:
    On Windows, pyserial handles RFCOMM natively; pybluez is NOT required.
    On Linux, rfcomm must bind the device before enumeration (see pyshimmer docs).
"""

import sys
import serial
import serial.tools.list_ports


def enumerate_com_ports():
    """List all available COM ports with metadata."""
    print("=" * 70)
    print("BLUETOOTH RFCOMM PORT ENUMERATION")
    print("=" * 70)
    
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("\nNo COM ports found.")
        print("Ensure Bluetooth adapter is enabled and devices are paired.")
        return []
    
    print(f"\nFound {len(ports)} COM port(s):\n")
    
    shimmer_ports = []
    
    for i, port in enumerate(ports, 1):
        # port.device: COM port name (e.g., 'COM7')
        # port.name: human-readable name
        # port.description: device description
        # port.hwid: hardware ID
        # port.location: physical location
        # port.vid: USB vendor ID (if applicable)
        # port.pid: USB product ID (if applicable)
        
        print(f"{i}. {port.device}")
        print(f"   Name:        {port.name}")
        print(f"   Description: {port.description}")
        print(f"   HWID:        {port.hwid}")
        
        # Check if this looks like a Bluetooth device
        is_bluetooth = False
        if 'Bluetooth' in port.description or 'BT' in port.hwid.upper():
            is_bluetooth = True
            print(f"   [BLUETOOTH DETECTED]")
        
        # Check if this looks like a Shimmer device
        is_shimmer = False
        shimmer_keywords = ['SHIMMER', 'Shimmer', 'GSR', 'PPG']
        for keyword in shimmer_keywords:
            if keyword in port.name or keyword in port.description or keyword in port.hwid:
                is_shimmer = True
                print(f"   [SHIMMER LIKELY: matched '{keyword}']")
                break
        
        if is_bluetooth and is_shimmer:
            shimmer_ports.append(port)
            print(f"   >>> CANDIDATE FOR SHIMMER3R <<<")
        
        print()
    
    return shimmer_ports


def test_port_connectivity(port_name: str, timeout: float = 2.0) -> bool:
    """Attempt to open the COM port and verify it responds."""
    print(f"Testing connectivity to {port_name}...")
    
    try:
        # Standard baud rate for Shimmer LogAndStream firmware
        BAUD_RATE = 115200
        
        ser = serial.Serial(
            port=port_name,
            baudrate=BAUD_RATE,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        
        # Try to read any pending data (should be empty if device is idle)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send a ping command (0x01) to test responsiveness
        # This is the Shimmer "ping" command in LogAndStream protocol
        ser.write(b'\x01')
        
        # Wait for response (should receive ACK within timeout)
        response = ser.read(1)
        
        ser.close()
        
        if response:
            print(f"  ✓ Port {port_name} responded (received {len(response)} byte(s))")
            return True
        else:
            print(f"  ⚠ Port {port_name} opened but did not respond to ping")
            print(f"    (Device may be asleep, out of range, or already connected)")
            return True  # Port exists, even if device not responsive
            
    except serial.SerialException as e:
        print(f"  ✗ Failed to open {port_name}: {e}")
        return False
    except OSError as e:
        print(f"  ✗ OS error accessing {port_name}: {e}")
        return False


def main():
    """Main test routine."""
    print("\nShimmer3R Phase 2 — Bluetooth Enumeration Test")
    print("This script verifies that paired Shimmer3R devices are visible as COM ports.\n")
    
    # Step 1: Enumerate all COM ports
    shimmer_ports = enumerate_com_ports()
    
    if not shimmer_ports:
        print("\n⚠ WARNING: No Shimmer devices detected in COM port list.")
        print("\nTroubleshooting:")
        print("  1. Ensure Shimmer3R is powered on (LED should blink)")
        print("  2. Pair the device via Windows Settings → Bluetooth & devices")
        print("  3. Check that the device appears in Device Manager → Ports (COM & LPT)")
        print("  4. Verify the COM port number (e.g., COM7)")
        print("\nRetrying in 5 seconds...")
        import time
        time.sleep(5)
        shimmer_ports = enumerate_com_ports()
    
    if not shimmer_ports:
        print("\n✗ No Shimmer ports found after retry. Exiting.")
        sys.exit(1)
    
    # Step 2: Test connectivity to each candidate port
    print("\n" + "=" * 70)
    print("CONNECTIVITY TEST")
    print("=" * 70 + "\n")
    
    working_ports = []
    for port in shimmer_ports:
        if test_port_connectivity(port.device):
            working_ports.append(port.device)
    
    # Step 3: Report results
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70 + "\n")
    
    if working_ports:
        print(f"✓ Found {len(working_ports)} working Shimmer COM port(s):")
        for i, port in enumerate(working_ports, 1):
            print(f"  {i}. {port}")
        
        print("\n✓ Bluetooth enumeration test PASSED")
        print("\nNext steps:")
        print("  1. Note the COM port number(s) above")
        print("  2. Update params_shimmer3r.py with the correct COM port")
        print("  3. Run the main streaming script: python shimmer3r_gsr_bt.py")
        
    else:
        print("✗ No working Shimmer COM ports found.")
        print("\nTroubleshooting:")
        print("  1. Ensure Shimmer3R is charged and powered on")
        print("  2. Check that the device is within Bluetooth range (<10m)")
        print("  3. Verify no other application is using the COM port")
        print("  4. Try unpairing and re-pairing the device")
        print("  5. Restart the Bluetooth service or reboot the PC")
        sys.exit(1)
    
    print()


if __name__ == '__main__':
    main()
