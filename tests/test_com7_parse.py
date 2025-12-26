"""
Quick test to verify COM7 data can be parsed correctly
"""

import sys
sys.path.insert(0, '.')

from src.utils.serial_parser import SerialParser

# Sample data from COM7 sensor
com7_data = "S  00.15 D  010 DV  013 U -00.03 V -00.14 W  00.03  22.64 H  46.46"

print("Testing COM7 Data Parsing")
print("=" * 60)
print(f"Raw data: {com7_data}\n")

try:
    # Parse the line
    parsed = SerialParser.parse_line(com7_data)
    print("✓ Parsing succeeded!")
    print(f"\nParsed data:")
    for tag, value in parsed.items():
        description = SerialParser.KNOWN_TAGS.get(tag, 'Unknown')
        print(f"  {tag:3s} = {value:7.2f}  ({description})")
    
    print(f"\nTotal tags parsed: {len(parsed)}")
    
    # Validate
    print("\n" + "=" * 60)
    is_valid = SerialParser.validate_data(parsed)
    print(f"Validation result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    
    if not is_valid:
        print("\nMissing required tags:")
        for tag in SerialParser.REQUIRED_TAGS:
            if tag not in parsed:
                print(f"  - {tag}")
    
    print("\n" + "=" * 60)
    if is_valid:
        print("✓ SUCCESS: COM7 data can be parsed and validated")
    else:
        print("✗ FAILED: Data validation failed")
        
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
