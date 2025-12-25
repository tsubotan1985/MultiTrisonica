"""
SerialParser単体テスト

SerialParserクラスの機能を検証:
- 有効なタグ付きデータのパース（可変スペース対応）
- 欠損タグの処理
- エラー値(-99.9, -99.99)検出
- 不正データ（不完全な行、非数値）の処理
- エッジケース（空行、単一タグ、未知タグ）
"""

import pytest
from src.utils.serial_parser import SerialParser


class TestSerialParser:
    """SerialParserクラスのテストスイート"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.parser = SerialParser()

    def test_parse_valid_line_single_space(self):
        """有効なタグ付きデータのパース（単一スペース）"""
        line = "S 5.23 D 270.15 U 2.45 V -1.33 W 0.12 T 23.45 PI 45.2 RO 1013.2"
        result = self.parser.parse_line(line)
        
        assert result['S'] == 5.23
        assert result['D'] == 270.15
        assert result['U'] == 2.45
        assert result['V'] == -1.33
        assert result['W'] == 0.12
        assert result['T'] == 23.45
        assert result['PI'] == 45.2
        assert result['RO'] == 1013.2

    def test_parse_valid_line_variable_spaces(self):
        """可変スペースに対応したパース"""
        line = "S  5.23   D 270.15 U    2.45  V -1.33    W 0.12 T  23.45"
        result = self.parser.parse_line(line)
        
        assert result['S'] == 5.23
        assert result['D'] == 270.15
        assert result['U'] == 2.45
        assert result['V'] == -1.33
        assert result['W'] == 0.12
        assert result['T'] == 23.45

    def test_parse_line_with_tabs(self):
        """タブ文字を含むデータのパース"""
        line = "S\t5.23\tD\t270.15\tU\t2.45\tV\t-1.33\tW\t0.12\tT\t23.45"
        result = self.parser.parse_line(line)
        
        assert result['S'] == 5.23
        assert result['D'] == 270.15
        assert result['U'] == 2.45
        assert result['V'] == -1.33
        assert result['W'] == 0.12
        assert result['T'] == 23.45

    def test_parse_line_missing_optional_tags(self):
        """オプショナルタグ（PI, RO）が欠損している場合"""
        line = "S 5.23 D 270.15 U 2.45 V -1.33 W 0.12 T 23.45"
        result = self.parser.parse_line(line)
        
        assert result['S'] == 5.23
        assert result['D'] == 270.15
        assert result['U'] == 2.45
        assert result['V'] == -1.33
        assert result['W'] == 0.12
        assert result['T'] == 23.45
        assert 'PI' not in result
        assert 'RO' not in result

    def test_is_error_value_negative_99_9(self):
        """エラー値-99.9の検出"""
        assert self.parser.is_error_value(-99.9) is True
        assert self.parser.is_error_value(-99.89) is False
        assert self.parser.is_error_value(-99.91) is False

    def test_is_error_value_negative_99_99(self):
        """エラー値-99.99の検出"""
        assert self.parser.is_error_value(-99.99) is True
        assert self.parser.is_error_value(-99.98) is False
        assert self.parser.is_error_value(-100.0) is False

    def test_is_error_value_normal_values(self):
        """正常な値はエラー値として検出されない"""
        assert self.parser.is_error_value(0.0) is False
        assert self.parser.is_error_value(5.23) is False
        assert self.parser.is_error_value(-10.5) is False
        assert self.parser.is_error_value(270.15) is False

    def test_validate_data_all_required_tags(self):
        """必須タグ(S, D, U, V, W, T)が全て含まれる場合"""
        data = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        assert self.parser.validate_data(data) is True

    def test_validate_data_missing_required_tag(self):
        """必須タグが欠損している場合"""
        # S欠損
        data = {'D': 270.15, 'U': 2.45, 'V': -1.33, 'W': 0.12, 'T': 23.45}
        assert self.parser.validate_data(data) is False
        
        # U欠損
        data = {'S': 5.23, 'D': 270.15, 'V': -1.33, 'W': 0.12, 'T': 23.45}
        assert self.parser.validate_data(data) is False
        
        # T欠損
        data = {'S': 5.23, 'D': 270.15, 'U': 2.45, 'V': -1.33, 'W': 0.12}
        assert self.parser.validate_data(data) is False

    def test_validate_data_with_optional_tags(self):
        """オプショナルタグ含む完全なデータ"""
        data = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45,
            'PI': 45.2,
            'RO': 1013.2
        }
        assert self.parser.validate_data(data) is True

    def test_parse_line_incomplete(self):
        """不完全な行（値が欠損）"""
        line = "S 5.23 D U 2.45 V -1.33 W 0.12 T 23.45"
        result = self.parser.parse_line(line)
        
        # Dの値が欠損しているためDキーは含まれない
        assert 'S' in result
        assert 'D' not in result  # 値がないため除外
        assert 'U' in result

    def test_parse_line_non_numeric_value(self):
        """非数値変換の処理"""
        line = "S 5.23 D ABC U 2.45 V -1.33 W 0.12 T 23.45"
        result = self.parser.parse_line(line)
        
        # ABCは数値に変換できないためDキーは除外
        assert 'S' in result
        assert 'D' not in result
        assert 'U' in result

    def test_parse_empty_line(self):
        """空行の処理（ParseError発生）"""
        line = ""
        with pytest.raises(Exception):  # ParseError
            self.parser.parse_line(line)
        
        line = "   "
        with pytest.raises(Exception):  # ParseError
            self.parser.parse_line(line)

    def test_parse_line_single_tag(self):
        """単一タグのみの行"""
        line = "S 5.23"
        result = self.parser.parse_line(line)
        
        assert result == {'S': 5.23}
        assert not self.parser.validate_data(result)  # 必須タグが足りない

    def test_parse_line_unknown_tags(self):
        """未知タグを含む行（既知タグのみパースされる）"""
        line = "S 5.23 D 270.15 U 2.45 V -1.33 W 0.12 T 23.45 UNKNOWN 99.9"
        result = self.parser.parse_line(line)
        
        assert result['S'] == 5.23
        assert result['D'] == 270.15
        # UNKNOWNタグは既知タグではないため含まれない
        assert 'UNKNOWN' not in result

    def test_has_error_values_with_errors(self):
        """エラー値を含むデータの検出"""
        data = {
            'S': -99.9,  # エラー値
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        assert self.parser.has_error_values(data) is True

    def test_has_error_values_multiple_errors(self):
        """複数のエラー値を含むデータ"""
        data = {
            'S': -99.9,  # エラー値
            'D': -99.99,  # エラー値
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        assert self.parser.has_error_values(data) is True

    def test_has_error_values_no_errors(self):
        """エラー値を含まないデータ"""
        data = {
            'S': 5.23,
            'D': 270.15,
            'U': 2.45,
            'V': -1.33,
            'W': 0.12,
            'T': 23.45
        }
        assert self.parser.has_error_values(data) is False

    def test_parse_line_with_negative_values(self):
        """負の値を含む正常なデータのパース"""
        line = "S 5.23 D 270.15 U -2.45 V -1.33 W -0.12 T -10.5"
        result = self.parser.parse_line(line)
        
        assert result['U'] == -2.45
        assert result['V'] == -1.33
        assert result['W'] == -0.12
        assert result['T'] == -10.5
        assert not self.parser.has_error_values(result)

    def test_parse_line_with_scientific_notation(self):
        """科学的記数法の処理（Pythonのfloat変換が対応）"""
        line = "S 5.23e0 D 2.7015e2 U 2.45E0 V -1.33 W 1.2e-1 T 23.45"
        result = self.parser.parse_line(line)
        
        assert abs(result['S'] - 5.23) < 0.0001
        assert abs(result['D'] - 270.15) < 0.0001
        assert abs(result['W'] - 0.12) < 0.0001

    def test_parse_line_realistic_sensor_output(self):
        """実際のTrisonicaセンサー出力に近いデータ"""
        # 実際のセンサーからの典型的な出力例
        line = "S 4.67 D 315.89 U 3.30 V -3.30 W 0.01 T 21.34 PI 50.12 RO 1013.25"
        result = self.parser.parse_line(line)
        
        assert self.parser.validate_data(result) is True
        assert not self.parser.has_error_values(result)
        assert result['S'] == 4.67
        assert result['D'] == 315.89
        assert result['PI'] == 50.12
        assert result['RO'] == 1013.25


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
