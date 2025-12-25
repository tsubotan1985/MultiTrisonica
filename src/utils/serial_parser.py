"""
Serial data parser for Trisonica ultrasonic anemometer output
Handles tagged data format with variable spacing
"""

import re
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ParseError(Exception):
    """Exception raised when parsing fails"""
    pass


class SerialParser:
    """
    Parser for Trisonica sensor data with tagged format
    
    Example input:
        "S  09.89 D  134 U -04.52 V  04.36 W -07.64 T  27.96 PI  02.1 RO -01.3"
    """
    
    # Known tags and their descriptions
    KNOWN_TAGS = {
        'S': '2D wind speed (m/s)',
        'D': 'Horizontal direction (degrees)',
        'DV': 'Vertical direction (degrees)',
        'U': 'U component (m/s)',
        'V': 'V component (m/s)',
        'W': 'W component (m/s)',
        'T': 'Sonic temperature (°C)',
        'PI': 'Pitch (degrees)',
        'RO': 'Roll (degrees)'
    }
    
    # Required tags for valid data packet
    REQUIRED_TAGS = ['S', 'D', 'U', 'V', 'W', 'T']
    
    # Known error values from sensor
    ERROR_VALUES = [-99.9, -99.99]
    
    @staticmethod
    def parse_line(line: str) -> Dict[str, float]:
        """
        Parse a line of tagged sensor data
        
        The parser splits on whitespace and processes tag-value pairs.
        Tag order is variable - parser handles any order.
        Unknown tags are logged but don't cause failure.
        
        Args:
            line: Raw data line from sensor
            
        Returns:
            Dictionary mapping tag names to float values
            
        Raises:
            ParseError: If line format is invalid or cannot be parsed
            
        Example:
            >>> SerialParser.parse_line("S  09.89 D  134 U -04.52")
            {'S': 9.89, 'D': 134.0, 'U': -4.52}
        """
        if not line or not isinstance(line, str):
            raise ParseError("Empty or invalid input line")
        
        # Strip whitespace and split by any amount of whitespace
        tokens = line.strip().split()
        
        if len(tokens) == 0:
            raise ParseError("No tokens in line")
        
        parsed_data = {}
        i = 0
        
        while i < len(tokens):
            # Check if current token could be a tag
            potential_tag = tokens[i].upper()
            
            # Look ahead for a value
            if i + 1 < len(tokens):
                potential_value = tokens[i + 1]
                
                # Try to parse as float
                try:
                    value = float(potential_value)
                    
                    # If tag is known or looks like a tag (1-2 uppercase letters)
                    if potential_tag in SerialParser.KNOWN_TAGS or re.match(r'^[A-Z]{1,2}$', potential_tag):
                        parsed_data[potential_tag] = value
                        
                        # Log unknown tags
                        if potential_tag not in SerialParser.KNOWN_TAGS:
                            logger.debug(f"Unknown tag encountered: {potential_tag} = {value}")
                        
                        i += 2  # Skip both tag and value
                        continue
                except ValueError:
                    # Not a valid number, might be part of next pair
                    pass
            
            # If we get here, couldn't parse as tag-value pair
            # Skip this token and try next
            i += 1
        
        if not parsed_data:
            raise ParseError(f"No valid tag-value pairs found in line: {line[:50]}")
        
        return parsed_data
    
    @staticmethod
    def is_error_value(value: float) -> bool:
        """
        Check if a value is a sensor error code
        
        Args:
            value: Numeric value to check
            
        Returns:
            True if value is an error code (-99.9 or -99.99)
            
        Example:
            >>> SerialParser.is_error_value(-99.9)
            True
            >>> SerialParser.is_error_value(5.3)
            False
        """
        # Use approximate comparison due to floating point precision
        return any(abs(value - err) < 0.001 for err in SerialParser.ERROR_VALUES)
    
    @staticmethod
    def validate_data(parsed: Dict[str, float]) -> bool:
        """
        Validate that all required tags are present in parsed data
        
        Args:
            parsed: Dictionary of parsed tag-value pairs
            
        Returns:
            True if all required tags (S, D, U, V, W, T) are present
            
        Example:
            >>> data = {'S': 9.89, 'D': 134.0, 'U': -4.52, 'V': 4.36, 'W': -7.64, 'T': 27.96}
            >>> SerialParser.validate_data(data)
            True
        """
        if not parsed or not isinstance(parsed, dict):
            return False
        
        # Check that all required tags are present
        for tag in SerialParser.REQUIRED_TAGS:
            if tag not in parsed:
                logger.warning(f"Missing required tag: {tag}")
                return False
        
        return True
    
    @staticmethod
    def has_error_values(parsed: Dict[str, float]) -> bool:
        """
        Check if any values in the parsed data are error codes
        
        Args:
            parsed: Dictionary of parsed tag-value pairs
            
        Returns:
            True if any value is an error code
        """
        return any(SerialParser.is_error_value(v) for v in parsed.values())
