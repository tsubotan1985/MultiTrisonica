"""
CSV export utilities for sensor data
Handles single and multi-sensor data export with proper formatting
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from src.models.sensor_data import SensorData
from src.utils.validators import Validators
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CSVWriter:
    """
    Utility class for writing sensor data to CSV files
    """
    
    # CSV header for single sensor export
    SINGLE_SENSOR_HEADER = [
        'Timestamp', 'Sensor_ID', 'S', 'D', 'U', 'V', 'W', 'T', 'PI', 'RO'
    ]
    
    # Tolerance for timestamp matching (seconds)
    TIMESTAMP_TOLERANCE = timedelta(seconds=0.5)
    
    @staticmethod
    def _format_timestamp(timestamp: datetime) -> str:
        """
        Format timestamp in ISO 8601 format with milliseconds
        
        Args:
            timestamp: Datetime object to format
            
        Returns:
            Formatted string: YYYY-MM-DD HH:mm:ss.fff
            
        Example:
            >>> dt = datetime(2024, 1, 1, 12, 0, 0, 123456)
            >>> CSVWriter._format_timestamp(dt)
            '2024-01-01 12:00:00.123'
        """
        return timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    @staticmethod
    def _validate_filepath(filepath: str) -> tuple[bool, str]:
        """
        Validate filepath for security (prevent path traversal attacks)
        
        Args:
            filepath: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return Validators.validate_csv_path(filepath)
    
    @staticmethod
    def write_single_sensor(filepath: str, data: List[SensorData]) -> tuple[bool, str]:
        """
        Write single sensor data to CSV file with UTF-8 BOM for Excel compatibility
        
        Args:
            filepath: Output CSV file path
            data: List of SensorData objects to write
            
        Returns:
            Tuple of (success, message)
            
        Example:
            >>> sensor_data = [SensorData(...), SensorData(...)]
            >>> success, msg = CSVWriter.write_single_sensor("output.csv", sensor_data)
        """
        # Validate filepath
        is_valid, error_msg = CSVWriter._validate_filepath(filepath)
        if not is_valid:
            logger.error(f"Invalid filepath: {error_msg}")
            return False, error_msg
        
        # Check if data is empty
        if not data:
            logger.warning("No data to write")
            return False, "No data to write"
        
        try:
            # Create parent directories if they don't exist
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Write with UTF-8 BOM for Excel compatibility
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(CSVWriter.SINGLE_SENSOR_HEADER)
                
                # Write data rows
                for sensor_data in data:
                    writer.writerow(sensor_data.to_csv_row())
            
            logger.info(f"Wrote {len(data)} records to {filepath}")
            return True, f"Successfully wrote {len(data)} records"
            
        except OSError as e:
            error_msg = f"File write error: {str(e)}"
            if "No space left on device" in str(e) or "[Errno 28]" in str(e):
                error_msg = "Disk full - insufficient space to write file"
            elif "Permission denied" in str(e) or "[Errno 13]" in str(e):
                error_msg = "Permission denied - cannot write to file"
            
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def _synchronize_timestamps(sensor_data_dict: Dict[str, List[SensorData]]) -> List[Dict[str, SensorData]]:
        """
        Synchronize data from multiple sensors by timestamp using nearest-neighbor matching
        
        Algorithm:
        1. Collect all unique timestamps from all sensors
        2. Sort timestamps
        3. For each timestamp, find the nearest data point from each sensor (within ±0.5s tolerance)
        4. Create synchronized rows with matched data or N/A for missing sensors
        
        Args:
            sensor_data_dict: Dictionary mapping sensor_id to list of SensorData
            
        Returns:
            List of dictionaries, each containing timestamp and sensor data for all sensors
            
        Example:
            >>> data = {
            ...     'Sensor1': [SensorData(...), ...],
            ...     'Sensor2': [SensorData(...), ...]
            ... }
            >>> synchronized = CSVWriter._synchronize_timestamps(data)
        """
        if not sensor_data_dict:
            return []
        
        # Collect all timestamps
        all_timestamps = set()
        for sensor_data_list in sensor_data_dict.values():
            for data in sensor_data_list:
                all_timestamps.add(data.timestamp)
        
        # Sort timestamps
        sorted_timestamps = sorted(all_timestamps)
        
        # Build synchronized rows
        synchronized_rows = []
        
        for target_timestamp in sorted_timestamps:
            row = {'timestamp': target_timestamp}
            
            # Find nearest data point from each sensor
            for sensor_id, sensor_data_list in sensor_data_dict.items():
                nearest_data = None
                min_time_diff = CSVWriter.TIMESTAMP_TOLERANCE
                
                for data in sensor_data_list:
                    time_diff = abs(data.timestamp - target_timestamp)
                    if time_diff <= min_time_diff:
                        min_time_diff = time_diff
                        nearest_data = data
                
                row[sensor_id] = nearest_data
            
            synchronized_rows.append(row)
        
        return synchronized_rows
    
    @staticmethod
    def write_multi_sensor(filepath: str, sensor_data_dict: Dict[str, List[SensorData]]) -> tuple[bool, str]:
        """
        Write multi-sensor synchronized data to CSV file
        
        Columns format:
        Timestamp, Sensor1_ID, S1_S, S1_D, S1_U, S1_V, S1_W, S1_T, S1_PI, S1_RO,
        Sensor2_ID, S2_S, S2_D, S2_U, S2_V, S2_W, S2_T, S2_PI, S2_RO, ...
        
        Args:
            filepath: Output CSV file path
            sensor_data_dict: Dictionary mapping sensor_id to list of SensorData
            
        Returns:
            Tuple of (success, message)
            
        Example:
            >>> data_dict = {
            ...     'Sensor1': [SensorData(...), ...],
            ...     'Sensor2': [SensorData(...), ...],
            ...     'Sensor3': [SensorData(...), ...],
            ...     'Sensor4': [SensorData(...), ...]
            ... }
            >>> success, msg = CSVWriter.write_multi_sensor("multi.csv", data_dict)
        """
        # Validate filepath
        is_valid, error_msg = CSVWriter._validate_filepath(filepath)
        if not is_valid:
            logger.error(f"Invalid filepath: {error_msg}")
            return False, error_msg
        
        # Check if data is empty
        if not sensor_data_dict or all(len(data) == 0 for data in sensor_data_dict.values()):
            logger.warning("No data to write")
            return False, "No data to write"
        
        try:
            # Synchronize timestamps
            synchronized_rows = CSVWriter._synchronize_timestamps(sensor_data_dict)
            
            if not synchronized_rows:
                return False, "No synchronized data available"
            
            # Build header
            sensor_ids = sorted(sensor_data_dict.keys())
            header = ['Timestamp']
            for sensor_id in sensor_ids:
                header.extend([
                    f'{sensor_id}_ID',
                    f'{sensor_id}_S',
                    f'{sensor_id}_D',
                    f'{sensor_id}_U',
                    f'{sensor_id}_V',
                    f'{sensor_id}_W',
                    f'{sensor_id}_T',
                    f'{sensor_id}_PI',
                    f'{sensor_id}_RO'
                ])
            
            # Create parent directories if they don't exist
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Write with UTF-8 BOM for Excel compatibility
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(header)
                
                # Write data rows
                for row in synchronized_rows:
                    csv_row = [CSVWriter._format_timestamp(row['timestamp'])]
                    
                    for sensor_id in sensor_ids:
                        sensor_data = row.get(sensor_id)
                        
                        if sensor_data is None:
                            # No data for this sensor at this timestamp
                            csv_row.extend(['N/A'] * 9)
                        else:
                            # Add sensor data
                            csv_row.extend([
                                sensor_data.sensor_id,
                                f"{sensor_data.speed_2d:.2f}",
                                f"{sensor_data.direction:.2f}",
                                f"{sensor_data.u_component:.2f}",
                                f"{sensor_data.v_component:.2f}",
                                f"{sensor_data.w_component:.2f}",
                                f"{sensor_data.temperature:.2f}",
                                f"{sensor_data.pitch:.2f}",
                                f"{sensor_data.roll:.2f}"
                            ])
                    
                    writer.writerow(csv_row)
            
            logger.info(f"Wrote {len(synchronized_rows)} synchronized records to {filepath}")
            return True, f"Successfully wrote {len(synchronized_rows)} synchronized records"
            
        except OSError as e:
            error_msg = f"File write error: {str(e)}"
            if "No space left on device" in str(e) or "[Errno 28]" in str(e):
                error_msg = "Disk full - insufficient space to write file"
            elif "Permission denied" in str(e) or "[Errno 13]" in str(e):
                error_msg = "Permission denied - cannot write to file"
            
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
