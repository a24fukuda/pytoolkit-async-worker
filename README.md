# pytoolkit-async-worker

Result 型による例外安全な非同期タスクワーカーライブラリ

## 概要

`pytoolkit-async-worker`は、非同期タスクの並列実行を簡単に実装するための Python ライブラリです。
タスクキューを通じて複数のワーカーがタスクを並列処理し、効率的な並行実行を可能にします。
Result 型により例外安全性を確保し、エラーと正常な結果を型安全に扱えます。

## 機能

- **非同期処理**: asyncio を使用した効率的な非同期タスク実行
- **ワーカープール**: 複数のワーカーによる並列タスク処理
- **型安全性**: 厳密な型チェックとジェネリクス対応
- **例外安全性**: Result 型による安全なエラーハンドリング
- **タスククラス**: 処理をクラスとして表現する直感的なAPI

## 要件

- Python 3.13 以上

## インストール

```bash
uv add pytoolkit-async-worker
```

## 使用方法

### 基本的な使用例

`Task`クラスを継承して、具体的な処理を実装します：

```python
import asyncio
from pytoolkit_async_worker.task import Task, frozen_dataclass
from pytoolkit_async_worker.worker_manager import WorkerManager

@frozen_dataclass
class CalculationTask(Task[int]):
    """数値計算タスク"""
    value: int
    multiplier: int = 2
    
    async def execute(self) -> int:
        # 何らかの非同期処理
        await asyncio.sleep(0.1)
        return self.value * self.multiplier

async def main():
    # ワーカーマネージャーを作成
    manager = WorkerManager(max_workers=3)
    
    # タスクを追加
    for i in range(10):
        task = CalculationTask(value=i, multiplier=3)
        await manager.add_task(task)
    
    # 結果を順次処理
    async for task_result in manager.execute():
        if task_result.result.is_ok():
            result = task_result.result.unwrap().unwrap()
            print(f"成功: {result}")
        else:
            error = task_result.result.unwrap_err()
            print(f"エラー: {error}")

asyncio.run(main())
```

### 実用的なタスク例

```python
import asyncio
from typing import Dict, List
from pytoolkit_async_worker.task import Task, frozen_dataclass
from pytoolkit_async_worker.worker_manager import WorkerManager

@frozen_dataclass
class EmailSendTask(Task[bool]):
    """メール送信タスク"""
    to: str
    subject: str
    body: str
    priority: str = "normal"
    
    async def execute(self) -> bool:
        # メール送信処理をシミュレート
        send_delay = 0.2 if self.priority == "high" else 0.5
        await asyncio.sleep(send_delay)
        
        if "@" not in self.to:
            raise ValueError(f"Invalid email address: {self.to}")
        
        print(f"Email sent to {self.to}: {self.subject}")
        return True

@frozen_dataclass
class FileProcessTask(Task[str]):
    """ファイル処理タスク"""
    file_path: str
    operation: str  # "compress", "encrypt", "backup"
    
    async def execute(self) -> str:
        # ファイル処理をシミュレート
        await asyncio.sleep(0.3)
        
        if self.operation == "compress":
            return f"{self.file_path}.gz"
        elif self.operation == "encrypt":
            return f"{self.file_path}.encrypted"
        else:
            raise ValueError(f"Unknown operation: {self.operation}")

async def main():
    manager = WorkerManager(max_workers=2)
    
    # 異なる種類のタスクを追加
    await manager.add_task(EmailSendTask(
        to="user@example.com",
        subject="処理完了",
        body="タスクが完了しました"
    ))
    
    await manager.add_task(FileProcessTask(
        file_path="/path/to/document.pdf",
        operation="compress"
    ))
    
    # 結果を処理
    async for task_result in manager.execute():
        if task_result.result.is_ok():
            result = task_result.result.unwrap().unwrap()
            print(f"タスク完了: {result}")
        else:
            error = task_result.result.unwrap_err()
            print(f"タスクエラー: {error}")

asyncio.run(main())
```

### エラーハンドリング

```python
@frozen_dataclass
class RiskyTask(Task[int]):
    """エラーが発生する可能性のあるタスク"""
    value: int
    
    async def execute(self) -> int:
        if self.value % 3 == 0:
            raise ValueError(f"値 {self.value} は処理できません")
        return self.value * 2

async def main():
    manager = WorkerManager(max_workers=2)
    
    # 正常なタスクとエラーになるタスクを混在
    for i in range(5):
        await manager.add_task(RiskyTask(value=i))
    
    async for task_result in manager.execute():
        if task_result.result.is_ok():
            result = task_result.result.unwrap().unwrap()
            print(f"成功: 値={task_result.task.value}, 結果={result}")
        else:
            error = task_result.result.unwrap_err()
            print(f"失敗: 値={task_result.task.value}, エラー={error}")

asyncio.run(main())
```

