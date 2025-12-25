"""
AppConfig単体テスト

AppConfigとSensorConfigクラスの機能を検証:
- load_or_default()のファイル欠損テスト
- load_or_default()のJSON破損テスト
- save()とラウンドトリップ(保存→読み込み)テスト
- デフォルト値の検証テスト
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.models.app_config import AppConfig, SensorConfig


class TestSensorConfig:
    """SensorConfigクラスのテストスイート"""

    def test_sensor_config_default_values(self):
        """SensorConfigのデフォルト値検証"""
        config = SensorConfig()
        
        assert config.port == ""
        assert config.baud == 115200
        assert isinstance(config.custom_init_commands, list)
        assert len(config.custom_init_commands) > 0
        assert "units si" in config.custom_init_commands
        assert "exit" in config.custom_init_commands

    def test_sensor_config_custom_values(self):
        """カスタム値でのSensorConfig生成"""
        config = SensorConfig(
            port="COM3",
            baud=9600,
            custom_init_commands=["test1", "test2"]
        )
        
        assert config.port == "COM3"
        assert config.baud == 9600
        assert config.custom_init_commands == ["test1", "test2"]


class TestAppConfig:
    """AppConfigクラスのテストスイート"""

    def test_app_config_default_values(self):
        """AppConfigのデフォルト値検証"""
        config = AppConfig()
        
        assert len(config.sensors) == 4
        assert 'Sensor1' in config.sensors
        assert 'Sensor2' in config.sensors
        assert 'Sensor3' in config.sensors
        assert 'Sensor4' in config.sensors
        assert config.output_rate == 5
        assert config.window_geometry == [100, 100, 1280, 800]

    def test_load_or_default_file_not_exists(self, monkeypatch, tmp_path):
        """ファイル欠損時はデフォルト値を返す"""
        # _get_config_path()をモックして存在しないパスを返す
        non_existent_path = tmp_path / "nonexistent_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', lambda: non_existent_path)
        
        config = AppConfig.load_or_default()
        
        # デフォルト値が返されること
        assert config.output_rate == 5
        assert len(config.sensors) == 4
        assert config.window_geometry == [100, 100, 1280, 800]

    def test_load_or_default_corrupted_json(self, monkeypatch, tmp_path):
        """JSON破損時はデフォルト値を返す"""
        # 破損したJSONファイルを作成
        corrupted_file = tmp_path / "corrupted_config.json"
        corrupted_file.write_text("{ invalid json content }", encoding='utf-8')
        
        monkeypatch.setattr(AppConfig, '_get_config_path', lambda: corrupted_file)
        
        config = AppConfig.load_or_default()
        
        # デフォルト値が返されること
        assert config.output_rate == 5
        assert len(config.sensors) == 4

    def test_save_and_load_roundtrip(self, monkeypatch, tmp_path):
        """保存→読み込みのラウンドトリップテスト"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', staticmethod(lambda: config_file))
        
        # カスタム設定を作成
        original_config = AppConfig()
        original_config.output_rate = 10
        original_config.window_geometry = [200, 200, 1920, 1080]
        original_config.sensors['Sensor1'].port = "COM3"
        original_config.sensors['Sensor1'].baud = 9600
        
        # 保存
        success = original_config.save()
        assert success is True
        assert config_file.exists()
        
        # 読み込み
        loaded_config = AppConfig.load_or_default()
        
        # 検証
        assert loaded_config.output_rate == 10
        assert loaded_config.window_geometry == [200, 200, 1920, 1080]
        assert loaded_config.sensors['Sensor1'].port == "COM3"
        assert loaded_config.sensors['Sensor1'].baud == 9600

    def test_save_creates_valid_json(self, monkeypatch, tmp_path):
        """save()が有効なJSON形式で保存すること"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', staticmethod(lambda: config_file))
        
        config = AppConfig()
        config.output_rate = 8
        config.save()
        
        # ファイルが存在し、有効なJSONであること
        assert config_file.exists()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'sensors' in data
        assert 'output_rate' in data
        assert 'window_geometry' in data
        assert data['output_rate'] == 8

    def test_save_write_failure(self, monkeypatch):
        """書き込み失敗時にFalseを返し、例外を発生させないこと"""
        # 書き込み不可能なパスを設定（Windowsでは無効なパス文字を使用）
        invalid_path = Path("Z:\\nonexistent\\invalid<>path\\config.json")
        monkeypatch.setattr(AppConfig, '_get_config_path', staticmethod(lambda: invalid_path))
        
        config = AppConfig()
        success = config.save()
        
        # Falseを返すが例外は発生しない
        assert success is False

    def test_get_sensor_config(self):
        """get_sensor_config()でセンサー設定を取得"""
        config = AppConfig()
        
        sensor1_config = config.get_sensor_config('Sensor1')
        assert sensor1_config is not None
        assert isinstance(sensor1_config, SensorConfig)
        
        # 存在しないセンサーIDはNoneを返す
        non_existent = config.get_sensor_config('NonExistent')
        assert non_existent is None

    def test_update_sensor_config(self):
        """update_sensor_config()でセンサー設定を更新"""
        config = AppConfig()
        
        new_sensor_config = SensorConfig(port="COM5", baud=19200)
        config.update_sensor_config('Sensor2', new_sensor_config)
        
        updated = config.get_sensor_config('Sensor2')
        assert updated.port == "COM5"
        assert updated.baud == 19200

    def test_load_with_custom_init_commands(self, monkeypatch, tmp_path):
        """カスタム初期化コマンドの保存と読み込み"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', staticmethod(lambda: config_file))
        
        # カスタムコマンドを設定
        config = AppConfig()
        config.sensors['Sensor1'].custom_init_commands = ["cmd1", "cmd2", "cmd3"]
        config.save()
        
        # 読み込み
        loaded = AppConfig.load_or_default()
        assert loaded.sensors['Sensor1'].custom_init_commands == ["cmd1", "cmd2", "cmd3"]

    def test_load_with_missing_sensors_uses_defaults(self, monkeypatch, tmp_path):
        """sensors欠損時はデフォルト4センサーを使用"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', lambda: config_file)
        
        # sensorsキーを含まないJSONを作成
        data = {
            'output_rate': 7,
            'window_geometry': [0, 0, 800, 600]
        }
        config_file.write_text(json.dumps(data), encoding='utf-8')
        
        loaded = AppConfig.load_or_default()
        
        # デフォルト4センサーが設定されること
        assert len(loaded.sensors) == 4
        assert 'Sensor1' in loaded.sensors
        assert loaded.output_rate == 7  # 他の値は読み込まれる

    def test_load_with_partial_sensor_data(self, monkeypatch, tmp_path):
        """一部のセンサー設定項目が欠損していても動作すること"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', lambda: config_file)
        
        # baudとcustom_init_commandsが欠損
        data = {
            'sensors': {
                'Sensor1': {'port': 'COM3'}
            },
            'output_rate': 5,
            'window_geometry': [100, 100, 1280, 800]
        }
        config_file.write_text(json.dumps(data), encoding='utf-8')
        
        loaded = AppConfig.load_or_default()
        
        # デフォルト値が使用されること
        assert loaded.sensors['Sensor1'].port == 'COM3'
        assert loaded.sensors['Sensor1'].baud == 115200  # デフォルト
        assert len(loaded.sensors['Sensor1'].custom_init_commands) > 0  # デフォルトコマンド

    def test_multiple_save_and_load_cycles(self, monkeypatch, tmp_path):
        """複数回の保存→読み込みサイクルが正常に動作すること"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', staticmethod(lambda: config_file))
        
        # サイクル1
        config1 = AppConfig()
        config1.output_rate = 3
        config1.save()
        
        loaded1 = AppConfig.load_or_default()
        assert loaded1.output_rate == 3
        
        # サイクル2
        loaded1.output_rate = 7
        loaded1.save()
        
        loaded2 = AppConfig.load_or_default()
        assert loaded2.output_rate == 7

    def test_config_file_encoding_utf8(self, monkeypatch, tmp_path):
        """UTF-8エンコーディングで保存・読み込み可能"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', staticmethod(lambda: config_file))
        
        config = AppConfig()
        config.save()
        
        # UTF-8で読み込み可能
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert isinstance(content, str)
        json.loads(content)  # パース可能

    def test_window_geometry_persistence(self, monkeypatch, tmp_path):
        """ウィンドウジオメトリの永続化"""
        config_file = tmp_path / "test_config.json"
        monkeypatch.setattr(AppConfig, '_get_config_path', staticmethod(lambda: config_file))
        
        config = AppConfig()
        config.window_geometry = [50, 50, 1600, 900]
        config.save()
        
        loaded = AppConfig.load_or_default()
        assert loaded.window_geometry == [50, 50, 1600, 900]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
