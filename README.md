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
- **シンプルな API**: 関数ベースの直感的なインターフェース

## 要件

- Python 3.13 以上

## インストール

```bash
uv add pytoolkit-async-worker
```

## 使用方法

### 基本的な使用例

```python
import asyncio
from pytoolkit_async_worker.worker import WorkerManager

# タスク関数を定義
async def process_data(value: int) -> int:
    # 何らかの非同期処理
    await asyncio.sleep(0.1)
    return value * 2

async def main():
    # ワーカーマネージャーを作成
    manager = WorkerManager(
        worker=worker,  # デフォルトのワーカー関数
        max_workers=3,  # 並列実行するワーカー数
    )

    # タスクを追加
    for i in range(10):
        await manager.add_task(process_data, i)

    # 結果を順次処理
    async for task_result in manager.execute():
        if task_result.result.is_ok():
            print(f"成功: {task_result.result.value}")
        else:
            print(f"エラー: {task_result.result.error}")

asyncio.run(main())
```

### エラーハンドリング

```python
async def failing_task(value: int) -> int:
    if value % 3 == 0:
        raise ValueError(f"値 {value} は処理できません")
    return value * 2

async def main():
    manager = WorkerManager(worker=worker, max_workers=2)

    # 正常なタスクとエラーになるタスクを混在
    for i in range(5):
        await manager.add_task(failing_task, i)

    async for task_result in manager.execute():
        if task_result.result.is_ok():
            print(f"成功: 引数={task_result.args}, 結果={task_result.result.value}")
        else:
            print(f"失敗: 引数={task_result.args}, エラー={task_result.result.error}")

asyncio.run(main())
```

### キーワード引数を使用したタスク

```python
async def process_with_options(data: str, multiplier: int = 1, prefix: str = "") -> str:
    result = data * multiplier
    return f"{prefix}{result}"

async def main():
    manager = WorkerManager(worker=worker, max_workers=2)

    # 位置引数とキーワード引数を組み合わせて使用
    await manager.add_task(process_with_options, "Hello", multiplier=3, prefix=">>> ")
    await manager.add_task(process_with_options, "World", multiplier=2)

    async for task_result in manager.execute():
        if task_result.result.is_ok():
            print(f"結果: {task_result.result.value}")
            print(f"引数: args={task_result.args}, kwargs={task_result.kwargs}")

asyncio.run(main())
```

### ワーカーの直接使用

```python
import asyncio
from pytoolkit_async_worker.worker import worker, Task, PendingTaskQueue, TaskResultQueue

async def simple_task(x: int) -> int:
    return x ** 2

async def run_worker_directly():
    # キューを作成
    pending_queue = PendingTaskQueue()
    result_queue = TaskResultQueue()

    # タスクを作成してキューに追加
    task = Task(func=simple_task, args=(5,), kwargs={})
    await pending_queue.put(task)

    # ワーカーを実行
    await worker(pending_queue, result_queue)

    # 結果を取得
    task_result = await result_queue.get()
    if task_result.result.is_ok():
        print(f"結果: {task_result.result.value}")  # 25

asyncio.run(run_worker_directly())
```

## API リファレンス

### Result[T]

エラーと正常な結果を安全に扱うための型です。

```python
from pytoolkit_async_worker.result import Result

# 正常な結果
result = Result[int](42)
assert result.is_ok()
assert result.value == 42

# エラー結果
error_result = Result[int](ValueError("エラー"))
assert error_result.is_error()
assert isinstance(error_result.error, ValueError)
```

**メソッド:**

- `is_ok() -> bool`: 正常な結果かどうか
- `is_error() -> bool`: エラー結果かどうか
- `value: T`: 正常な値を取得（エラーの場合は例外発生）
- `error: Exception`: エラーを取得（正常な場合は例外発生）

### Task[P, R]

実行するタスクを表すデータクラスです。

```python
from pytoolkit_async_worker.worker import Task

task = Task(
    func=my_async_function,
    args=(arg1, arg2),
    kwargs={"key": "value"}
)
```

### TaskResult[R]

タスクの実行結果を表すデータクラスです。

```python
from pytoolkit_async_worker.worker import TaskResult

# task_result.result は Result[R] 型
# task_result.args は実行時の位置引数
# task_result.kwargs は実行時のキーワード引数
```

### WorkerManager[P, R]

複数のワーカーを管理し、分散タスク処理を行います。

```python
from pytoolkit_async_worker.worker import WorkerManager, worker

manager = WorkerManager(
    worker=worker,      # ワーカー関数
    max_workers=3,      # 最大ワーカー数
)

# タスクを追加
await manager.add_task(my_function, arg1, arg2, key=value)

# タスクを実行して結果を取得
async for task_result in manager.execute():
    # 結果を処理
    pass
```

### worker 関数

タスクを実行するデフォルトのワーカー関数です。

```python
from pytoolkit_async_worker.worker import worker, PendingTaskQueue, TaskResultQueue

await worker(
    pending_task_queue,  # 実行待ちタスクのキュー
    task_result_queue,   # 実行結果のキュー
)
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
