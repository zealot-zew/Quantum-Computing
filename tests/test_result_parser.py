"""
Unit tests for src.rqaoa.result_parser.
"""

from typing import Dict

import pytest

from src.rqaoa.result_parser import EXPECTED_TASK_COUNT, decode_bitstring


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
