"""
Test script for debugging TriSonica JSON protocol initialization
Specifically designed to diagnose COM6 sensor initialization issues
"""

import time
import json
import serial
import sys
from typing import Optional, Dict, Any


def send_json_command(ser: serial.Serial, command: str, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
    """
    Send a JSON command to the sensor and parse response
    
    Args:
        ser: Serial port object
        command: JSON command string (e.g., "{json}", "{settings}")
        timeout: Response timeout in seconds
    
    Returns:
        dict: Parsed JSON response, or dict with 'error' key if failed
    """
    try:
        print(f"Sending command: {command} (timeout: {timeout}s)")
        
        # Clear input buffer before sending command
        ser.reset_input_buffer()
        time.sleep(0.1)
        
        # Send command character by character
        for char in command:
            ser.write(char.encode('ascii'))
            time.sleep(0.01)  # 10ms delay between characters
        
        ser.flush()
        time.sleep(0.1)  # Additional delay after flush
        
        # Read response
        response_lines = []
        start_time = time.time()
        brace_count = 0
        in_json = False
        
        while (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('ascii', errors='ignore').strip()
                    
                    # Skip sensor data lines (start with "S ")
                    if line.startswith('S ') or line.startswith('s '):
                        continue
                    
                    if line:
                        print(f"  Response line: {line}")
                        response_lines.append(line)
                        
                        # Track braces to detect complete JSON
                        if '{' in line:
                            in_json = True
                            brace_count += line.count('{')
                        if '}' in line:
                            brace_count -= line.count('}')
                        
                        # Complete JSON received
                        if in_json and brace_count <= 0:
                            break
                
                except Exception as e:
                    print(f"  Error reading response: {e}")
            
            time.sleep(0.05)
        
        if not response_lines:
            print(f"  ERROR: No response received")
            return {'error': 'No response'}
        
        # Join response lines
        response_text = '\n'.join(response_lines)
        print(f"  Full response ({len(response_lines)} lines):\n{response_text}\n")
        
        # Check for error messages
        if 'Invalid Parameter' in response_text or 'Invalid Command' in response_text:
            print(f"  ERROR: Command rejected")
            return {'error': 'Invalid command'}
        
        # Try to parse as JSON
        try:
            # Handle nested JSON (outer braces may be wrapper)
            if response_text.startswith('{') and response_text.endswith('}'):
                try:
                    parsed = json.loads(response_text)
                    return parsed
                except json.JSONDecodeError:
                    # Try finding inner JSON
                    inner_start = response_text.find('{', 1)
                    inner_end = response_text.rfind('}', 0, -1)
                    if inner_start > 0 and inner_end > inner_start:
                        inner_json = response_text[inner_start:inner_end + 1]
                        return json.loads(inner_json)
            
            # Return as raw text if not parseable as JSON
            return {'raw': response_text}
            
        except json.JSONDecodeError as e:
            print(f"  Could not parse as JSON: {e}")
            return {'raw': response_text}
    
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return {'error': str(e)}


def test_json_initialization(port: str, baud: int = 115200):
    """
    Test JSON protocol initialization for a specific port
    
    Args:
        port: COM port (e.g., "COM6")
        baud: Baud rate (default: 115200)
    """
    print(f"\n{'=' * 60}")
    print(f"Testing JSON Protocol on {port} @ {baud} baud")
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
        
        # Flush any existing data in buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Wait for sensor to be ready
        print("Waiting for sensor to be ready...")
        time.sleep(0.5)
        ser.reset_input_buffer()
        time.sleep(0.2)
        
        # Test 1: {json} command (with retry)
        print("\n" + "=" * 60)
        print("TEST 1: {json} command (checking protocol support)")
        print("=" * 60)
        
        json_response = None
        for attempt in range(2):
            print(f"\nAttempt {attempt + 1}/2:")
            json_response = send_json_command(ser, "{json}", timeout=3.0)
            
            if json_response and 'error' not in json_response:
                print("✓ SUCCESS: JSON protocol supported")
                break
            
            if attempt == 0:
                print("✗ FAILED: Retrying...")
                time.sleep(0.5)
                ser.reset_input_buffer()
        
        if not json_response or 'error' in json_response:
            print("\n✗ FINAL RESULT: JSON protocol NOT supported")
            print("This sensor may be running older firmware (<3.0.0)")
            ser.close()
            return
        
        # Extract firmware version
        fw_version = json_response.get('Version', 'unknown')
        print(f"\n✓ JSON protocol confirmed (Firmware: {fw_version})")
        
        # Test 2: {version} command
        print("\n" + "=" * 60)
        print("TEST 2: {version} command (getting version info)")
        print("=" * 60)
        time.sleep(0.2)
        version_response = send_json_command(ser, "{version}", timeout=3.0)
        
        if version_response and 'error' not in version_response:
            print("✓ SUCCESS: Version info retrieved")
        else:
            print("✗ FAILED: Could not get version info")
        
        # Test 3: {settings} command
        print("\n" + "=" * 60)
        print("TEST 3: {settings} command (getting configuration)")
        print("=" * 60)
        time.sleep(0.2)
        settings_response = send_json_command(ser, "{settings}", timeout=4.0)
        
        if settings_response and 'Settings' in settings_response:
            print("✓ SUCCESS: Settings retrieved")
            settings = settings_response['Settings']
            model = settings.get('Model', 'Unknown')
            serial_num = settings.get('Serial Number', 'Unknown')
            sample_rate = settings.get('Probe', {}).get('SampleRate', 'Unknown')
            
            print(f"\nSensor Information:")
            print(f"  Model: {model}")
            print(f"  Serial Number: {serial_num}")
            print(f"  Sample Rate: {sample_rate} Hz")
            
            # Check enabled tags
            output_config = settings.get('Output', {})
            if output_config:
                print(f"\n  Output Configuration:")
                for key, value in output_config.items():
                    print(f"    {key}: {value}")
        else:
            print("✗ FAILED: Could not get settings")
        
        # Close serial port
        ser.close()
        print(f"\n{'=' * 60}")
        print(f"Test completed - Serial port closed")
        print(f"{'=' * 60}\n")
        
    except serial.SerialException as e:
        print(f"\n✗ SERIAL ERROR: {e}")
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Default test configuration
    test_port = "COM6"  # Change this to test different ports
    test_baud = 115200
    
    # Allow command-line override
    if len(sys.argv) > 1:
        test_port = sys.argv[1]
    if len(sys.argv) > 2:
        test_baud = int(sys.argv[2])
    
    print("""
╔════════════════════════════════════════════════════════════╗
║  TriSonica JSON Protocol Test Script                      ║
║  Diagnose sensor initialization issues                     ║
╚════════════════════════════════════════════════════════════╝
""")
    
    print(f"Usage: python {sys.argv[0]} [PORT] [BAUD]")
    print(f"Example: python {sys.argv[0]} COM6 115200\n")
    
    test_json_initialization(test_port, test_baud)
    
    print("\nTo test multiple sensors sequentially:")
    print(f"  python {sys.argv[0]} COM3")
    print(f"  python {sys.argv[0]} COM5")
    print(f"  python {sys.argv[0]} COM6")
