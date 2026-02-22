"""Taxonomy dimensions for the ICT electricity demand model.

Implements the five application-area / product-group / unit-type taxonomy
aligned with the Fraunhofer Green ICT @ FMD study (June 2025).

Dimension tables:
  APPLICATION_AREAS  — the five modelled domains
  PRODUCT_GROUPS     — product groups under each area (representative v1 subset)
  UNIT_TYPES         — inventory unit type per product group

Mapping layer:
  LEGACY_SEGMENT_MAP — maps old (segment, product) keys to new dims so
                       existing API outputs and tests remain valid.
"""

from __future__ import annotations

from typing import NamedTuple


# ── Dimension constants ───────────────────────────────────────────────────────

APPLICATION_AREAS: tuple[str, ...] = (
    "households",
    "workplace",
    "public_spaces",
    "datacentres",
    "telecom_networks",
)

UNIT_TYPES: tuple[str, ...] = (
    "device_unit",
    "cpu_unit",
    "storage_unit",
    "port_unit",
    "lan_port_unit",
)

# Telecom network layers (sub-dimension of telecom_networks)
TELECOM_LAYERS: tuple[str, ...] = (
    "mobile_access",
    "fixed_access",
    "aggregation",
    "core_transport",
)


# ── Product group registry ────────────────────────────────────────────────────

class ProductGroupDef(NamedTuple):
    """Definition of a single product group."""

    product_group: str
    application_area: str
    unit_type: str
    description: str
    placeholder: bool = False  # True = defined but not yet parameterised


PRODUCT_GROUP_REGISTRY: tuple[ProductGroupDef, ...] = (
    # ── Households ────────────────────────────────────────────────────────────
    ProductGroupDef("tv_large",      "households", "device_unit", "TV ≥55 inch"),
    ProductGroupDef("tv_medium",     "households", "device_unit", "TV 40–54 inch"),
    ProductGroupDef("tv_small",      "households", "device_unit", "TV <40 inch"),
    ProductGroupDef("laptop_hh",     "households", "device_unit", "Laptop (household)"),
    ProductGroupDef("desktop_hh",    "households", "device_unit", "Desktop PC (household)"),
    ProductGroupDef("smartphone_hh", "households", "device_unit", "Smartphone (household)"),
    ProductGroupDef("tablet_hh",     "households", "device_unit", "Tablet (household)"),
    ProductGroupDef("printer_hh",    "households", "device_unit", "Printer (household)"),
    ProductGroupDef("monitor_hh",    "households", "device_unit", "Monitor (household)"),
    ProductGroupDef("home_router",   "households", "device_unit", "Home router / CPE"),
    ProductGroupDef("audio_device",  "households", "device_unit", "Smart speaker / audio device", placeholder=True),
    ProductGroupDef("wearable",      "households", "device_unit", "Wearable device", placeholder=True),

    # ── Workplace ─────────────────────────────────────────────────────────────
    ProductGroupDef("pc_notebook_wp",  "workplace", "device_unit",   "PC / notebook (workplace)"),
    ProductGroupDef("printer_mfd_wp",  "workplace", "device_unit",   "Printer / MFD (workplace)"),
    ProductGroupDef("monitor_wp",      "workplace", "device_unit",   "Monitor (workplace)"),
    ProductGroupDef("telephone_wp",    "workplace", "device_unit",   "Telephone / VoIP device (workplace)"),
    ProductGroupDef("lan_port_wp",     "workplace", "lan_port_unit", "LAN port (workplace network technology)"),

    # ── Public spaces ─────────────────────────────────────────────────────────
    ProductGroupDef("pos_terminal",      "public_spaces", "device_unit", "Point-of-sale terminal"),
    ProductGroupDef("atm_ticket_machine","public_spaces", "device_unit", "ATM / ticket machine"),
    ProductGroupDef("digital_signage",   "public_spaces", "device_unit", "Digital advertising / display"),
    ProductGroupDef("wifi_hotspot",      "public_spaces", "device_unit", "Public Wi-Fi hotspot"),
    ProductGroupDef("toll_system",       "public_spaces", "device_unit", "Toll system unit", placeholder=True),

    # ── Data centres ──────────────────────────────────────────────────────────
    ProductGroupDef("cpu_unit",     "datacentres", "cpu_unit",     "Server CPU unit (compute proxy)"),
    ProductGroupDef("hdd_unit",     "datacentres", "storage_unit", "HDD storage unit"),
    ProductGroupDef("ssd_unit",     "datacentres", "storage_unit", "SSD storage unit"),
    ProductGroupDef("dc_port_unit", "datacentres", "port_unit",    "DC network port unit"),

    # ── Telecom networks ──────────────────────────────────────────────────────
    ProductGroupDef("mobile_access_port",    "telecom_networks", "port_unit", "Mobile access port unit (RAN)"),
    ProductGroupDef("fixed_access_port",     "telecom_networks", "port_unit", "Fixed-line access port unit (DSL/FTTH)"),
    ProductGroupDef("aggregation_port",      "telecom_networks", "port_unit", "Aggregation network port unit"),
    ProductGroupDef("core_transport_port",   "telecom_networks", "port_unit", "Core / transport network port unit"),
)

