"""
AppController - Main application controller

Manages multiple sensor controllers and coordinates application-level operations.
Handles sensor connections, configuration persistence, and CSV export.
"""

from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

import serial.tools.list_ports
import psutil

from src.utils.logger import get_logger
from src.controllers.sensor_controller import SensorController
from src.models.app_config import AppConfig, SensorConfig
from src.models.sensor_data import SensorData
from src.utils.csv_writer import CSVWriter
from src.utils.validators import Validators

logger = get_logger(__name__)


class AppController(QObject):
    """
    Main application controller
    
    Manages:
    - 4 SensorController instances (Sensor1-4)
    - Application configuration (load/save)
    - COM port enumeration
    - Sensor connection/disconnection
    - CSV export coordination
    - Memory usage monitoring
    """
    
    # Signal emitted when memory usage exceeds threshold (500MB)
    memory_warning = pyqtSignal(float)  # Emits memory usage in MB
    
    # Memory monitoring constants
    MEMORY_CHECK_INTERVAL_MS = 30000  # 30 seconds
    MEMORY_WARNING_THRESHOLD_MB = 500.0  # 500 MB
    
    def __init__(self):
        """
        Initialize application controller
        
        Creates 4 SensorController instances, loads configuration,
        and sets up memory monitoring.
        """
        super().__init__()
        
        # Load configuration
        self.config = AppConfig.load_or_default()
        logger.info(f"Configuration loaded: {len(self.config.sensors)} sensors configured")
        
        # Create sensor controllers
        self.sensor_controllers: Dict[str, SensorController] = {}
        
        for sensor_id, sensor_config in self.config.sensors.items():
            controller = SensorController(sensor_id, sensor_config)
            self.sensor_controllers[sensor_id] = controller
            logger.info(f"Created controller for {sensor_id}")
        
        # Setup memory monitoring
        self._setup_memory_monitor()
        
        logger.info("AppController initialized")
    
    def get_available_ports(self) -> List[str]:
        """
        Get list of available COM ports
        
        Uses serial.tools.list_ports to enumerate available serial ports.
        
        Returns:
            List of COM port names (e.g., ["COM3", "COM4"])
        """
        try:
            ports = serial.tools.list_ports.comports()
            port_names = [port.device for port in ports]
            logger.debug(f"Available COM ports: {port_names}")
            return port_names
        except Exception as e:
            logger.error(f"Error enumerating COM ports: {e}")
            return []
    
    def connect_sensor(self, sensor_id: str, port: str, baud: int, 
                      init_commands: List[str]) -> bool:
        """
        Connect a sensor
        
        Updates configuration, connects the sensor, and saves config.
        
        Args:
            sensor_id: Sensor identifier (e.g., "Sensor1")
            port: COM port (e.g., "COM3")
            baud: Baud rate (e.g., 115200)
            init_commands: List of initialization commands
            
        Returns:
            True if connection started successfully, False otherwise
        """
        if sensor_id not in self.sensor_controllers:
            logger.error(f"Unknown sensor ID: {sensor_id}")
            return False
        
        logger.info(
            f"Connecting {sensor_id} to {port} @ {baud} baud "
            f"with {len(init_commands)} init commands"
        )
        
        # Update configuration
        self.config.sensors[sensor_id] = SensorConfig(
            port=port,
            baud=baud,
            custom_init_commands=init_commands
        )
        
        # Update controller config
        controller = self.sensor_controllers[sensor_id]
        controller.config = self.config.sensors[sensor_id]
        
        # Attempt connection
        success = controller.connect()
        
        if success:
            # Save configuration
            self.config.save()
            logger.info(f"{sensor_id}: Connection initiated successfully")
        else:
            logger.warning(f"{sensor_id}: Failed to initiate connection")
        
        return success
    
    def disconnect_sensor(self, sensor_id: str) -> None:
        """
        Disconnect a sensor
        
        Args:
            sensor_id: Sensor identifier (e.g., "Sensor1")
        """
        if sensor_id not in self.sensor_controllers:
            logger.error(f"Unknown sensor ID: {sensor_id}")
            return
        
        logger.info(f"Disconnecting {sensor_id}")
        controller = self.sensor_controllers[sensor_id]
        controller.disconnect()
    
    def disconnect_all(self) -> None:
        """
        Disconnect all sensors
        
        Blocks until all sensors are disconnected.
        Called during application shutdown.
        """
        logger.info("Disconnecting all sensors...")
        
        for sensor_id, controller in self.sensor_controllers.items():
            if controller.is_connected() or controller.worker is not None:
                logger.info(f"Disconnecting {sensor_id}...")
                controller.disconnect()
        
        logger.info("All sensors disconnected")
    
    def get_sensor_controller(self, sensor_id: str) -> Optional[SensorController]:
        """
        Get a sensor controller by ID
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            SensorController instance or None if not found
        """
        return self.sensor_controllers.get(sensor_id)
    
    def get_all_sensor_ids(self) -> List[str]:
        """
        Get list of all sensor IDs
        
        Returns:
            List of sensor IDs (e.g., ["Sensor1", "Sensor2", "Sensor3", "Sensor4"])
        """
        return list(self.sensor_controllers.keys())
    
    def get_connected_sensor_ids(self) -> List[str]:
        """
        Get list of currently connected sensor IDs
        
        Returns:
            List of connected sensor IDs
        """
        connected = [
            sensor_id for sensor_id, controller in self.sensor_controllers.items()
            if controller.is_connected()
        ]
        return connected
    
    def save_config(self) -> None:
        """
        Save current configuration to disk
        
        Useful for persisting changes made during runtime.
        """
        self.config.save()
        logger.debug("Configuration saved")
    
    def export_single_sensor_csv(self, sensor_id: str, filepath: str) -> Tuple[bool, str]:
        """
        Export data from a single sensor to CSV file
        
        Args:
            sensor_id: Sensor identifier (e.g., "Sensor1")
            filepath: Output CSV file path
            
        Returns:
            Tuple of (success, message)
            
        Example:
            >>> success, msg = app_controller.export_single_sensor_csv(
            ...     "Sensor1", "C:/data/sensor1_export.csv"
            ... )
            >>> if success:
            ...     print(f"Export succeeded: {msg}")
            ... else:
            ...     print(f"Export failed: {msg}")
        """
        # Validate sensor ID
        if sensor_id not in self.sensor_controllers:
            error_msg = f"Unknown sensor ID: {sensor_id}"
            logger.error(error_msg)
            return False, error_msg
        
        # Validate filepath
        is_valid, error_msg = Validators.validate_csv_path(filepath)
        if not is_valid:
            logger.error(f"Invalid filepath: {error_msg}")
            return False, error_msg
        
        # Get data buffer from sensor controller
        controller = self.sensor_controllers[sensor_id]
        data_buffer = controller.get_data_buffer()
        
        if not data_buffer:
            warning_msg = f"No data available for {sensor_id}"
            logger.warning(warning_msg)
            return False, warning_msg
        
        logger.info(
            f"Exporting {len(data_buffer)} records from {sensor_id} to {filepath}"
        )
        
        # Write to CSV using CSVWriter
        try:
            success, message = CSVWriter.write_single_sensor(filepath, data_buffer)
            
            if success:
                logger.info(f"Successfully exported {sensor_id} data: {message}")
            else:
                logger.error(f"Failed to export {sensor_id} data: {message}")
            
            return success, message
            
        except OSError as e:
            # Handle disk I/O errors (disk full, permissions, etc.)
            error_msg = f"File write error: {str(e)}"
            if "No space left on device" in str(e) or "[Errno 28]" in str(e):
                error_msg = "Disk full - insufficient space to write file"
            elif "Permission denied" in str(e) or "[Errno 13]" in str(e):
                error_msg = "Permission denied - cannot write to file"
            
            logger.error(f"OSError during CSV export: {error_msg}")
            return False, error_msg
            
        except Exception as e:
            # Catch any unexpected errors
            error_msg = f"Unexpected error during export: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def export_multi_sensor_csv(self, filepath: str,
                                sensor_ids: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Export synchronized data from multiple sensors to CSV file
        
        Args:
            filepath: Output CSV file path
            sensor_ids: List of sensor IDs to include (None = all sensors)
            
        Returns:
            Tuple of (success, message)
            
        Example:
            >>> # Export all sensors
            >>> success, msg = app_controller.export_multi_sensor_csv(
            ...     "C:/data/multi_sensor_export.csv"
            ... )
            
            >>> # Export specific sensors
            >>> success, msg = app_controller.export_multi_sensor_csv(
            ...     "C:/data/sensors_1_2.csv",
            ...     sensor_ids=["Sensor1", "Sensor2"]
            ... )
        """
        # Validate filepath
        is_valid, error_msg = Validators.validate_csv_path(filepath)
        if not is_valid:
            logger.error(f"Invalid filepath: {error_msg}")
            return False, error_msg
        
        # Determine which sensors to export
        if sensor_ids is None:
            # Export all sensors
            target_sensor_ids = list(self.sensor_controllers.keys())
        else:
            # Validate provided sensor IDs
            target_sensor_ids = []
            for sensor_id in sensor_ids:
                if sensor_id not in self.sensor_controllers:
                    error_msg = f"Unknown sensor ID: {sensor_id}"
                    logger.error(error_msg)
                    return False, error_msg
                target_sensor_ids.append(sensor_id)
        
        if not target_sensor_ids:
            error_msg = "No sensors specified for export"
            logger.error(error_msg)
            return False, error_msg
        
        # Collect data from all target sensors
        sensor_data_dict: Dict[str, List[SensorData]] = {}
        
        for sensor_id in target_sensor_ids:
            controller = self.sensor_controllers[sensor_id]
            data_buffer = controller.get_data_buffer()
            
            if data_buffer:
                sensor_data_dict[sensor_id] = data_buffer
                logger.debug(f"{sensor_id}: {len(data_buffer)} records collected")
            else:
                logger.warning(f"{sensor_id}: No data available")
        
        # Check if we have any data at all
        if not sensor_data_dict:
            warning_msg = "No data available from any selected sensor"
            logger.warning(warning_msg)
            return False, warning_msg
        
        total_records = sum(len(data) for data in sensor_data_dict.values())
        logger.info(
            f"Exporting {total_records} total records from "
            f"{len(sensor_data_dict)} sensors to {filepath}"
        )
        
        # Write to CSV using CSVWriter
        try:
            success, message = CSVWriter.write_multi_sensor(filepath, sensor_data_dict)
            
            if success:
                logger.info(f"Successfully exported multi-sensor data: {message}")
            else:
                logger.error(f"Failed to export multi-sensor data: {message}")
            
            return success, message
            
        except OSError as e:
            # Handle disk I/O errors (disk full, permissions, etc.)
            error_msg = f"File write error: {str(e)}"
            if "No space left on device" in str(e) or "[Errno 28]" in str(e):
                error_msg = "Disk full - insufficient space to write file"
            elif "Permission denied" in str(e) or "[Errno 13]" in str(e):
                error_msg = "Permission denied - cannot write to file"
            
            logger.error(f"OSError during CSV export: {error_msg}")
            return False, error_msg
            
        except Exception as e:
            # Catch any unexpected errors
            error_msg = f"Unexpected error during export: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _setup_memory_monitor(self) -> None:
        """
        Setup memory monitoring timer
        
        Creates a QTimer that checks memory usage every 30 seconds.
        Called during initialization.
        """
        self.memory_timer = QTimer(self)
        self.memory_timer.timeout.connect(self.check_memory_usage)
        self.memory_timer.start(self.MEMORY_CHECK_INTERVAL_MS)
        
        logger.info(
            f"Memory monitor started: checking every "
            f"{self.MEMORY_CHECK_INTERVAL_MS / 1000:.0f} seconds, "
            f"threshold={self.MEMORY_WARNING_THRESHOLD_MB}MB"
        )
    
    def check_memory_usage(self) -> None:
        """
        Check current memory usage and emit warning if threshold exceeded
        
        Called periodically by memory_timer (every 30 seconds).
        Uses psutil.Process().memory_info().rss to get resident set size.
        Emits memory_warning signal if usage exceeds 500MB threshold.
        """
        try:
            # Get current process
            process = psutil.Process()
            
            # Get memory info (rss = Resident Set Size in bytes)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
            
            logger.debug(f"Memory usage: {memory_mb:.1f} MB")
            
            # Check if memory exceeds threshold
            if memory_mb > self.MEMORY_WARNING_THRESHOLD_MB:
                logger.warning(
                    f"Memory usage exceeded threshold: {memory_mb:.1f} MB "
                    f"(threshold: {self.MEMORY_WARNING_THRESHOLD_MB} MB)"
                )
                
                # Emit warning signal
                self.memory_warning.emit(memory_mb)
                
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
    
    def stop_memory_monitor(self) -> None:
        """
        Stop memory monitoring timer
        
        Should be called during application shutdown.
        """
        if hasattr(self, 'memory_timer') and self.memory_timer.isActive():
            self.memory_timer.stop()
            logger.info("Memory monitor stopped")
