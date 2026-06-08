"""
Unit tests for task_runner.py bandwidth throttling helpers.
"""

from typing import List

import numpy as np
import pytest

import task_runner


def test_calculate_bandwidth_sleep_uses_mib_per_second() -> None:
    """One MiB written at 64 MiB/s should sleep for 1/64 second."""
    sleep_s: float = task_runner._calculate_bandwidth_sleep_s(
        task_runner.BYTES_PER_MIB,
        bandwidth_limit_mb_s=64.0,
    )

    assert sleep_s == pytest.approx(1.0 / 64.0)


def test_calculate_bandwidth_sleep_rejects_invalid_limit() -> None:
    """Bandwidth caps must be positive."""
    with pytest.raises(ValueError, match="must be positive"):
        task_runner._calculate_bandwidth_sleep_s(1024, bandwidth_limit_mb_s=0.0)


def test_simulate_work_throttles_cxl_bandwidth(monkeypatch: pytest.MonkeyPatch) -> None:
    """CXL tasks with a bandwidth cap should sleep after writing chunks."""
    sleep_calls: List[float] = []
    data = np.ones(task_runner.CHUNK_SIZE, dtype=np.float64)

    monkeypatch.setattr(task_runner.time, "sleep", sleep_calls.append)

    task_runner.simulate_work(data, node=1, bandwidth_limit_mb_s=1.0)

    expected_bandwidth_sleep = data.nbytes / task_runner.BYTES_PER_MIB
    assert sleep_calls[0] == pytest.approx(expected_bandwidth_sleep)
    assert len(sleep_calls) >= 2  # bandwidth sleep plus CXL latency sleep


def test_simulate_work_does_not_throttle_dram(monkeypatch: pytest.MonkeyPatch) -> None:
    """DRAM tasks ignore bandwidth caps and do not inject extra sleeps."""
    sleep_calls: List[float] = []
    data = np.ones(task_runner.CHUNK_SIZE, dtype=np.float64)

    monkeypatch.setattr(task_runner.time, "sleep", sleep_calls.append)

    task_runner.simulate_work(data, node=0, bandwidth_limit_mb_s=1.0)

    assert sleep_calls == []