### より複雑なタスクの例

```python
@frozen_dataclass
class DatabaseQueryTask(Task[Dict[str, any]]):
    """データベースクエリタスク"""
    query: str
    params: Dict[str, any]
    timeout: int = 30
    
    async def execute(self) -> Dict[str, any]:
        # データベースクエリをシミュレート
        await asyncio.sleep(0.05)
        
        if "SELECT" in self.query.upper():
            return {
                "rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                "count": 2
            }
        else:
            return {"affected_rows": 1}

@frozen_dataclass
class WebScrapingTask(Task[Dict[str, any]]):
    """Webスクレイピングタスク"""
    url: str
    selectors: Dict[str, str]
    timeout: int = 30
    
    async def execute(self) -> Dict[str, any]:
        # Webスクレイピングをシミュレート
        await asyncio.sleep(0.3)
        
        return {
            "url": self.url,
            "title": "Sample Page Title",
            "content": "Sample scraped content...",
            "timestamp": "2024-01-01T00:00:00Z"
        }
```

## API リファレンス

### Task[T]

非同期処理を表現する抽象基底クラスです。

```python
from pytoolkit_async_worker.task import Task, frozen_dataclass

@frozen_dataclass
class MyTask(Task[str]):
    data: str
    
    async def execute(self) -> str:
        # ここに処理を実装
        return self.data.upper()
```

**重要なポイント:**
- `@frozen_dataclass` で不変オブジェクトとして定義
- `execute()` メソッドで実際の処理を実装
- ジェネリクスで戻り値の型を指定

### TaskResult[T]

タスクの実行結果を表すデータクラスです。

```python
from pytoolkit_async_worker.task import TaskResult

# task_result.task は実行されたTaskオブジェクト
# task_result.result は Result[Option[T]] 型
```

### WorkerManager[T]

複数のワーカーを管理し、分散タスク処理を行います。

```python
from pytoolkit_async_worker.worker_manager import WorkerManager

manager = WorkerManager(
    max_workers=3,      # 最大ワーカー数
    worker=worker,      # ワーカー関数（デフォルト）
)

# タスクを追加
await manager.add_task(my_task)

# タスクを実行して結果を取得
async for task_result in manager.execute():
    # 結果を処理
    pass
```

### worker 関数

タスクを実行するデフォルトのワーカー関数です。

```python
from pytoolkit_async_worker.worker import worker, PendingTaskQueue

pending_queue = PendingTaskQueue()
async for task_result in worker(pending_queue):
    # 結果を処理
    pass
```

## 開発

### 開発環境のセットアップ

```bash
# 依存関係のインストール
uv sync --dev

# テストの実行
uv run pytest

# 型チェック
uv run pyright

# リンター
uv run ruff check
uv run ruff format
```

### テスト

```bash
# すべてのテストを実行
uv run pytest tests/

# 特定のテストファイルを実行
uv run pytest tests/test_worker.py -v

# カバレッジ付きでテスト実行
uv run pytest --cov=pytoolkit_async_worker
```

## 設計思想

### なぜTaskクラスを使うのか

1. **明確な責任分離**: 各タスクは特定の処理を表現する独立したクラス
2. **型安全性**: ジェネリクスにより、戻り値の型が明確
3. **再利用性**: 同じタスクを異なるパラメータで複数回実行可能
4. **テストしやすさ**: 各タスクを個別にテスト可能
5. **保守性**: 処理の変更が他の処理に影響しない

### 使用例の比較

**従来の関数ベースアプローチ:**
```python
# 処理が散らばりやすい
async def process_email(to, subject, body, priority="normal"):
    # 処理実装
    pass

# 呼び出し側
await manager.add_task(process_email, "user@example.com", "件名", "本文")
```

**Taskクラスベースアプローチ:**
```python
# 処理が整理されている
@frozen_dataclass
class EmailSendTask(Task[bool]):
    to: str
    subject: str
    body: str
    priority: str = "normal"
    
    async def execute(self) -> bool:
        # 処理実装
        pass

# 呼び出し側
task = EmailSendTask(to="user@example.com", subject="件名", body="本文")
await manager.add_task(task)
```

Taskクラスアプローチにより、コードの可読性、保守性、テストしやすさが向上します。