# Fast lookup: product_group → ProductGroupDef
PRODUCT_GROUP_MAP: dict[str, ProductGroupDef] = {
    pg.product_group: pg for pg in PRODUCT_GROUP_REGISTRY
}

# Fast lookup: application_area → list[product_group]
AREA_PRODUCT_GROUPS: dict[str, list[str]] = {}
for _pg in PRODUCT_GROUP_REGISTRY:
    AREA_PRODUCT_GROUPS.setdefault(_pg.application_area, []).append(_pg.product_group)


# ── Legacy segment mapping ────────────────────────────────────────────────────
# Maps (old_segment, old_product) → (application_area, product_group)
# Allows existing gold tables and API outputs to be translated without
# breaking changes. Unmapped combinations fall through to segment-level defaults.

class LegacyMapping(NamedTuple):
    """Mapping from legacy (segment, product) to new taxonomy dims."""

    application_area: str
    product_group: str
    unit_type: str


LEGACY_SEGMENT_MAP: dict[tuple[str, str], LegacyMapping] = {
    # devices → households (default mapping; workplace variants need explicit tagging)
    ("devices", "laptop"):      LegacyMapping("households",   "laptop_hh",     "device_unit"),
    ("devices", "desktop"):     LegacyMapping("households",   "desktop_hh",    "device_unit"),
    ("devices", "smartphone"):  LegacyMapping("households",   "smartphone_hh", "device_unit"),
    ("devices", "tablet"):      LegacyMapping("households",   "tablet_hh",     "device_unit"),
    ("devices", "monitor"):     LegacyMapping("households",   "monitor_hh",    "device_unit"),
    # workplace device variants
    ("devices", "pc_notebook_wp"): LegacyMapping("workplace", "pc_notebook_wp", "device_unit"),
    ("devices", "printer_mfd_wp"): LegacyMapping("workplace", "printer_mfd_wp", "device_unit"),
    ("devices", "monitor_wp"):     LegacyMapping("workplace", "monitor_wp",     "device_unit"),
    ("devices", "telephone_wp"):   LegacyMapping("workplace", "telephone_wp",   "device_unit"),
    ("devices", "lan_port_wp"):    LegacyMapping("workplace", "lan_port_wp",    "lan_port_unit"),

    # networks → telecom_networks
    ("networks", "5g_base_station"):      LegacyMapping("telecom_networks", "mobile_access_port",  "port_unit"),
    ("networks", "4g_base_station"):      LegacyMapping("telecom_networks", "mobile_access_port",  "port_unit"),
    ("networks", "fixed_broadband_cpe"):  LegacyMapping("telecom_networks", "fixed_access_port",   "port_unit"),
    ("networks", "core_network"):         LegacyMapping("telecom_networks", "core_transport_port", "port_unit"),

    # datacentres → datacentres
    ("datacentres", "hyperscale"):   LegacyMapping("datacentres", "cpu_unit",     "cpu_unit"),
    ("datacentres", "sovereign"):    LegacyMapping("datacentres", "cpu_unit",     "cpu_unit"),
    ("datacentres", "colocation"):   LegacyMapping("datacentres", "cpu_unit",     "cpu_unit"),
    ("datacentres", "on_premises"):  LegacyMapping("datacentres", "cpu_unit",     "cpu_unit"),
    ("datacentres", "edge"):         LegacyMapping("datacentres", "cpu_unit",     "cpu_unit"),
    # new-style DC product groups
    ("datacentres", "cpu_unit"):     LegacyMapping("datacentres", "cpu_unit",     "cpu_unit"),
    ("datacentres", "hdd_unit"):     LegacyMapping("datacentres", "hdd_unit",     "storage_unit"),
    ("datacentres", "ssd_unit"):     LegacyMapping("datacentres", "ssd_unit",     "storage_unit"),
    ("datacentres", "dc_port_unit"): LegacyMapping("datacentres", "dc_port_unit", "port_unit"),
}

