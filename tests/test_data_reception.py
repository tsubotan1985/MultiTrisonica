"""
Test script for verifying sensor data reception
Tests if sensor is sending valid data that can be parsed
"""

import time
import serial
import sys
from typing import Optional


def test_data_reception(port: str, baud: int = 115200, duration: int = 10):
    """
    Test data reception from a specific sensor port
    
    Args:
        port: COM port (e.g., "COM7")
        baud: Baud rate (default: 115200)
        duration: Test duration in seconds (default: 10)
    """
    print(f"\n{'=' * 60}")
    print(f"Testing Data Reception on {port} @ {baud} baud")
    print(f"Duration: {duration} seconds")
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
        
        # Wait a moment for sensor to start sending
        print("Waiting for sensor data...")
        time.sleep(1.0)
        
        # Read data for specified duration
        start_time = time.time()
        line_count = 0
        valid_data_lines = 0
        error_count = 0
        sample_lines = []
        
        print(f"\n{'=' * 60}")
        print(f"Reading data (showing first 10 lines)...")
        print(f"{'=' * 60}\n")
        
        while (time.time() - start_time) < duration:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('ascii', errors='ignore').strip()
                    
                    if line:
                        line_count += 1
                        
                        # Check if this looks like valid sensor data
                        # TriSonica data typically starts with "S " and contains tags
                        if line.startswith('S ') or line.startswith('s '):
                            valid_data_lines += 1
                            
                            # Store first few samples
                            if len(sample_lines) < 10:
                                sample_lines.append(line)
                                print(f"  Line {line_count}: {line}")
                        elif line.startswith('{'):
                            # JSON response - might be leftover from initialization
                            if len(sample_lines) < 10:
                                print(f"  Line {line_count} (JSON): {line[:60]}...")
                        else:
                            # Unexpected format
                            if len(sample_lines) < 10:
                                print(f"  Line {line_count} (Unknown): {line}")
                
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        print(f"  ERROR reading line: {e}")
            
            time.sleep(0.01)
        
        # Close serial port
        ser.close()
        
        # Print summary
        print(f"\n{'=' * 60}")
        print(f"Test Results Summary")
        print(f"{'=' * 60}")
        print(f"Total lines received:     {line_count}")
        print(f"Valid data lines (S ...): {valid_data_lines}")
        print(f"Error count:              {error_count}")
        print(f"Test duration:            {duration} seconds")
        
        if valid_data_lines > 0:
            data_rate = valid_data_lines / duration
            print(f"Data rate:                {data_rate:.1f} lines/second")
            print(f"\n✓ SUCCESS: Sensor is sending valid data")
            
            # Analyze sample data
            if sample_lines:
                print(f"\n{'=' * 60}")
                print(f"Data Analysis (first line)")
                print(f"{'=' * 60}")
                analyze_data_line(sample_lines[0])
        else:
            print(f"\n✗ FAILED: No valid data lines received")
            print(f"The sensor may not be sending data, or data format is unexpected")
        
        print(f"\n{'=' * 60}")
        print(f"Test completed")
        print(f"{'=' * 60}\n")
        
    except serial.SerialException as e:
        print(f"\n✗ SERIAL ERROR: {e}")
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()


def analyze_data_line(line: str):
    """
    Analyze a single data line to extract tag information
    
    Args:
        line: Data line from sensor (e.g., "S 0.12 D 45 U 0.08 V 0.10 W -0.02 T 20.5")
    """
    try:
        print(f"Raw line: {line}\n")
        
        # Split into tokens
        tokens = line.split()
        
        if not tokens:
            print("ERROR: Empty line")
            return
        
        # First token should be 'S' or 's'
        if tokens[0].upper() != 'S':
            print(f"WARNING: Line does not start with 'S' (got '{tokens[0]}')")
        
        # Parse tag-value pairs
        print("Detected tags and values:")
        i = 0
        tags_found = []
        
        while i < len(tokens):
            token = tokens[i]
            
            # Check if this is a tag (alphabetic)
            if token.isalpha() or token.replace('2', '').isalpha():
                tag = token
                
                # Next token should be value
                if i + 1 < len(tokens):
                    try:
                        value = float(tokens[i + 1])
                        tags_found.append((tag, value))
                        print(f"  {tag}: {value}")
                        i += 2
                    except ValueError:
                        print(f"  {tag}: ERROR - invalid value '{tokens[i + 1]}'")
                        i += 1
                else:
                    print(f"  {tag}: ERROR - no value")
                    i += 1
            else:
                # Try to parse as float (might be value without tag)
                try:
                    value = float(token)
                    print(f"  (No tag): {value}")
                except ValueError:
                    print(f"  UNKNOWN: '{token}'")
                i += 1
        
        print(f"\nTotal tags found: {len(tags_found)}")
        
        if not tags_found:
            print("\n✗ WARNING: No valid tag-value pairs found!")
            print("This may indicate a data format issue")
        
    except Exception as e:
        print(f"\nERROR analyzing data: {e}")


if __name__ == "__main__":
    # Default test configuration
    test_port = "COM7"  # Change this to test different ports
    test_baud = 115200
    test_duration = 10  # seconds
    
    # Allow command-line override
    if len(sys.argv) > 1:
        test_port = sys.argv[1]
    if len(sys.argv) > 2:
        test_baud = int(sys.argv[2])
    if len(sys.argv) > 3:
        test_duration = int(sys.argv[3])
    
    print("""
╔════════════════════════════════════════════════════════════╗
║  TriSonica Data Reception Test Script                     ║
║  Verify sensor is sending valid data                       ║
╚════════════════════════════════════════════════════════════╝
""")
    
    print(f"Usage: python {sys.argv[0]} [PORT] [BAUD] [DURATION]")
    print(f"Example: python {sys.argv[0]} COM7 115200 10\n")
    
    test_data_reception(test_port, test_baud, test_duration)
    
    print("\nTo test multiple sensors:")
    print(f"  python {sys.argv[0]} COM3 115200 5")
    print(f"  python {sys.argv[0]} COM5 115200 5")
    print(f"  python {sys.argv[0]} COM6 115200 5")
    print(f"  python {sys.argv[0]} COM7 115200 5")
