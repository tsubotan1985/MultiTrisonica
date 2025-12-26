"""
Test various save/commit commands to find the correct one
"""

import time
import serial
import sys


def test_command(ser, command, timeout=3.0):
    """Test a single command and return response"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {command}")
    print(f"{'=' * 60}")
    
    # Clear buffer
    ser.reset_input_buffer()
    time.sleep(0.2)
    
    # Send command
    for char in command:
        ser.write(char.encode('ascii'))
        time.sleep(0.01)
    
    ser.flush()
    
    # Read response
    start_time = time.time()
    response_lines = []
    
    while (time.time() - start_time) < timeout:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                
                # Skip sensor data lines
                if line.startswith('S ') or line.startswith('s '):
                    continue
                
                if line:
                    response_lines.append(line)
                    print(f"  {line}")
            
            except Exception as e:
                print(f"  Error: {e}")
        
        time.sleep(0.05)
    
    if not response_lines:
        print("  (No response)")
    
    return response_lines


def test_save_commands(port: str, baud: int = 115200):
    print(f"\n{'=' * 60}")
    print(f"Testing Save Commands on {port}")
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
        time.sleep(0.5)
        
        # Commands to test
        commands_to_test = [
            "{save}",
            "{commit}",
            "{store}",
            "{write}",
            "{persist}",
            "{savesettings}",
            "{help}",  # To see available commands
        ]
        
        results = {}
        
        for cmd in commands_to_test:
            response = test_command(ser, cmd, timeout=2.0)
            results[cmd] = response
            time.sleep(0.3)
        
        ser.close()
        
        # Summary
        print(f"\n{'=' * 60}")
        print(f"SUMMARY")
        print(f"{'=' * 60}\n")
        
        for cmd, response in results.items():
            response_text = ' '.join(response) if response else "(no response)"
            
            if not response:
                status = "⚠ No response"
            elif 'Invalid Command' in response_text:
                status = "❌ Invalid"
            elif 'error' in response_text.lower():
                status = "❌ Error"
            else:
                status = "✓ Valid response"
            
            print(f"{cmd:20s} : {status}")
            if response and len(response) <= 3:
                for line in response:
                    print(f"{'':22s}   {line}")
        
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
║  Test Various Save Commands                                ║
║  Find the correct command to save configuration            ║
╚════════════════════════════════════════════════════════════╝
""")
    
    print(f"Usage: python {sys.argv[0]} [PORT]")
    print(f"Example: python {sys.argv[0]} COM7\n")
    
    test_save_commands(test_port)
