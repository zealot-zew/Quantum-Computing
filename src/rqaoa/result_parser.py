
"""result_parser.py — Decodes RQAOA output. 0=DRAM, 1=CXL."""

import logging
logger = logging.getLogger(__name__)


def decode_assignment_to_memory_map(assignment: dict) -> dict:
    """Returns {task_id: "DRAM" or "CXL"}. Raises ValueError on invalid values."""
    memory_map = {}
    for task_id, bit in assignment.items():
        if bit not in (0, 1):
            raise ValueError(f"Task {task_id}: expected 0/1, got {bit}")
        memory_map[task_id] = "DRAM" if bit == 0 else "CXL"
    return memory_map


def validate_assignment(assignment: dict, expected_count: int) -> bool:
    if len(assignment) != expected_count:
        logger.error(f"Expected {expected_count} tasks, got {len(assignment)}")
        return False
    for tid, bit in assignment.items():
        if bit not in (0, 1):
            logger.error(f"Task {tid}: invalid value {bit}")
            return False
    logger.info("Validation passed ✅")
    return True
