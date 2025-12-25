"""
Connection Tab for Multi-Trisonica GUI Application

This module implements the connection tab containing sensor connection panels
and output rate configuration.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QTextEdit, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from src.controllers.app_controller import AppController

from src.utils.validators import Validators

logger = logging.getLogger(__name__)


class SensorConnectionPanel(QGroupBox):
    """
    Panel for configuring and connecting a single sensor
    
    Provides UI for:
    - COM port selection
    - Baud rate selection
    - Custom initialization commands
    - Connection/disconnection control
    - Status LED indicator
    
    Attributes:
        sensor_id: Identifier for this sensor (e.g., "Sensor1")
        controller: Application controller reference
        port_combo: COM port dropdown
        baud_combo: Baud rate dropdown
        init_commands_edit: Text area for initialization commands
        connect_button: Connect/Disconnect button
        status_led: Status indicator label
        refresh_button: Button to refresh COM port list
    """
    
    def __init__(self, sensor_id: str, controller: 'AppController'):
        """
        Initialize sensor connection panel
        
        Args:
            sensor_id: Sensor identifier (e.g., "Sensor1")
            controller: Application controller instance
        """
        super().__init__(sensor_id)
        self.sensor_id = sensor_id
        self.controller = controller
        self.is_connected = False
        
        self._setup_ui()
        self._load_config()
        
        logger.debug(f"{sensor_id}: SensorConnectionPanel initialized")
    
    def _setup_ui(self):
        """Setup the panel user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # COM Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("COM Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(100)
        port_layout.addWidget(self.port_combo)
        
        self.refresh_button = QPushButton("↻")
        self.refresh_button.setMaximumWidth(30)
        self.refresh_button.setToolTip("Refresh COM port list")
        self.refresh_button.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.refresh_button)
        
        layout.addLayout(port_layout)
        
        # Baud Rate selection
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("Baud Rate:"))
        self.baud_combo = QComboBox()
        self.baud_combo.setMinimumWidth(100)
        # Populate with valid baud rates
        for baud in Validators.VALID_BAUD_RATES:
            self.baud_combo.addItem(str(baud), baud)
        # Set default to 115200
        default_index = self.baud_combo.findData(115200)
        if default_index >= 0:
            self.baud_combo.setCurrentIndex(default_index)
        baud_layout.addWidget(self.baud_combo)
        baud_layout.addStretch()
        layout.addLayout(baud_layout)
        
        # Sensor Info Display (initially hidden, shown after connection)
        self.info_group = QGroupBox("Sensor Information")
        self.info_group.setVisible(False)
        info_layout = QVBoxLayout()
        self.info_group.setLayout(info_layout)
        
        self.info_label = QLabel("No sensor information available")
        self.info_label.setWordWrap(True)
        font = QFont("Courier New", 9)
        self.info_label.setFont(font)
        info_layout.addWidget(self.info_label)
        layout.addWidget(self.info_group)
        
        # Initialization Commands
        layout.addWidget(QLabel("Initialization Commands:"))
        self.init_commands_edit = QTextEdit()
        self.init_commands_edit.setMaximumHeight(60)
        self.init_commands_edit.setPlaceholderText("Enter initialization commands (one per line)")
        
        # Set default initialization commands (docs/Trisonica-setting-datatransfer.md)
        # Based on actual Trisonica sensor command syntax
        default_commands = []
        self.init_commands_edit.setPlainText("\n".join(default_commands))
        layout.addWidget(self.init_commands_edit)
        
        # Status and Connect button
        status_layout = QHBoxLayout()
        
        # Status LED
        self.status_led = QLabel()
        self.status_led.setFixedSize(20, 20)
        self._update_status_led(False, False)
        status_layout.addWidget(self.status_led)
        
        status_layout.addStretch()
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        status_layout.addWidget(self.connect_button)
        
        layout.addLayout(status_layout)
        
        # Populate COM ports
        self._refresh_ports()
    
    def _load_config(self):
        """Load saved configuration for this sensor"""
        try:
            sensor_config = self.controller.config.sensors.get(self.sensor_id)
            if sensor_config:
                # Set COM port if saved
                if sensor_config.port:
                    index = self.port_combo.findText(sensor_config.port)
                    if index >= 0:
                        self.port_combo.setCurrentIndex(index)
                
                # Set baud rate if saved
                if sensor_config.baud:
                    index = self.baud_combo.findData(sensor_config.baud)
                    if index >= 0:
                        self.baud_combo.setCurrentIndex(index)
                
                # Set custom init commands if saved
                if sensor_config.custom_init_commands:
                    self.init_commands_edit.setPlainText(
                        "\n".join(sensor_config.custom_init_commands)
                    )
        except Exception as e:
            logger.warning(f"{self.sensor_id}: Failed to load config: {e}")
    
    def _refresh_ports(self):
        """Refresh the list of available COM ports"""
        try:
            current_port = self.port_combo.currentText()
            self.port_combo.clear()
            
            # Get available ports from controller (returns list of port names as strings)
            ports = self.controller.get_available_ports()
            
            if ports:
                for port in ports:
                    self.port_combo.addItem(port)
                
                # Try to restore previous selection
                if current_port:
                    index = self.port_combo.findText(current_port)
                    if index >= 0:
                        self.port_combo.setCurrentIndex(index)
            else:
                self.port_combo.addItem("No ports available")
            
            logger.debug(f"{self.sensor_id}: Refreshed COM ports, found {len(ports)} ports")
        except Exception as e:
            logger.error(f"{self.sensor_id}: Failed to refresh ports: {e}")
            QMessageBox.warning(self, "Error", f"Failed to refresh COM ports: {e}")
    
    @pyqtSlot()
    def _on_connect_clicked(self):
        """Handle connect/disconnect button click"""
        if self.is_connected:
            # Disconnect
            self._disconnect()
        else:
            # Connect
            self._connect()
    
    def _connect(self):
        """Connect to the sensor"""
        try:
            # Get selected values
            port = self.port_combo.currentText()
            baud = self.baud_combo.currentData()
            
            # Validate inputs
            if not Validators.validate_com_port(port):
                QMessageBox.warning(self, "Invalid Input", f"Invalid COM port: {port}")
                return
            
            if not Validators.validate_baud_rate(baud):
                QMessageBox.warning(self, "Invalid Input", f"Invalid baud rate: {baud}")
                return
            
            # Get initialization commands
            commands_text = self.init_commands_edit.toPlainText()
            init_commands = [
                cmd.strip()
                for cmd in commands_text.split('\n')
                if cmd.strip()
            ]
            
            # Save connection settings to config
            from src.models.app_config import SensorConfig
            sensor_config = SensorConfig(
                port=port,
                baud=baud,
                custom_init_commands=init_commands
            )
            self.controller.config.update_sensor_config(self.sensor_id, sensor_config)
            self.controller.save_config()
            logger.debug(f"{self.sensor_id}: Connection settings saved to config")
            
            # Connect via controller
            logger.info(f"{self.sensor_id}: Connecting to {port} at {baud} baud")
            self.controller.connect_sensor(self.sensor_id, port, baud, init_commands)
            
            # Update UI state
            self.is_connected = True
            self.connect_button.setText("Disconnect")
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.init_commands_edit.setEnabled(False)
            self.refresh_button.setEnabled(False)
            
            # Connect to sensor controller signals
            sensor_controller = self.controller.sensor_controllers.get(self.sensor_id)
            if sensor_controller and sensor_controller.worker:
                sensor_controller.worker.connection_status.connect(
                    self._on_connection_status_changed
                )
                sensor_controller.worker.error_occurred.connect(
                    self._on_error_occurred
                )
                sensor_controller.worker.sensor_info_received.connect(
                    self._on_sensor_info_received
                )
            
            self._update_status_led(True, False)  # Connected but not yet receiving
            
        except Exception as e:
            logger.error(f"{self.sensor_id}: Connection failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {e}")
    
    def _disconnect(self):
        """Disconnect from the sensor"""
        try:
            logger.info(f"{self.sensor_id}: Disconnecting")
            self.controller.disconnect_sensor(self.sensor_id)
            
            # Update UI state
            self.is_connected = False
            self.connect_button.setText("Connect")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.init_commands_edit.setEnabled(True)
            self.refresh_button.setEnabled(True)
            
            self._update_status_led(False, False)
            
        except Exception as e:
            logger.error(f"{self.sensor_id}: Disconnection failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Disconnection Error", f"Failed to disconnect: {e}")
    
    @pyqtSlot(str, bool)
    def _on_connection_status_changed(self, sensor_id: str, connected: bool):
        """
        Handle connection status change from worker
        
        Args:
            sensor_id: Sensor identifier
            connected: True if connected, False if disconnected
        """
        if not connected and self.is_connected:
            # Connection lost
            logger.warning(f"{self.sensor_id}: Connection lost")
            self._update_status_led(False, False)
            
            QMessageBox.warning(
                self,
                "Connection Lost",
                f"{self.sensor_id} connection lost. Attempting to reconnect..."
            )
        elif connected:
            # Successfully connected/reconnected
            logger.info(f"{self.sensor_id}: Connection established")
            self._update_status_led(True, True)
    
    @pyqtSlot(str, str)
    def _on_error_occurred(self, sensor_id: str, error_message: str):
        """
        Handle error from worker
        
        Args:
            sensor_id: Sensor identifier
            error_message: Error description
        """
        logger.error(f"{self.sensor_id}: Error occurred: {error_message}")
        self._update_status_led(True, False)  # Connected but error state
        
        QMessageBox.warning(
            self,
            f"{self.sensor_id} Error",
            f"An error occurred:\n{error_message}"
        )
    
    def _update_status_led(self, connected: bool, receiving: bool):
        """
        Update the status LED indicator
        
        Args:
            connected: True if sensor is connected
            receiving: True if receiving valid data
        """
        if connected and receiving:
            # Green: Connected and receiving data
            color = "#4CAF50"
            tooltip = f"{self.sensor_id}: Connected and receiving data"
        elif connected and not receiving:
            # Yellow: Connected but not receiving or error
            color = "#FFC107"
            tooltip = f"{self.sensor_id}: Connected but not receiving valid data"
        else:
            # Red: Disconnected
            color = "#F44336"
            tooltip = f"{self.sensor_id}: Disconnected"
        
        self.status_led.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 10px;
                border: 1px solid #333;
            }}
        """)
        self.status_led.setToolTip(tooltip)
    
    @pyqtSlot(str, dict)
    def _on_sensor_info_received(self, sensor_id: str, info: dict):
        """
        Handle sensor information received from worker
        
        Args:
            sensor_id: Sensor identifier
            info: Dictionary containing sensor information
        """
        if sensor_id != self.sensor_id:
            return
        
        logger.info(f"{self.sensor_id}: Received sensor information")
        
        # Format sensor information for display
        info_text = []
        
        protocol = info.get('protocol', 'Unknown')
        info_text.append(f"Protocol: {protocol}")
        
        if 'model' in info:
            info_text.append(f"Model: {info['model']}")
        
        if 'serial_number' in info:
            info_text.append(f"S/N: {info['serial_number']}")
        
        if 'firmware_version' in info:
            info_text.append(f"Firmware: {info['firmware_version']}")
        
        if 'sample_rate' in info:
            rate = info['sample_rate']
            if isinstance(rate, (int, float)):
                info_text.append(f"Sample Rate: {rate} Hz")
        
        # Display enabled tags if available
        if 'enabled_tags' in info:
            enabled_tags = info['enabled_tags']
            if enabled_tags:
                info_text.append(f"\nEnabled Tags: {', '.join(enabled_tags)}")
        
        # Display in info panel
        self.info_label.setText('\n'.join(info_text))
        self.info_group.setVisible(True)


class ConnectionTab(QWidget):
    """
    Connection tab containing sensor connection panels and output rate control
    
    Provides:
    - Output rate configuration (1-10 Hz)
    - 4 sensor connection panels in 2x2 grid layout
    
    Attributes:
        controller: Application controller reference
        output_rate_spinbox: SpinBox for output rate configuration
        sensor_panels: Dictionary of sensor connection panels
    """
    
    def __init__(self, controller: 'AppController'):
        """
        Initialize connection tab
        
        Args:
            controller: Application controller instance
        """
        super().__init__()
        self.controller = controller
        self.sensor_panels: Dict[str, SensorConnectionPanel] = {}
        
        self._setup_ui()
        
        logger.info("ConnectionTab initialized")
    
    def _setup_ui(self):
        """Setup the tab user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Output Rate Configuration
        rate_group = QGroupBox("Output Rate Configuration")
        rate_layout = QHBoxLayout()
        rate_group.setLayout(rate_layout)
        
        rate_layout.addWidget(QLabel("Output Rate:"))
        self.output_rate_spinbox = QSpinBox()
        self.output_rate_spinbox.setRange(1, 10)
        self.output_rate_spinbox.setValue(self.controller.config.output_rate)
        self.output_rate_spinbox.setSuffix(" Hz")
        self.output_rate_spinbox.setToolTip("Data output rate (1-10 Hz)")
        self.output_rate_spinbox.valueChanged.connect(self._on_output_rate_changed)
        rate_layout.addWidget(self.output_rate_spinbox)
        rate_layout.addStretch()
        
        layout.addWidget(rate_group)
        
        # Sensor Connection Panels (2x2 grid)
        panels_group = QGroupBox("Sensor Connections")
        panels_layout = QGridLayout()
        panels_group.setLayout(panels_layout)
        
        # Create 4 sensor panels
        sensor_ids = ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for sensor_id, (row, col) in zip(sensor_ids, positions):
            panel = SensorConnectionPanel(sensor_id, self.controller)
            self.sensor_panels[sensor_id] = panel
            panels_layout.addWidget(panel, row, col)
        
        layout.addWidget(panels_group)
        layout.addStretch()
    
    @pyqtSlot(int)
    def _on_output_rate_changed(self, value: int):
        """
        Handle output rate change
        
        Args:
            value: New output rate in Hz
        """
        try:
            if not Validators.validate_output_rate(value):
                logger.warning(f"Invalid output rate: {value}")
                return
            
            logger.info(f"Output rate changed to {value} Hz")
            
            # Update config
            self.controller.config.output_rate = value
            self.controller.save_config()
            
            # Send outputrate command to all connected JSON protocol sensors
            for sensor_id, panel in self.sensor_panels.items():
                if panel.is_connected:
                    sensor_controller = self.controller.sensor_controllers.get(sensor_id)
                    if sensor_controller and sensor_controller.worker:
                        # Check if sensor supports JSON protocol
                        if hasattr(sensor_controller, 'state') and sensor_controller.state.sensor_info:
                            protocol = sensor_controller.state.sensor_info.get('protocol')
                            if protocol == 'JSON':
                                # Send JSON command to change output rate
                                command = f"{{outputrate {value}}}"
                                success = sensor_controller.worker.send_command(command)
                                if success:
                                    logger.info(f"Output rate command sent to {sensor_id}: {value} Hz")
                                else:
                                    logger.warning(f"Failed to send output rate command to {sensor_id}")
                            else:
                                logger.debug(f"{sensor_id} does not support JSON protocol, skipping output rate change")
                        else:
                            logger.debug(f"{sensor_id} sensor info not available yet, skipping output rate change")
            
        except Exception as e:
            logger.error(f"Failed to update output rate: {e}", exc_info=True)
