"""
Input validation utilities for Multi-Trisonica GUI Application
Validates COM ports, baud rates, file paths, and sensor parameters
"""

import re
from pathlib import Path
from typing import Union


class Validators:
    """
    Collection of validation methods for user inputs and configuration
    """
    
    # Valid baud rates for serial communication
    VALID_BAUD_RATES = [9600, 19200, 38400, 57600, 115200]
    
    # COM port pattern (Windows)
    COM_PORT_PATTERN = re.compile(r'^COM\d+$', re.IGNORECASE)
    
    @staticmethod
    def validate_com_port(port: str) -> bool:
        """
        Validate COM port format (Windows: COM1, COM2, etc.)
        
        Args:
            port: COM port string to validate
            
        Returns:
            True if valid COM port format, False otherwise
            
        Example:
            >>> Validators.validate_com_port("COM3")
            True
            >>> Validators.validate_com_port("USB0")
            False
        """
        if not port or not isinstance(port, str):
            return False
        return Validators.COM_PORT_PATTERN.match(port) is not None
    
    @staticmethod
    def validate_baud_rate(baud_rate: Union[int, str]) -> bool:
        """
        Validate baud rate against allowed values
        
        Args:
            baud_rate: Baud rate to validate (int or string)
            
        Returns:
            True if valid baud rate, False otherwise
            
        Example:
            >>> Validators.validate_baud_rate(115200)
            True
            >>> Validators.validate_baud_rate(9601)
            False
        """
        try:
            baud = int(baud_rate)
            return baud in Validators.VALID_BAUD_RATES
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_csv_path(filepath: Union[str, Path]) -> tuple[bool, str]:
        """
        Validate CSV file path for security and format
        
        Checks:
        - No path traversal attempts (..)
        - Has .csv extension
        - Is an absolute path or relative to current directory
        
        Args:
            filepath: File path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Example:
            >>> Validators.validate_csv_path("data.csv")
            (True, "")
            >>> Validators.validate_csv_path("../../../etc/passwd")
            (False, "Path contains invalid traversal")
        """
        if not filepath:
            return False, "File path is empty"
        
        try:
            path = Path(filepath)
            
            # Check for path traversal
            if ".." in path.parts:
                return False, "Path contains invalid traversal (..)"
            
            # Check for .csv extension
            if path.suffix.lower() != '.csv':
                return False, "File must have .csv extension"
            
            # Resolve to absolute path and check if it's within allowed directories
            abs_path = path.resolve()
            
            # Additional security check: ensure resolved path doesn't escape
            if ".." in str(abs_path):
                return False, "Resolved path contains invalid traversal"
            
            return True, ""
            
        except (ValueError, OSError) as e:
            return False, f"Invalid path: {str(e)}"
    
    @staticmethod
    def validate_output_rate(rate: Union[int, float, str]) -> bool:
        """
        Validate sensor output rate (1-10 Hz range)
        
        Args:
            rate: Output rate to validate
            
        Returns:
            True if valid output rate (1-10 Hz), False otherwise
            
        Example:
            >>> Validators.validate_output_rate(5)
            True
            >>> Validators.validate_output_rate(15)
            False
        """
        try:
            rate_value = float(rate)
            return 1.0 <= rate_value <= 10.0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_sensor_id(sensor_id: str) -> bool:
        """
        Validate sensor ID format
        
        Args:
            sensor_id: Sensor identifier to validate
            
        Returns:
            True if valid sensor ID, False otherwise
            
        Example:
            >>> Validators.validate_sensor_id("Sensor1")
            True
            >>> Validators.validate_sensor_id("")
            False
        """
        if not sensor_id or not isinstance(sensor_id, str):
            return False
        # Allow alphanumeric and underscores, 1-20 characters
        return bool(re.match(r'^[a-zA-Z0-9_]{1,20}$', sensor_id))
