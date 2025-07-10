# pytoolkit-async-worker

複数のワーカーによる並列タスク処理のための非同期タスクワーカーライブラリ

## 概要

`pytoolkit-async-worker`は、非同期タスクの並列実行を簡単に実装するためのPythonライブラリです。
タスクキューを通じて複数のワーカーがタスクを並列処理し、効率的な並行実行を可能にします。

## 機能

- **非同期処理**: asyncioを使用した効率的な非同期タスク実行
- **ワーカープール**: 複数のワーカーによる並列タスク処理
- **型安全性**: 厳密な型チェックとジェネリクス対応
- **拡張可能**: カスタムタスククラスの簡単な実装
- **例外処理**: タスク実行時のエラーハンドリング

## 要件

- Python 3.13以上

## インストール

```bash
uv add pytoolkit-async-worker
```

## 使用方法

### 基本的な使用例

```python
import asyncio
from dataclasses import dataclass
from pytoolkit_async_worker.task import BaseTask
from pytoolkit_async_worker.worker import worker
from pytoolkit_async_worker.worker_manager import WorkerManager

@dataclass
class MyTaskArgs:
    value: int

@dataclass
class MyTaskResult:
    result: int

class MyTask(BaseTask[MyTaskArgs, MyTaskResult]):
    async def execute(self) -> MyTaskResult:
        # 具体的なタスク処理を実装
        result = self.args.value * 2
        self.result = Optionl(MyTaskResult(result=result))
        return self.result.unwrap()

async def main():
    # タスクキューの作成
    pending_queue = asyncio.Queue()
    
    # タスクをキューに追加
    for i in range(10):
        task = MyTask(MyTaskArgs(value=i))
        await pending_queue.put(task)
    
    # ワーカーマネージャーで並列処理
    manager = WorkerManager(
        worker=worker,
        max_workers=3,
        pending_task_queue=pending_queue
    )
    
    # 結果を順次処理
    async for completed_task in manager.execute():
        print(f"結果: {completed_task.result.unwrap().result}")

asyncio.run(main())
```

### ワーカーの直接使用

```python
import asyncio
from pytoolkit_async_worker.worker import worker

async def run_worker():
    pending_queue = asyncio.Queue()
    completed_queue = asyncio.Queue()
    
    # タスクを追加
    task = MyTask(MyTaskArgs(value=5))
    await pending_queue.put(task)
    
    # ワーカーを実行
    await worker(
        worker_id=1,
        pending_task_queue=pending_queue,
        completed_task_queue=completed_queue
    )
    
    # 結果を取得
    result = await completed_queue.get()
    print(f"処理結果: {result.result.unwrap().result}")
```

## APIリファレンス

### BaseTask

カスタムタスクを作成する際に継承する抽象基底クラスです。

```python
class BaseTask(ABC, Generic[TaskArgs, TaskResult]):
    def __init__(self, args: TaskArgs)
    async def execute(self) -> TaskResult  # 実装必須
```

### Worker

タスクを実行するワーカー関数です。

```python
async def worker(
    worker_id: WorkerId,
    pending_task_queue: Queue[Task],
    completed_task_queue: Queue[Task],
) -> None
```

### WorkerManager

複数のワーカーを管理し、分散タスク処理を行います。

```python
class WorkerManager(Generic[Task]):
    def __init__(
        self,
        worker: Worker[Task],
        max_workers: int,
        pending_task_queue: asyncio.Queue[Task],
    )
    
    async def execute(self) -> AsyncGenerator[Task]
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
uv run pytest tests/
```

## ライセンス

ライセンス情報については、プロジェクトのルートディレクトリを確認してください。