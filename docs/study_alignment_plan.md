# Study Alignment Plan — Fraunhofer "Green ICT @ FMD" (June 2025)

**Date:** 2026-02-22  
**Branch:** `chore/debloat-and-docs`  
**Status:** In progress

---

## 1. Current State

### Taxonomy (3 flat segments)
```
segment ∈ {devices, networks, datacentres}
product ∈ {laptop, desktop, smartphone, tablet, monitor,
           5g_base_station, 4g_base_station, fixed_broadband_cpe, core_network,
           hyperscale, sovereign, colocation, on_premises, edge}
```
No `application_area` dimension. No `unit_type` dimension. No five-year parameter sets.

### Modules
| Module | Current approach | Gap vs study |
|---|---|---|
| `devices.py` | Stock-flow (shipments − retirements via single avg lifespan). 4 power states. | Missing lifespan distribution. Missing `application_area`. Missing `active_medium`/`active_high` split. |
| `networks.py` | Equipment count × power × utilisation. No layer split. | Missing layer model (mobile access / fixed access / aggregation / core). Missing port-unit channel model. Missing PUE for telecom sites. |
| `datacentres.py` | Capacity MW × utilisation × PUE. | Missing CPU-unit / storage-unit / port-unit architecture. Missing plausibility cross-checks (rack power, CPU count). |
| `carbon.py` | Single grid EF per geo/year. | Missing grid scenario switching from 2025 onward (3 scenarios). |
| `scenarios/engine.py` | Runs 3 modules, concatenates. | Missing `application_area` routing. Missing reference-year parameter dispatch. |

### Scenario framework
7 named scenarios (ai_base, ai_high, ai_low, ai_stress, sovereignty_push, grid_constrained, efficiency_breakthrough). No grid mix scenarios. No five-year parameter sets.

### Outputs
Raw `OutputSchema` rows. No appendix-style tables. No 2015/2025/2035 reference-year aggregation. No per-product-group summary.

---

## 2. Target State (Study-Aligned)

### Taxonomy (5 application areas, N product groups)
```
application_area ∈ {households, workplace, public_spaces, datacentres, telecom_networks}

product_group (representative subset v1):
  households:      tv_large, tv_medium, tv_small, laptop_hh, desktop_hh, smartphone_hh,
                   tablet_hh, printer_hh, monitor_hh, home_router, audio_device, wearable
  workplace:       pc_notebook_wp, printer_mfd_wp, monitor_wp, telephone_wp, lan_port_wp
  public_spaces:   pos_terminal, atm_ticket_machine, digital_signage, wifi_hotspot, toll_system
  datacentres:     cpu_unit, hdd_unit, ssd_unit, dc_port_unit
  telecom_networks: mobile_access_port, fixed_access_port, aggregation_port, core_transport_port

unit_type ∈ {device_unit, cpu_unit, storage_unit, port_unit, lan_port_unit}
```

### Module target architecture
```
src/models/
  taxonomy.py          NEW — dim tables, mapping layer, LEGACY_SEGMENT_MAP
  inventory.py         NEW — lifespan-distribution stock-flow (replaces device loop in devices.py)
  load_profile.py      NEW — power-state → annual kWh (off/ready/active_med/active_high)
  devices.py           REFACTOR — use inventory.py + load_profile.py; add application_area
  networks.py          REFACTOR — add layer model + port-unit channel model + telecom PUE
  datacentres.py       REFACTOR — add CPU/storage/port unit architecture + plausibility checks
  carbon.py            EXTEND — add grid_scenario_id dispatch (3 scenarios from 2025)
  reference_params.py  NEW — five-year parameter set loader + year→set resolver
  reporting.py         NEW — appendix tables generator (2015/2025/2035)
```

### Scenario framework additions
```
configs/scenarios/
  grid_mix_reference.yaml    NEW — historical EF + 3 grid scenarios from 2025
  grid_mix_ambitious.yaml    NEW
  grid_mix_fossil.yaml       NEW
configs/assumptions/
  reference_params/          NEW directory
    params_2007.yaml
    params_2012.yaml
    params_2017.yaml
    params_2022.yaml
    params_2027.yaml  (projected)
    params_2032.yaml  (projected)
```

