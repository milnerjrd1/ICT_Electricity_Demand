"""Load profile model — power states to annual kWh per device.

Converts a device's power-state profile (off / ready / active_medium /
active_high) and daily usage hours into annual electricity consumption
per unit, aligned with the Fraunhofer Green ICT @ FMD study approach.

The study uses four power states:
  off           — device fully powered down
  ready         — standby / idle (always-on background draw)
  active_medium — typical active use (e.g. browsing, office work)
  active_high   — intensive use (e.g. gaming, video rendering)

Legacy mapping from the old three-state model:
  idle  → ready
  sleep → off  (sleep draw is small; merged into off for simplicity)
  active → active_medium (active_high defaults to 0 hours if not provided)

Formula:
    annual_kwh_per_unit =
        (hours_off × power_off_w
       + hours_ready × power_ready_w
       + hours_active_medium × power_active_medium_w
       + hours_active_high × power_active_high_w) / 1000
"""

from __future__ import annotations

import logging
from typing import TypedDict

import pandas as pd

logger = logging.getLogger(__name__)

HOURS_PER_YEAR = 8760.0


class PowerStateProfile(TypedDict):
    """Power draw (W) and annual hours for each power state."""

    power_off_w: float
    power_ready_w: float
    power_active_medium_w: float
    power_active_high_w: float
    hours_off: float
    hours_ready: float
    hours_active_medium: float
    hours_active_high: float


def annual_kwh_per_unit(profile: PowerStateProfile) -> float:
    """Compute annual kWh consumption per device unit from a power-state profile.

    Args:
        profile: PowerStateProfile with power (W) and hours for each state.
            Hours across all states need not sum to 8760; the model uses
            absolute hours per state (not fractions).

    Returns:
        Annual kWh per device unit.
    """
    kwh = (
        profile["hours_off"] * profile["power_off_w"]
        + profile["hours_ready"] * profile["power_ready_w"]
        + profile["hours_active_medium"] * profile["power_active_medium_w"]
        + profile["hours_active_high"] * profile["power_active_high_w"]
    ) / 1000.0
    return max(0.0, kwh)


def profile_from_legacy(
    power_active_w: float,
    power_idle_w: float,
    power_sleep_w: float,
    power_off_w: float,
    hours_active: float,
    hours_idle: float,
    hours_sleep: float,
    hours_off: float,
) -> PowerStateProfile:
    """Build a PowerStateProfile from legacy four-state parameters.

    Legacy mapping:
      active → active_medium (active_high = 0 hours)
      idle   → ready
      sleep  → off (merged; sleep draw added to off draw weighted by hours)
      off    → off

    Args:
        power_active_w: Active power draw in watts.
        power_idle_w: Idle power draw in watts.
        power_sleep_w: Sleep power draw in watts.
        power_off_w: Off power draw in watts.
        hours_active: Annual hours in active state.
        hours_idle: Annual hours in idle state.
        hours_sleep: Annual hours in sleep state.
        hours_off: Annual hours in off state.

    Returns:
        PowerStateProfile compatible with annual_kwh_per_unit().
    """
    # Merge sleep into off: compute effective off power weighted by hours
    total_off_hours = hours_sleep + hours_off
    if total_off_hours > 0:
        effective_off_w = (
            hours_sleep * power_sleep_w + hours_off * power_off_w
        ) / total_off_hours
    else:
        effective_off_w = power_off_w

    return PowerStateProfile(
        power_off_w=effective_off_w,
        power_ready_w=power_idle_w,
        power_active_medium_w=power_active_w,
        power_active_high_w=power_active_w,  # no high-intensity split in legacy data
        hours_off=total_off_hours,
        hours_ready=hours_idle,
        hours_active_medium=hours_active,
        hours_active_high=0.0,
    )


def apply_load_profile(
    stock_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute annual kWh per unit and total kWh for each row in a stock DataFrame.

    Supports both new-style (power_ready_w, hours_ready, ...) and legacy-style
    (power_idle_w, hours_idle, ...) column names. Legacy columns are mapped
    automatically via profile_from_legacy().

    Args:
        stock_df: DataFrame with 'active_stock' column and power-state columns.
            New-style columns: power_off_w, power_ready_w, power_active_medium_w,
                power_active_high_w, hours_off, hours_ready, hours_active_medium,
                hours_active_high.
            Legacy columns: power_active_w, power_idle_w, power_sleep_w,
                power_off_w, hours_active, hours_idle, hours_sleep, hours_off.

    Returns:
        DataFrame with additional columns: kwh_per_unit, annual_kwh.
    """
    out = stock_df.copy()
    kwh_per_unit_list: list[float] = []

    new_style = "power_ready_w" in out.columns

    for _, row in out.iterrows():
        if new_style:
            profile = PowerStateProfile(
                power_off_w=float(row.get("power_off_w", 0.0)),
                power_ready_w=float(row.get("power_ready_w", 0.0)),
                power_active_medium_w=float(row.get("power_active_medium_w", 0.0)),
                power_active_high_w=float(row.get("power_active_high_w", 0.0)),
                hours_off=float(row.get("hours_off", 0.0)),
                hours_ready=float(row.get("hours_ready", 0.0)),
                hours_active_medium=float(row.get("hours_active_medium", 0.0)),
                hours_active_high=float(row.get("hours_active_high", 0.0)),
            )
        else:
            profile = profile_from_legacy(
                power_active_w=float(row.get("power_active_w", 0.0)),
                power_idle_w=float(row.get("power_idle_w", 0.0)),
                power_sleep_w=float(row.get("power_sleep_w", 0.0)),
                power_off_w=float(row.get("power_off_w", 0.0)),
                hours_active=float(row.get("hours_active", 0.0)),
                hours_idle=float(row.get("hours_idle", 0.0)),
                hours_sleep=float(row.get("hours_sleep", 0.0)),
                hours_off=float(row.get("hours_off", 0.0)),
            )
        kwh_per_unit_list.append(annual_kwh_per_unit(profile))

    out["kwh_per_unit"] = kwh_per_unit_list
    out["annual_kwh"] = out["active_stock"] * out["kwh_per_unit"]

    logger.info("Load profile applied: %d rows", len(out))
    return out
