"""
Application and sensor configuration models
Handles loading, saving, and managing configuration persistence
"""

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Optional, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SensorConfig:
    """
    Configuration for a single sensor
    
    Attributes:
        port: COM port (e.g., "COM3")
        baud: Baud rate (default: 115200)
        custom_init_commands: Optional list of custom initialization commands
    """
    port: str = ""
    baud: int = 115200
    custom_init_commands: List[str] = field(default_factory=list)


@dataclass
class AppConfig:
    """
    Application-wide configuration
    
    Attributes:
        sensors: Dictionary of sensor configurations (key: sensor_id, value: SensorConfig)
        output_rate: Global output rate in Hz (1-10)
        window_geometry: Window position and size [x, y, width, height]
    """
    sensors: Dict[str, SensorConfig] = field(default_factory=lambda: {
        'Sensor1': SensorConfig(),
        'Sensor2': SensorConfig(),
        'Sensor3': SensorConfig(),
        'Sensor4': SensorConfig()
    })
    output_rate: int = 5
    window_geometry: List[int] = field(default_factory=lambda: [100, 100, 1280, 800])
    
    @staticmethod
    def _get_config_path() -> Path:
        """
        Get the path to the configuration file
        
        Returns:
            Path to config.json in application root directory
        """
        return Path("config.json")
    
    @classmethod
    def load_or_default(cls) -> 'AppConfig':
        """
        Load configuration from config.json or return default if missing/corrupted
        
        Returns:
            AppConfig instance with loaded or default values
            
        Example:
            >>> config = AppConfig.load_or_default()
            >>> print(config.output_rate)
            5
        """
        config_path = cls._get_config_path()
        
        # If config file doesn't exist, return default
        if not config_path.exists():
            logger.info(f"Configuration file not found at {config_path}, using defaults")
            return cls()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Start with default sensors (all 4)
            default_sensors = {
                'Sensor1': SensorConfig(),
                'Sensor2': SensorConfig(),
                'Sensor3': SensorConfig(),
                'Sensor4': SensorConfig()
            }
            
            # Update with loaded sensor configs (merge with defaults)
            for sensor_id, sensor_data in data.get('sensors', {}).items():
                if sensor_id in default_sensors:
                    default_sensors[sensor_id] = SensorConfig(
                        port=sensor_data.get('port', ''),
                        baud=sensor_data.get('baud', 115200),
                        custom_init_commands=sensor_data.get('custom_init_commands', SensorConfig().custom_init_commands)
                    )
            
            sensors = default_sensors
            
            config = cls(
                sensors=sensors,
                output_rate=data.get('output_rate', 5),
                window_geometry=data.get('window_geometry', [100, 100, 1280, 800])
            )
            
            logger.info(f"Configuration loaded from {config_path}")
            return config
            
        except json.JSONDecodeError as e:
            logger.warning(f"Configuration file is corrupted: {e}. Using defaults.")
            return cls()
        except Exception as e:
            logger.warning(f"Error loading configuration: {e}. Using defaults.")
            return cls()
    
    def save(self) -> bool:
        """
        Save configuration to config.json
        
        Returns:
            True if save successful, False otherwise
            
        Note:
            If write fails (OSError), logs warning and continues with in-memory config
            
        Example:
            >>> config = AppConfig()
            >>> config.output_rate = 10
            >>> success = config.save()
        """
        config_path = self._get_config_path()
        
        try:
            # Convert to dictionary
            data = {
                'sensors': {
                    sensor_id: {
                        'port': sensor_config.port,
                        'baud': sensor_config.baud,
                        'custom_init_commands': sensor_config.custom_init_commands
                    }
                    for sensor_id, sensor_config in self.sensors.items()
                },
                'output_rate': self.output_rate,
                'window_geometry': self.window_geometry
            }
            
            # Write to file with indentation for readability
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration saved to {config_path}")
            return True
            
        except OSError as e:
            logger.warning(f"Failed to write configuration file: {e}. Continuing with in-memory settings.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving configuration: {e}")
            return False
    
    def get_sensor_config(self, sensor_id: str) -> Optional[SensorConfig]:
        """
        Get configuration for a specific sensor
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            SensorConfig if found, None otherwise
        """
        return self.sensors.get(sensor_id)
    
    def update_sensor_config(self, sensor_id: str, sensor_config: SensorConfig) -> None:
        """
        Update configuration for a specific sensor
        
        Args:
            sensor_id: Sensor identifier
            sensor_config: New sensor configuration
        """
        self.sensors[sensor_id] = sensor_config
        logger.debug(f"Updated configuration for {sensor_id}")
