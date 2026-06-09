"""
Unit tests for src.rqaoa.result_parser.

Tests all three public functions:
  - decode_bitstring()              — string bitstring → {task_id: "DRAM"|"CXL"}
  - decode_assignment_to_memory_map() — int dict → {task_id: "DRAM"|"CXL"}
  - validate_assignment()           — validates binary assignment dict

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

from typing import Dict

import pytest

from src.rqaoa.result_parser import (
    EXPECTED_TASK_COUNT,
    decode_bitstring,
    decode_assignment_to_memory_map,
    validate_assignment,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: decode_bitstring()
# ─────────────────────────────────────────────────────────────────────────────


def test_decode_valid_eight_bit_string() -> None:
    """A valid 8-bit RQAOA result must map every task to a memory tier."""
    assignment: Dict[int, str] = decode_bitstring("10110010")

    assert assignment == {
        0: "CXL",
        1: "DRAM",
        2: "CXL",
        3: "CXL",
        4: "DRAM",
        5: "DRAM",
        6: "CXL",
        7: "DRAM",
    }


def test_decode_strips_outer_whitespace() -> None:
    """Whitespace around the bitstring should not affect decoding."""
    assignment: Dict[int, str] = decode_bitstring(" 00000000\n")

    assert len(assignment) == EXPECTED_TASK_COUNT
    assert set(assignment.values()) == {"DRAM"}


def test_decode_rejects_wrong_length() -> None:
    """The parser must reject partial assignments."""
    with pytest.raises(ValueError, match="Expected 8 bits"):
        decode_bitstring("101")


def test_decode_rejects_non_binary_characters() -> None:
    """Only 0 and 1 are valid RQAOA decision bits."""
    with pytest.raises(ValueError, match="non-binary"):
        decode_bitstring("10110x10")


def test_decode_rejects_empty_string() -> None:
    """An empty result cannot produce a valid assignment."""
    with pytest.raises(ValueError, match="must not be empty"):
        decode_bitstring("")


def test_decode_rejects_non_string_input() -> None:
    """The parser contract is intentionally string-only."""
    with pytest.raises(TypeError, match="must be a str"):
        decode_bitstring(10110010)  # type: ignore[arg-type]


def test_decode_supports_explicit_task_count() -> None:
    """Small fixtures can override expected_task_count for focused tests."""
    assert decode_bitstring("10", expected_task_count=2) == {
        0: "CXL",
        1: "DRAM",
    }


def test_decode_all_cxl() -> None:
    """All-ones bitstring should assign every task to CXL."""
    result = decode_bitstring("11111111")
    assert all(tier == "CXL" for tier in result.values())
    assert len(result) == EXPECTED_TASK_COUNT


def test_decode_all_dram() -> None:
    """All-zeros bitstring should assign every task to DRAM."""
    result = decode_bitstring("00000000")
    assert all(tier == "DRAM" for tier in result.values())
    assert len(result) == EXPECTED_TASK_COUNT


# ─────────────────────────────────────────────────────────────────────────────
# Tests: decode_assignment_to_memory_map()
# ─────────────────────────────────────────────────────────────────────────────


def test_memory_map_valid_all_dram() -> None:
    """All-zero assignment should map to all DRAM."""
    assignment = {0: 0, 1: 0, 2: 0}
    result = decode_assignment_to_memory_map(assignment)
    assert result == {0: "DRAM", 1: "DRAM", 2: "DRAM"}


def test_memory_map_valid_all_cxl() -> None:
    """All-one assignment should map to all CXL."""
    assignment = {0: 1, 1: 1, 2: 1}
    result = decode_assignment_to_memory_map(assignment)
    assert result == {0: "CXL", 1: "CXL", 2: "CXL"}


def test_memory_map_valid_mixed() -> None:
    """Mixed 0/1 assignment should produce correct DRAM/CXL mapping."""
    assignment = {0: 0, 1: 1, 2: 0, 3: 1}
    result = decode_assignment_to_memory_map(assignment)
    assert result == {0: "DRAM", 1: "CXL", 2: "DRAM", 3: "CXL"}


def test_memory_map_rejects_invalid_value() -> None:
    """Values other than 0 or 1 should raise ValueError."""
    with pytest.raises(ValueError, match="expected 0/1"):
        decode_assignment_to_memory_map({0: 0, 1: 2})


def test_memory_map_rejects_negative_value() -> None:
    """Negative values should raise ValueError."""
    with pytest.raises(ValueError, match="expected 0/1"):
        decode_assignment_to_memory_map({0: -1})


def test_memory_map_rejects_string_value() -> None:
    """String values should raise ValueError."""
    with pytest.raises(ValueError, match="expected 0/1"):
        decode_assignment_to_memory_map({0: "DRAM"})  # type: ignore[dict-item]


def test_memory_map_empty_dict() -> None:
    """Empty assignment should return empty map."""
    result = decode_assignment_to_memory_map({})
    assert result == {}


def test_memory_map_single_task() -> None:
    """Single-task assignment should work."""
    assert decode_assignment_to_memory_map({5: 0}) == {5: "DRAM"}
    assert decode_assignment_to_memory_map({5: 1}) == {5: "CXL"}


# ─────────────────────────────────────────────────────────────────────────────
# Tests: validate_assignment()
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_correct_assignment() -> None:
    """A correct 8-task binary assignment should pass validation."""
    assignment = {i: i % 2 for i in range(8)}
    assert validate_assignment(assignment, expected_count=8) is True


def test_validate_wrong_count() -> None:
    """Too few tasks should fail validation."""
    assignment = {0: 0, 1: 1}
    assert validate_assignment(assignment, expected_count=8) is False


def test_validate_extra_tasks() -> None:
    """Too many tasks should fail validation."""
    assignment = {i: 0 for i in range(10)}
    assert validate_assignment(assignment, expected_count=8) is False


def test_validate_invalid_bit_value() -> None:
    """Non-binary values (e.g. 2) should fail validation."""
    assignment = {0: 0, 1: 2}
    assert validate_assignment(assignment, expected_count=2) is False


def test_validate_single_task() -> None:
    """Single-task assignment should validate correctly."""
    assert validate_assignment({0: 0}, expected_count=1) is True
    assert validate_assignment({0: 1}, expected_count=1) is True
