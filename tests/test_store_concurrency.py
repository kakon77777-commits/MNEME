from __future__ import annotations

import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty
from threading import Barrier, BrokenBarrierError

import pytest

from mneme.errors import StoreConflictError
from mneme.records import MemoryRecord
from mneme.store import MemoryStore
from mneme.transactions import TransactionProposal


def _transaction(label: str) -> dict[str, object]:
    record = {
        "record_version": "mneme.memory-record/0.1",
        "record_id": f"record-{label}",
        "record_type": "lesson",
        "scope": {"kind": "global", "subject": "concurrency"},
        "content": {"text": f"Synthetic writer {label}."},
        "relations": [],
        "provenance": {
            "event_id": f"event-{label}",
            "source_ref": "synthetic:concurrency",
        },
        "status": "active",
    }
    return {
        "transaction_version": "mneme.transaction/0.1",
        "transaction_id": f"tx-{label}",
        "expected_source_head": "GENESIS",
        "declared_record_count": 1,
        "record_digests": [MemoryRecord.from_dict(record).digest()],
        "records": [record],
        "authority_ref": "synthetic-authority:test",
        "commit_marker": "MNEME_COMMIT/0.1",
    }


def _process_commit(root: str, raw: dict[str, object], start, results) -> None:
    start.wait(timeout=10)
    try:
        receipt = MemoryStore(Path(root)).commit(TransactionProposal.from_dict(raw))
    except StoreConflictError as error:
        results.put(("refused", type(error).__name__))
    except Exception as error:  # noqa: BLE001  # pragma: no cover - child diagnostic
        results.put(("unexpected", f"{type(error).__name__}: {error}"))
    else:
        results.put(("success", receipt.new_head))


def test_head_compare_and_write_cannot_return_two_successes(tmp_path, monkeypatch):
    root = tmp_path / "memory.mlfdir"
    MemoryStore(root).initialize()
    original = MemoryStore._atomic_write_head
    barrier = Barrier(2)

    def synchronized_write(self, head):
        try:
            barrier.wait(timeout=1)
        except BrokenBarrierError:
            pass
        original(self, head)

    monkeypatch.setattr(MemoryStore, "_atomic_write_head", synchronized_write)

    def commit(label: str):
        try:
            receipt = MemoryStore(root).commit(
                TransactionProposal.from_dict(_transaction(label))
            )
        except StoreConflictError as error:
            return "refused", type(error).__name__
        return "success", receipt.new_head

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(commit, ("a", "b")))

    assert sum(kind == "success" for kind, _ in outcomes) == 1
    assert sum(kind == "refused" for kind, _ in outcomes) == 1


def test_two_process_writers_have_exactly_one_success(tmp_path):
    root = tmp_path / "memory.mlfdir"
    MemoryStore(root).initialize()
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_process_commit,
            args=(str(root), _transaction(label), start, results),
        )
        for label in ("a", "b")
    ]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0

    try:
        outcomes = [results.get(timeout=5), results.get(timeout=5)]
    except Empty as error:  # pragma: no cover - diagnostic boundary
        pytest.fail(f"writer process did not report: {error}")

    assert sum(kind == "success" for kind, _ in outcomes) == 1
    assert sum(kind == "refused" for kind, _ in outcomes) == 1
    assert len(list(MemoryStore(root).iter_committed_transactions())) == 1
