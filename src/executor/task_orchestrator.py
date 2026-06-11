"""
Task Orchestrator — Launches all 8 tasks as concurrent subprocesses.

This module sits between the scheduler layer and the task runner. It receives
a scheduler's assignment (which task goes to which memory tier), maps each
task to its numactl-bound subprocess command, launches all subprocesses
concurrently, waits for completion, and returns per-task result records.

Typical call chain:
    scheduler.schedule(tasks)              → assignment dict
    task_orchestrator.run_all_tasks(...)   → list of result dicts
    evaluation.metrics.*                   → computed metrics

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

import logging
import subprocess
import sys
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from src.scheduler.task_model import Task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps string tier names (from scheduler output) to integer NUMA node IDs
# used by numactl and task_runner.py --node flag.
TIER_TO_NODE: Dict[str, int] = {
    "DRAM": 0,
    "CXL": 1,
}

# Absolute path to task_runner.py.
# Path(__file__) is this file: src/executor/task_orchestrator.py
# .parents[2] walks two levels up: src/executor/ → src/ → project root
TASK_RUNNER_PATH: Path = Path(__file__).parents[2] / "task_runner.py"

# Python interpreter to use — same one running this process.
# This ensures the same .venv is used inside the subprocess.
PYTHON_EXECUTABLE: str = sys.executable

# Discover available NUMA nodes to avoid numactl crashes if a node is missing.
AVAILABLE_NUMA_NODES: Set[int] = set()
try:
    _numa_out = subprocess.check_output(
        ["numactl", "--hardware"], text=True, stderr=subprocess.DEVNULL
    )
    for _line in _numa_out.splitlines():
        if _line.startswith("node ") and " size:" in _line:
            _match = re.match(r"node (\d+) size:", _line)
            if _match:
                AVAILABLE_NUMA_NODES.add(int(_match.group(1)))
except (FileNotFoundError, subprocess.CalledProcessError):
    pass

if not AVAILABLE_NUMA_NODES:
    logger.info("numactl unavailable or no nodes detected. Using software latency simulation only.")
else:
    logger.info("Detected hardware NUMA nodes: %s", AVAILABLE_NUMA_NODES)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_command(
    task: Task,
    node: int,
    bandwidth_limit_mb_s: Optional[float] = None,
) -> List[str]:
    """
    Build the subprocess command list for a single task.

    We prefer numactl when available (Linux with NUMA support). On macOS or
    environments without numactl, we fall back to a plain python call.
    The numactl fallback is handled in run_all_tasks via FileNotFoundError.

    Command structure (with numactl):
        numactl --cpunodebind=<node> --membind=<node> -- python task_runner.py
            --task-id <id> --memory-mb <mb> --node <node>

    Command structure (without numactl):
        python task_runner.py --task-id <id> --memory-mb <mb> --node <node>

    Args:
        task: A Task object from src/scheduler/task_model.py.
        node: NUMA node integer (0=DRAM, 1=CXL).
        bandwidth_limit_mb_s: Optional CXL bandwidth cap in MiB/s. Added only
                              for CXL commands because DRAM tasks are unthrottled.

    Returns:
        List of strings representing the shell command and its arguments.
    """
    task_runner_args: List[str] = [
        PYTHON_EXECUTABLE,
        str(TASK_RUNNER_PATH),
        "--task-id", str(task.task_id),
        "--memory-mb", str(task.memory_requirement_mb),
        "--node", str(node),
    ]
    if node == 1 and bandwidth_limit_mb_s is not None:
        task_runner_args.extend([
            "--bandwidth-limit",
            str(bandwidth_limit_mb_s),
        ])

    if node in AVAILABLE_NUMA_NODES:
        numactl_prefix: List[str] = [
            "numactl",
            f"--cpunodebind={node}",
            f"--membind={node}",
            "--",  # separates numactl flags from the wrapped command
        ]
        return numactl_prefix + task_runner_args
    else:
        return task_runner_args


def _parse_csv_output(raw_stdout: str, task_id: int) -> Dict:
    """
    Parse the CSV line printed by task_runner.py from subprocess stdout.

    Expected format (one line):
        task_id,node,start_time_s,end_time_s,duration_s

    Args:
        raw_stdout: Raw captured stdout string from the subprocess.
        task_id:    Expected task_id (used for validation).

    Returns:
        Dict with keys: task_id, node, start_time_s, end_time_s, duration_s.
        Returns an empty dict if parsing fails (malformed output).
    """
    # strip() removes trailing newlines; split('\n') handles multi-line output
    # We look for the last non-empty line in case logs leaked to stdout
    lines = [line.strip() for line in raw_stdout.strip().split("\n") if line.strip()]
    if not lines:
        logger.warning("Task %d: no stdout output captured.", task_id)
        return {}

    csv_line = lines[-1]  # task_runner always prints CSV as the last stdout line
    parts = csv_line.split(",")

    if len(parts) != 5:
        logger.warning(
            "Task %d: unexpected CSV format '%s'", task_id, csv_line
        )
        return {}

    try:
        return {
            "task_id": int(parts[0]),
            "node": int(parts[1]),
            "start_time_s": float(parts[2]),
            "end_time_s": float(parts[3]),
            "duration_s": float(parts[4]),
        }
    except ValueError as exc:
        logger.warning("Task %d: CSV parse error — %s", task_id, exc)
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_all_tasks(
    assignment: Dict[int, str],
    tasks: List[Task],
    dry_run: bool = False,
    bandwidth_limit_mb_s: Optional[float] = None,
) -> List[Dict]:
    """
    Launch all tasks as concurrent subprocesses with NUMA binding.

    This is the primary entry point for the execution layer. It:
      1. Builds a numactl-wrapped subprocess command for each task.
      2. Launches all subprocesses simultaneously using Popen (non-blocking).
      3. Waits for all to finish (blocking .wait() per process).
      4. Collects stdout CSV lines from each process.
      5. Returns a list of per-task result dicts for the evaluation layer.

    Concurrency model:
        Popen launches without blocking → all 8 tasks start at roughly the
        same wall-clock time. We then call .wait() sequentially, but since
        they're already running the waits overlap — total wall time ≈ the
        duration of the slowest task, not the sum of all tasks.

    Args:
        assignment: Dict mapping task_id → "DRAM" or "CXL".
                    This comes directly from any scheduler's .schedule() method.
        tasks:      List of Task objects (from src/scheduler/tasks.py).
                    Used to look up each task's memory_requirement_mb.
        dry_run:    If True, print commands to logger but do not execute.
                    Useful for testing and CI environments without numactl.
        bandwidth_limit_mb_s: Optional CXL bandwidth cap in MiB/s, passed to
                              task_runner.py only for tasks assigned to CXL.

    Returns:
        List of per-task result dicts. Each dict contains:
            task_id      (int)   — task identifier
            assigned_tier (str)  — "DRAM" or "CXL"
            node         (int)   — NUMA node used
            start_time_s (float) — Unix timestamp of task start
            end_time_s   (float) — Unix timestamp of task end
            duration_s   (float) — total execution time in seconds
            return_code  (int)   — subprocess exit code (0 = success)

    Raises:
        ValueError: If a task_id in assignment has no matching Task object.
    """
    if bandwidth_limit_mb_s is not None and bandwidth_limit_mb_s <= 0:
        raise ValueError("bandwidth_limit_mb_s must be positive when provided.")

    # Build a lookup from task_id → Task object for fast access
    task_lookup: Dict[int, Task] = {t.task_id: t for t in tasks}

    # Validate that every task_id in the assignment exists in our task list
    for assigned_task_id in assignment:
        if assigned_task_id not in task_lookup:
            raise ValueError(
                f"task_id={assigned_task_id} in assignment not found in tasks list."
            )

    # -------------------------------------------------------------------------
    # Phase 1: Build commands and launch all subprocesses (non-blocking Popen)
    # -------------------------------------------------------------------------
    running_processes: List[Dict] = []  # holds (process, meta) pairs

    orchestration_start: float = time.time()
    logger.info(
        "Launching %d tasks concurrently (dry_run=%s)...", len(assignment), dry_run
    )

    for assigned_task_id, tier in assignment.items():
        task: Task = task_lookup[assigned_task_id]
        node: int = TIER_TO_NODE[tier]
        cmd: List[str] = _build_command(task, node, bandwidth_limit_mb_s)

        logger.info(
            "  Task %d → %s (node %d) | cmd: %s",
            assigned_task_id, tier, node, " ".join(cmd)
        )

        if dry_run:
            # In dry-run mode we record the intended command but don't run it
            running_processes.append({
                "task_id": assigned_task_id,
                "assigned_tier": tier,
                "node": node,
                "process": None,
                "cmd": cmd,
            })
            continue

        # Try to launch with numactl. If numactl is not installed (e.g. macOS,
        # or a Linux VM without the package), fall back to launching without it.
        try:
            launched_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,  # capture CSV result line
                stderr=subprocess.PIPE,  # capture log messages separately
                text=True,               # decode bytes → str automatically
            )
        except FileNotFoundError:
            # numactl not found — strip the numactl prefix and retry
            logger.warning(
                "numactl not found. Running task %d without NUMA binding.",
                assigned_task_id,
            )
            fallback_cmd = cmd[4:]  # skip: numactl --cpunodebind=N --membind=N --
            launched_proc = subprocess.Popen(
                fallback_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        running_processes.append({
            "task_id": assigned_task_id,
            "assigned_tier": tier,
            "node": node,
            "process": launched_proc,
            "cmd": cmd,
        })

    # -------------------------------------------------------------------------
    # Phase 2: Wait for all subprocesses to finish and collect results
    # -------------------------------------------------------------------------
    results: List[Dict] = []

    for entry in running_processes:
        completed_task_id: int = entry["task_id"]

        if dry_run:
            logger.info("  [dry-run] Would have run: %s", " ".join(entry["cmd"]))
            results.append({
                "task_id": completed_task_id,
                "assigned_tier": entry["assigned_tier"],
                "node": entry["node"],
                "start_time_s": 0.0,
                "end_time_s": 0.0,
                "duration_s": 0.0,
                "return_code": 0,
            })
            continue

        completed_proc: subprocess.Popen = entry["process"]
        stdout_str, stderr_str = completed_proc.communicate()
        return_code: int = completed_proc.returncode

        # Forward subprocess log lines to our own logger so they appear in the
        # parent process's output — useful for debugging task failures.
        if stderr_str:
            for line in stderr_str.strip().split("\n"):
                if line:
                    logger.debug("  [task %d stderr] %s", completed_task_id, line)

        if return_code != 0:
            logger.error(
                "Task %d exited with code %d. stderr: %s",
                completed_task_id, return_code, stderr_str.strip()
            )

        # Parse the CSV line from stdout
        timing = _parse_csv_output(stdout_str, completed_task_id)

        result: Dict = {
            "task_id": completed_task_id,
            "assigned_tier": entry["assigned_tier"],
            "node": entry["node"],
            "start_time_s": timing.get("start_time_s", 0.0),
            "end_time_s": timing.get("end_time_s", 0.0),
            "duration_s": timing.get("duration_s", 0.0),
            "return_code": return_code,
        }
        results.append(result)
        logger.info(
            "  Task %d done | tier=%s | duration=%.4f s | exit=%d",
            completed_task_id,
            entry["assigned_tier"],
            result["duration_s"],
            return_code,
        )

    total_wall_time: float = time.time() - orchestration_start
    logger.info(
        "All %d tasks complete. Wall time: %.4f s", len(results), total_wall_time
    )

    return results
