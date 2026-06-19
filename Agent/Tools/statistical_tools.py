"""
Statistical verification tools for the Tool Calling Agent.
These are the actual computational tools that verify reported statistics.
Uses scipy for recalculations and numpy for pattern detection.
"""

from langchain.tools import tool
from typing import Optional
import math
from Agent.logging_config import setup_logging, get_agent_logger

setup_logging()
logger = get_agent_logger("statistical_tools")


@tool
def verify_p_value(
    test_statistic_value: float,
    degrees_of_freedom: list[int],
    test_statistic_type: str,
    reported_p_value: float,
) -> dict:
    """Recalculate a p-value from the test statistic and degrees of freedom,
    then compare it to the reported p-value. Flags discrepancies > 0.01.
    
    Args:
        test_statistic_value: The reported test statistic (F, t, chi2)
        degrees_of_freedom: Degrees of freedom as a list (e.g. [2, 27] for ANOVA)
        test_statistic_type: Type of test statistic - 'F', 't', or 'chi2'
        reported_p_value: The p-value reported in the paper (numeric)
    """
    try:
        from scipy import stats as sp_stats
    except ImportError:
        logger.error("scipy not installed — cannot verify p-value")
        return {"error": "scipy not available", "match": None}

    stat_type = test_statistic_type.lower().strip()
    value = test_statistic_value
    df = degrees_of_freedom

    try:
        if stat_type == "f" and len(df) == 2:
            calculated_p = 1 - sp_stats.f.cdf(value, df[0], df[1])
        elif stat_type == "t" and len(df) >= 1:
            calculated_p = 2 * (1 - sp_stats.t.cdf(abs(value), df[0]))  # two-tailed
        elif stat_type in ("chi2", "chi-square", "chi_square") and len(df) >= 1:
            calculated_p = 1 - sp_stats.chi2.cdf(value, df[0])
        else:
            return {
                "error": f"Unsupported test type '{stat_type}' with df={df}",
                "match": None,
            }
    except Exception as e:
        logger.error(f"p-value calculation failed: {e}")
        return {"error": str(e), "match": None}

    discrepancy = abs(calculated_p - reported_p_value)
    match = discrepancy <= 0.01  # tolerance

    result = {
        "calculated_p_value": round(calculated_p, 6),
        "reported_p_value": reported_p_value,
        "discrepancy": round(discrepancy, 6),
        "match": match,
        "flag": "P-VALUE MISMATCH" if not match else None,
    }
    logger.info(f"p-value verify: calc={calculated_p:.6f} vs reported={reported_p_value} → {'MATCH' if match else 'MISMATCH'}")
    return result


@tool
def check_sample_size_power(
    sample_size: int,
    effect_size: float,
    alpha: float = 0.05,
    test_type: str = "t-test",
) -> dict:
    """Basic statistical power check given sample size and effect size.
    Returns estimated power and whether it meets the 0.80 threshold.

    Args:
        sample_size: Number of subjects/observations
        effect_size: Cohen's d or equivalent effect size
        alpha: Significance level (default 0.05)
        test_type: Type of test for context (default 't-test')
    """
    # Simplified power estimation using normal approximation
    # For a two-sample t-test: power ≈ Φ(d*√(n/2) - z_α/2)
    try:
        from scipy import stats as sp_stats
    except ImportError:
        logger.error("scipy not installed — cannot check power")
        return {"error": "scipy not available"}

    z_alpha = sp_stats.norm.ppf(1 - alpha / 2)

    # two sample t-test approximation
    noncentrality = effect_size * math.sqrt(sample_size / 2)
    estimated_power = 1 - sp_stats.norm.cdf(z_alpha - noncentrality)

    adequate = estimated_power >= 0.80

    result = {
        "sample_size": sample_size,
        "effect_size": effect_size,
        "alpha": alpha,
        "estimated_power": round(estimated_power, 4),
        "power_adequate": adequate,
        "flag": "UNDERPOWERED STUDY" if not adequate else None,
    }
    logger.info(f"Power check: n={sample_size}, d={effect_size} → power={estimated_power:.4f} ({'adequate' if adequate else 'UNDERPOWERED'})")
    return result


@tool
def detect_p_hacking_pattern(p_values: list[float]) -> dict:
    """Scan a list of p-values for suspicious clustering just below 0.05.
    Uses a simple heuristic: if > 50% of p-values fall in [0.01, 0.05], flag it.

    Args:
        p_values: List of numeric p-values extracted from the paper
    """
    if not p_values:
        return {"error": "No p-values provided", "suspicious": False}

    total = len(p_values)
    suspicious_range = [p for p in p_values if 0.01 <= p <= 0.05]
    barely_significant = [p for p in p_values if 0.04 <= p <= 0.05]

    ratio = len(suspicious_range) / total if total > 0 else 0
    barely_ratio = len(barely_significant) / total if total > 0 else 0

    suspicious = ratio > 0.5 or barely_ratio > 0.3

    result = {
        "total_p_values": total,
        "in_suspicious_range_0.01_0.05": len(suspicious_range),
        "barely_significant_0.04_0.05": len(barely_significant),
        "suspicious_ratio": round(ratio, 3),
        "barely_significant_ratio": round(barely_ratio, 3),
        "suspicious": suspicious,
        "flag": "POSSIBLE P-HACKING PATTERN" if suspicious else None,
    }
    logger.info(f"p-hacking check: {len(suspicious_range)}/{total} in [0.01,0.05] → {'SUSPICIOUS' if suspicious else 'OK'}")
    return result
