"""
Main Window for Multi-Trisonica GUI Application

This module implements the main window of the application with tabbed interface.
"""

import logging
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QAction, QMessageBox, QWidget, QVBoxLayout
)
from PyQt5.QtCore import Qt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.controllers.app_controller import AppController

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with tabbed interface
    
    Contains three main tabs:
    - Connection Tab: Sensor connection management
    - Single Sensor Tab: Single sensor data visualization
    - Multi Sensor Tab: Multi-sensor synchronized visualization
    
    Attributes:
        controller: Application controller instance
        tab_widget: QTabWidget containing all tabs
    """
    
    def __init__(self, controller: 'AppController'):
        """
        Initialize main window
        
        Args:
            controller: AppController instance for managing application logic
        """
        super().__init__()
        self.controller = controller
        
        # Set window properties
        self.setWindowTitle("Multi-Trisonica Data Acquisition")
        
        # Restore window geometry from config if available
        if self.controller.config.window_geometry:
            geom = self.controller.config.window_geometry
            if isinstance(geom, list) and len(geom) == 4:
                self.setGeometry(geom[0], geom[1], geom[2], geom[3])
            elif isinstance(geom, dict):
                self.setGeometry(
                    geom.get('x', 100),
                    geom.get('y', 100),
                    geom.get('width', 1280),
                    geom.get('height', 800)
                )
        else:
            # Default window size
            self.setGeometry(100, 100, 1280, 800)
        
        # Setup UI components
        self._setup_ui()
        self._setup_menu_bar()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """Setup the main user interface with tab widget"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Import and create tabs (avoid circular imports)
        # These will be implemented in subsequent tasks
        try:
            from src.views.connection_tab import ConnectionTab
            self.connection_tab = ConnectionTab(self.controller)
            self.tab_widget.addTab(self.connection_tab, "Connection")
        except ImportError:
            logger.warning("ConnectionTab not yet implemented")
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "Connection (Not Implemented)")
        
        try:
            from src.views.single_sensor_tab import SingleSensorTab
            self.single_sensor_tab = SingleSensorTab(self.controller)
            self.tab_widget.addTab(self.single_sensor_tab, "Single Sensor")
        except ImportError:
            logger.warning("SingleSensorTab not yet implemented")
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "Single Sensor (Not Implemented)")
        
        try:
            from src.views.multi_sensor_tab import MultiSensorTab
            self.multi_sensor_tab = MultiSensorTab(self.controller)
            self.tab_widget.addTab(self.multi_sensor_tab, "Multi Sensor")
        except ImportError:
            logger.warning("MultiSensorTab not yet implemented")
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "Multi Sensor (Not Implemented)")
        
        logger.debug("UI setup completed")
    
    def _setup_menu_bar(self):
        """Setup the menu bar with File menu"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        logger.debug("Menu bar setup completed")
    
    def closeEvent(self, event):
        """
        Handle window close event with graceful shutdown
        
        This method:
        1. Disconnects all sensors
        2. Saves current configuration
        3. Waits for worker threads to finish
        4. Accepts the close event
        
        Args:
            event: QCloseEvent instance
        """
        logger.info("Application closing - performing graceful shutdown")
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit?\nAll sensor connections will be closed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            event.ignore()
            return
        
        try:
            # Save window geometry to config
            geom = self.geometry()
            self.controller.config.window_geometry = [
                geom.x(), geom.y(), geom.width(), geom.height()
            ]
            
            # Disconnect all sensors and wait for threads to finish
            logger.info("Disconnecting all sensors...")
            self.controller.disconnect_all()
            
            # Save configuration
            logger.info("Saving configuration...")
            self.controller.save_config()
            
            logger.info("Graceful shutdown completed")
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            # Still accept the close event even if there was an error
            event.accept()
