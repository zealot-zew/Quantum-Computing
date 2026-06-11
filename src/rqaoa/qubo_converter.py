
"""
qubo_converter.py
Converts numpy QUBO matrix to OpenQAOA dict format: {(i, j): coefficient}
"""

import numpy as np


def convert_numpy_qubo_to_openqaoa_dict(qubo_matrix: np.ndarray) -> dict:
    """
    Args:
        qubo_matrix: Upper-triangular NxN numpy array.
    Returns:
        Dict {(i, j): coeff} for all non-zero entries. i <= j.
    """
    n = qubo_matrix.shape[0]
    return {
        (i, j): float(qubo_matrix[i][j])
        for i in range(n)
        for j in range(i, n)
        if abs(qubo_matrix[i][j]) > 1e-10
    }
