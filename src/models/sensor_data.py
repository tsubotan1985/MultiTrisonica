"""
Data model for sensor readings from Trisonica anemometers
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from src.utils.serial_parser import SerialParser


@dataclass(frozen=True)
class SensorData:
    """
    Immutable data structure representing a single sensor reading
    
    Note: Humidity field is NOT included as Trisonica sensors do not output RH data.
    Only sonic temperature is available from the sensor.
    
    Attributes:
        timestamp: Time when data was received
        sensor_id: Sensor identifier (COM port or user label)
        speed_2d: 2D wind speed (S) in m/s
        direction: Horizontal direction (D) in degrees
        u_component: U component (m/s)
        v_component: V component (m/s)
        w_component: W component (m/s)
        temperature: Sonic temperature (T) in °C
        pitch: Pitch angle (PI) in degrees
        roll: Roll angle (RO) in degrees
        is_valid: False if contains error values (-99.9, -99.99)
    """
    
    timestamp: datetime
    sensor_id: str
    speed_2d: float  # S
    direction: float  # D
    u_component: float  # U
    v_component: float  # V
    w_component: float  # W
    temperature: float  # T
    pitch: float  # PI
    roll: float  # RO
    is_valid: bool
    
    @classmethod
    def from_parsed_dict(cls, sensor_id: str, parsed: Dict[str, float], 
                        timestamp: Optional[datetime] = None) -> 'SensorData':
        """
        Create SensorData from a parsed dictionary
        
        Args:
            sensor_id: Identifier for the sensor
            parsed: Dictionary of tag-value pairs from SerialParser
            timestamp: Optional timestamp (uses current time if not provided)
            
        Returns:
            SensorData instance
            
        Raises:
            KeyError: If required tags are missing
            ValueError: If sensor_id is empty
            
        Example:
            >>> parsed = {'S': 9.89, 'D': 134.0, 'U': -4.52, 'V': 4.36, 
            ...           'W': -7.64, 'T': 27.96, 'PI': 2.1, 'RO': -1.3}
            >>> data = SensorData.from_parsed_dict("COM3", parsed)
        """
        if not sensor_id:
            raise ValueError("sensor_id cannot be empty")
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Extract required fields (will raise KeyError if missing)
        speed_2d = parsed['S']
        direction = parsed['D']
        u_component = parsed['U']
        v_component = parsed['V']
        w_component = parsed['W']
        temperature = parsed['T']
        
        # Extract optional fields with defaults
        pitch = parsed.get('PI', 0.0)
        roll = parsed.get('RO', 0.0)
        
        # Check if any values are error codes
        values_to_check = [speed_2d, direction, u_component, v_component, 
                          w_component, temperature, pitch, roll]
        has_errors = any(SerialParser.is_error_value(v) for v in values_to_check)
        is_valid = not has_errors
        
        return cls(
            timestamp=timestamp,
            sensor_id=sensor_id,
            speed_2d=speed_2d,
            direction=direction,
            u_component=u_component,
            v_component=v_component,
            w_component=w_component,
            temperature=temperature,
            pitch=pitch,
            roll=roll,
            is_valid=is_valid
        )
    
    def is_error_value(self, value: float) -> bool:
        """
        Check if a value is a sensor error code
        
        Args:
            value: Value to check
            
        Returns:
            True if value is an error code
        """
        return SerialParser.is_error_value(value)
    
    def to_csv_row(self) -> List[str]:
        """
        Convert to CSV row format
        
        Returns:
            List of strings representing CSV columns
            
        Format:
            [Timestamp, Sensor_ID, S, D, U, V, W, T, PI, RO]
            
        Example:
            >>> data.to_csv_row()
            ['2024-01-01 12:00:00.000', 'COM3', '9.89', '134.0', '-4.52', 
             '4.36', '-7.64', '27.96', '2.1', '-1.3']
        """
        # Format timestamp in ISO 8601 with milliseconds
        timestamp_str = self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        return [
            timestamp_str,
            self.sensor_id,
            f"{self.speed_2d:.2f}",
            f"{self.direction:.2f}",
            f"{self.u_component:.2f}",
            f"{self.v_component:.2f}",
            f"{self.w_component:.2f}",
            f"{self.temperature:.2f}",
            f"{self.pitch:.2f}",
            f"{self.roll:.2f}"
        ]
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return (f"SensorData({self.sensor_id} @ {self.timestamp.strftime('%H:%M:%S')}: "
                f"U={self.u_component:.2f}, V={self.v_component:.2f}, W={self.w_component:.2f}, "
                f"T={self.temperature:.2f}°C, Valid={self.is_valid})")
