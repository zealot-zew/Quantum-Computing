"""
Unit tests for src/executor/task_orchestrator.py.

These tests verify that the orchestrator:
  1. Builds correct numactl commands for DRAM and CXL nodes.
  2. Launches all tasks as concurrent subprocesses (one Popen per task).
  3. Falls back gracefully when numactl is not installed (FileNotFoundError).
  4. Handles failed subprocesses (non-zero exit code) without crashing.
  5. Correctly parses CSV output from task_runner.py stdout.
  6. Returns zero subprocesses in dry-run mode.

All subprocess.Popen calls are mocked — no real processes are spawned.
This keeps the tests fast, deterministic, and environment-independent.

Run with:
    pytest tests/test_numa_executor.py -v

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

import sys
from io import StringIO
from typing import Dict, List
from unittest.mock import MagicMock, call, patch

import pytest

from src.scheduler.task_model import Task
from src.executor.task_orchestrator import (
    _build_command,
    _parse_csv_output,
    run_all_tasks,
    TIER_TO_NODE,
)


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

# A minimal set of 3 tasks that covers different memory sizes and tiers.
# These mirror the structure of the real 8-task set in src/scheduler/tasks.py
# but are kept small to keep tests fast.
SAMPLE_TASKS: List[Task] = [
    Task(task_id=0, memory_requirement_mb=512.0, priority=5, memory_sensitivity=0.9),
    Task(task_id=1, memory_requirement_mb=256.0, priority=3, memory_sensitivity=0.7),
    Task(task_id=2, memory_requirement_mb=128.0, priority=2, memory_sensitivity=0.4),
]

# Assignment dict: task 0 and 2 go to DRAM, task 1 goes to CXL
SAMPLE_ASSIGNMENT: Dict[int, str] = {
    0: "DRAM",
    1: "CXL",
    2: "DRAM",
}

# A valid CSV line in the format task_runner.py prints to stdout
_VALID_CSV_TEMPLATE = "{task_id},{{node}},1717839600.000000,1717839601.500000,1.500000"


def _make_csv(task_id: int, node: int) -> str:
    """Return a valid CSV stdout string for a given task_id and node."""
    return f"{task_id},{node},1717839600.000000,1717839601.500000,1.500000\n"


def _make_mock_proc(task_id: int, node: int, returncode: int = 0) -> MagicMock:
    """
    Create a MagicMock that behaves like a subprocess.Popen object.

    .communicate() returns (stdout_str, stderr_str).
    .returncode is set to the given value.
    """
    mock_proc = MagicMock()
    mock_proc.returncode = returncode
    mock_proc.communicate.return_value = (
        _make_csv(task_id, node),  # stdout
        "",                         # stderr
    )
    return mock_proc


# ---------------------------------------------------------------------------
# Tests: _build_command()
# ---------------------------------------------------------------------------

class TestBuildCommand:
    """Tests for the internal command-builder helper."""

    def test_dram_command_has_node_zero(self) -> None:
        """DRAM tasks must use --cpunodebind=0 --membind=0."""
        task = SAMPLE_TASKS[0]  # task_id=0
        cmd = _build_command(task, node=0)

        assert "numactl" in cmd[0]
        assert "--cpunodebind=0" in cmd
        assert "--membind=0" in cmd
        assert "--task-id" in cmd
        assert str(task.task_id) in cmd
        assert "--memory-mb" in cmd
        assert str(task.memory_requirement_mb) in cmd
        assert "--node" in cmd
        assert "0" in cmd

    def test_cxl_command_has_node_one(self) -> None:
        """CXL tasks must use --cpunodebind=1 --membind=1."""
        task = SAMPLE_TASKS[1]  # task_id=1
        cmd = _build_command(task, node=1)

        assert "--cpunodebind=1" in cmd
        assert "--membind=1" in cmd
        assert "--node" in cmd
        assert "1" in cmd

    def test_command_contains_double_dash_separator(self) -> None:
        """numactl -- separator must appear between numactl flags and python cmd."""
        cmd = _build_command(SAMPLE_TASKS[0], node=0)
        assert "--" in cmd

    def test_command_references_task_runner(self) -> None:
        """Command must point to task_runner.py."""
        cmd = _build_command(SAMPLE_TASKS[0], node=0)
        # Join to a string for easy substring check
        cmd_str = " ".join(cmd)
        assert "task_runner.py" in cmd_str

    def test_tier_to_node_mapping(self) -> None:
        """TIER_TO_NODE must correctly map string tiers to node integers."""
        assert TIER_TO_NODE["DRAM"] == 0
        assert TIER_TO_NODE["CXL"] == 1


# ---------------------------------------------------------------------------
# Tests: _parse_csv_output()
# ---------------------------------------------------------------------------

class TestParseCsvOutput:
    """Tests for the CSV stdout parser."""

    def test_parses_valid_csv(self) -> None:
        """A well-formed CSV line must be parsed into a result dict."""
        csv = "3,1,1717839600.123456,1717839601.456789,1.333333\n"
        result = _parse_csv_output(csv, task_id=3)

        assert result["task_id"] == 3
        assert result["node"] == 1
        assert abs(result["start_time_s"] - 1717839600.123456) < 1e-6
        assert abs(result["end_time_s"] - 1717839601.456789) < 1e-6
        assert abs(result["duration_s"] - 1.333333) < 1e-6

    def test_returns_empty_dict_on_empty_stdout(self) -> None:
        """Empty stdout must return an empty dict (not crash)."""
        result = _parse_csv_output("", task_id=0)
        assert result == {}

    def test_returns_empty_dict_on_malformed_csv(self) -> None:
        """Stdout with wrong column count must return an empty dict."""
        result = _parse_csv_output("only,three,cols\n", task_id=0)
        assert result == {}

    def test_takes_last_line_of_multiline_stdout(self) -> None:
        """If stderr leaked to stdout, the CSV must still be found on the last line."""
        multiline = "some debug line\nanother line\n3,0,1.0,2.0,1.0\n"
        result = _parse_csv_output(multiline, task_id=3)
        assert result["task_id"] == 3
        assert result["duration_s"] == 1.0


# ---------------------------------------------------------------------------
# Tests: run_all_tasks() — with mocked Popen
# ---------------------------------------------------------------------------

class TestRunAllTasks:
    """Tests for the main orchestration function."""

    def test_launches_one_process_per_task(self) -> None:
        """Popen must be called exactly once per task in the assignment."""
        mock_procs = [
            _make_mock_proc(task_id, TIER_TO_NODE[SAMPLE_ASSIGNMENT[task_id]])
            for task_id in SAMPLE_ASSIGNMENT
        ]

        with patch("src.executor.task_orchestrator.subprocess.Popen") as mock_popen:
            mock_popen.side_effect = mock_procs
            results = run_all_tasks(SAMPLE_ASSIGNMENT, SAMPLE_TASKS)

        assert mock_popen.call_count == len(SAMPLE_ASSIGNMENT)
        assert len(results) == len(SAMPLE_ASSIGNMENT)

    def test_dram_task_gets_node_zero_command(self) -> None:
        """Popen for DRAM tasks must include --cpunodebind=0 in the command."""
        mock_proc = _make_mock_proc(task_id=0, node=0)

        with patch("src.executor.task_orchestrator.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_proc
            # Run with only one DRAM task to isolate the assertion
            run_all_tasks({0: "DRAM"}, SAMPLE_TASKS)

        call_args = mock_popen.call_args[0][0]  # first positional arg = cmd list
        assert "--cpunodebind=0" in call_args
        assert "--membind=0" in call_args

    def test_cxl_task_gets_node_one_command(self) -> None:
        """Popen for CXL tasks must include --cpunodebind=1 in the command."""
        mock_proc = _make_mock_proc(task_id=1, node=1)

        with patch("src.executor.task_orchestrator.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_proc
            run_all_tasks({1: "CXL"}, SAMPLE_TASKS)

        call_args = mock_popen.call_args[0][0]
        assert "--cpunodebind=1" in call_args
        assert "--membind=1" in call_args

    def test_fallback_when_numactl_not_found(self) -> None:
        """
        When numactl raises FileNotFoundError, the orchestrator must retry
        without the numactl prefix (4 tokens: numactl, --cpunodebind, --membind, --).
        """
        mock_proc = _make_mock_proc(task_id=0, node=0)

        with patch("src.executor.task_orchestrator.subprocess.Popen") as mock_popen:
            # First call raises FileNotFoundError (numactl missing)
            # Second call succeeds (fallback without numactl)
            mock_popen.side_effect = [FileNotFoundError, mock_proc]
            run_all_tasks({0: "DRAM"}, SAMPLE_TASKS)

        # Popen must have been called twice: once with numactl, once without
        assert mock_popen.call_count == 2

        # The second call (fallback) must NOT contain numactl in the command
        fallback_cmd = mock_popen.call_args_list[1][0][0]
        assert "numactl" not in fallback_cmd[0]

    def test_non_zero_exit_code_does_not_raise(self) -> None:
        """
        A task that exits with a non-zero return code must NOT crash the
        orchestrator — the failure is logged and the result is still returned.
        """
        mock_proc = _make_mock_proc(task_id=0, node=0, returncode=1)

        with patch("src.executor.task_orchestrator.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_proc
            results = run_all_tasks({0: "DRAM"}, SAMPLE_TASKS)

        assert len(results) == 1
        assert results[0]["return_code"] == 1

    def test_dry_run_launches_no_subprocesses(self) -> None:
        """In dry-run mode, Popen must never be called."""
        with patch("src.executor.task_orchestrator.subprocess.Popen") as mock_popen:
            results = run_all_tasks(SAMPLE_ASSIGNMENT, SAMPLE_TASKS, dry_run=True)

        mock_popen.assert_not_called()
        assert len(results) == len(SAMPLE_ASSIGNMENT)
        # All results have zeroed timing in dry-run mode
        for r in results:
            assert r["duration_s"] == 0.0
            assert r["return_code"] == 0

    def test_result_dict_has_required_keys(self) -> None:
        """Every result dict must contain all required keys."""
        required_keys = {
            "task_id", "assigned_tier", "node",
            "start_time_s", "end_time_s", "duration_s", "return_code",
        }
        mock_proc = _make_mock_proc(task_id=0, node=0)

        with patch("src.executor.task_orchestrator.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_proc
            results = run_all_tasks({0: "DRAM"}, SAMPLE_TASKS)

        assert required_keys.issubset(results[0].keys())

    def test_raises_on_unknown_task_id_in_assignment(self) -> None:
        """If assignment contains a task_id not in tasks list, raise ValueError."""
        bad_assignment = {99: "DRAM"}  # task_id=99 doesn't exist in SAMPLE_TASKS
        with pytest.raises(ValueError, match="task_id=99"):
            run_all_tasks(bad_assignment, SAMPLE_TASKS)
