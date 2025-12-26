"""
Test {save} command response
"""

import time
import serial
import sys


def test_save_command(port: str, baud: int = 115200):
    print(f"\n{'=' * 60}")
    print(f"Testing {{save}} command on {port}")
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
        
        print(f"Serial port opened\n")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.5)
        
        # Send {save} command
        command = "{save}"
        print(f"Sending command: {command}")
        
        for char in command:
            ser.write(char.encode('ascii'))
            time.sleep(0.01)
        
        ser.flush()
        
        # Read response
        print("\nWaiting for response (3 seconds)...\n")
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
                        print(f"  Line {len(response_lines)}: {line}")
                
                except Exception as e:
                    print(f"  Error reading: {e}")
            
            time.sleep(0.05)
        
        ser.close()
        
        print(f"\n{'=' * 60}")
        print(f"Response Summary")
        print(f"{'=' * 60}")
        print(f"Total lines received: {len(response_lines)}")
        
        if response_lines:
            full_response = '\n'.join(response_lines)
            print(f"\nFull response:\n{full_response}")
            
            # Analyze response
            print(f"\n{'=' * 60}")
            print(f"Analysis")
            print(f"{'=' * 60}")
            
            response_lower = full_response.lower()
            
            if 'error' in response_lower:
                print("❌ Contains 'error'")
            else:
                print("✓ No 'error' found")
            
            if 'invalid' in response_lower:
                print("❌ Contains 'invalid'")
            else:
                print("✓ No 'invalid' found")
            
            if 'saved' in response_lower or 'ok' in response_lower:
                print("✓ Contains success indicator ('saved' or 'ok')")
            else:
                print("⚠ No explicit success indicator")
            
            if len(response_lines) == 0 or (len(response_lines) == 1 and response_lines[0] == ''):
                print("⚠ Empty or minimal response")
            
            print(f"\n{'=' * 60}")
            print(f"Recommendation")
            print(f"{'=' * 60}")
            
            if 'error' not in response_lower and 'invalid' not in response_lower:
                print("✓ Response looks good - treat as SUCCESS")
            else:
                print("❌ Response indicates failure")
        else:
            print("\n❌ No response received")
            print("\nThis could mean:")
            print("  1. Command was accepted but no response sent")
            print("  2. Response timeout too short")
            print("  3. Command not supported")
        
        print(f"\n{'=' * 60}\n")
        
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
║  Test {save} Command Response                              ║
║  Verify what response the sensor returns                   ║
╚════════════════════════════════════════════════════════════╝
""")
    
    print(f"Usage: python {sys.argv[0]} [PORT]")
    print(f"Example: python {sys.argv[0]} COM7\n")
    
    test_save_command(test_port)
