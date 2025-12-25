"""
CSVWriter単体テスト

CSVWriterクラスの機能を検証:
- 単一センサーCSVフォーマットとヘッダーテスト
- マルチセンサーCSV同期ロジックテスト
- タイムスタンプフォーマット(ISO 8601)テスト
- 欠損データ(N/A値)の処理テスト
- _validate_filepath()のパストラバーサル攻撃防止テスト
"""

import pytest
import csv
from datetime import datetime, timedelta
from pathlib import Path
from src.utils.csv_writer import CSVWriter
from src.models.sensor_data import SensorData


class TestCSVWriter:
    """CSVWriterクラスのテストスイート"""

    def test_format_timestamp(self):
        """タイムスタンプフォーマット(ISO 8601 with milliseconds)"""
        dt = datetime(2024, 1, 15, 13, 45, 30, 123456)
        formatted = CSVWriter._format_timestamp(dt)
        
        assert formatted == "2024-01-15 13:45:30.123"
        assert len(formatted) == 23  # YYYY-MM-DD HH:MM:SS.fff

    def test_validate_filepath_valid(self):
        """有効なCSVパスの検証"""
        valid_path = "test_output.csv"
        is_valid, error_msg = CSVWriter._validate_filepath(valid_path)
        
        assert is_valid is True
        assert error_msg == ""

    def test_validate_filepath_path_traversal(self):
        """パストラバーサル攻撃の検出"""
        malicious_path = "../../../etc/passwd.csv"
        is_valid, error_msg = CSVWriter._validate_filepath(malicious_path)
        
        assert is_valid is False
        assert "traversal" in error_msg.lower()

    def test_write_single_sensor_success(self, tmp_path):
        """単一センサーCSVの正常な書き込み"""
        output_file = tmp_path / "single_sensor.csv"
        
        # テストデータ作成
        parsed_data = [
            {'S': 5.23, 'D': 270.15, 'U': 2.45, 'V': -1.33, 'W': 0.12, 'T': 23.45, 'PI': 45.2, 'RO': 1013.2},
            {'S': 4.67, 'D': 315.89, 'U': 3.30, 'V': -3.30, 'W': 0.01, 'T': 21.34, 'PI': 50.12, 'RO': 1013.25}
        ]
        sensor_data_list = [SensorData.from_parsed_dict("Sensor1", d) for d in parsed_data]
        
        # 書き込み
        success, message = CSVWriter.write_single_sensor(str(output_file), sensor_data_list)
        
        assert success is True
        assert "2 records" in message
        assert output_file.exists()

    def test_write_single_sensor_csv_format(self, tmp_path):
        """単一センサーCSVのフォーマット検証"""
        output_file = tmp_path / "format_test.csv"
        
        parsed = {'S': 5.23, 'D': 270.15, 'U': 2.45, 'V': -1.33, 'W': 0.12, 'T': 23.45, 'PI': 45.2, 'RO': 1013.2}
        sensor_data = SensorData.from_parsed_dict("TestSensor", parsed)
        
        CSVWriter.write_single_sensor(str(output_file), [sensor_data])
        
        # CSVを読み込んで検証
        with open(output_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # ヘッダー確認
        assert rows[0] == ['Timestamp', 'Sensor_ID', 'S', 'D', 'U', 'V', 'W', 'T', 'PI', 'RO']
        
        # データ行確認
        assert len(rows) == 2  # ヘッダー + データ1行
        assert rows[1][1] == "TestSensor"
        assert rows[1][2] == "5.23"  # S
        assert rows[1][3] == "270.15"  # D

    def test_write_single_sensor_empty_data(self, tmp_path):
        """空データの処理"""
        output_file = tmp_path / "empty.csv"
        
        success, message = CSVWriter.write_single_sensor(str(output_file), [])
        
        assert success is False
        assert "No data" in message

    def test_write_single_sensor_invalid_path(self):
        """無効なパスでの書き込み失敗"""
        invalid_path = "../invalid/../test.csv"
        
        parsed = {'S': 5.23, 'D': 270.15, 'U': 2.45, 'V': -1.33, 'W': 0.12, 'T': 23.45}
        sensor_data = SensorData.from_parsed_dict("Sensor1", parsed)
        
        success, message = CSVWriter.write_single_sensor(invalid_path, [sensor_data])
        
        assert success is False
        assert "traversal" in message.lower()

    def test_write_single_sensor_utf8_bom(self, tmp_path):
        """UTF-8 BOM付きで保存（Excel互換性）"""
        output_file = tmp_path / "bom_test.csv"
        
        parsed = {'S': 5.23, 'D': 270.15, 'U': 2.45, 'V': -1.33, 'W': 0.12, 'T': 23.45}
        sensor_data = SensorData.from_parsed_dict("Sensor1", parsed)
        
        CSVWriter.write_single_sensor(str(output_file), [sensor_data])
        
        # BOMの確認
        with open(output_file, 'rb') as f:
            first_bytes = f.read(3)
        
        # UTF-8 BOMは 0xEF, 0xBB, 0xBF
        assert first_bytes == b'\xef\xbb\xbf'

    def test_synchronize_timestamps_exact_match(self):
        """タイムスタンプが完全一致する場合の同期"""
        timestamp = datetime.now()
        
        sensor1_data = SensorData.from_parsed_dict(
            "Sensor1",
            {'S': 5.0, 'D': 270.0, 'U': 2.0, 'V': -1.0, 'W': 0.1, 'T': 23.0},
            timestamp=timestamp
        )
        sensor2_data = SensorData.from_parsed_dict(
            "Sensor2",
            {'S': 4.5, 'D': 315.0, 'U': 3.0, 'V': -3.0, 'W': 0.2, 'T': 21.0},
            timestamp=timestamp
        )
        
        data_dict = {
            'Sensor1': [sensor1_data],
            'Sensor2': [sensor2_data]
        }
        
        synchronized = CSVWriter._synchronize_timestamps(data_dict)
        
        assert len(synchronized) == 1
        assert synchronized[0]['timestamp'] == timestamp
        assert synchronized[0]['Sensor1'] == sensor1_data
        assert synchronized[0]['Sensor2'] == sensor2_data

    def test_synchronize_timestamps_within_tolerance(self):
        """許容範囲内(±0.5秒)のタイムスタンプ同期"""
        base_time = datetime.now()
        time1 = base_time
        time2 = base_time + timedelta(milliseconds=300)  # 0.3秒差（許容範囲内）
        
        sensor1_data = SensorData.from_parsed_dict(
            "Sensor1",
            {'S': 5.0, 'D': 270.0, 'U': 2.0, 'V': -1.0, 'W': 0.1, 'T': 23.0},
            timestamp=time1
        )
        sensor2_data = SensorData.from_parsed_dict(
            "Sensor2",
            {'S': 4.5, 'D': 315.0, 'U': 3.0, 'V': -3.0, 'W': 0.2, 'T': 21.0},
            timestamp=time2
        )
        
        data_dict = {
            'Sensor1': [sensor1_data],
            'Sensor2': [sensor2_data]
        }
        
        synchronized = CSVWriter._synchronize_timestamps(data_dict)
        
        # 2つのタイムスタンプがあるが、近いので両方にデータがマッチ
        assert len(synchronized) >= 1

    def test_synchronize_timestamps_missing_sensor(self):
        """センサーデータ欠損時にNoneを設定"""
        time1 = datetime.now()
        time2 = time1 + timedelta(seconds=2)  # 許容範囲外
        
        sensor1_data1 = SensorData.from_parsed_dict(
            "Sensor1",
            {'S': 5.0, 'D': 270.0, 'U': 2.0, 'V': -1.0, 'W': 0.1, 'T': 23.0},
            timestamp=time1
        )
        sensor2_data2 = SensorData.from_parsed_dict(
            "Sensor2",
            {'S': 4.5, 'D': 315.0, 'U': 3.0, 'V': -3.0, 'W': 0.2, 'T': 21.0},
            timestamp=time2
        )
        
        data_dict = {
            'Sensor1': [sensor1_data1],
            'Sensor2': [sensor2_data2]
        }
        
        synchronized = CSVWriter._synchronize_timestamps(data_dict)
        
        # 2つの異なるタイムスタンプ
        assert len(synchronized) == 2
        
        # time1の行: Sensor1あり、Sensor2なし
        row1 = next(r for r in synchronized if r['timestamp'] == time1)
        assert row1['Sensor1'] is not None
        assert row1.get('Sensor2') is None
        
        # time2の行: Sensor1なし、Sensor2あり
        row2 = next(r for r in synchronized if r['timestamp'] == time2)
        assert row2.get('Sensor1') is None
        assert row2['Sensor2'] is not None

    def test_write_multi_sensor_success(self, tmp_path):
        """マルチセンサーCSVの正常な書き込み"""
        output_file = tmp_path / "multi_sensor.csv"
        timestamp = datetime.now()
        
        data_dict = {}
        for i in range(1, 5):
            sensor_id = f"Sensor{i}"
            data = SensorData.from_parsed_dict(
                sensor_id,
                {'S': 5.0 + i, 'D': 270.0, 'U': 2.0, 'V': -1.0, 'W': 0.1, 'T': 23.0},
                timestamp=timestamp
            )
            data_dict[sensor_id] = [data]
        
        success, message = CSVWriter.write_multi_sensor(str(output_file), data_dict)
        
        assert success is True
        assert output_file.exists()

    def test_write_multi_sensor_csv_format(self, tmp_path):
        """マルチセンサーCSVのフォーマット検証"""
        output_file = tmp_path / "multi_format.csv"
        timestamp = datetime.now()
        
        sensor1_data = SensorData.from_parsed_dict(
            "Sensor1",
            {'S': 5.0, 'D': 270.0, 'U': 2.0, 'V': -1.0, 'W': 0.1, 'T': 23.0},
            timestamp=timestamp
        )
        sensor2_data = SensorData.from_parsed_dict(
            "Sensor2",
            {'S': 4.5, 'D': 315.0, 'U': 3.0, 'V': -3.0, 'W': 0.2, 'T': 21.0},
            timestamp=timestamp
        )
        
        data_dict = {
            'Sensor1': [sensor1_data],
            'Sensor2': [sensor2_data]
        }
        
        CSVWriter.write_multi_sensor(str(output_file), data_dict)
        
        # CSVを読み込んで検証
        with open(output_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # ヘッダー確認（Sensor1, Sensor2の順にソート）
        expected_header = [
            'Timestamp',
            'Sensor1_ID', 'Sensor1_S', 'Sensor1_D', 'Sensor1_U', 'Sensor1_V', 
            'Sensor1_W', 'Sensor1_T', 'Sensor1_PI', 'Sensor1_RO',
            'Sensor2_ID', 'Sensor2_S', 'Sensor2_D', 'Sensor2_U', 'Sensor2_V',
            'Sensor2_W', 'Sensor2_T', 'Sensor2_PI', 'Sensor2_RO'
        ]
        assert rows[0] == expected_header
        
        # データ行確認
        assert len(rows) == 2  # ヘッダー + データ1行

    def test_write_multi_sensor_with_na_values(self, tmp_path):
        """欠損データをN/Aで埋める"""
        output_file = tmp_path / "multi_na.csv"
        
        time1 = datetime.now()
        time2 = time1 + timedelta(seconds=2)  # 許容範囲外
        
        sensor1_data = SensorData.from_parsed_dict(
            "Sensor1",
            {'S': 5.0, 'D': 270.0, 'U': 2.0, 'V': -1.0, 'W': 0.1, 'T': 23.0},
            timestamp=time1
        )
        sensor2_data = SensorData.from_parsed_dict(
            "Sensor2",
            {'S': 4.5, 'D': 315.0, 'U': 3.0, 'V': -3.0, 'W': 0.2, 'T': 21.0},
            timestamp=time2
        )
        
        data_dict = {
            'Sensor1': [sensor1_data],
            'Sensor2': [sensor2_data]
        }
        
        CSVWriter.write_multi_sensor(str(output_file), data_dict)
        
        # CSVを読み込んで検証
        with open(output_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # 2つのタイムスタンプ行がある
        assert len(rows) == 3  # ヘッダー + 2データ行
        
        # N/A値を含むことを確認
        all_values = [cell for row in rows[1:] for cell in row]
        assert 'N/A' in all_values

    def test_write_multi_sensor_empty_data(self, tmp_path):
        """空データの処理"""
        output_file = tmp_path / "multi_empty.csv"
        
        success, message = CSVWriter.write_multi_sensor(str(output_file), {})
        
        assert success is False
        assert "No data" in message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
