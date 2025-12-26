"""
Get complete settings from TriSonica sensor
Specifically to see temperature (T) tag configuration
"""

import time
import json
import serial
import sys


def get_complete_settings(port: str, baud: int = 115200):
    """
    Get complete settings from sensor with very long timeout
    
    Args:
        port: COM port (e.g., "COM7")
        baud: Baud rate (default: 115200)
    """
    print(f"\n{'=' * 60}")
    print(f"Getting Complete Settings from {port}")
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
        
        # Send {settings} command
        command = "{settings}"
        print(f"Sending command: {command}")
        print("(This will take 10-15 seconds to receive all data...)\n")
        
        # Send character by character
        for char in command:
            ser.write(char.encode('ascii'))
            time.sleep(0.01)
        
        ser.flush()
        time.sleep(0.1)
        
        # Read response with very long timeout
        response_lines = []
        start_time = time.time()
        timeout = 15.0  # 15 seconds
        brace_count = 0
        in_json = False
        last_data_time = time.time()
        
        print("Reading response...")
        
        while (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('ascii', errors='ignore').strip()
                    
                    # Skip sensor data lines
                    if line.startswith('S ') or line.startswith('s '):
                        continue
                    
                    if line:
                        response_lines.append(line)
                        last_data_time = time.time()
                        
                        # Track braces
                        if '{' in line:
                            in_json = True
                            brace_count += line.count('{')
                        if '}' in line:
                            brace_count -= line.count('}')
                        
                        # Complete JSON received
                        if in_json and brace_count <= 0:
                            print(f"Complete JSON received ({len(response_lines)} lines)")
                            break
                
                except Exception as e:
                    print(f"Error reading line: {e}")
            
            # If no data for 3 seconds after receiving some data, assume complete
            if response_lines and (time.time() - last_data_time) > 3.0:
                print(f"No more data for 3 seconds, assuming complete ({len(response_lines)} lines)")
                break
            
            time.sleep(0.05)
        
        ser.close()
        
        if not response_lines:
            print("✗ No response received")
            return
        
        # Save to file
        response_text = '\n'.join(response_lines)
        filename = f"settings_{port.replace(':', '_')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response_text)
        
        print(f"\n✓ Settings saved to: {filename}")
        print(f"  Total lines: {len(response_lines)}")
        
        # Try to parse as JSON
        try:
            # Try to extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed = json.loads(json_text)
                
                # Pretty print to file
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(parsed, f, indent=2)
                
                print(f"  Formatted JSON saved to: {filename}")
                
                # Look for temperature configuration
                if 'Settings' in parsed:
                    settings = parsed['Settings']
                    if 'Display' in settings:
                        display = settings['Display']
                        
                        print(f"\n{'=' * 60}")
                        print(f"Output Tag Configuration")
                        print(f"{'=' * 60}")
                        
                        for key in ['S', 'D', 'DV', 'U', 'V', 'W', 'T', 'H']:
                            if key in display:
                                tag_info = display[key]
                                enabled = tag_info.get('Enabled', False)
                                status = '✓ Enabled' if enabled else '✗ Disabled'
                                print(f"  {key:3s} : {status}")
                
        except Exception as e:
            print(f"  Could not parse as JSON: {e}")
            print(f"  Raw response saved to: {filename}")
        
        print(f"\n{'=' * 60}")
        print(f"Complete!")
        print(f"{'=' * 60}\n")
        
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
║  TriSonica Complete Settings Retrieval                    ║
║  Get full configuration including tag settings             ║
╚════════════════════════════════════════════════════════════╝
""")
    
    print(f"Usage: python {sys.argv[0]} [PORT]")
    print(f"Example: python {sys.argv[0]} COM7\n")
    
    get_complete_settings(test_port)
