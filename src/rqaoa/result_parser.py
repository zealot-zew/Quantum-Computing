"""
RQAOA result parser.

The quantum runner returns one binary decision variable per task:
    x[i] = 0 -> task i goes to DRAM
    x[i] = 1 -> task i goes to CXL

This module converts that raw bitstring into the scheduler assignment dict
consumed by src.executor.task_orchestrator.run_all_tasks().
"""

from typing import Dict

EXPECTED_TASK_COUNT: int = 8
DRAM_BIT: str = "0"
CXL_BIT: str = "1"
DRAM_TIER: str = "DRAM"
CXL_TIER: str = "CXL"
VALID_BITS = frozenset({DRAM_BIT, CXL_BIT})


def decode_bitstring(
    bitstring: str,
    expected_task_count: int = EXPECTED_TASK_COUNT,
) -> Dict[int, str]:
    """
    Decode an RQAOA bitstring into a task-to-memory-tier assignment.

    Args:
        bitstring: Binary output from RQAOA, with one character per task.
        expected_task_count: Number of task variables expected in bitstring.

    Returns:
        Dict mapping task_id to "DRAM" or "CXL".

    Raises:
        TypeError: If bitstring is not a string.
        ValueError: If the bitstring is empty, has the wrong length, contains
                    non-binary characters, or expected_task_count is invalid.
    """
    if not isinstance(bitstring, str):
        raise TypeError(
            f"bitstring must be a str, got {type(bitstring).__name__}."
        )
    if expected_task_count <= 0:
        raise ValueError("expected_task_count must be positive.")

    normalized_bitstring: str = bitstring.strip()
    if not normalized_bitstring:
        raise ValueError("bitstring must not be empty.")
    if len(normalized_bitstring) != expected_task_count:
        raise ValueError(
            f"Expected {expected_task_count} bits, got "
            f"{len(normalized_bitstring)}: {normalized_bitstring!r}."
        )

    invalid_bits = sorted(set(normalized_bitstring) - VALID_BITS)
    if invalid_bits:
        raise ValueError(
            f"bitstring contains non-binary characters: {invalid_bits}."
        )

    assignment: Dict[int, str] = {}
    for task_id, bit in enumerate(normalized_bitstring):
        assignment[task_id] = CXL_TIER if bit == CXL_BIT else DRAM_TIER

    if len(assignment) != expected_task_count:
        raise ValueError(
            "Decoded assignment does not cover every expected task."
        )

    return assignment
