"""Unit tests for src/models/taxonomy.py."""

import pytest
import pandas as pd

from src.models.taxonomy import (
    APPLICATION_AREAS,
    PRODUCT_GROUP_MAP,
    PRODUCT_GROUP_REGISTRY,
    UNIT_TYPES,
    TELECOM_LAYERS,
    LEGACY_SEGMENT_MAP,
    AREA_PRODUCT_GROUPS,
    resolve_application_area,
    resolve_product_group,
    resolve_unit_type,
    enrich_with_taxonomy,
    validate_application_area,
    validate_product_group,
)


def test_application_areas_complete():
    assert set(APPLICATION_AREAS) == {
        "households", "workplace", "public_spaces", "datacentres", "telecom_networks"
    }


def test_all_product_groups_have_valid_area():
    for pg in PRODUCT_GROUP_REGISTRY:
        assert pg.application_area in APPLICATION_AREAS, (
            f"{pg.product_group} has invalid application_area '{pg.application_area}'"
        )


def test_all_product_groups_have_valid_unit_type():
    for pg in PRODUCT_GROUP_REGISTRY:
        assert pg.unit_type in UNIT_TYPES, (
            f"{pg.product_group} has invalid unit_type '{pg.unit_type}'"
        )


def test_product_group_map_keys_match_registry():
    registry_keys = {pg.product_group for pg in PRODUCT_GROUP_REGISTRY}
    assert set(PRODUCT_GROUP_MAP.keys()) == registry_keys


def test_area_product_groups_covers_all_areas():
    for area in APPLICATION_AREAS:
        assert area in AREA_PRODUCT_GROUPS, f"No product groups for area '{area}'"
        assert len(AREA_PRODUCT_GROUPS[area]) > 0


def test_area_product_groups_no_duplicates():
    for area, pgs in AREA_PRODUCT_GROUPS.items():
        assert len(pgs) == len(set(pgs)), f"Duplicate product groups in area '{area}'"


def test_telecom_layers_complete():
    assert set(TELECOM_LAYERS) == {
        "mobile_access", "fixed_access", "aggregation", "core_transport"
    }


# ── Legacy mapping tests ──────────────────────────────────────────────────────

def test_resolve_application_area_devices_laptop():
    assert resolve_application_area("devices", "laptop") == "households"


def test_resolve_application_area_devices_pc_notebook_wp():
    assert resolve_application_area("devices", "pc_notebook_wp") == "workplace"


def test_resolve_application_area_networks_5g():
    assert resolve_application_area("networks", "5g_base_station") == "telecom_networks"


def test_resolve_application_area_networks_core():
    assert resolve_application_area("networks", "core_network") == "telecom_networks"


def test_resolve_application_area_datacentres_hyperscale():
    assert resolve_application_area("datacentres", "hyperscale") == "datacentres"


def test_resolve_application_area_unknown_falls_back():
    # Unknown product falls back to segment-level default
    assert resolve_application_area("devices", "unknown_gadget") == "households"
    assert resolve_application_area("networks", "unknown_net") == "telecom_networks"


def test_resolve_product_group_known():
    assert resolve_product_group("devices", "laptop") == "laptop_hh"
    assert resolve_product_group("networks", "5g_base_station") == "mobile_access_port"
    assert resolve_product_group("datacentres", "cpu_unit") == "cpu_unit"


def test_resolve_product_group_unknown_returns_product():
    assert resolve_product_group("devices", "mystery_device") == "mystery_device"


def test_resolve_unit_type_device():
    assert resolve_unit_type("devices", "laptop") == "device_unit"


def test_resolve_unit_type_port():
    assert resolve_unit_type("networks", "5g_base_station") == "port_unit"


def test_resolve_unit_type_cpu():
    assert resolve_unit_type("datacentres", "cpu_unit") == "cpu_unit"


def test_resolve_unit_type_lan_port():
    assert resolve_unit_type("devices", "lan_port_wp") == "lan_port_unit"


# ── enrich_with_taxonomy tests ────────────────────────────────────────────────

def test_enrich_with_taxonomy_adds_columns():
    df = pd.DataFrame([
        {"geo": "DE", "segment": "devices", "product": "laptop", "year": 2022, "kwh_estimate": 1e6},
        {"geo": "DE", "segment": "networks", "product": "5g_base_station", "year": 2022, "kwh_estimate": 2e6},
        {"geo": "DE", "segment": "datacentres", "product": "hyperscale", "year": 2022, "kwh_estimate": 3e6},
    ])
    enriched = enrich_with_taxonomy(df)
    assert "application_area" in enriched.columns
    assert "product_group" in enriched.columns
    assert "unit_type" in enriched.columns


def test_enrich_with_taxonomy_correct_values():
    df = pd.DataFrame([
        {"geo": "DE", "segment": "devices", "product": "laptop", "year": 2022, "kwh_estimate": 1e6},
    ])
    enriched = enrich_with_taxonomy(df)
    assert enriched.iloc[0]["application_area"] == "households"
    assert enriched.iloc[0]["product_group"] == "laptop_hh"
    assert enriched.iloc[0]["unit_type"] == "device_unit"


def test_enrich_with_taxonomy_preserves_existing_columns():
    df = pd.DataFrame([
        {
            "geo": "DE", "segment": "devices", "product": "laptop", "year": 2022,
            "kwh_estimate": 1e6,
            "application_area": "workplace",  # pre-set — should be preserved
        },
    ])
    enriched = enrich_with_taxonomy(df)
    assert enriched.iloc[0]["application_area"] == "workplace"


def test_enrich_with_taxonomy_idempotent():
    df = pd.DataFrame([
        {"geo": "DE", "segment": "devices", "product": "laptop", "year": 2022, "kwh_estimate": 1e6},
    ])
    once = enrich_with_taxonomy(df)
    twice = enrich_with_taxonomy(once)
    assert list(once["application_area"]) == list(twice["application_area"])


# ── Validation tests ──────────────────────────────────────────────────────────

def test_validate_application_area_valid():
    for area in APPLICATION_AREAS:
        validate_application_area(area)  # should not raise


def test_validate_application_area_invalid():
    with pytest.raises(ValueError, match="Invalid application_area"):
        validate_application_area("invalid_area")


def test_validate_product_group_valid():
    validate_product_group("laptop_hh")
    validate_product_group("cpu_unit")
    validate_product_group("mobile_access_port")


def test_validate_product_group_invalid():
    with pytest.raises(ValueError, match="Unknown product_group"):
        validate_product_group("nonexistent_product")


def test_legacy_segment_map_all_areas_valid():
    for (seg, prod), mapping in LEGACY_SEGMENT_MAP.items():
        assert mapping.application_area in APPLICATION_AREAS, (
            f"({seg}, {prod}) maps to invalid area '{mapping.application_area}'"
        )
        assert mapping.unit_type in UNIT_TYPES, (
            f"({seg}, {prod}) maps to invalid unit_type '{mapping.unit_type}'"
        )
