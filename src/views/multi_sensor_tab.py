"""
Multi Sensor Tab for Multi-Trisonica GUI Application

This module implements the multi-sensor synchronized visualization tab.
"""

import logging
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from src.controllers.app_controller import AppController

from src.utils.validators import Validators
from src.models.sensor_data import SensorData

logger = logging.getLogger(__name__)


class MultiSensorTab(QWidget):
    """
    Multi-sensor synchronized visualization tab
    
    Provides:
    - 4x3 grid of plots (4 sensors × 3 components U/V/W)
    - Synchronized X-axis (time) across all plots
    - Temperature/humidity table for all sensors
    - Recording controls (Start All, Stop All, Clear All)
    - Multi-sensor CSV export with time synchronization
    
    Attributes:
        controller: Application controller reference
        figure: Matplotlib figure with 4x3 subplots
        canvas: Qt canvas for matplotlib
        axes: Dictionary mapping sensor_id to (axes_u, axes_v, axes_w)
        lines: Dictionary mapping sensor_id to (line_u, line_v, line_w)
        temp_humidity_table: QTableWidget for temperature/humidity display
        start_button, stop_button, clear_button, save_button: Control buttons
        update_timer: Timer for plot updates (30 FPS)
        is_recording: Recording state flag
    """
    
    def __init__(self, controller: 'AppController'):
        """
        Initialize multi-sensor tab
        
        Args:
            controller: Application controller instance
        """
        super().__init__()
        self.controller = controller
        self.is_recording = False
        
        # Axes and lines storage
        self.axes: Dict[str, tuple] = {}  # {sensor_id: (axes_u, axes_v, axes_w)}
        self.lines: Dict[str, tuple] = {}  # {sensor_id: (line_u, line_v, line_w)}
        
        self._setup_ui()
        self._setup_plots()
        
        # Update timer (30 FPS = ~33ms)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plots)
        
        logger.info("MultiSensorTab initialized")
    
    def _setup_ui(self):
        """Setup the tab user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Control panel
        control_group = QGroupBox("Recording Controls")
        control_layout = QHBoxLayout()
        control_group.setLayout(control_layout)
        
        self.start_button = QPushButton("Start All")
        self.start_button.clicked.connect(self._on_start_clicked)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop All")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        control_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("Save Multi-Sensor CSV")
        self.save_button.clicked.connect(self._on_save_csv_clicked)
        control_layout.addWidget(self.save_button)
        
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        # Temperature and Humidity table
        temp_humidity_group = QGroupBox("Temperature and Humidity")
        temp_humidity_layout = QVBoxLayout()
        temp_humidity_group.setLayout(temp_humidity_layout)
        
        self.temp_humidity_table = QTableWidget()
        self.temp_humidity_table.setRowCount(4)
        self.temp_humidity_table.setColumnCount(2)
        self.temp_humidity_table.setHorizontalHeaderLabels(["Temperature", "Humidity"])
        self.temp_humidity_table.setVerticalHeaderLabels(["Sensor1", "Sensor2", "Sensor3", "Sensor4"])
        self.temp_humidity_table.setMaximumHeight(150)
        
        # Initialize table with default values
        for row in range(4):
            self.temp_humidity_table.setItem(row, 0, QTableWidgetItem("--°C"))
            self.temp_humidity_table.setItem(row, 1, QTableWidgetItem("N/A"))
        
        temp_humidity_layout.addWidget(self.temp_humidity_table)
        layout.addWidget(temp_humidity_group)
        
        # Matplotlib plot grid (4 rows × 3 columns)
        plot_group = QGroupBox("Velocity Components (All Sensors)")
        plot_layout = QVBoxLayout()
        plot_group.setLayout(plot_layout)
        
        self.figure = Figure(figsize=(12, 10))
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)
        
        layout.addWidget(plot_group)
    
    def _setup_plots(self):
        """Setup matplotlib subplots in 4x3 grid"""
        self.figure.clear()
        
        sensor_ids = ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]
        component_labels = ["U (East-West)", "V (North-South)", "W (Vertical)"]
        colors = ['b', 'g', 'r']  # Blue, Green, Red for U, V, W
        
        for row, sensor_id in enumerate(sensor_ids):
            axes_list = []
            lines_list = []
            
            for col, (component, color) in enumerate(zip(component_labels, colors)):
                # Create subplot (4 rows, 3 columns)
                ax = self.figure.add_subplot(4, 3, row * 3 + col + 1)
                
                # Configure axis
                ax.set_title(f"{sensor_id} - {component}", fontsize=9)
                ax.set_ylabel('Velocity (m/s)', fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
                
                # Only show x-label on bottom row
                if row == 3:
                    ax.set_xlabel('Time (s)', fontsize=8)
                
                # Create empty line
                line, = ax.plot([], [], color=color, linewidth=1)
                
                axes_list.append(ax)
                lines_list.append(line)
            
            # Store axes and lines for this sensor
            self.axes[sensor_id] = tuple(axes_list)
            self.lines[sensor_id] = tuple(lines_list)
        
        self.figure.tight_layout()
        self.canvas.draw()
        
        logger.debug("Multi-sensor plots initialized")
    
    @pyqtSlot()
    def _on_start_clicked(self):
        """Handle Start All button click"""
        self.is_recording = True
        self.update_timer.start(33)  # 30 FPS
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        logger.info("Multi-sensor recording started")
    
    @pyqtSlot()
    def _on_stop_clicked(self):
        """Handle Stop All button click"""
        self.is_recording = False
        self.update_timer.stop()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        logger.info("Multi-sensor recording stopped")
    
    @pyqtSlot()
    def _on_clear_clicked(self):
        """Handle Clear All button click"""
        # Confirm clear operation
        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Clear all data for all sensors?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Clear all sensor buffers
        for sensor_id in ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]:
            sensor_controller = self.controller.sensor_controllers.get(sensor_id)
            if sensor_controller:
                sensor_controller.clear_buffer()
        
        # Clear plots
        self._setup_plots()
        
        # Reset temperature/humidity table
        for row in range(4):
            self.temp_humidity_table.item(row, 0).setText("--°C")
            self.temp_humidity_table.item(row, 1).setText("N/A")
        
        logger.info("All sensor data cleared")
    
    @pyqtSlot()
    def _update_plots(self):
        """Update all plots with latest data (called by timer)"""
        if not self.is_recording:
            return
        
        try:
            # Find global time range across all sensors
            all_times = []
            sensor_data_map = {}
            
            for sensor_id in ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]:
                sensor_controller = self.controller.sensor_controllers.get(sensor_id)
                if not sensor_controller:
                    continue
                
                data_buffer = sensor_controller.get_data_buffer()
                if not data_buffer:
                    sensor_data_map[sensor_id] = None
                    continue
                
                # Get latest 1000 points
                recent_data = data_buffer[-1000:]
                sensor_data_map[sensor_id] = recent_data
                
                # Collect timestamps for synchronization
                if recent_data:
                    first_time = recent_data[0].timestamp
                    times = [(d.timestamp - first_time).total_seconds() for d in recent_data]
                    all_times.extend(times)
            
            # Determine common X-axis limits
            if all_times:
                x_min = min(all_times)
                x_max = max(all_times)
            else:
                x_min, x_max = 0, 1
            
            # Update each sensor's plots
            for sensor_id in ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]:
                axes_u, axes_v, axes_w = self.axes[sensor_id]
                line_u, line_v, line_w = self.lines[sensor_id]
                
                recent_data = sensor_data_map.get(sensor_id)
                
                if recent_data:
                    # Extract data
                    first_time = recent_data[0].timestamp
                    times = [(d.timestamp - first_time).total_seconds() for d in recent_data]
                    u_values = [d.u_component if not d.is_error_value(d.u_component) else np.nan for d in recent_data]
                    v_values = [d.v_component if not d.is_error_value(d.v_component) else np.nan for d in recent_data]
                    w_values = [d.w_component if not d.is_error_value(d.w_component) else np.nan for d in recent_data]
                    
                    # Update lines
                    line_u.set_data(times, u_values)
                    line_v.set_data(times, v_values)
                    line_w.set_data(times, w_values)
                    
                    # Rescale Y axes
                    axes_u.relim()
                    axes_u.autoscale_view(scalex=False)
                    axes_v.relim()
                    axes_v.autoscale_view(scalex=False)
                    axes_w.relim()
                    axes_w.autoscale_view(scalex=False)
                    
                    # Update temperature/humidity table
                    latest_data = recent_data[-1]
                    self._update_temp_humidity_table(sensor_id, latest_data)
                    
                else:
                    # No data - show "No Data" text
                    line_u.set_data([], [])
                    line_v.set_data([], [])
                    line_w.set_data([], [])
                    
                    # Clear text if exists, then add new one
                    for ax in [axes_u, axes_v, axes_w]:
                        # Remove old "No Data" texts
                        for txt in ax.texts:
                            txt.remove()
                        ax.text(0.5, 0.5, 'No Data', 
                               horizontalalignment='center',
                               verticalalignment='center',
                               transform=ax.transAxes,
                               fontsize=12, color='gray')
                
                # Synchronize X-axis
                axes_u.set_xlim(x_min, x_max)
                axes_v.set_xlim(x_min, x_max)
                axes_w.set_xlim(x_min, x_max)
            
            # Redraw canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating multi-sensor plots: {e}", exc_info=True)
    
    def _update_temp_humidity_table(self, sensor_id: str, data: SensorData):
        """
        Update temperature/humidity table for a specific sensor
        
        Args:
            sensor_id: Sensor identifier
            data: Latest sensor data
        """
        try:
            # Determine row index
            sensor_ids = ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]
            row = sensor_ids.index(sensor_id)
            
            # Update temperature
            if data.is_error_value(data.temperature):
                temp_text = "--°C"
            else:
                temp = data.temperature
                temp_text = f"{temp:.2f}°C"
                
                # Warn if out of range
                if temp < -40 or temp > 60:
                    self.temp_humidity_table.item(row, 0).setForeground(Qt.darkYellow)
                else:
                    self.temp_humidity_table.item(row, 0).setForeground(Qt.black)
            
            self.temp_humidity_table.item(row, 0).setText(temp_text)
            
            # Humidity is always N/A
            self.temp_humidity_table.item(row, 1).setText("N/A")
            
        except Exception as e:
            logger.error(f"Error updating temp/humidity table: {e}")
    
    @pyqtSlot()
    def _on_save_csv_clicked(self):
        """Handle Save Multi-Sensor CSV button click"""
        try:
            # Check if any sensor has data
            has_data = False
            for sensor_id in ["Sensor1", "Sensor2", "Sensor3", "Sensor4"]:
                sensor_controller = self.controller.sensor_controllers.get(sensor_id)
                if sensor_controller and sensor_controller.get_data_buffer():
                    has_data = True
                    break
            
            if not has_data:
                QMessageBox.information(self, "No Data", "No data to save from any sensor")
                return
            
            # Show file dialog
            default_filename = f"MultiSensor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Save Multi-Sensor CSV File",
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
            
            # Export multi-sensor CSV
            success = self.controller.export_multi_sensor_csv(filepath)
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Multi-sensor CSV file saved successfully:\n{filepath}"
                )
                logger.info(f"Multi-sensor CSV exported to {filepath}")
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
