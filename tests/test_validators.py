"""
Validators単体テスト

Validatorsクラスの機能を検証:
- validate_com_port()の有効/無効COMポート形式テスト
- validate_baud_rate()の有効/無効ボーレートテスト
- validate_csv_path()のパストラバーサル攻撃検出テスト
- validate_output_rate()の範囲(1-10 Hz)テスト
- validate_sensor_id()のセンサーID形式テスト
"""

import pytest
from pathlib import Path
from src.utils.validators import Validators


class TestValidators:
    """Validatorsクラスのテストスイート"""

    # COM Port Validation Tests
    def test_validate_com_port_valid(self):
        """有効なCOMポート形式"""
        assert Validators.validate_com_port("COM1") is True
        assert Validators.validate_com_port("COM3") is True
        assert Validators.validate_com_port("COM10") is True
        assert Validators.validate_com_port("COM99") is True
        assert Validators.validate_com_port("com5") is True  # 大文字小文字不問

    def test_validate_com_port_invalid(self):
        """無効なCOMポート形式"""
        assert Validators.validate_com_port("USB0") is False
        assert Validators.validate_com_port("COMA") is False
        assert Validators.validate_com_port("COM") is False
        assert Validators.validate_com_port("1COM") is False
        assert Validators.validate_com_port("/dev/ttyUSB0") is False

    def test_validate_com_port_empty_or_none(self):
        """空またはNone"""
        assert Validators.validate_com_port("") is False
        assert Validators.validate_com_port(None) is False

    def test_validate_com_port_invalid_type(self):
        """無効な型"""
        assert Validators.validate_com_port(123) is False
        assert Validators.validate_com_port([]) is False

    # Baud Rate Validation Tests
    def test_validate_baud_rate_valid(self):
        """有効なボーレート"""
        for baud in Validators.VALID_BAUD_RATES:
            assert Validators.validate_baud_rate(baud) is True

    def test_validate_baud_rate_as_string(self):
        """文字列としての有効なボーレート"""
        assert Validators.validate_baud_rate("115200") is True
        assert Validators.validate_baud_rate("9600") is True

    def test_validate_baud_rate_invalid(self):
        """無効なボーレート"""
        assert Validators.validate_baud_rate(9601) is False
        assert Validators.validate_baud_rate(115201) is False
        assert Validators.validate_baud_rate(0) is False
        assert Validators.validate_baud_rate(-1) is False

    def test_validate_baud_rate_invalid_string(self):
        """無効な文字列"""
        assert Validators.validate_baud_rate("abc") is False
        assert Validators.validate_baud_rate("") is False

    def test_validate_baud_rate_none(self):
        """None値"""
        assert Validators.validate_baud_rate(None) is False

    # CSV Path Validation Tests
    def test_validate_csv_path_valid(self):
        """有効なCSVパス"""
        is_valid, error_msg = Validators.validate_csv_path("output.csv")
        assert is_valid is True
        assert error_msg == ""

    def test_validate_csv_path_with_subdirectory(self):
        """サブディレクトリを含む有効なパス"""
        is_valid, error_msg = Validators.validate_csv_path("data/output.csv")
        assert is_valid is True
        assert error_msg == ""

    def test_validate_csv_path_path_traversal(self):
        """パストラバーサル攻撃の検出"""
        is_valid, error_msg = Validators.validate_csv_path("../../../etc/passwd.csv")
        assert is_valid is False
        assert "traversal" in error_msg.lower()

    def test_validate_csv_path_no_extension(self):
        """拡張子なしのファイル"""
        is_valid, error_msg = Validators.validate_csv_path("output")
        assert is_valid is False
        assert "csv extension" in error_msg.lower()

    def test_validate_csv_path_wrong_extension(self):
        """間違った拡張子"""
        is_valid, error_msg = Validators.validate_csv_path("output.txt")
        assert is_valid is False
        assert "csv extension" in error_msg.lower()

    def test_validate_csv_path_empty(self):
        """空パス"""
        is_valid, error_msg = Validators.validate_csv_path("")
        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_validate_csv_path_none(self):
        """Noneパス"""
        is_valid, error_msg = Validators.validate_csv_path(None)
        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_validate_csv_path_case_insensitive_extension(self):
        """大文字小文字を区別しない拡張子"""
        is_valid, error_msg = Validators.validate_csv_path("output.CSV")
        assert is_valid is True

        is_valid, error_msg = Validators.validate_csv_path("output.Csv")
        assert is_valid is True

    def test_validate_csv_path_pathlib_path(self):
        """Pathオブジェクトでの検証"""
        is_valid, error_msg = Validators.validate_csv_path(Path("output.csv"))
        assert is_valid is True

    # Output Rate Validation Tests
    def test_validate_output_rate_valid_integer(self):
        """有効な整数レート（1-10 Hz）"""
        for rate in range(1, 11):
            assert Validators.validate_output_rate(rate) is True

    def test_validate_output_rate_valid_float(self):
        """有効な浮動小数点レート"""
        assert Validators.validate_output_rate(1.0) is True
        assert Validators.validate_output_rate(5.5) is True
        assert Validators.validate_output_rate(10.0) is True

    def test_validate_output_rate_as_string(self):
        """文字列としての有効なレート"""
        assert Validators.validate_output_rate("5") is True
        assert Validators.validate_output_rate("1.5") is True
        assert Validators.validate_output_rate("10") is True

    def test_validate_output_rate_out_of_range(self):
        """範囲外のレート"""
        assert Validators.validate_output_rate(0) is False
        assert Validators.validate_output_rate(0.5) is False
        assert Validators.validate_output_rate(11) is False
        assert Validators.validate_output_rate(100) is False
        assert Validators.validate_output_rate(-1) is False

    def test_validate_output_rate_invalid_string(self):
        """無効な文字列"""
        assert Validators.validate_output_rate("abc") is False
        assert Validators.validate_output_rate("") is False

    def test_validate_output_rate_none(self):
        """None値"""
        assert Validators.validate_output_rate(None) is False

    def test_validate_output_rate_boundary_values(self):
        """境界値テスト"""
        assert Validators.validate_output_rate(1.0) is True  # 下限
        assert Validators.validate_output_rate(10.0) is True  # 上限
        assert Validators.validate_output_rate(0.999) is False  # 下限未満
        assert Validators.validate_output_rate(10.001) is False  # 上限超過

    # Sensor ID Validation Tests
    def test_validate_sensor_id_valid(self):
        """有効なセンサーID"""
        assert Validators.validate_sensor_id("Sensor1") is True
        assert Validators.validate_sensor_id("Sensor2") is True
        assert Validators.validate_sensor_id("COM3_Sensor") is True
        assert Validators.validate_sensor_id("Trisonica_A") is True

    def test_validate_sensor_id_alphanumeric(self):
        """英数字とアンダースコア"""
        assert Validators.validate_sensor_id("abc123") is True
        assert Validators.validate_sensor_id("ABC_123") is True
        assert Validators.validate_sensor_id("sensor_01") is True

    def test_validate_sensor_id_invalid_characters(self):
        """無効な文字を含むセンサーID"""
        assert Validators.validate_sensor_id("Sensor-1") is False  # ハイフン
        assert Validators.validate_sensor_id("Sensor 1") is False  # スペース
        assert Validators.validate_sensor_id("Sensor.1") is False  # ドット
        assert Validators.validate_sensor_id("Sensor@1") is False  # 記号

    def test_validate_sensor_id_empty(self):
        """空のセンサーID"""
        assert Validators.validate_sensor_id("") is False

    def test_validate_sensor_id_none(self):
        """NoneセンサーID"""
        assert Validators.validate_sensor_id(None) is False

    def test_validate_sensor_id_too_long(self):
        """長すぎるセンサーID（20文字制限）"""
        assert Validators.validate_sensor_id("a" * 20) is True  # 20文字はOK
        assert Validators.validate_sensor_id("a" * 21) is False  # 21文字はNG

    def test_validate_sensor_id_single_character(self):
        """単一文字のセンサーID"""
        assert Validators.validate_sensor_id("A") is True
        assert Validators.validate_sensor_id("1") is True
        assert Validators.validate_sensor_id("_") is True

    # VALID_BAUD_RATES constant test
    def test_valid_baud_rates_constant(self):
        """VALID_BAUD_RATES定数の検証"""
        expected_rates = [9600, 19200, 38400, 57600, 115200]
        assert Validators.VALID_BAUD_RATES == expected_rates

    # COM_PORT_PATTERN constant test
    def test_com_port_pattern_constant(self):
        """COM_PORT_PATTERN正規表現パターンの検証"""
        import re
        pattern = Validators.COM_PORT_PATTERN
        assert isinstance(pattern, re.Pattern)
        assert pattern.match("COM1") is not None
        assert pattern.match("com1") is not None  # IGNORECASE
        assert pattern.match("USB1") is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
