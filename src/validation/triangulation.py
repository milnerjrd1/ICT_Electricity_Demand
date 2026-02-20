"""Triangulation and cross-check validation utilities.

Compares model outputs against published benchmarks and alternative calculation methods.
Germany is the primary calibration anchor.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

GERMANY_CALIBRATION_TOLERANCE = 0.15
TIER1_CROSSCHECK_TOLERANCE = 0.20


def check_germany_calibration(
    model_df: pd.DataFrame,
    benchmark_twh: float,
    year: int,
) -> dict[str, float | bool | str]:
    """Check Germany total ICT electricity against published benchmark.

    Args:
        model_df: Output DataFrame with columns: geo, year, kwh_estimate.
        benchmark_twh: Published Germany ICT electricity estimate in TWh.
        year: Year to check.

    Returns:
        Dict with keys: model_twh, benchmark_twh, deviation, passed, message.
    """
    germany_rows = model_df[(model_df["geo"] == "DE") & (model_df["year"] == year)]

    if germany_rows.empty:
        return {
            "model_twh": 0.0,
            "benchmark_twh": benchmark_twh,
            "deviation": 1.0,
            "passed": False,
            "message": f"No Germany (DE) data found for year {year}",
        }

    model_kwh = germany_rows["kwh_estimate"].sum()
    model_twh = model_kwh / 1e9

    deviation = abs(model_twh - benchmark_twh) / benchmark_twh if benchmark_twh > 0 else 1.0
    passed = deviation <= GERMANY_CALIBRATION_TOLERANCE

    message = (
        f"Germany {year}: model={model_twh:.1f} TWh, benchmark={benchmark_twh:.1f} TWh, "
        f"deviation={deviation:.1%} — {'PASS' if passed else 'FAIL'}"
    )

    if passed:
        logger.info(message)
    else:
        logger.error(message)

    return {
        "model_twh": model_twh,
        "benchmark_twh": benchmark_twh,
        "deviation": deviation,
        "passed": passed,
        "message": message,
    }


def check_crosscheck_agreement(
    primary_kwh: float,
    alternative_kwh: float,
    geo: str,
    year: int,
    tolerance: float = TIER1_CROSSCHECK_TOLERANCE,
) -> dict[str, float | bool | str]:
    """Check agreement between primary and alternative calculation methods.

    Args:
        primary_kwh: Primary model kWh estimate.
        alternative_kwh: Alternative method kWh estimate.
        geo: Geography identifier for logging.
        year: Year for logging.
        tolerance: Maximum fractional deviation (default 0.20 = ±20%).

    Returns:
        Dict with keys: primary_kwh, alternative_kwh, deviation, passed, message.
    """
    deviation = abs(primary_kwh - alternative_kwh) / alternative_kwh if alternative_kwh > 0 else 1.0
    passed = deviation <= tolerance

    message = (
        f"Cross-check {geo} {year}: primary={primary_kwh/1e9:.2f} TWh, "
        f"alternative={alternative_kwh/1e9:.2f} TWh, deviation={deviation:.1%} — "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if passed:
        logger.info(message)
    else:
        logger.error(message)

    return {
        "primary_kwh": primary_kwh,
        "alternative_kwh": alternative_kwh,
        "deviation": deviation,
        "passed": passed,
        "message": message,
    }


def build_validation_report(
    calibration_results: list[dict],
    crosscheck_results: list[dict],
) -> pd.DataFrame:
    """Compile all validation results into a summary DataFrame.

    Args:
        calibration_results: List of dicts from check_germany_calibration.
        crosscheck_results: List of dicts from check_crosscheck_agreement.

    Returns:
        DataFrame with columns: check_type, passed, message, deviation.
    """
    rows = []
    for r in calibration_results:
        rows.append({"check_type": "germany_calibration", **r})
    for r in crosscheck_results:
        rows.append({"check_type": "crosscheck", **r})

    df = pd.DataFrame(rows)
    n_pass = df["passed"].sum() if not df.empty else 0
    n_total = len(df)
    logger.info("Validation report: %d/%d checks passed", n_pass, n_total)
    return df
