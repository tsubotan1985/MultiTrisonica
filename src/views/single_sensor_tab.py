"""
Single Sensor Tab for Multi-Trisonica GUI Application

This module implements the single sensor visualization tab with real-time plotting.
"""

import logging
import numpy as np
from collections import deque
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QComboBox, QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from src.controllers.app_controller import AppController

from src.utils.validators import Validators
from src.models.sensor_data import SensorData

logger = logging.getLogger(__name__)


class SingleSensorTab(QWidget):
    """
    Single sensor visualization tab
    
    Provides:
    - Sensor selection dropdown
    - Real-time plotting of U, V, W velocity components
    - Temperature and humidity display
    - Recording controls (Start, Stop, Clear)
    - CSV export functionality
    
    Attributes:
        controller: Application controller reference
        sensor_combo: Sensor selection dropdown
        figure: Matplotlib figure
        canvas: Qt canvas for matplotlib
        axes_u, axes_v, axes_w: Subplot axes for velocity components
        line_u, line_v, line_w: Line2D objects for plotting
        temp_label: Temperature display label
        humidity_label: Humidity display label
        start_button, stop_button, clear_button, save_button: Control buttons
        update_timer: Timer for plot updates (30 FPS)
        is_recording: Recording state flag
        plot_data: Dictionary holding plot data buffers
    """
    
    def __init__(self, controller: 'AppController'):
        """
        Initialize single sensor tab
        
        Args:
            controller: Application controller instance
        """
        super().__init__()
        self.controller = controller
        self.is_recording = False
        self.selected_sensor = None
        
        # Plot data buffers (for efficient plotting)
        self.plot_data = {
            'timestamps': deque(maxlen=1000),
            'u': deque(maxlen=1000),
            'v': deque(maxlen=1000),
            'w': deque(maxlen=1000)
        }
        
        self._setup_ui()
        self._setup_plots()
        
        # Update timer (30 FPS = ~33ms)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plots)
        
        logger.info("SingleSensorTab initialized")
    
    def _setup_ui(self):
        """Setup the tab user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Control panel
        control_group = QGroupBox("Sensor Selection and Controls")
        control_layout = QHBoxLayout()
        control_group.setLayout(control_layout)
        
        # Sensor selection
        control_layout.addWidget(QLabel("Sensor:"))
        self.sensor_combo = QComboBox()
        self.sensor_combo.addItem("Select a sensor...")
        for sensor_id in ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]:
            self.sensor_combo.addItem(sensor_id)
        self.sensor_combo.currentTextChanged.connect(self._on_sensor_changed)
        control_layout.addWidget(self.sensor_combo)
        
        control_layout.addStretch()
        
        # Control buttons
        self.start_button = QPushButton("Start Recording")
        self.start_button.clicked.connect(self._on_start_clicked)
        self.start_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("Clear Data")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.clear_button.setEnabled(False)
        control_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("Save CSV")
        self.save_button.clicked.connect(self._on_save_csv_clicked)
        self.save_button.setEnabled(False)
        control_layout.addWidget(self.save_button)
        
        layout.addWidget(control_group)
        
        # Temperature and Humidity display
        temp_humidity_group = QGroupBox("Temperature and Humidity")
        temp_humidity_layout = QHBoxLayout()
        temp_humidity_group.setLayout(temp_humidity_layout)
        
        temp_humidity_layout.addWidget(QLabel("Temperature:"))
        self.temp_label = QLabel("--°C")
        self.temp_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        temp_humidity_layout.addWidget(self.temp_label)
        
        temp_humidity_layout.addStretch()
        
        temp_humidity_layout.addWidget(QLabel("Humidity:"))
        self.humidity_label = QLabel("N/A")
        self.humidity_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        temp_humidity_layout.addWidget(self.humidity_label)
        
        layout.addWidget(temp_humidity_group)
        
        # Matplotlib plot
        plot_group = QGroupBox("Velocity Components")
        plot_layout = QVBoxLayout()
        plot_group.setLayout(plot_layout)
        
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)
        
        layout.addWidget(plot_group)
    
    def _setup_plots(self):
        """Setup matplotlib subplots for U, V, W components"""
        self.figure.clear()
        
        # Create 3 vertically stacked subplots
        self.axes_u = self.figure.add_subplot(3, 1, 1)
        self.axes_v = self.figure.add_subplot(3, 1, 2)
        self.axes_w = self.figure.add_subplot(3, 1, 3)
        
        # Configure U axis
        self.axes_u.set_ylabel('U Velocity (m/s)')
        self.axes_u.grid(True, alpha=0.3)
        self.line_u, = self.axes_u.plot([], [], 'b-', linewidth=1)
        self.axes_u.set_title('U Component (East-West)')
        
        # Configure V axis
        self.axes_v.set_ylabel('V Velocity (m/s)')
        self.axes_v.grid(True, alpha=0.3)
        self.line_v, = self.axes_v.plot([], [], 'g-', linewidth=1)
        self.axes_v.set_title('V Component (North-South)')
        
        # Configure W axis
        self.axes_w.set_xlabel('Time (s)')
        self.axes_w.set_ylabel('W Velocity (m/s)')
        self.axes_w.grid(True, alpha=0.3)
        self.line_w, = self.axes_w.plot([], [], 'r-', linewidth=1)
        self.axes_w.set_title('W Component (Vertical)')
        
        self.figure.tight_layout()
        self.canvas.draw()
        
        logger.debug("Plots initialized")
    
    @pyqtSlot(str)
    def _on_sensor_changed(self, sensor_id: str):
        """
        Handle sensor selection change
        
        Args:
            sensor_id: Selected sensor identifier
        """
        if sensor_id == "Select a sensor...":
            self.selected_sensor = None
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.save_button.setEnabled(False)
        else:
            self.selected_sensor = sensor_id
            self.start_button.setEnabled(True)
            self.clear_button.setEnabled(True)
            self.save_button.setEnabled(True)
            logger.info(f"Sensor changed to {sensor_id}")
    
    @pyqtSlot()
    def _on_start_clicked(self):
        """Handle Start Recording button click"""
        if not self.selected_sensor:
            return
        
        self.is_recording = True
        self.update_timer.start(33)  # 30 FPS
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.sensor_combo.setEnabled(False)
        
        logger.info(f"Recording started for {self.selected_sensor}")
    
    @pyqtSlot()
    def _on_stop_clicked(self):
        """Handle Stop Recording button click"""
        self.is_recording = False
        self.update_timer.stop()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.sensor_combo.setEnabled(True)
        
        logger.info(f"Recording stopped for {self.selected_sensor}")
    
    @pyqtSlot()
    def _on_clear_clicked(self):
        """Handle Clear Data button click"""
        if not self.selected_sensor:
            return
        
        # Confirm clear operation
        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            f"Clear all data for {self.selected_sensor}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Clear controller buffer
        sensor_controller = self.controller.sensor_controllers.get(self.selected_sensor)
        if sensor_controller:
            sensor_controller.clear_buffer()
        
        # Clear local plot buffers
        self.plot_data['timestamps'].clear()
        self.plot_data['u'].clear()
        self.plot_data['v'].clear()
        self.plot_data['w'].clear()
        
        # Clear plots
        self._setup_plots()
        
        # Reset temperature display
        self.temp_label.setText("--°C")
        
        logger.info(f"Data cleared for {self.selected_sensor}")
    
    @pyqtSlot()
    def _update_plots(self):
        """Update plots with latest data (called by timer)"""
        if not self.selected_sensor or not self.is_recording:
            return
        
        try:
            # Get sensor controller
            sensor_controller = self.controller.sensor_controllers.get(self.selected_sensor)
            if not sensor_controller:
                return
            
            # Get latest data from buffer
            data_buffer = sensor_controller.get_data_buffer()
            
            if not data_buffer:
                return
            
            # Extract latest 1000 points (rolling window)
            recent_data = data_buffer[-1000:]
            
            # Extract timestamps and velocity components
            if recent_data:
                # Get first timestamp for relative time
                first_time = recent_data[0].timestamp
                
                times = [(d.timestamp - first_time).total_seconds() for d in recent_data]
                u_values = [d.u_component if not d.is_error_value(d.u_component) else np.nan for d in recent_data]
                v_values = [d.v_component if not d.is_error_value(d.v_component) else np.nan for d in recent_data]
                w_values = [d.w_component if not d.is_error_value(d.w_component) else np.nan for d in recent_data]
                
                # Update line data
                self.line_u.set_data(times, u_values)
                self.line_v.set_data(times, v_values)
                self.line_w.set_data(times, w_values)
                
                # Rescale axes
                self.axes_u.relim()
                self.axes_u.autoscale_view()
                self.axes_v.relim()
                self.axes_v.autoscale_view()
                self.axes_w.relim()
                self.axes_w.autoscale_view()
                
                # Update temperature display
                latest_data = recent_data[-1]
                self._update_temp_humidity(latest_data)
                
                # Redraw canvas
                self.canvas.draw()
                
        except Exception as e:
            logger.error(f"Error updating plots: {e}", exc_info=True)
    
    def _update_temp_humidity(self, data: SensorData):
        """
        Update temperature and humidity display
        
        Args:
            data: Latest sensor data
        """
        try:
            if data.is_error_value(data.temperature):
                self.temp_label.setText("--°C")
                self.temp_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            else:
                temp = data.temperature
                self.temp_label.setText(f"{temp:.2f}°C")
                
                # Warning for out-of-range temperature
                if temp < -40 or temp > 60:
                    self.temp_label.setStyleSheet(
                        "font-weight: bold; font-size: 14px; color: #FFA500;"
                    )
                else:
                    self.temp_label.setStyleSheet(
                        "font-weight: bold; font-size: 14px; color: #000000;"
                    )
            
            # Humidity is always N/A for this sensor
            self.humidity_label.setText("N/A")
            
        except Exception as e:
            logger.error(f"Error updating temperature/humidity: {e}")
    
    @pyqtSlot()
    def _on_save_csv_clicked(self):
        """Handle Save CSV button click"""
        if not self.selected_sensor:
            return
        
        try:
            # Get sensor controller
            sensor_controller = self.controller.sensor_controllers.get(self.selected_sensor)
            if not sensor_controller:
                QMessageBox.warning(self, "Error", "Sensor controller not found")
                return
            
            # Check if there's data to save
            data_buffer = sensor_controller.get_data_buffer()
            if not data_buffer:
                QMessageBox.information(self, "No Data", "No data to save")
                return
            
            # Show file dialog
            default_filename = f"{self.selected_sensor}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Save CSV File",
                default_filename,
                "CSV Files (*.csv)"
            )
            
            if not filepath:
                return  # User cancelled
            
            # Validate filepath
            if not Validators.validate_csv_path(filepath):
                QMessageBox.warning(
                    self,
                    "Invalid Path",
                    "Invalid file path. Please use a valid path with .csv extension."
                )
                return
            
            # Export CSV
            success = self.controller.export_single_sensor_csv(self.selected_sensor, filepath)
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"CSV file saved successfully:\n{filepath}"
                )
                logger.info(f"CSV exported to {filepath}")
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    "Failed to export CSV file. Check logs for details."
                )
            
        except OSError as e:
            logger.error(f"OSError during CSV export: {e}")
            QMessageBox.critical(
                self,
                "File Error",
                f"Failed to save CSV file:\n{e}"
            )
        except Exception as e:
            logger.error(f"Error during CSV export: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred:\n{e}"
            )
