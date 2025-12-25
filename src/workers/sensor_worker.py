"""
Background worker thread for sensor communication
Handles serial I/O, initialization, and data streaming in a separate thread
Supports TriSonica JSON protocol (firmware 3.0.0+)
"""

import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal
import serial
from serial import SerialException

from src.utils.logger import get_logger
from src.utils.serial_parser import SerialParser, ParseError
from src.models.sensor_data import SensorData

logger = get_logger(__name__)


class SensorWorker(QThread):
    """
    Background thread for serial communication with a single sensor
    
    Runs independently to avoid blocking the GUI thread.
    Emits signals for data reception, connection status, and errors.
    """
    
    # Qt Signals for cross-thread communication
    data_received = pyqtSignal(SensorData)  # Emitted when valid data is parsed
    connection_status = pyqtSignal(str, bool)  # (sensor_id, is_connected)
    error_occurred = pyqtSignal(str, str)  # (sensor_id, error_message)
    initialization_progress = pyqtSignal(str, str)  # (sensor_id, command_sent)
    sensor_info_received = pyqtSignal(str, dict)  # (sensor_id, info_dict)
    
    def __init__(self, sensor_id: str, port: str, baud: int, init_commands: List[str]):
        """
        Initialize sensor worker thread
        
        Args:
            sensor_id: Identifier for this sensor
            port: COM port (e.g., "COM3")
            baud: Baud rate (e.g., 115200)
            init_commands: List of initialization commands to send
        """
        super().__init__()
        
        self.sensor_id = sensor_id
        self.port = port
        self.baud = baud
        self.init_commands = init_commands
        
        self._stop_requested = False
        self.serial_port: Optional[serial.Serial] = None
        self.buffer_overflow_count = 0
        
        logger.info(f"SensorWorker created for {sensor_id} on {port} @ {baud} baud")
    
    def run(self):
        """
        Main thread execution loop
        
        Sequence:
        1. Open serial port
        2. Send initialization commands
        3. Enter continuous read loop
        4. Handle cleanup on stop
        """
        try:
            # Open serial port
            logger.info(f"{self.sensor_id}: Opening serial port {self.port}")
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0,
                write_timeout=2.0
            )
            
            # Flush any existing data in buffers
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            self.connection_status.emit(self.sensor_id, True)
            logger.info(f"{self.sensor_id}: Serial port opened successfully")
            
            # Try JSON protocol initialization first
            sensor_info = self._try_json_initialization()
            
            if sensor_info:
                # JSON protocol succeeded
                logger.info(f"{self.sensor_id}: JSON protocol confirmed - sensor ready")
                self.sensor_info_received.emit(self.sensor_id, sensor_info)
            elif self.init_commands and len(self.init_commands) > 0:
                # Fallback to legacy CLI commands
                logger.info(f"{self.sensor_id}: JSON protocol not available, trying legacy CLI commands")
                self._send_init_commands()
            else:
                logger.info(f"{self.sensor_id}: No initialization - starting data read immediately")
            
            # Enter continuous read loop
            self._read_loop()
            
        except SerialException as e:
            error_msg = f"Serial port error: {str(e)}"
            logger.error(f"{self.sensor_id}: {error_msg}")
            self.error_occurred.emit(self.sensor_id, error_msg)
            self.connection_status.emit(self.sensor_id, False)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"{self.sensor_id}: {error_msg}", exc_info=True)
            self.error_occurred.emit(self.sensor_id, error_msg)
            self.connection_status.emit(self.sensor_id, False)
            
        finally:
            # Cleanup
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.close()
                    logger.info(f"{self.sensor_id}: Serial port closed")
                except Exception as e:
                    logger.error(f"{self.sensor_id}: Error closing port: {e}")
    
    def stop(self):
        """
        Request the worker thread to stop
        
        Sets the stop flag which will cause the read loop to exit.
        Call wait() after this to ensure thread has finished.
        """
        logger.info(f"{self.sensor_id}: Stop requested")
        self._stop_requested = True
    
    def send_command(self, command: str) -> bool:
        """
        Send a command to the sensor (thread-safe)
        
        Args:
            command: Command string (e.g., "{outputrate 10}")
        
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        if not self.serial_port or not self.serial_port.is_open:
            logger.error(f"{self.sensor_id}: Cannot send command - port not open")
            return False
        
        try:
            logger.info(f"{self.sensor_id}: Sending command: {command}")
            
            # Send command character by character (JSON protocol)
            for char in command:
                self.serial_port.write(char.encode('ascii'))
                time.sleep(0.01)  # 10ms delay between characters
            
            self.serial_port.flush()
            
            # Brief delay to allow sensor to process
            time.sleep(0.1)
            
            logger.info(f"{self.sensor_id}: Command sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"{self.sensor_id}: Failed to send command: {e}")
            return False
    
    def _try_json_initialization(self) -> Optional[Dict[str, Any]]:
        """
        Try to initialize sensor using JSON protocol (firmware 3.0.0+)
        
        Sequence:
        1. Send {json} command to check protocol support
        2. Send {version} command to get sensor info
        3. Send {settings} command to get configuration
        
        Returns:
            dict: Sensor information if JSON protocol is supported, None otherwise
        """
        if not self.serial_port or not self.serial_port.is_open:
            logger.error(f"{self.sensor_id}: Cannot send JSON commands - port not open")
            return None
        
        try:
            logger.info(f"{self.sensor_id}: Attempting JSON protocol initialization")
            
            # Clear any existing data
            time.sleep(0.3)
            self.serial_port.reset_input_buffer()
            
            # Step 1: Check JSON protocol support with {json} command
            json_response = self._send_json_command("{json}", timeout=2.0)
            
            if not json_response or 'error' in json_response:
                logger.info(f"{self.sensor_id}: JSON protocol not supported or not available")
                return None
            
            # Check if we got valid JSON protocol response
            if 'JSON' in json_response:
                fw_version = json_response.get('Version', 'unknown')
                logger.info(f"{self.sensor_id}: JSON protocol confirmed (FW: {fw_version})")
                self.initialization_progress.emit(self.sensor_id, f"JSON Protocol v{fw_version}")
            else:
                logger.warning(f"{self.sensor_id}: Unexpected JSON response: {json_response}")
                return None
            
            # Step 2: Get version information
            version_response = self._send_json_command("{version}", timeout=2.0)
            
            sensor_info = {
                'protocol': 'JSON',
                'firmware_version': fw_version,
                'json_response': json_response,
                'version_info': version_response
            }
            
            # Parse version info if available
            if version_response and 'raw' in version_response:
                raw_version = version_response['raw']
                # Extract model, serial number from text response
                for line in raw_version.split('\n'):
                    if 'TriSonica' in line:
                        sensor_info['model'] = line.strip()
                    elif 'Serial Number:' in line:
                        sensor_info['serial_number'] = line.split(':', 1)[1].strip()
                    elif 'Version:' in line and 'firmware_version' not in sensor_info:
                        sensor_info['firmware_version'] = line.split(':', 1)[1].strip()
                
                self.initialization_progress.emit(
                    self.sensor_id,
                    f"Model: {sensor_info.get('model', 'Unknown')}"
                )
            
            # Step 3: Get settings (optional, for information)
            settings_response = self._send_json_command("{settings}", timeout=3.0)
            
            if settings_response and 'Settings' in settings_response:
                settings = settings_response['Settings']
                sensor_info['settings'] = settings
                
                # Extract useful information
                model = settings.get('Model', 'Unknown')
                serial_num = settings.get('Serial Number', 'Unknown')
                sample_rate = settings.get('Probe', {}).get('SampleRate', 'Unknown')
                
                sensor_info['model'] = model
                sensor_info['serial_number'] = serial_num
                sensor_info['sample_rate'] = sample_rate
                
                # Extract enabled tags from Output configuration
                output_config = settings.get('Output', {})
                if output_config:
                    enabled_tags = []
                    tag_mapping = {
                        'Wind Speed': 'S',
                        'Wind Direction': 'D',
                        'Vertical Direction': 'DV',
                        'U': 'U',
                        'V': 'V',
                        'W': 'W',
                        'Sonic Temperature': 'T',
                        'Pitch': 'PI',
                        'Roll': 'RO',
                        'Status': 'ST'
                    }
                    
                    for key, tag in tag_mapping.items():
                        if output_config.get(key) == 'Yes':
                            enabled_tags.append(tag)
                    
                    if enabled_tags:
                        sensor_info['enabled_tags'] = enabled_tags
                        logger.info(f"{self.sensor_id}: Enabled tags: {', '.join(enabled_tags)}")
                
                logger.info(
                    f"{self.sensor_id}: Settings retrieved - "
                    f"Model: {model}, S/N: {serial_num}, Sample Rate: {sample_rate}Hz"
                )
                
                self.initialization_progress.emit(
                    self.sensor_id,
                    f"S/N: {serial_num}, Rate: {sample_rate}Hz"
                )
            
            # Small delay before starting data acquisition
            time.sleep(0.2)
            self.serial_port.reset_input_buffer()
            
            logger.info(f"{self.sensor_id}: JSON initialization completed successfully")
            return sensor_info
            
        except Exception as e:
            logger.warning(f"{self.sensor_id}: JSON initialization failed: {e}")
            return None
    
    def _send_json_command(self, command: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Send a JSON command to the sensor and parse response
        
        Args:
            command: JSON command string (e.g., "{json}", "{settings}")
            timeout: Response timeout in seconds
        
        Returns:
            dict: Parsed JSON response, or dict with 'error' key if failed
        """
        if not self.serial_port or not self.serial_port.is_open:
            return {'error': 'Port not open'}
        
        try:
            logger.debug(f"{self.sensor_id}: Sending JSON command: {command}")
            
            # Send command character by character (as observed in protocol log)
            for char in command:
                self.serial_port.write(char.encode('ascii'))
                time.sleep(0.01)  # 10ms delay between characters
            
            self.serial_port.flush()
            
            # Read response
            response_lines = []
            start_time = time.time()
            brace_count = 0
            in_json = False
            
            while (time.time() - start_time) < timeout:
                if self.serial_port.in_waiting > 0:
                    try:
                        line = self.serial_port.readline().decode('ascii', errors='ignore').strip()
                        
                        # Skip sensor data lines (start with "S ")
                        if line.startswith('S ') or line.startswith('s '):
                            continue
                        
                        if line:
                            logger.debug(f"{self.sensor_id}: JSON response line: {line}")
                            response_lines.append(line)
                            
                            # Track braces to detect complete JSON
                            if '{' in line:
                                in_json = True
                                brace_count += line.count('{')
                            if '}' in line:
                                brace_count -= line.count('}')
                            
                            # Complete JSON received
                            if in_json and brace_count <= 0:
                                break
                    
                    except Exception as e:
                        logger.warning(f"{self.sensor_id}: Error reading JSON response: {e}")
                
                time.sleep(0.05)
            
            if not response_lines:
                logger.warning(f"{self.sensor_id}: No response to JSON command: {command}")
                return {'error': 'No response'}
            
            # Join response lines
            response_text = '\n'.join(response_lines)
            
            # Check for error messages
            if 'Invalid Parameter' in response_text or 'Invalid Command' in response_text:
                logger.warning(f"{self.sensor_id}: JSON command rejected: {response_text}")
                return {'error': 'Invalid command'}
            
            # Try to parse as JSON
            try:
                # Handle nested JSON (outer braces may be wrapper)
                if response_text.startswith('{') and response_text.endswith('}'):
                    # Try parsing the full response
                    try:
                        parsed = json.loads(response_text)
                        # If it's a wrapper with single key, unwrap it
                        if len(parsed) == 1 and isinstance(list(parsed.values())[0], dict):
                            return list(parsed.values())[0]
                        return parsed
                    except json.JSONDecodeError:
                        # Try finding inner JSON
                        inner_start = response_text.find('{', 1)
                        inner_end = response_text.rfind('}', 0, -1)
                        if inner_start > 0 and inner_end > inner_start:
                            inner_json = response_text[inner_start:inner_end + 1]
                            return json.loads(inner_json)
                
                # Return as raw text if not parseable as JSON
                return {'raw': response_text}
                
            except json.JSONDecodeError as e:
                logger.debug(f"{self.sensor_id}: Could not parse as JSON: {e}")
                return {'raw': response_text}
        
        except Exception as e:
            logger.error(f"{self.sensor_id}: Error sending JSON command: {e}")
            return {'error': str(e)}
    
    def _send_init_commands(self):
        """
        Send legacy CLI initialization commands (fallback for older firmware)
        
        Sequence:
        1. Send Ctrl+C (0x03) to enter CLI mode
        2. Wait for prompt '>'
        3. Send each init command with 100ms delay
        
        Each command has a 2-second timeout for response.
        Emits initialization_progress signal for each command sent.
        """
        if not self.serial_port or not self.serial_port.is_open:
            logger.error(f"{self.sensor_id}: Cannot send init commands - port not open")
            return
        
        try:
            logger.info(f"{self.sensor_id}: Starting initialization sequence")
            
            # Step 1: Send Ctrl+C (0x03) to enter CLI mode
            logger.debug(f"{self.sensor_id}: Sending Ctrl+C to enter CLI mode")
            self.serial_port.write(b'\x03')
            self.serial_port.flush()
            self.initialization_progress.emit(self.sensor_id, "Ctrl+C (entering CLI mode)")
            
            # Step 2: Wait for prompt '>' to confirm CLI mode entry
            start_time = time.time()
            cli_mode_entered = False
            prompt_response = []
            
            while (time.time() - start_time) < 2.0:  # 2 second timeout for CLI mode entry
                if self.serial_port.in_waiting > 0:
                    try:
                        line = self.serial_port.readline().decode('ascii', errors='ignore').strip()
                        if line:
                            prompt_response.append(line)
                            logger.debug(f"{self.sensor_id}: CLI response: {line}")
                            
                            # Look for '>' prompt indicating CLI mode
                            if '>' in line:
                                cli_mode_entered = True
                                logger.info(f"{self.sensor_id}: CLI mode confirmed (prompt received)")
                                break
                    except Exception as e:
                        logger.warning(f"{self.sensor_id}: Error reading CLI prompt: {e}")
                
                time.sleep(0.05)
            
            if not cli_mode_entered:
                logger.warning(
                    f"{self.sensor_id}: CLI prompt '>' not detected. "
                    f"Received: {prompt_response}. Attempting to continue anyway..."
                )
            else:
                # Small delay after prompt before sending commands
                time.sleep(0.1)
            
            # Step 3: Send each initialization command
            for cmd in self.init_commands:
                if self._stop_requested:
                    logger.warning(f"{self.sensor_id}: Initialization interrupted by stop request")
                    return
                
                try:
                    # Send command
                    cmd_bytes = (cmd + '\r\n').encode('ascii')
                    logger.debug(f"{self.sensor_id}: Sending command: {cmd}")
                    self.serial_port.write(cmd_bytes)
                    self.serial_port.flush()
                    self.initialization_progress.emit(self.sensor_id, cmd)
                    
                    # Wait for response with timeout
                    start_time = time.time()
                    response_lines = []
                    
                    while (time.time() - start_time) < 2.0:  # 2 second timeout
                        if self.serial_port.in_waiting > 0:
                            try:
                                line = self.serial_port.readline().decode('ascii', errors='ignore').strip()
                                if line:
                                    response_lines.append(line)
                                    logger.debug(f"{self.sensor_id}: Response: {line}")
                                    
                                    # Check for error indicators
                                    if 'error' in line.lower() or 'invalid' in line.lower():
                                        error_msg = f"Command '{cmd}' returned error: {line}"
                                        logger.error(f"{self.sensor_id}: {error_msg}")
                                        self.error_occurred.emit(self.sensor_id, error_msg)
                            except Exception as e:
                                logger.warning(f"{self.sensor_id}: Error reading response: {e}")
                        
                        time.sleep(0.05)  # Small delay between checks
                    
                    # Check if we got any response
                    if not response_lines:
                        logger.warning(f"{self.sensor_id}: No response to command '{cmd}' (may be normal)")
                    
                    # Delay between commands
                    time.sleep(0.1)
                    
                except SerialException as e:
                    error_msg = f"Serial error sending command '{cmd}': {str(e)}"
                    logger.error(f"{self.sensor_id}: {error_msg}")
                    self.error_occurred.emit(self.sensor_id, error_msg)
                    raise
                
                except Exception as e:
                    error_msg = f"Unexpected error sending command '{cmd}': {str(e)}"
                    logger.error(f"{self.sensor_id}: {error_msg}")
                    self.error_occurred.emit(self.sensor_id, error_msg)
            
            logger.info(f"{self.sensor_id}: Initialization sequence completed successfully")
            
            # Clear any remaining data in buffer before starting data acquisition
            time.sleep(0.2)
            self.serial_port.reset_input_buffer()
            
        except SerialException as e:
            error_msg = f"Serial error during initialization: {str(e)}"
            logger.error(f"{self.sensor_id}: {error_msg}")
            self.error_occurred.emit(self.sensor_id, error_msg)
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error during initialization: {str(e)}"
            logger.error(f"{self.sensor_id}: {error_msg}", exc_info=True)
            self.error_occurred.emit(self.sensor_id, error_msg)
            raise
    
    def _read_loop(self):
        """
        Continuous data reading loop
        
        Reads lines from serial port, parses them, and emits signals.
        Handles buffer overflow, timeouts, and parsing errors.
        Continues until stop is requested or connection is lost.
        
        Error handling:
        - Buffer overflow (>4096 bytes): Flush and log warning
        - SerialException: Emit connection_status(False) and exit
        - ParseError: Log and continue (data line is skipped)
        - Timeout (2s): Log and continue
        - Error codes (-99.9, -99.99): Emit data with is_valid=False
        """
        logger.info(f"{self.sensor_id}: Entering data read loop")
        parser = SerialParser()
        
        while not self._stop_requested:
            try:
                # Check for buffer overflow (4096 bytes threshold)
                if self.serial_port and self.serial_port.in_waiting > 4096:
                    self.buffer_overflow_count += 1
                    logger.warning(
                        f"{self.sensor_id}: Input buffer overflow detected "
                        f"({self.serial_port.in_waiting} bytes). "
                        f"Flushing buffer. Overflow count: {self.buffer_overflow_count}"
                    )
                    self.serial_port.reset_input_buffer()
                    continue
                
                # Read line with 1 second timeout (set in serial port initialization)
                try:
                    line_bytes = self.serial_port.readline()
                    
                    # Check if we got a complete line (ends with \n)
                    if not line_bytes or not line_bytes.endswith(b'\n'):
                        # Timeout or incomplete data
                        if line_bytes:
                            logger.debug(
                                f"{self.sensor_id}: Incomplete line received, discarding: "
                                f"{line_bytes[:50]}"
                            )
                        continue
                    
                    # Decode line
                    line = line_bytes.decode('ascii', errors='ignore').strip()
                    
                    if not line:
                        continue  # Skip empty lines
                    
                    logger.debug(f"{self.sensor_id}: Received: {line}")
                    
                except SerialException as e:
                    logger.error(f"{self.sensor_id}: Serial error reading data: {e}")
                    self.connection_status.emit(self.sensor_id, False)
                    break
                
                # Parse the line
                try:
                    parsed_dict = parser.parse_line(line)
                    
                    # Validate parsed data (check for required tags)
                    if not parser.validate_data(parsed_dict):
                        logger.warning(
                            f"{self.sensor_id}: Incomplete data (missing required tags), skipping"
                        )
                        continue
                    
                    # Convert to SensorData
                    sensor_data = SensorData.from_parsed_dict(
                        sensor_id=self.sensor_id,
                        parsed=parsed_dict,
                        timestamp=datetime.now()
                    )
                    
                    # Check for error values (but still emit the data)
                    # The is_valid flag is already set during construction
                    if not sensor_data.is_valid:
                        logger.debug(
                            f"{self.sensor_id}: Data contains error codes (-99.9/-99.99)"
                        )
                    
                    # Emit data signal
                    self.data_received.emit(sensor_data)
                    
                except ParseError as e:
                    # Non-numeric values or parsing failure
                    logger.warning(f"{self.sensor_id}: Parse error: {e}. Line: {line}")
                    continue
                
                except ValueError as e:
                    # Conversion error
                    logger.warning(f"{self.sensor_id}: Value conversion error: {e}. Line: {line}")
                    continue
                
                except Exception as e:
                    # Unexpected parsing error
                    logger.error(
                        f"{self.sensor_id}: Unexpected error parsing data: {e}",
                        exc_info=True
                    )
                    continue
                
            except SerialException as e:
                # Connection lost
                logger.error(f"{self.sensor_id}: Serial exception in read loop: {e}")
                self.connection_status.emit(self.sensor_id, False)
                break
            
            except Exception as e:
                # Unexpected error in read loop
                logger.error(
                    f"{self.sensor_id}: Unexpected error in read loop: {e}",
                    exc_info=True
                )
                # Continue reading unless it's a critical error
                time.sleep(0.1)
        
        logger.info(
            f"{self.sensor_id}: Read loop exited. "
            f"Buffer overflows: {self.buffer_overflow_count}"
        )
