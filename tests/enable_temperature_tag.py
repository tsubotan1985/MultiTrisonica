"""
Enable T (temperature) tag on TriSonica sensor
Sets Display.T.Tagged to true so temperature is output with "T" tag
"""

import time
import serial
import sys


def enable_temperature_tag(port: str, baud: int = 115200):
    """
    Enable temperature tag output on sensor
    
    Args:
        port: COM port (e.g., "COM7")
        baud: Baud rate (default: 115200)
    """
    print(f"\n{'=' * 60}")
    print(f"Enabling Temperature Tag on {port}")
    print(f"{'=' * 60}\n")
    
    try:
        # Open serial port
        print(f"Opening serial port...")
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0,
            write_timeout=2.0
        )
        
        print(f"Serial port opened successfully\n")
        
        # Flush buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.5)
        
        # Command to enable T tag
        command = "{set Display.T.Tagged true}"
        print(f"Sending command: {command}")
        
        # Send character by character
        for char in command:
            ser.write(char.encode('ascii'))
            time.sleep(0.01)
        
        ser.flush()
        time.sleep(0.2)
        
        # Read response
        print("\nWaiting for response...")
        start_time = time.time()
        response_lines = []
        
        while (time.time() - start_time) < 3.0:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('ascii', errors='ignore').strip()
                    
                    # Skip sensor data lines
                    if line.startswith('S ') or line.startswith('s '):
                        continue
                    
                    if line:
                        response_lines.append(line)
                        print(f"  Response: {line}")
                        
                        # Check for success
                        if 'true' in line.lower() or 'ok' in line.lower():
                            break
                
                except Exception as e:
                    print(f"  Error reading: {e}")
            
            time.sleep(0.05)
        
        if response_lines:
            print(f"\n✓ Command sent successfully")
            print(f"  Response: {' '.join(response_lines)}")
        else:
            print(f"\n⚠ No response received (command may still have succeeded)")
        
        # Now save to non-volatile memory
        print(f"\n{'=' * 60}")
        print("Saving configuration to non-volatile memory...")
        save_command = "{save}"
        print(f"Sending command: {save_command}")
        
        ser.reset_input_buffer()
        time.sleep(0.2)
        
        for char in save_command:
            ser.write(char.encode('ascii'))
            time.sleep(0.01)
        
        ser.flush()
        time.sleep(0.5)
        
        # Read save response
        response_lines = []
        start_time = time.time()
        
        while (time.time() - start_time) < 3.0:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('ascii', errors='ignore').strip()
                    
                    if line and not line.startswith('S ') and not line.startswith('s '):
                        response_lines.append(line)
                        print(f"  Response: {line}")
                        
                        if 'saved' in line.lower() or 'ok' in line.lower():
                            break
                
                except Exception as e:
                    print(f"  Error reading: {e}")
            
            time.sleep(0.05)
        
        if response_lines:
            print(f"\n✓ Configuration saved!")
        else:
            print(f"\n⚠ No save confirmation (configuration may still be saved)")
        
        ser.close()
        
        print(f"\n{'=' * 60}")
        print(f"✓ Temperature tag enabled!")
        print(f"{'=' * 60}")
        print(f"\nThe sensor should now output temperature with 'T' tag.")
        print(f"Example: S 0.15 D 10 U -0.03 V -0.14 W 0.03 T 22.64 H 46.46")
        print(f"\nRun the data reception test to verify:")
        print(f"  python tests/test_data_reception.py {port} 115200 5")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_port = "COM7"
    
    if len(sys.argv) > 1:
        test_port = sys.argv[1]
    
    print("""
╔════════════════════════════════════════════════════════════╗
║  Enable Temperature Tag on TriSonica Sensor                ║
║  Fix "Tagged: false" issue for temperature output          ║
╚════════════════════════════════════════════════════════════╝
""")
    
    print(f"Usage: python {sys.argv[0]} [PORT]")
    print(f"Example: python {sys.argv[0]} COM7\n")
    
    print("⚠ WARNING: This will modify sensor configuration!")
    print("  The change will be saved to non-volatile memory.\n")
    
    response = input("Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        enable_temperature_tag(test_port)
    else:
        print("Cancelled.")
