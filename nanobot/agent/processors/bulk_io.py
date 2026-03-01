"""Bulk I/O Processor — batched vector store reads and writes.

Accumulates individual read/write requests and flushes them in single
LMDB transactions for dramatically higher throughput.

Architecture Rationale
─────────────────────
LMDB enforces a single-writer lock.  50 individual write transactions
carry 50× the fsync overhead compared to a single batched transaction.
This processor converts many small writes into few large ones,
achieving 10-50× throughput improvement under sustained load.

Complexity: LOW-MEDIUM
Necessity:  HIGH — without batching, concurrent subagent writes
            serialize on the LMDB writer lock, creating a bottleneck.
"""

from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Any, Callable

from loguru import logger


class WriteBuffer:
    """Thread-safe buffer that accumulates entries and flushes in batch."""

    def __init__(
        self,
        flush_callback: Callable[[list[dict[str, Any]]], None],
        max_buffer: int = 50,
        max_wait_seconds: float = 2.0,
    ):
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._flush_cb = flush_callback
        self._max_buffer = max_buffer
        self._max_wait = max_wait_seconds
        self._last_flush = time.time()
        self._total_flushed = 0
        self._total_batches = 0

    def add(self, entry: dict[str, Any]) -> None:
        """Add an entry to the buffer. Auto-flushes when full."""
        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= self._max_buffer:
                self._do_flush()

    def flush(self) -> int:
        """Force-flush the buffer. Returns number of entries flushed."""
        with self._lock:
            return self._do_flush()

    def _do_flush(self) -> int:
        if not self._buffer:
            return 0
        batch = self._buffer[:]
        self._buffer.clear()
        count = len(batch)
        try:
            self._flush_cb(batch)
            self._total_flushed += count
            self._total_batches += 1
            self._last_flush = time.time()
            logger.debug("BulkIO: flushed {} entries in 1 transaction", count)
        except Exception as e:
            logger.error("BulkIO flush error: {}", e)
            # Put entries back
            self._buffer.extend(batch)
        return count

    def check_time_flush(self) -> int:
        """Flush if max_wait_seconds have elapsed since last flush."""
        with self._lock:
            if self._buffer and (time.time() - self._last_flush) > self._max_wait:
                return self._do_flush()
        return 0

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def get_stats(self) -> dict[str, Any]:
        return {
            "pending": self.pending,
            "total_flushed": self._total_flushed,
            "total_batches": self._total_batches,
            "avg_batch_size": round(self._total_flushed / max(1, self._total_batches), 1),
        }


class BulkReader:
    """Reads multiple keys from LMDB in a single cursor scan."""

    def __init__(self, workspace: Path):
        self._workspace = workspace

    def multi_get(self, env, keys: list[bytes]) -> dict[bytes, dict[str, Any]]:
        """Fetch multiple keys in a single LMDB read transaction.

        Args:
            env: The LMDB environment.
            keys: List of byte-encoded keys to retrieve.

        Returns:
            Dict mapping found keys to their parsed JSON payloads.
        """
        results: dict[bytes, dict[str, Any]] = {}
        key_set = set(keys)
        with env.begin() as txn:
            for key in key_set:
                value = txn.get(key)
                if value:
                    try:
                        results[key] = json.loads(value.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
        return results

    def scan_prefix(self, env, prefix: bytes, limit: int = 100) -> list[dict[str, Any]]:
        """Scan all entries with a given key prefix.

        Args:
            env: The LMDB environment.
            prefix: Byte prefix to match.
            limit: Maximum entries to return.

        Returns:
            List of parsed JSON payloads.
        """
        results: list[dict[str, Any]] = []
        with env.begin() as txn:
            cursor = txn.cursor()
            if cursor.set_range(prefix):
                for key, value in cursor:
                    if not key.startswith(prefix):
                        break
                    try:
                        results.append(json.loads(value.decode("utf-8")))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if len(results) >= limit:
                        break
        return results


class BulkIOProcessor:
    """Coordinates bulk reads and writes for the vector store.

    Usage:
        bio = BulkIOProcessor(workspace, flush_callback=vector_store.batch_write)
        bio.enqueue_write({"prefix": "vh:", "text": "...", "labels": [...]})
        bio.enqueue_write({"prefix": "vh:", "text": "...", "labels": [...]})
        bio.flush()  # or wait for auto-flush
    """

    def __init__(
        self,
        workspace: Path,
        flush_callback: Callable[[list[dict[str, Any]]], None] | None = None,
        max_buffer: int = 50,
        max_wait_seconds: float = 2.0,
    ):
        self._workspace = workspace
        self._writer = WriteBuffer(
            flush_callback=flush_callback or self._default_flush,
            max_buffer=max_buffer,
            max_wait_seconds=max_wait_seconds,
        )
        self._reader = BulkReader(workspace)

    def _default_flush(self, batch: list[dict[str, Any]]) -> None:
        """Default no-op flush; override via flush_callback."""
        logger.warning("BulkIO: no flush callback configured, {} entries dropped", len(batch))

    def enqueue_write(self, entry: dict[str, Any]) -> None:
        """Add an entry to the write buffer."""
        self._writer.add(entry)

    def flush(self) -> int:
        """Force-flush all pending writes."""
        return self._writer.flush()

    def check_time_flush(self) -> int:
        """Time-based auto-flush."""
        return self._writer.check_time_flush()

    @property
    def reader(self) -> BulkReader:
        return self._reader

    def get_stats(self) -> dict[str, Any]:
        return self._writer.get_stats()

    def render_status(self) -> str:
        s = self.get_stats()
        return (
            f"=== BULK I/O STATUS ===\n"
            f"Pending writes: {s['pending']}\n"
            f"Total flushed: {s['total_flushed']} in {s['total_batches']} batches\n"
            f"Avg batch size: {s['avg_batch_size']}"
        )