---

## 3. Key Refactors — Current → Target Mapping

### 3a. Taxonomy mapping (non-breaking)
Old `segment=devices, product=laptop` → new `application_area=households, product_group=laptop_hh, unit_type=device_unit`.  
A `LEGACY_SEGMENT_MAP` dict in `taxonomy.py` provides the reverse mapping so existing API outputs remain valid.

### 3b. Inventory model
Current: single `avg_lifespan_years` → integer retirement lookback.  
Target: lifespan distribution (triangular) → weighted retirement across multiple years.  
Implementation: `inventory.py::compute_stock_flow(shipments, lifespan_mean, lifespan_std)`.  
Backward compat: `devices.py` calls `compute_stock_flow` with `lifespan_std=0` by default (degrades to current behaviour).

### 3c. Load profile
Current: 4 states (active/idle/sleep/off) × fixed hours.  
Target: 4 states (off/ready/active_medium/active_high) × daily hours → annual kWh.  
Implementation: `load_profile.py::annual_kwh_per_unit(power_states_w, daily_hours)`.  
Backward compat: `idle` maps to `ready`, `sleep` maps to `off` in `POWER_STATE_MAP`.

### 3d. Data centres
Current: `installed_capacity_mw × utilisation × PUE`.  
Target: `cpu_units × power_per_cpu_w × utilisation + storage_units × power_per_unit_w + port_units × power_per_port_w`, then `× PUE`.  
Plausibility: `check_rack_power(cpu_units, rack_count)` and `check_cpu_unit_count(cpu_units, server_count_proxy)`.

### 3e. Telecom networks
Current: `equipment_count × power × utilisation`.  
Target: `subscribers → port_units per layer (mobile_access / fixed_access / aggregation / core)` via channel model coefficients. Each layer has `power_per_port_w` and `site_pue`.

### 3f. Grid scenarios
Current: single EF trajectory per geo.  
Target: `grid_scenario_id ∈ {reference, ambitious, fossil}`. Historical (≤2024) is fixed. From 2025, scenario selects EF trajectory. `carbon.py::apply_carbon_overlay` gains `grid_scenario_id` param.

### 3g. Reference-year parameters
Current: flat YAML per product.  
Target: `configs/assumptions/reference_params/params_{year}.yaml` sets. `reference_params.py::get_params(product_group, year)` resolves to most recent reference year ≤ year.

### 3h. Reporting
New `reporting.py::build_appendix_table(results_df, reference_years=[2015, 2025, 2035])` returns a wide-format DataFrame with inventory, kWh, emissions columns per reference year per product group.

---

## 4. What Is NOT Changed
- `OutputSchema` column names/types (locked — migration required for any change)
- `run_id` / `source_ids` / `confidence_tier` / `uncertainty_band` on every row
- `gold_writer.py` interface
- Existing 7 scenario YAMLs (extended, not replaced)
- `backend/` FastAPI routes (consume new dims transparently)
- `tests/conftest.py` fixtures (extended with new fixtures)

---

## 5. Execution Order
1. `src/models/taxonomy.py` — dims + mapping layer  
2. `src/models/inventory.py` — lifespan-distribution stock-flow  
3. `src/models/load_profile.py` — power-state → annual kWh  
4. `src/models/reference_params.py` — five-year parameter resolver  
5. Refactor `src/models/datacentres.py` — CPU/storage/port units + plausibility  
6. Refactor `src/models/networks.py` — layer model + port-unit channel model  
7. Refactor `src/models/devices.py` — use inventory + load_profile + application_area  
8. Extend `src/models/carbon.py` — grid scenario dispatch  
9. `src/models/reporting.py` — appendix tables  
10. `configs/assumptions/reference_params/` — six YAML parameter sets  
11. `configs/scenarios/grid_mix_*.yaml` — 3 grid scenarios  
12. Tests for all new modules  
13. Frontend: application area filter + appendix export page  