# Segment-level fallback when no product-level mapping exists
LEGACY_SEGMENT_FALLBACK: dict[str, str] = {
    "devices":     "households",
    "networks":    "telecom_networks",
    "datacentres": "datacentres",
}


def resolve_application_area(segment: str, product: str) -> str:
    """Resolve application_area from legacy (segment, product) pair.

    Args:
        segment: Legacy segment value (e.g. 'devices', 'networks', 'datacentres').
        product: Legacy product value (e.g. 'laptop', '5g_base_station').

    Returns:
        application_area string.
    """
    mapping = LEGACY_SEGMENT_MAP.get((segment, product))
    if mapping:
        return mapping.application_area
    return LEGACY_SEGMENT_FALLBACK.get(segment, "households")


def resolve_product_group(segment: str, product: str) -> str:
    """Resolve product_group from legacy (segment, product) pair.

    Args:
        segment: Legacy segment value.
        product: Legacy product value.

    Returns:
        product_group string. Falls back to the product value itself if unmapped.
    """
    mapping = LEGACY_SEGMENT_MAP.get((segment, product))
    if mapping:
        return mapping.product_group
    return product


def resolve_unit_type(segment: str, product: str) -> str:
    """Resolve unit_type from legacy (segment, product) pair.

    Args:
        segment: Legacy segment value.
        product: Legacy product value.

    Returns:
        unit_type string.
    """
    mapping = LEGACY_SEGMENT_MAP.get((segment, product))
    if mapping:
        return mapping.unit_type
    # Default by segment
    defaults = {"devices": "device_unit", "networks": "port_unit", "datacentres": "cpu_unit"}
    return defaults.get(segment, "device_unit")


def enrich_with_taxonomy(df: "import pandas; pandas.DataFrame") -> "import pandas; pandas.DataFrame":  # type: ignore[name-defined]
    """Add application_area, product_group, unit_type columns to a legacy output DataFrame.

    Non-destructive: adds columns only if not already present. Existing values
    are preserved so new-style outputs (which already carry these dims) pass through.

    Args:
        df: DataFrame with at minimum 'segment' and 'product' columns.

    Returns:
        DataFrame with application_area, product_group, unit_type columns added.
    """
    import pandas as pd  # noqa: PLC0415

    out = df.copy()
    if out.empty:
        for col in ("application_area", "product_group", "unit_type"):
            if col not in out.columns:
                out[col] = []
        return out
    if "application_area" not in out.columns:
        out["application_area"] = [
            resolve_application_area(str(seg), str(prod))
            for seg, prod in zip(out["segment"], out["product"])
        ]
    if "product_group" not in out.columns:
        out["product_group"] = [
            resolve_product_group(str(seg), str(prod))
            for seg, prod in zip(out["segment"], out["product"])
        ]
    if "unit_type" not in out.columns:
        out["unit_type"] = [
            resolve_unit_type(str(seg), str(prod))
            for seg, prod in zip(out["segment"], out["product"])
        ]
    return out


def validate_application_area(area: str) -> None:
    """Raise ValueError if area is not a valid application_area.

    Args:
        area: application_area string to validate.

    Raises:
        ValueError: If area is not in APPLICATION_AREAS.
    """
    if area not in APPLICATION_AREAS:
        raise ValueError(
            f"Invalid application_area '{area}'. Must be one of: {APPLICATION_AREAS}"
        )


def validate_product_group(product_group: str) -> None:
    """Raise ValueError if product_group is not registered.

    Args:
        product_group: product_group string to validate.

    Raises:
        ValueError: If product_group is not in PRODUCT_GROUP_MAP.
    """
    if product_group not in PRODUCT_GROUP_MAP:
        raise ValueError(
            f"Unknown product_group '{product_group}'. "
            f"Register it in src/models/taxonomy.py::PRODUCT_GROUP_REGISTRY."
        )
