"""
Quick script to enable T tag on COM7 without confirmation prompt
"""

import time
import serial


def enable_t_tag_com7():
    port = "COM7"
    baud = 115200
    
    print(f"Enabling T tag on {port}...")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0,
            write_timeout=2.0
        )
        
        print("  Port opened")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.5)
        
        # Send command to enable T tag
        command = "{set Display.T.Tagged true}"
        print(f"  Sending: {command}")
        
        for char in command:
            ser.write(char.encode('ascii'))
            time.sleep(0.01)
        
        ser.flush()
        time.sleep(0.5)
        
        # Clear response
        ser.reset_input_buffer()
        
        # Save configuration
        command = "{save}"
        print(f"  Sending: {command}")
        
        for char in command:
            ser.write(char.encode('ascii'))
            time.sleep(0.01)
        
        ser.flush()
        time.sleep(0.5)
        
        ser.close()
        
        print("  ✓ T tag enabled and saved!")
        print("\nNow test data reception:")
        print("  python tests/test_data_reception.py COM7 115200 5")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    enable_t_tag_com7()
