# TriSonica JSON Protocol Test Script

## 概要

COM6センサーのJSON初期化失敗問題を診断するためのテストスクリプトです。
センサーのJSON protocol対応状況を単体で詳細にテストします。

## 実行方法

### 基本的な使い方

```bash
# COM6をテスト（デフォルト）
python tests/test_json_protocol.py

# 特定のCOMポートをテスト
python tests/test_json_protocol.py COM3
python tests/test_json_protocol.py COM5
python tests/test_json_protocol.py COM6

# ボーレートを指定してテスト
python tests/test_json_protocol.py COM6 115200
```

### 複数センサーの順次テスト

```bash
# 3つのセンサーを順番にテスト
python tests/test_json_protocol.py COM3 && python tests/test_json_protocol.py COM5 && python tests/test_json_protocol.py COM6
```

## テスト内容

このスクリプトは以下のテストを実行します：

### TEST 1: `{json}` コマンド
- JSON protocol対応確認
- ファームウェアバージョン取得
- 失敗時は自動リトライ（最大2回）

### TEST 2: `{version}` コマンド
- センサーバージョン情報取得
- モデル名、シリアル番号の確認

### TEST 3: `{settings}` コマンド
- センサー設定情報取得
- サンプルレート、出力タグ設定の確認

## 期待される出力

### 成功時

```
╔════════════════════════════════════════════════════════════╗
║  TriSonica JSON Protocol Test Script                      ║
║  Diagnose sensor initialization issues                     ║
╚════════════════════════════════════════════════════════════╝

============================================================
Testing JSON Protocol on COM6 @ 115200 baud
============================================================

Opening serial port...
Serial port opened successfully

Waiting for sensor to be ready...

============================================================
TEST 1: {json} command (checking protocol support)
============================================================

Attempt 1/2:
Sending command: {json} (timeout: 3.0s)
  Response line: {"JSON":{"Version":"3.0.0"}}
  Full response (1 lines):
{"JSON":{"Version":"3.0.0"}}

✓ SUCCESS: JSON protocol supported

✓ JSON protocol confirmed (Firmware: 3.0.0)

============================================================
TEST 2: {version} command (getting version info)
============================================================
Sending command: {version} (timeout: 3.0s)
  ...
✓ SUCCESS: Version info retrieved

============================================================
TEST 3: {settings} command (getting configuration)
============================================================
Sending command: {settings} (timeout: 4.0s)
  ...
✓ SUCCESS: Settings retrieved

Sensor Information:
  Model: TriSonica Mini
  Serial Number: 12345678
  Sample Rate: 32 Hz

  Output Configuration:
    Wind Speed: Yes
    Wind Direction: Yes
    ...
```

### 失敗時（JSON protocol非対応）

```
TEST 1: {json} command (checking protocol support)
============================================================

Attempt 1/2:
Sending command: {json} (timeout: 3.0s)
  ERROR: No response received
✗ FAILED: Retrying...

Attempt 2/2:
Sending command: {json} (timeout: 3.0s)
  ERROR: No response received

✗ FINAL RESULT: JSON protocol NOT supported
This sensor may be running older firmware (<3.0.0)
```

## トラブルシューティング

### 問題: "Serial port error: could not open port"

**原因**: ポートが他のプログラムで使用中

**解決策**:
1. MultiTrisonicaアプリを終了
2. 他のシリアル通信ソフトを終了
3. デバイスマネージャーでポートを確認

### 問題: "No response received"

**原因**:
- センサーの電源が入っていない
- ケーブル接続不良
- ボーレートが間違っている
- ファームウェアがJSON非対応（<3.0.0）

**解決策**:
1. センサーの電源を確認
2. ケーブル接続を確認
3. ボーレートを確認（通常115200）
4. ファームウェアバージョンを確認

### 問題: COM6だけ失敗する

**考えられる原因**:
1. **起動タイミング**: COM6のセンサーだけ起動が遅い
2. **ハードウェア問題**: USB-シリアル変換器の性能差
3. **ファームウェア差異**: COM6だけ古いバージョン
4. **ケーブル問題**: COM6のケーブルが長い/品質が低い

**診断手順**:
```bash
# 1. COM6を単体でテスト
python tests/test_json_protocol.py COM6

# 2. 成功するCOM3と比較
python tests/test_json_protocol.py COM3

# 3. ログを保存して比較
python tests/test_json_protocol.py COM3 > com3_test.log 2>&1
python tests/test_json_protocol.py COM6 > com6_test.log 2>&1
```

## 修正内容（sensor_worker.py）

このテストスクリプトと同じロジックを`sensor_worker.py`に実装済み：

1. ✅ 初期バッファクリア時の待機時間を延長（0.3s → 0.5s）
2. ✅ バッファクリア後に追加の待機時間（0.2s）
3. ✅ `{json}`コマンドのタイムアウト延長（2.0s → 3.0s）
4. ✅ `{version}`コマンドのタイムアウト延長（2.0s → 3.0s）
5. ✅ `{settings}`コマンドのタイムアウト延長（3.0s → 4.0s）
6. ✅ `{json}`コマンドのリトライロジック追加（最大2回）
7. ✅ コマンド間の待機時間追加（0.2s）
8. ✅ コマンド送信前のバッファクリア追加
9. ✅ より詳細なデバッグログ追加

## 期待される効果

これらの修正により、以下が改善されるはずです：

- ✅ センサー起動直後の初期化失敗を回避
- ✅ タイムアウトによる誤判定を防止
- ✅ 一時的な通信エラーからの自動回復
- ✅ 複数センサー同時接続時の安定性向上

## 次のステップ

1. **このテストスクリプトを実行**してCOM6の動作を確認
2. テスト結果に基づいて追加の調整を実施
3. 必要に応じてタイムアウトやリトライ回数を調整

## 連絡先

問題が解決しない場合は、以下の情報を含めて報告してください：

- テストスクリプトの完全な出力
- 各センサーのテスト結果の比較
- センサーのモデル名とシリアル番号
- ファームウェアバージョン
