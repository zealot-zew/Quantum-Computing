"""
QUBO Format Converter — Translates PyQUBO output to OpenQAOA input format.

PyQUBO (used by P1 in qubo_builder.py) represents QUBO variables as strings
like 'x[0]', 'x[1]', etc. OpenQAOA (the quantum circuit runner) expects
variables as plain integer indices in a dict with tuple keys.

This module provides a single function, convert_to_openqaoa_format(), that
performs this translation so P1's qubo_builder.py output can feed directly
into P1's rqaoa_runner.py without any manual reformatting.

Example:
    PyQUBO format (input):
        {
            ('x[0]', 'x[0]'): 102.4,    # diagonal: cost of sending task 0 to CXL
            ('x[0]', 'x[1]'): 50.0,     # off-diagonal: interaction penalty
            ('x[1]', 'x[1]'): 43.8,
        }

    OpenQAOA format (output):
        {
            (0, 0): 102.4,
            (0, 1): 50.0,
            (1, 1): 43.8,
        }

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

import logging
import re
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Regex pattern to extract the integer index from a PyQUBO variable name.
# Matches strings of the form 'x[N]' and captures N as group 1.
# Examples: 'x[0]' → '0', 'x[12]' → '12', 'x[7]' → '7'
_PYQUBO_VAR_PATTERN: re.Pattern = re.compile(r"^x\[(\d+)\]$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_variable_index(var_name: str) -> int:
    """
    Extract the integer index from a PyQUBO variable name string.

    PyQUBO names variables as 'x[i]' where i is the task index.
    This function strips the 'x[' prefix and ']' suffix to return i.

    Args:
        var_name: A PyQUBO variable name string, e.g. 'x[3]'.

    Returns:
        Integer index i, e.g. 3.

    Raises:
        ValueError: If var_name does not match the expected 'x[N]' pattern.
    """
    match = _PYQUBO_VAR_PATTERN.match(var_name)
    if match is None:
        raise ValueError(
            f"Cannot parse PyQUBO variable name '{var_name}'. "
            f"Expected format: 'x[N]' where N is a non-negative integer."
        )
    return int(match.group(1))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_to_openqaoa_format(
    pyqubo_dict: Dict[Tuple[str, str], float],
) -> Dict[Tuple[int, int], float]:
    """
    Convert a PyQUBO QUBO dictionary to OpenQAOA-compatible integer-key format.

    PyQUBO uses string variable names ('x[0]', 'x[1]', ...) as keys.
    OpenQAOA requires plain integer indices as tuple keys ((0, 0), (0, 1), ...).

    This function:
      1. Iterates over every (var_i, var_j) → coefficient entry.
      2. Parses the integer index from each variable name.
      3. Rebuilds the dict with (int, int) tuple keys.
      4. Merges duplicate entries by summing their coefficients
         (PyQUBO sometimes produces both (i, j) and (j, i) for the same pair;
          OpenQAOA treats the QUBO as upper-triangular so we normalise to i ≤ j).

    Args:
        pyqubo_dict: QUBO dict from PyQUBO's .to_qubo() or qubo_builder.
                     Keys are (str, str) variable name pairs.
                     Values are float coefficients.

    Returns:
        OpenQAOA-compatible QUBO dict with (int, int) tuple keys and float values.
        Keys are normalised so that key[0] <= key[1] (upper-triangular form).

    Raises:
        ValueError: If any variable name cannot be parsed.
        TypeError:  If pyqubo_dict is not a dict.

    Example:
        >>> pyqubo = {('x[0]', 'x[0]'): 102.4, ('x[0]', 'x[1]'): 50.0}
        >>> convert_to_openqaoa_format(pyqubo)
        {(0, 0): 102.4, (0, 1): 50.0}
    """
    if not isinstance(pyqubo_dict, dict):
        raise TypeError(
            f"pyqubo_dict must be a dict, got {type(pyqubo_dict).__name__}."
        )

    openqaoa_dict: Dict[Tuple[int, int], float] = {}

    for (var_i, var_j), coefficient in pyqubo_dict.items():
        # Parse both variable names to integer indices
        idx_i: int = _parse_variable_index(var_i)
        idx_j: int = _parse_variable_index(var_j)

        # Normalise to upper-triangular: always store with smaller index first.
        # This prevents duplicate entries like (1, 0) and (0, 1) from being
        # stored separately — OpenQAOA only reads (i, j) where i <= j.
        key: Tuple[int, int] = (min(idx_i, idx_j), max(idx_i, idx_j))

        # Accumulate coefficients in case PyQUBO emits both (i, j) and (j, i)
        openqaoa_dict[key] = openqaoa_dict.get(key, 0.0) + coefficient

    logger.info(
        "Converted %d PyQUBO entries → %d OpenQAOA entries.",
        len(pyqubo_dict),
        len(openqaoa_dict),
    )

    return openqaoa_dict


def validate_qubo_dict(
    qubo_dict: Dict[Tuple[int, int], float],
    expected_n_variables: int,
) -> bool:
    """
    Sanity-check an OpenQAOA-format QUBO dict before passing it to the runner.

    Checks:
      - All keys are (int, int) tuples with 0 <= i <= j < expected_n_variables.
      - All values are finite floats.
      - Diagonal entries (i == j) exist for every variable 0..N-1.

    Args:
        qubo_dict:            The converted OpenQAOA QUBO dict.
        expected_n_variables: Expected number of variables (tasks). For this
                              project this is always 8.

    Returns:
        True if the dict passes all checks.

    Raises:
        ValueError: On the first validation failure encountered, with a
                    descriptive message explaining what is wrong.
    """
    import math

    # Check all keys and values
    for key, value in qubo_dict.items():
        if not isinstance(key, tuple) or len(key) != 2:
            raise ValueError(f"Key {key} is not a 2-tuple.")
        i, j = key
        if not (0 <= i <= j < expected_n_variables):
            raise ValueError(
                f"Key {key} violates 0 <= i <= j < {expected_n_variables}."
            )
        if not math.isfinite(value):
            raise ValueError(f"Coefficient at {key} is not finite: {value}.")

    # Check that every variable has a diagonal entry
    for idx in range(expected_n_variables):
        if (idx, idx) not in qubo_dict:
            raise ValueError(
                f"Diagonal entry ({idx}, {idx}) is missing. "
                f"Every variable must have a self-cost term."
            )

    logger.info(
        "QUBO dict validation passed: %d variables, %d entries.",
        expected_n_variables,
        len(qubo_dict),
    )
    return True
