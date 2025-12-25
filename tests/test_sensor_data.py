"""
SensorData単体テスト

SensorDataクラスの機能を検証:
- from_parsed_dict()の完全/部分データテスト
- is_valid属性のエラーコードテスト
- to_csv_row()のフォーマットテスト
- frozen dataclassの不変性テスト
"""

import pytest
from datetime import datetime
from src.models.sensor_data import SensorData


class TestSensorData:
    """SensorDataクラスのテストスイート"""

    def test_from_parsed_dict_complete(self):
        """完全なパースデータからSensorData生成"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45,
            'PI': 45.2,
            'RO': 1013.2
        }
        sensor_id = "Sensor1"
        
        data = SensorData.from_parsed_dict(sensor_id, parsed)
        
        assert data.sensor_id == "Sensor1"
        assert data.speed_2d == 5.23
        assert data.direction == 270.15
        assert data.u_component == 2.45
        assert data.v_component == -1.33
        assert data.w_component == 0.12
        assert data.temperature == 23.45
        assert data.pitch == 45.2
        assert data.roll == 1013.2
        assert isinstance(data.timestamp, datetime)
        assert data.is_valid is True

    def test_from_parsed_dict_minimal_required(self):
        """必須タグのみのパースデータ（PI, RO欠損時はデフォルト0.0）"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        sensor_id = "Sensor2"
        
        data = SensorData.from_parsed_dict(sensor_id, parsed)
        
        assert data.sensor_id == "Sensor2"
        assert data.speed_2d == 5.23
        assert data.direction == 270.15
        assert data.u_component == 2.45
        assert data.v_component == -1.33
        assert data.w_component == 0.12
        assert data.temperature == 23.45
        assert data.pitch == 0.0  # デフォルト値
        assert data.roll == 0.0   # デフォルト値
        assert data.is_valid is True

    def test_from_parsed_dict_missing_required_tag(self):
        """必須タグが欠損している場合はKeyError"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            # U欠損
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        sensor_id = "Sensor3"
        
        with pytest.raises(KeyError):
            SensorData.from_parsed_dict(sensor_id, parsed)

    def test_is_valid_with_error_in_speed(self):
        """速度にエラー値(-99.9)を含む場合、is_valid=False"""
        parsed = {
            'S': -99.9,  # エラー値
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        assert data.is_valid is False

    def test_is_valid_with_error_in_temperature(self):
        """温度にエラー値(-99.99)を含む場合、is_valid=False"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': -99.99  # エラー値
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        assert data.is_valid is False

    def test_is_valid_with_multiple_errors(self):
        """複数のフィールドにエラー値を含む場合、is_valid=False"""
        parsed = {
            'S': -99.9,   # エラー値
            'D': -99.99,  # エラー値
            'U': 2.45,
            'V': -1.33,
            'W': -99.9,   # エラー値
            'T': 23.45
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        assert data.is_valid is False

    def test_is_valid_no_errors(self):
        """エラー値を含まない正常データ、is_valid=True"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        assert data.is_valid is True

    def test_is_valid_normal_negative_values(self):
        """正常な負の値はエラーとして扱わない"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': -2.45,
            'V': -1.33,
            'W': -0.12,
            'T': -10.5
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        assert data.is_valid is True

    def test_to_csv_row_complete_data(self):
        """完全なデータのCSV行変換"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45,
            'PI': 45.2,
            'RO': 1013.2
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        csv_row = data.to_csv_row()
        
        # CSV行は [timestamp, sensor_id, S, D, U, V, W, T, PI, RO] の順
        assert len(csv_row) == 10
        assert csv_row[0]  # timestamp (ISO形式文字列)
        assert csv_row[1] == "Sensor1"
        assert csv_row[2] == "5.23"
        assert csv_row[3] == "270.15"
        assert csv_row[4] == "2.45"
        assert csv_row[5] == "-1.33"
        assert csv_row[6] == "0.12"
        assert csv_row[7] == "23.45"
        assert csv_row[8] == "45.20"
        assert csv_row[9] == "1013.20"

    def test_to_csv_row_minimal_data(self):
        """オプショナルフィールド欠損時のCSV行（デフォルト0.0）"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        data = SensorData.from_parsed_dict("Sensor2", parsed)
        csv_row = data.to_csv_row()
        
        assert len(csv_row) == 10
        assert csv_row[1] == "Sensor2"
        assert csv_row[8] == "0.00"  # PI default value
        assert csv_row[9] == "0.00"  # RO default value

    def test_to_csv_row_timestamp_format(self):
        """タイムスタンプがISO 8601形式で出力される"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        csv_row = data.to_csv_row()
        
        # タイムスタンプは "YYYY-MM-DD HH:MM:SS.fff" 形式
        timestamp_str = csv_row[0]
        assert isinstance(timestamp_str, str)
        assert len(timestamp_str) >= 19  # 最低 "YYYY-MM-DD HH:MM:SS" 長
        
        # ISO形式のパースが可能か確認
        datetime.fromisoformat(timestamp_str.replace(' ', 'T'))

    def test_frozen_dataclass_immutability(self):
        """frozen dataclassは不変である"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        
        # フィールドの変更を試みるとFrozenInstanceErrorが発生
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            data.speed_2d = 10.0
        
        with pytest.raises(Exception):
            data.temperature = 25.0

    def test_sensor_data_equality(self):
        """同じデータを持つSensorDataインスタンスは等価"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        # 同一タイムスタンプで2つ生成
        timestamp = datetime.now()
        data1 = SensorData.from_parsed_dict("Sensor1", parsed, timestamp=timestamp)
        data2 = SensorData.from_parsed_dict("Sensor1", parsed, timestamp=timestamp)
        
        assert data1 == data2

    def test_sensor_data_with_different_sensor_ids(self):
        """異なるsensor_idのデータは区別される"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        data1 = SensorData.from_parsed_dict("Sensor1", parsed)
        data2 = SensorData.from_parsed_dict("Sensor2", parsed)
        
        assert data1.sensor_id != data2.sensor_id
        assert data1 != data2  # sensor_idが異なるため非等価

    def test_sensor_data_realistic_scenario(self):
        """実際のTrisonicaセンサーデータシナリオ"""
        # 風速4.67 m/s, 方向315.89度, 温度21.34°C
        parsed = {
            'S': 4.67,
            'D': 315.89,
            'U': 3.30,
            'V': -3.30,
            'W': 0.01,
            'T': 21.34,
            'PI': 50.12,
            'RO': 1013.25
        }
        
        data = SensorData.from_parsed_dict("Trisonica_A", parsed)
        
        assert data.speed_2d == 4.67
        assert data.direction == 315.89
        assert data.temperature == 21.34
        assert data.is_valid is True
        
        csv_row = data.to_csv_row()
        assert csv_row[1] == "Trisonica_A"
        assert csv_row[2] == "4.67"

    def test_sensor_data_with_extreme_values(self):
        """極端な値（範囲境界）のテスト"""
        parsed = {
            'S': 0.0,      # 最小風速
            'D': 359.99,   # 最大方向
            'U': -50.0,    # 極端なU成分
            'V': 50.0,     # 極端なV成分
            'W': 10.0,     # 極端なW成分
            'T': -40.0     # 極低温
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        
        assert data.speed_2d == 0.0
        assert data.direction == 359.99
        assert data.temperature == -40.0
        assert data.is_valid is True  # -40.0は-99.9や-99.99ではない

    def test_is_error_value_method(self):
        """is_error_value()メソッドのテスト"""
        parsed = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        
        data = SensorData.from_parsed_dict("Sensor1", parsed)
        
        assert data.is_error_value(-99.9) is True
        assert data.is_error_value(-99.99) is True
        assert data.is_error_value(5.23) is False
        assert data.is_error_value(0.0) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
