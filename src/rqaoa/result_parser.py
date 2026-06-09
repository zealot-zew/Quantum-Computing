
"""result_parser.py — Decodes RQAOA output. 0=DRAM, 1=CXL."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

EXPECTED_TASK_COUNT = 8

def decode_bitstring(bitstring: str, expected_task_count: int = EXPECTED_TASK_COUNT) -> Dict[int, str]:
    """
    Decodes a bitstring like '10110010' into a dictionary mapping task IDs to memory tiers.
    0 = DRAM, 1 = CXL.
    """
    if not isinstance(bitstring, str):
        raise TypeError("bitstring must be a str")
    
    bitstring = bitstring.strip()
    
    if not bitstring:
        raise ValueError("bitstring must not be empty")
        
    if len(bitstring) != expected_task_count:
        raise ValueError(f"Expected {expected_task_count} bits, got {len(bitstring)}")
        
    assignment = {}
    for task_id, bit in enumerate(bitstring):
        if bit not in ('0', '1'):
            raise ValueError(f"Found non-binary character '{bit}' at index {task_id}")
        assignment[task_id] = "CXL" if bit == '1' else "DRAM"
        
    return assignment


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
