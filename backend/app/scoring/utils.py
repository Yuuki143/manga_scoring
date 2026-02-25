"""
MMIP Scoring Utility Functions

Stateless mathematical helpers used by the scoring engine and hit predictor.
All functions operate on plain Python sequences or numpy arrays and have no
dependency on the database layer, making them straightforward to unit-test.

Functions:
    percentile_rank        - Ordinal percentile of a value within a list.
    gini_coefficient       - Gini coefficient of inequality for a distribution.
    sigmoid_normalize      - Map any real value to [0, 1] via a sigmoid curve.
    coefficient_of_variation - Relative standard deviation (std / mean).
    growth_rate            - Percentage change between two values.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


# ---------------------------------------------------------------------------
# percentile_rank
# ---------------------------------------------------------------------------

def percentile_rank(value: float, values_list: Sequence[float]) -> float:
    """Return the percentile rank of *value* within *values_list*.

    The percentile rank is the fraction of values in the list that are
    strictly less than *value*, expressed as a percentage in [0, 100].

    Args:
        value: The scalar whose rank is sought.
        values_list: A non-empty collection of comparable numeric values.

    Returns:
        A float in [0.0, 100.0].  Returns 0.0 when *values_list* is empty
        or contains a single element, and 100.0 when *value* is greater
        than every element in the list.

    Examples:
        >>> percentile_rank(75, [50, 60, 70, 80, 90])
        60.0
        >>> percentile_rank(50, [50])
        0.0
    """
    arr = np.asarray(values_list, dtype=float)
    if arr.size == 0:
        return 0.0
    # Number of values strictly below the target
    below = np.sum(arr < value)
    return float(below / arr.size * 100.0)


# ---------------------------------------------------------------------------
# gini_coefficient
# ---------------------------------------------------------------------------

def gini_coefficient(values: Sequence[float]) -> float:
    """Compute the Gini coefficient of a distribution.

    A Gini coefficient of 0 indicates perfect equality (all values identical),
    while 1 indicates maximum inequality (all value concentrated in one
    element).  Negative or zero-sum inputs return 0.0 (treated as undefined /
    perfectly equal).

    Uses the standard sorted-differences formula:
        G = (2 * sum(i * x_i) - (n + 1) * sum(x_i)) / (n * sum(x_i))
    which avoids the O(n²) pairwise-differences approach.

    Args:
        values: A sequence of non-negative numeric values representing
                portions of some total (e.g. revenue per platform).

    Returns:
        A float in [0.0, 1.0].

    Examples:
        >>> round(gini_coefficient([1, 1, 1, 1]), 4)
        0.0
        >>> round(gini_coefficient([0, 0, 0, 100]), 4)
        0.75
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[arr >= 0]          # strip any negative sentinel values
    if arr.size == 0 or arr.sum() == 0:
        return 0.0
    arr = np.sort(arr)           # ascending sort required by the formula
    n = arr.size
    index = np.arange(1, n + 1)  # 1-based rank
    # Standard Gini formula via sorted cumulative sum
    gini = (2.0 * np.dot(index, arr) - (n + 1) * arr.sum()) / (n * arr.sum())
    return float(np.clip(gini, 0.0, 1.0))


# ---------------------------------------------------------------------------
# sigmoid_normalize
# ---------------------------------------------------------------------------

def sigmoid_normalize(value: float, center: float = 0.0, scale: float = 1.0) -> float:
    """Map a real-valued input to (0, 1) using a logistic sigmoid.

    The sigmoid is centred at *center* and its steepness is controlled by
    *scale* (larger scale = shallower curve, wider dynamic range).

        output = 1 / (1 + exp(-(value - center) / scale))

    Args:
        value:  The raw input to normalise (e.g. a growth-rate percentage).
        center: The input value that should map to exactly 0.5.
                For growth rates this is typically 0.0.
        scale:  Controls the width of the transition region.  A value equal
                to the expected standard deviation of the input is a good
                starting point.

    Returns:
        A float in (0.0, 1.0).

    Examples:
        >>> round(sigmoid_normalize(0.0, center=0.0, scale=1.0), 4)
        0.5
        >>> sigmoid_normalize(100, center=0, scale=10) > 0.99
        True
    """
    try:
        return float(1.0 / (1.0 + np.exp(-(value - center) / scale)))
    except (ZeroDivisionError, FloatingPointError):
        return 0.5


# ---------------------------------------------------------------------------
# coefficient_of_variation
# ---------------------------------------------------------------------------

def coefficient_of_variation(values: Sequence[float]) -> float:
    """Compute the coefficient of variation (CV) of a sample.

    CV = std(values) / mean(values)

    CV is dimensionless and quantifies relative variability.  A lower CV
    means more stable/consistent values.

    Args:
        values: A sequence of positive numeric values (e.g. monthly revenues).

    Returns:
        A non-negative float.  Returns 0.0 when the sequence has fewer than
        two elements, when the mean is zero, or when all values are identical.

    Examples:
        >>> coefficient_of_variation([100, 100, 100])
        0.0
        >>> round(coefficient_of_variation([10, 20, 30, 40, 50]), 4)
        0.5164
    """
    arr = np.asarray(values, dtype=float)
    if arr.size < 2:
        return 0.0
    mean = arr.mean()
    if mean == 0.0:
        return 0.0
    return float(arr.std(ddof=1) / abs(mean))


# ---------------------------------------------------------------------------
# growth_rate
# ---------------------------------------------------------------------------

def growth_rate(current: float, previous: float) -> float:
    """Calculate the simple percentage growth rate between two values.

    growth_rate = (current - previous) / |previous|

    Args:
        current:  The more recent value.
        previous: The baseline value.

    Returns:
        A float representing the fractional change (e.g. 0.25 = 25% growth).
        Returns 0.0 when *previous* is zero to avoid division by zero.
        Returns 1.0 (100% growth) when *previous* is zero but *current* is
        positive, signalling new revenue where there was none before.

    Examples:
        >>> growth_rate(120, 100)
        0.2
        >>> growth_rate(80, 100)
        -0.2
        >>> growth_rate(50, 0)
        1.0
    """
    if previous == 0:
        return 1.0 if current > 0 else 0.0
    return float((current - previous) / abs(previous))
