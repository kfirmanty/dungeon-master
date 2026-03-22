"""
Utility functions — small, reusable helpers.
"""

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    GEOMETRIC INTERPRETATION:
    Cosine similarity measures the cosine of the angle between two vectors
    in high-dimensional space.

        cos(θ) = (a · b) / (‖a‖ × ‖b‖)

    Where:
        a · b  = dot product = sum of element-wise products
        ‖a‖   = L2 norm = sqrt(sum of squared elements)

    Results range from:
        1.0  → vectors point in the same direction (identical meaning)
        0.0  → vectors are perpendicular (unrelated meaning)
       -1.0  → vectors point in opposite directions (rare for embeddings)

    For L2-normalized vectors (unit length), this simplifies to just the
    dot product:  cos(θ) = a · b   (because ‖a‖ = ‖b‖ = 1)

    NOTE: pgvector uses cosine DISTANCE (1 - similarity) with the <=> operator.
    Distance: 0.0 = identical, 2.0 = opposite. We use similarity here because
    "0.92 similarity" is more intuitive than "0.08 distance".
    """
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
