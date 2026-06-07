#!/usr/bin/env python3
"""
Task Runner — Simulates a memory-bound workload on a given NUMA node.

Each run of this script represents one task being executed. It is always
launched as a subprocess by task_orchestrator.py — never run directly in
production.

Responsibilities:
    1. Parse CLI arguments (task-id, memory-mb, node).
    2. Allocate the requested amount of memory using NumPy.
    3. Simulate memory-bound work by iterating over the array in chunks.
    4. Inject artificial CXL latency for node=1 tasks (software simulation
       since hardware NUMA emulation is unavailable — see docs/numa_verification.md).
    5. Print a single CSV line to stdout with timing results.

Output format (stdout):
    task_id,node,start_time_s,end_time_s,duration_s
    3,1,1717839600.123,1717839601.456,1.333

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

import argparse
import logging
import sys
import time

import numpy as np

# ---------------------------------------------------------------------------
# Logging — goes to stdout like everything else; orchestrator reads stdout
# for the final CSV line and stderr for log messages. We split them.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] task_runner | %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],  # logs → stderr
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# How many float64 elements we process per loop iteration.
# 1024 floats × 8 bytes = 8 KB — one or two cache lines. Keeps the loop
# tight enough to be measurable without being trivially fast.
CHUNK_SIZE: int = 1024

# Artificial delay injected per chunk for CXL (node=1) tasks.
# Real CXL adds ~200 ns extra latency per access. At 1024 accesses per chunk
# that is ~200 µs. We round up to 2 ms for clear measurability in tests.
# DRAM (node=0) tasks: no sleep — they run at full speed.
CXL_LATENCY_PENALTY_S: float = 0.002  # 2 ms per chunk
DRAM_LATENCY_PENALTY_S: float = 0.0   # No penalty for DRAM


# ---------------------------------------------------------------------------
# Argument parsing (kept as a pure function for easy testing)
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the task runner.

    Returns:
        Namespace with attributes: task_id (int), memory_mb (float), node (int).
    """
    parser = argparse.ArgumentParser(
        description="Simulate a memory-bound task on a target NUMA node."
    )

    parser.add_argument(
        "--task-id",
        type=int,
        required=True,
        help="Unique identifier for this task (0–7).",
    )

    def _positive_float(value: str) -> float:
        """Validator: ensures memory-mb is a positive number."""
        v = float(value)
        if v <= 0:
            raise argparse.ArgumentTypeError("--memory-mb must be > 0")
        return v

    parser.add_argument(
        "--memory-mb",
        type=_positive_float,
        required=True,
        help="Memory to allocate in Megabytes (e.g. 512.0).",
    )

    parser.add_argument(
        "--node",
        type=int,
        choices=[0, 1],
        required=True,
        help="Target NUMA node: 0 = DRAM (fast), 1 = CXL (slow).",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Core work simulation
# ---------------------------------------------------------------------------

def allocate_memory(memory_mb: float) -> np.ndarray:
    """
    Allocate a NumPy array large enough to occupy the requested memory.

    We use np.random.rand so the OS actually commits physical pages
    immediately. A zeroed array (np.zeros) might be deferred by the kernel's
    copy-on-write mechanism, giving inaccurate timing.

    Args:
        memory_mb: Memory size to allocate in megabytes.

    Returns:
        1-D array of float64 values. Each float64 is 8 bytes, so:
        n_elements = memory_mb × 1024 × 1024 / 8.

    Raises:
        MemoryError: If the system cannot satisfy the allocation.
    """
    # Number of float64 elements needed to fill 'memory_mb' megabytes.
    # Integer division (//) ensures we never exceed the requested size.
    n_elements: int = int(memory_mb * 1024 * 1024) // 8
    logger.info(
        "Allocating %.1f MB → %d float64 elements (%.1f MB actual)",
        memory_mb,
        n_elements,
        n_elements * 8 / (1024 * 1024),
    )
    return np.random.rand(n_elements)


def simulate_work(data: np.ndarray, node: int) -> None:
    """
    Simulate a memory-bound workload by reading the array in chunks.

    Iterating over the array forces the CPU to touch every memory page,
    creating realistic memory pressure — the same pressure a real task
    (e.g. a database buffer scan) would create.

    For CXL (node=1) tasks, a small sleep is injected between chunks to
    simulate the extra latency of CXL-attached memory versus local DRAM.
    This is the software-simulation workaround approved in docs/numa_verification.md.

    Args:
        data: The NumPy array to iterate over.
        node: NUMA node ID. 0 = DRAM (no penalty), 1 = CXL (with penalty).
    """
    latency_penalty_s: float = (
        CXL_LATENCY_PENALTY_S if node == 1 else DRAM_LATENCY_PENALTY_S
    )
    tier_name: str = "CXL" if node == 1 else "DRAM"

    n_chunks: int = 0
    # Iterate over the array in non-overlapping CHUNK_SIZE slices.
    # np.sum on each slice forces a real read — the compiler cannot
    # optimise it away because we use the result (even if we discard it).
    for start in range(0, len(data), CHUNK_SIZE):
        chunk = data[start : start + CHUNK_SIZE]
        _ = np.sum(chunk)  # force memory read

        if latency_penalty_s > 0:
            time.sleep(latency_penalty_s)  # simulate CXL access overhead

        n_chunks += 1

    logger.info(
        "Work complete: %d chunks processed on %s node (penalty=%.3f s/chunk)",
        n_chunks,
        tier_name,
        latency_penalty_s,
    )


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def emit_csv_result(
    task_id: int,
    node: int,
    start_time_s: float,
    end_time_s: float,
) -> None:
    """
    Print a single CSV-formatted result line to stdout.

    The orchestrator captures this line via subprocess.PIPE and
    feeds it into the evaluation pipeline.

    Format:
        task_id,node,start_time_s,end_time_s,duration_s

    Args:
        task_id:      Task identifier.
        node:         NUMA node used (0=DRAM, 1=CXL).
        start_time_s: Unix timestamp when task work began.
        end_time_s:   Unix timestamp when task work finished.
    """
    duration_s: float = end_time_s - start_time_s
    csv_line: str = (
        f"{task_id},{node},{start_time_s:.6f},{end_time_s:.6f},{duration_s:.6f}"
    )
    # Print to stdout — this is the contract with task_orchestrator.py
    print(csv_line, flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Main entry point: parse args → allocate → simulate → log CSV.

    Exit codes:
        0 — success
        1 — MemoryError (could not allocate requested memory)
    """
    args = parse_arguments()

    logger.info(
        "Starting task %d | memory=%.1f MB | node=%d (%s)",
        args.task_id,
        args.memory_mb,
        args.node,
        "CXL" if args.node == 1 else "DRAM",
    )

    # --- Step 1: Allocate memory ---
    try:
        data = allocate_memory(args.memory_mb)
    except MemoryError:
        logger.error(
            "Task %d failed: cannot allocate %.1f MB — system out of memory.",
            args.task_id,
            args.memory_mb,
        )
        sys.exit(1)

    # --- Step 2: Record start time and run work ---
    start_time_s: float = time.time()
    simulate_work(data, args.node)
    end_time_s: float = time.time()

    # --- Step 3: Emit CSV result to stdout ---
    emit_csv_result(args.task_id, args.node, start_time_s, end_time_s)

    logger.info(
        "Task %d finished in %.4f s",
        args.task_id,
        end_time_s - start_time_s,
    )


if __name__ == "__main__":
    main()
