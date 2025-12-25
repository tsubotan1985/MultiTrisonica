"""
SensorController - Manages a single sensor's connection and data buffering

Coordinates the SensorWorker thread and maintains a circular buffer of received data.
Provides thread-safe access to sensor data and connection management.
Supports TriSonica JSON protocol for sensor information retrieval.
"""

import threading
from collections import deque
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from src.utils.logger import get_logger
from src.workers.sensor_worker import SensorWorker
from src.models.sensor_data import SensorData
from src.models.app_config import SensorConfig

logger = get_logger(__name__)


@dataclass
class ConnectionState:
    """Current connection state for a sensor"""
    is_connected: bool = False
    reconnect_count: int = 0
    last_error: Optional[str] = None
    sensor_info: Dict[str, Any] = field(default_factory=dict)


class SensorController(QObject):
    """
    Controller for a single sensor
    
    Manages:
    - SensorWorker thread lifecycle
    - Data buffer (circular deque with max 200000 entries)
    - Connection state and reconnection logic
    - Thread-safe data access
    - Sensor information from JSON protocol
    """
    
    # Qt Signals
    sensor_info_updated = pyqtSignal(str, dict)  # (sensor_id, info_dict)
    initialization_status = pyqtSignal(str, str)  # (sensor_id, status_message)
    
    # Maximum reconnection attempts
    MAX_RECONNECT_ATTEMPTS = 4
    
    def __init__(self, sensor_id: str, config: SensorConfig):
        """
        Initialize sensor controller
        
        Args:
            sensor_id: Unique identifier for this sensor
            config: Sensor configuration (port, baud, init commands)
        """
        super().__init__()
        
        self.sensor_id = sensor_id
        self.config = config
        
        # Data buffer (circular buffer with max 200000 entries for long-term measurements)
        # At 25Hz sampling rate: ~133 minutes (2.2 hours) of continuous data
        self.data_buffer: deque[SensorData] = deque(maxlen=200000)
        self.latest_data: Optional[SensorData] = None
        
        # Thread synchronization
        self._buffer_lock = threading.Lock()
        
        # Connection state
        self.state = ConnectionState()
        
        # Worker thread reference
        self.worker: Optional[SensorWorker] = None
        
        # Reconnection tracking
        self._reconnect_timer: Optional[QTimer] = None
        self._is_reconnecting = False
        
        logger.info(
            f"SensorController created for '{sensor_id}' "
            f"(port: {config.port}, baud: {config.baud})"
        )
    
    def connect(self) -> bool:
        """
        Start sensor connection
        
        Creates and starts the SensorWorker thread.
        Connects worker signals to controller slots.
        
        Returns:
            True if worker was started successfully, False if already connected
        """
        if self.worker is not None and self.worker.isRunning():
            logger.warning(f"{self.sensor_id}: Already connected")
            return False
        
        logger.info(f"{self.sensor_id}: Starting sensor connection")
        
        # Create worker thread
        self.worker = SensorWorker(
            sensor_id=self.sensor_id,
            port=self.config.port,
            baud=self.config.baud,
            init_commands=self.config.custom_init_commands
        )
        
        # Connect signals
        self.worker.data_received.connect(self._on_data_received)
        self.worker.connection_status.connect(self._on_connection_status)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.initialization_progress.connect(self._on_init_progress)
        self.worker.sensor_info_received.connect(self._on_sensor_info_received)
        
        # Start worker thread
        self.worker.start()
        
        logger.info(f"{self.sensor_id}: Worker thread started")
        return True
    
    def disconnect(self) -> None:
        """
        Stop sensor connection
        
        Requests worker thread to stop and waits for it to finish.
        Cancels any pending reconnection attempts.
        """
        if self.worker is None:
            logger.warning(f"{self.sensor_id}: No worker to disconnect")
            return
        
        logger.info(f"{self.sensor_id}: Disconnecting sensor")
        
        # Cancel any pending reconnection
        self._cancel_reconnection()
        
        # Request worker to stop
        self.worker.stop()
        
        # Wait for worker thread to finish (with timeout)
        if not self.worker.wait(5000):  # 5 second timeout
            logger.error(f"{self.sensor_id}: Worker thread did not stop within timeout")
        else:
            logger.info(f"{self.sensor_id}: Worker thread stopped")
        
        # Clear worker reference
        self.worker = None
        
        # Update connection state
        self.state.is_connected = False
    
    def get_data_buffer(self) -> List[SensorData]:
        """
        Get a copy of the data buffer
        
        Thread-safe access to the data buffer.
        Returns a list copy to avoid concurrent modification issues.
        
        Returns:
            List of SensorData objects (copy of deque)
        """
        with self._buffer_lock:
            return list(self.data_buffer)
    
    def clear_buffer(self) -> None:
        """
        Clear the data buffer
        
        Thread-safe buffer clearing operation.
        Useful when starting a new measurement or resetting state.
        """
        with self._buffer_lock:
            self.data_buffer.clear()
            logger.debug(f"{self.sensor_id}: Data buffer cleared")
    
    def get_latest_data(self) -> Optional[SensorData]:
        """
        Get the most recent data point
        
        Returns:
            Latest SensorData or None if no data received yet
        """
        with self._buffer_lock:
            return self.latest_data
    
    def get_buffer_size(self) -> int:
        """
        Get current number of entries in buffer
        
        Returns:
            Number of data points in buffer
        """
        with self._buffer_lock:
            return len(self.data_buffer)
    
    def is_connected(self) -> bool:
        """
        Check if sensor is currently connected
        
        Returns:
            True if connected, False otherwise
        """
        return self.state.is_connected
    
    def get_reconnect_count(self) -> int:
        """
        Get number of reconnection attempts
        
        Returns:
            Reconnection attempt counter
        """
        return self.state.reconnect_count
    
    def _on_data_received(self, data: SensorData) -> None:
        """
        Slot for handling received sensor data
        
        Called by SensorWorker.data_received signal when new data arrives.
        Adds data to the circular buffer and updates latest_data.
        Thread-safe operation using buffer lock.
        
        Args:
            data: Received SensorData object
        """
        with self._buffer_lock:
            # Add to circular buffer (auto-removes oldest if > 10000 entries)
            self.data_buffer.append(data)
            
            # Update latest data reference
            self.latest_data = data
        
        # Log debug info (outside lock to minimize lock hold time)
        logger.debug(
            f"{self.sensor_id}: Data received - "
            f"U={data.u_component:.2f}, V={data.v_component:.2f}, W={data.w_component:.2f}, "
            f"T={data.temperature:.1f}°C, "
            f"Buffer={len(self.data_buffer)}/200000"
        )
    
    def _on_connection_status(self, sensor_id: str, is_connected: bool) -> None:
        """
        Slot for handling connection status changes
        
        Called by SensorWorker.connection_status signal.
        Updates connection state and triggers reconnection if disconnected.
        
        Args:
            sensor_id: ID of the sensor (should match self.sensor_id)
            is_connected: True if connected, False if disconnected
        """
        if sensor_id != self.sensor_id:
            logger.warning(
                f"{self.sensor_id}: Received status for different sensor: {sensor_id}"
            )
            return
        
        self.state.is_connected = is_connected
        
        if is_connected:
            logger.info(f"{self.sensor_id}: Connection established")
            # Reset reconnect counter on successful connection
            self.state.reconnect_count = 0
            self._is_reconnecting = False
        else:
            logger.warning(f"{self.sensor_id}: Connection lost")
            # Trigger reconnection logic
            self._schedule_reconnection()
    
    def _on_error_occurred(self, sensor_id: str, error_message: str) -> None:
        """
        Slot for handling worker errors
        
        Called by SensorWorker.error_occurred signal.
        Logs error and stores in connection state.
        
        Args:
            sensor_id: ID of the sensor (should match self.sensor_id)
            error_message: Error description
        """
        if sensor_id != self.sensor_id:
            logger.warning(
                f"{self.sensor_id}: Received error for different sensor: {sensor_id}"
            )
            return
        
        logger.error(f"{self.sensor_id}: Worker error - {error_message}")
        self.state.last_error = error_message
    
    def _on_init_progress(self, sensor_id: str, progress_message: str) -> None:
        """
        Slot for handling initialization progress updates
        
        Called by SensorWorker.initialization_progress signal.
        Forwards initialization status to views.
        
        Args:
            sensor_id: ID of the sensor (should match self.sensor_id)
            progress_message: Progress description (e.g., "JSON Protocol v3.0.0")
        """
        if sensor_id != self.sensor_id:
            logger.warning(
                f"{self.sensor_id}: Received init progress for different sensor: {sensor_id}"
            )
            return
        
        logger.info(f"{self.sensor_id}: Initialization progress - {progress_message}")
        self.initialization_status.emit(self.sensor_id, progress_message)
    
    def _on_sensor_info_received(self, sensor_id: str, info_dict: Dict[str, Any]) -> None:
        """
        Slot for handling sensor information from JSON protocol
        
        Called by SensorWorker.sensor_info_received signal when JSON protocol
        initialization succeeds.
        
        Args:
            sensor_id: ID of the sensor (should match self.sensor_id)
            info_dict: Dictionary containing sensor information
        """
        if sensor_id != self.sensor_id:
            logger.warning(
                f"{self.sensor_id}: Received sensor info for different sensor: {sensor_id}"
            )
            return
        
        # Store sensor info in connection state
        self.state.sensor_info = info_dict
        
        # Log sensor information
        model = info_dict.get('model', 'Unknown')
        serial_num = info_dict.get('serial_number', 'Unknown')
        fw_version = info_dict.get('firmware_version', 'Unknown')
        protocol = info_dict.get('protocol', 'Unknown')
        sample_rate = info_dict.get('sample_rate', 'Unknown')
        
        logger.info(
            f"{self.sensor_id}: Sensor info received - "
            f"Protocol: {protocol}, Model: {model}, S/N: {serial_num}, "
            f"FW: {fw_version}, Rate: {sample_rate}Hz"
        )
        
        # Emit signal for views to update
        self.sensor_info_updated.emit(self.sensor_id, info_dict)
    
    def get_sensor_info(self) -> Dict[str, Any]:
        """
        Get stored sensor information
        
        Returns:
            Dictionary with sensor information (empty if not available)
        """
        return self.state.sensor_info.copy()
    
    def _schedule_reconnection(self) -> None:
        """
        Schedule reconnection attempt with exponential backoff
        
        Uses exponential backoff: 1s, 2s, 4s, 8s
        Maximum 4 attempts (reconnect_count: 0->1, 1->2, 2->4, 3->8)
        """
        if self._is_reconnecting:
            logger.debug(f"{self.sensor_id}: Reconnection already scheduled")
            return
        
        if self.state.reconnect_count >= self.MAX_RECONNECT_ATTEMPTS:
            logger.error(
                f"{self.sensor_id}: Max reconnection attempts ({self.MAX_RECONNECT_ATTEMPTS}) "
                "reached. Giving up."
            )
            return
        
        # Calculate backoff delay: 1s, 2s, 4s, 8s
        delay_ms = 1000 * (2 ** self.state.reconnect_count)
        
        logger.info(
            f"{self.sensor_id}: Scheduling reconnection attempt "
            f"{self.state.reconnect_count + 1}/{self.MAX_RECONNECT_ATTEMPTS} "
            f"in {delay_ms}ms"
        )
        
        self._is_reconnecting = True
        self.state.reconnect_count += 1
        
        # Use QTimer.singleShot for delayed reconnection
        QTimer.singleShot(delay_ms, self._attempt_reconnection)
    
    def _attempt_reconnection(self) -> None:
        """
        Attempt to reconnect to the sensor
        
        Called by QTimer after exponential backoff delay.
        """
        if not self._is_reconnecting:
            logger.debug(f"{self.sensor_id}: Reconnection cancelled")
            return
        
        logger.info(
            f"{self.sensor_id}: Attempting reconnection "
            f"(attempt {self.state.reconnect_count}/{self.MAX_RECONNECT_ATTEMPTS})"
        )
        
        # Disconnect any existing worker
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(2000)  # 2 second timeout
            self.worker = None
        
        # Try to reconnect
        success = self.connect()
        
        if not success:
            logger.warning(f"{self.sensor_id}: Reconnection attempt failed")
            self._is_reconnecting = False
            # Connection status signal will trigger next retry if needed
    
    def _cancel_reconnection(self) -> None:
        """
        Cancel any pending reconnection attempts
        
        Called when user manually disconnects.
        """
        if self._is_reconnecting:
            logger.info(f"{self.sensor_id}: Cancelling reconnection")
            self._is_reconnecting = False
            self.state.reconnect_count = 0
