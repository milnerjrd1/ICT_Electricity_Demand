import { useState, useCallback } from 'react';
import { PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/Card';

/* ═══════════════════════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════════════════════ */

type TierKey = 'sources' | 'loaders' | 'models' | 'overlays' | 'outputs' | 'phase0';
type NodeStatus = 'implemented' | 'stub' | 'config' | 'reference' | 'phase0';

interface FlowNodeDef {
  id: string;
  tier: TierKey;
  label: string;
  shortDesc: string;
  detailPlain: string;
  detailCode?: string;
  formula?: string;
  status: NodeStatus;
  confidenceTier?: 1 | 2 | 3;
}

interface FlowEdgeDef {
  from: string;
  to: string;
  label?: string;
  dashed?: boolean;
}

/* ═══════════════════════════════════════════════════════════════════════════
   THEME
   ═══════════════════════════════════════════════════════════════════════════ */

const TIER_META: Record<TierKey, { label: string; color: string; bg: string }> = {
  sources:  { label: 'External Data Sources', color: 'var(--chart-1)', bg: 'rgba(0,151,169,0.06)' },
  loaders:  { label: 'Data Loaders',          color: 'var(--chart-2)', bg: 'rgba(0,163,224,0.06)' },
  models:   { label: 'Model Functions',        color: 'var(--accent)',  bg: 'rgba(134,188,36,0.06)' },
  overlays: { label: 'Overlays & Aggregation', color: 'var(--chart-3)', bg: 'rgba(0,118,168,0.06)' },
  outputs:  { label: 'Outputs',                color: 'var(--chart-4)', bg: 'rgba(117,120,123,0.06)' },
  phase0:   { label: 'Phase 0 — Synthetic',    color: 'var(--accent-amber)', bg: 'rgba(237,139,0,0.06)' },
};

const STATUS_STYLE: Record<NodeStatus, { label: string; bg: string; color: string }> = {
  implemented: { label: 'Implemented', bg: 'var(--accent-soft)',      color: 'var(--accent-active)' },
  stub:        { label: 'Stub',        bg: 'rgba(237,139,0,0.12)',    color: '#B06C00' },
  config:      { label: 'Config',      bg: 'rgba(0,163,224,0.10)',    color: '#005587' },
  reference:   { label: 'Reference',   bg: 'rgba(117,120,123,0.10)',  color: '#53565A' },
  phase0:      { label: 'Phase 0',     bg: 'rgba(237,139,0,0.12)',    color: '#B06C00' },
};

/* ═══════════════════════════════════════════════════════════════════════════
   NODE & EDGE DATA
   ═══════════════════════════════════════════════════════════════════════════ */

const NODES: FlowNodeDef[] = [
  // ── Tier 1: Sources ───────────────────────────────────────────────────
  { id: 'src_eurostat', tier: 'sources', label: 'Eurostat NRG_BAL_C',
    shortDesc: 'EU energy balances — electricity by sector',
    detailPlain: 'Eurostat energy balance dataset provides electricity consumption by economic sector for all EU member states. We use the Information and Communication sector code (FC_IND_IS_E) as a cross-check for total ICT electricity in European geographies.',
    detailCode: 'loader_eurostat.py → load_germany_dc_anchor()\nDataset: NRG_BAL_C via Eurostat JSON API\nSIEC: FC_IND_IS_E',
    status: 'implemented', confidenceTier: 1 },
  { id: 'src_borderstep', tier: 'sources', label: 'Borderstep 2023',
    shortDesc: 'Germany DC benchmark (~18 TWh) — calibration anchor',
    detailPlain: 'Borderstep Institut publishes the most comprehensive public data on German DC electricity. Their 2023 report estimates ~18 TWh for 2022, split by hyperscale (~30%), colocation (~38%), on-premises (~32%). This is the primary calibration anchor — model must reproduce within ±15%.',
    detailCode: 'loader_eurostat.py → _DE_DC_ANCHOR\nBenchmark: 18.0 TWh (2022)\nModel output: 18.59 TWh (+3.3% ✓)',
    status: 'implemented', confidenceTier: 1 },
  { id: 'src_iea', tier: 'sources', label: 'IEA World Energy Stats',
    shortDesc: 'Grid emission factors, electricity prices',
    detailPlain: 'IEA provides global electricity statistics, grid emission factors (kgCO₂e/kWh), and electricity prices by country. Grid EFs drive the carbon overlay; prices drive the cost overlay.',
    detailCode: 'loader_iea.py → load_grid_emission_factors(), load_electricity_prices()',
    status: 'stub' },
  { id: 'src_itu', tier: 'sources', label: 'ITU ICT Indicators',
    shortDesc: 'Subscribers, base stations, broadband penetration',
    detailPlain: 'ITU provides subscriber counts (mobile, fixed broadband), base station counts, and penetration rates by country — primary inputs for the networks model.',
    detailCode: 'loader_itu.py → load_network_subscribers()\nColumns: geo, year, mobile_subscribers, fixed_broadband_subscribers, base_stations_4g/5g',
    status: 'stub' },
  { id: 'src_comtrade', tier: 'sources', label: 'UN Comtrade',
    shortDesc: 'Device shipments via HS codes',
    detailPlain: 'UN Comtrade trade data provides device shipment proxies using HS codes for computers (8471), phones (8517), printers (8443), monitors (8528). Import volumes serve as proxy for annual shipments feeding the stock-flow model.',
    detailCode: 'loader_trade.py → load_device_shipments()\nHS: 8471, 8517, 8443, 8528',
    status: 'stub' },
  { id: 'src_dcbyte', tier: 'sources', label: 'DC Byte / Uptime',
    shortDesc: 'DC capacity + PUE benchmarks by geography',
    detailPlain: 'DC Byte provides colocation and hyperscale capacity by geography. Uptime Institute Annual Survey provides PUE benchmarks by DC type. Together they give installed capacity (MW) and efficiency (PUE) per geography and DC type.',
    detailCode: 'loader_dc_byte.py → load_dc_capacity(), load_pue_benchmarks()',
    status: 'stub' },
  { id: 'src_grid_yaml', tier: 'sources', label: 'Grid Emissions Config',
    shortDesc: 'EF per geography (YAML)',
    detailPlain: 'YAML config with 2024 baseline grid emission factors for all 25 modelled geographies. Used by synthetic engine (Phase 0) and carbon overlay (Phase 1).',
    detailCode: 'configs/assumptions/grid_emissions.yaml\nFormat: geographies → {geo} → ef_2024: float',
    status: 'config' },
  { id: 'src_ref_params', tier: 'sources', label: 'Reference Parameters',
    shortDesc: '6 × five-year parameter sets (2007–2032)',
    detailPlain: 'Technical parameters updated in five-year steps aligned with the Fraunhofer study. Each set has power draws, usage hours, and lifespans for all product groups. Resolved via "most recent reference year ≤ target year" rule.',
    detailCode: 'configs/assumptions/reference_params/params_{year}.yaml\nYears: 2007, 2012, 2017, 2022, 2027, 2032\nResolver: reference_params.py → get_params()',
    status: 'config' },
  { id: 'src_scenarios', tier: 'sources', label: 'Scenario Registry',
    shortDesc: '7 demand + 3 grid mix scenarios',
    detailPlain: 'Registry defines all available scenarios with id, family, label, description, and color. Each scenario has a dedicated YAML with parameters like PUE improvement rate, AI growth rate, and placement shares.',
    detailCode: 'configs/scenarios/registry.yaml + ai_base.yaml, ai_high.yaml, ai_low.yaml, ai_stress.yaml, sovereignty_push.yaml, grid_constrained.yaml, efficiency_breakthrough.yaml',
    status: 'config' },
  { id: 'src_geo_tiers', tier: 'sources', label: 'Geo Tiers',
    shortDesc: '25 geographies across 4 tiers',
    detailPlain: 'Geography tiering driven by DC presence and AI significance. Tier 1 hotspots (US, DE, GB, IE, NL, SG, JP, AE), Tier 1 emerging (CN, IN, AU, CA, SE, PL), Tier 2 (FR, KR, BR, ZA, SA, MY), Tier 3 (regional aggregates). Germany is the calibration anchor.',
    detailCode: 'configs/geo_tiers.yaml\n8 Tier 1 hotspots, 6 Tier 1 emerging, 6 Tier 2, 5 Tier 3 aggregates',
    status: 'config' },

  // ── Tier 2: Loaders ───────────────────────────────────────────────────
  { id: 'ldr_eurostat', tier: 'loaders', label: 'Eurostat Loader',
    shortDesc: 'load_germany_dc_anchor() → gold DC capacity (DE)',
    detailPlain: 'Loads the Germany DC capacity calibration anchor from Borderstep 2023 data. Produces a gold-table-compatible DataFrame for DE data centres calibrated so the model outputs ≈18 TWh for 2022.',
    detailCode: 'src/data/loader_eurostat.py\ndef load_germany_dc_anchor(run_id, years) → pd.DataFrame\nColumns: geo, product, year, installed_capacity_mw, utilisation_rate, pue, ai_share, confidence_tier, source_ids',
    status: 'implemented' },
  { id: 'ldr_iea', tier: 'loaders', label: 'IEA Loader',
    shortDesc: 'Grid EFs + electricity prices → gold tables',
    detailPlain: 'Loads IEA grid emission factors and electricity prices. Grid EFs are kgCO₂e/kWh by country and year. Prices are USD/kWh by country, year, and sector.',
    detailCode: 'src/data/loader_iea.py\ndef load_grid_emission_factors(raw_path, run_id, version) → pd.DataFrame\ndef load_electricity_prices(raw_path, run_id, version) → pd.DataFrame',
    status: 'stub' },
  { id: 'ldr_itu', tier: 'loaders', label: 'ITU Loader',
    shortDesc: 'Network subscribers → gold table',
    detailPlain: 'Loads ITU subscriber and base station data. Cleans and normalises country × indicator × year structure into a flat DataFrame.',
    detailCode: 'src/data/loader_itu.py\ndef load_network_subscribers(raw_path, run_id, version) → pd.DataFrame',
    status: 'stub' },
  { id: 'ldr_trade', tier: 'loaders', label: 'Comtrade Loader',
    shortDesc: 'Device shipments → gold table',
    detailPlain: 'Loads UN Comtrade device shipment proxies from HS code trade data. Maps HS codes to product categories and aggregates import volumes by country and year.',
    detailCode: 'src/data/loader_trade.py\ndef load_device_shipments(raw_path, run_id, version) → pd.DataFrame',
    status: 'stub' },
  { id: 'ldr_dcbyte', tier: 'loaders', label: 'DC Byte Loader',
    shortDesc: 'DC capacity + PUE → gold tables',
    detailPlain: 'Loads DC capacity data (installed MW by geography and DC type) and PUE benchmarks from Uptime Institute survey data.',
    detailCode: 'src/data/loader_dc_byte.py\ndef load_dc_capacity(...) → pd.DataFrame\ndef load_pue_benchmarks(...) → pd.DataFrame',
    status: 'stub' },
  { id: 'ldr_gold_writer', tier: 'loaders', label: 'Gold Writer',
    shortDesc: 'Central write gate — adds lineage columns',
    detailPlain: 'All gold table writes go through this module. It enriches every DataFrame with source_id, ingestion_date, version, and run_id columns before writing to DuckDB. Ensures full data lineage.',
    detailCode: 'src/data/gold_writer.py\ndef write_gold_table(df, table_name, source_id, version, run_id, db_path, if_exists) → None\nTarget: data/gold/ict_demand.duckdb',
    status: 'implemented' },

  // ── Tier 3: Models ────────────────────────────────────────────────────
  { id: 'mdl_inventory', tier: 'models', label: 'Stock-Flow Inventory',
    shortDesc: 'Triangular lifespan distribution → active stock',
    detailPlain: 'Implements the sales → active stock calculation. Uses a triangular lifespan distribution so retirements spread across multiple years, producing smoother inventory curves. Retirements are a weighted sum of past shipments by age.',
    detailCode: 'src/models/inventory.py\ndef compute_stock_flow(shipments, lifespan_mean, lifespan_std, initial_stock) → np.ndarray\ndef build_stock_series(gold_df, ...) → pd.DataFrame (adds active_stock column)',
    formula: 'stock(t) = stock(t-1) + shipments(t) − Σ[shipments(t−age) × weight(age)]',
    status: 'implemented' },
  { id: 'mdl_load_profile', tier: 'models', label: 'Load Profile',
    shortDesc: '4-state power profile → kWh per unit',
    detailPlain: 'Converts a device power-state profile (off / ready / active_medium / active_high) and daily usage hours into annual kWh per unit. Supports both new 4-state and legacy 3-state column formats.',
    detailCode: 'src/models/load_profile.py\ndef annual_kwh_per_unit(profile: PowerStateProfile) → float\ndef apply_load_profile(stock_df) → pd.DataFrame (adds kwh_per_unit, annual_kwh)',
    formula: 'kWh/unit = Σ[hours(state) × watts(state)] / 1000',
    status: 'implemented' },
  { id: 'mdl_devices', tier: 'models', label: 'Devices Model',
    shortDesc: 'Households, workplace, public spaces electricity',
    detailPlain: 'Runs the devices electricity demand model. v1 uses simple stock-flow with single lifespan. v2 (study-aligned) uses lifespan distribution, 4-state load profiles, and reference-year parameters. Covers laptops, desktops, smartphones, tablets, monitors, printers.',
    detailCode: 'src/models/devices.py → run_devices_model(gold_df, scenario_params, run_id)\nsrc/models/devices_v2.py → run_devices_v2_model(gold_df, scenario_params, run_id, use_reference_params)\nReturns: DataFrame with segment="devices"',
    formula: 'annual_kwh = installed_base × Σ[hours(state) × power(state)] / 1000',
    status: 'implemented' },
  { id: 'mdl_networks', tier: 'models', label: 'Networks Model',
    shortDesc: 'Telecom infrastructure electricity',
    detailPlain: 'Equipment inventory approach scaled from subscriber data. v1 uses simple equipment_count × power × utilisation. v2 (port-unit channel model) splits into 4 layers: mobile access, fixed access, aggregation, core transport — each with site-specific PUE and energy management factors.',
    detailCode: 'src/models/networks.py → run_networks_model(gold_df, scenario_params, run_id)\nsrc/models/telecom_networks.py → run_telecom_networks_model(gold_df, scenario_params, run_id)\nLayers: mobile_access, fixed_access, aggregation, core_transport',
    formula: 'kwh = port_units × power_per_port × PUE × energy_mgmt × 8760 / 1000',
    status: 'implemented' },
  { id: 'mdl_datacentres', tier: 'models', label: 'Data Centres Model',
    shortDesc: 'DC electricity with AI workload separation',
    detailPlain: 'Capacity-based approach with explicit AI workload separation and PUE trajectories. v1 uses installed capacity (MW) × utilisation × PUE. v2 (architecture-centric) uses CPU/HDD/SSD/port unit counts. Monte Carlo simulation for Tier 1 geos. 5 DC types: hyperscale, sovereign, colocation, on-premises, edge.',
    detailCode: 'src/models/datacentres.py → run_datacentres_model(gold_df, scenario_params, run_id, monte_carlo_iterations)\nsrc/models/datacentres_v2.py → run_datacentres_v2_model(...)\nMonte Carlo: triangular distributions on PUE and utilisation',
    formula: 'total_kwh = capacity_MW × utilisation × PUE × 8760 × 1000',
    status: 'implemented' },
  { id: 'mdl_taxonomy', tier: 'models', label: 'Taxonomy',
    shortDesc: '5 application areas × 32 product groups',
    detailPlain: 'Implements the Fraunhofer Green ICT taxonomy: households, workplace, public spaces, data centres, telecom networks. Maps legacy (segment, product) pairs to the new dimensions. 32 product groups across 5 areas.',
    detailCode: 'src/models/taxonomy.py\nAPPLICATION_AREAS, PRODUCT_GROUP_REGISTRY, LEGACY_SEGMENT_MAP\ndef resolve_application_area(segment, product) → str\ndef enrich_with_taxonomy(df) → pd.DataFrame',
    status: 'implemented' },
  { id: 'mdl_uncertainty', tier: 'models', label: 'Uncertainty',
    shortDesc: 'Sensitivity tornado + MC convergence',
    detailPlain: 'Provides sensitivity analysis (tornado charts) via one-at-a-time parameter swings, and Monte Carlo convergence checks ensuring P50 converges within ±2% across independent splits.',
    detailCode: 'src/models/uncertainty.py\ndef sensitivity_tornado(base_params, model_fn, swing_fraction) → pd.DataFrame\ndef check_monte_carlo_convergence(samples, tolerance, n_splits) → dict',
    status: 'implemented' },
  { id: 'mdl_schema', tier: 'models', label: 'Output Schema',
    shortDesc: 'OutputRow TypedDict + validate_output()',
    detailPlain: 'Canonical output schema — locked contract. Every model function returns DataFrames validated against this schema. Key columns: geo, segment, product, year, kwh_estimate, kwh_p10/p50/p90, confidence_tier (1/2/3), uncertainty_band, scenario_id, run_id, source_ids.',
    detailCode: 'src/models/schema.py\nclass OutputRow(TypedDict)\ndef validate_output(df, context) → pd.DataFrame\ndef make_stub_output(...) → OutputRow',
    status: 'implemented' },

  // ── Tier 4: Overlays ──────────────────────────────────────────────────
  { id: 'ovl_carbon', tier: 'overlays', label: 'Carbon Overlay',
    shortDesc: 'emissions = kwh × grid_ef',
    detailPlain: 'Applies grid emission factors to electricity outputs. v1 uses static EFs. v2 adds three grid mix scenarios from 2025 onward (reference, ambitious, fossil) with annual EF reduction rates.',
    detailCode: 'src/models/carbon.py → apply_carbon_overlay(electricity_df, grid_ef_df)\nsrc/models/carbon_v2.py → apply_carbon_overlay_v2(electricity_df, grid_ef_df, grid_scenario_id)\nAdds: emissions_kgco2e, emissions_p10/p50/p90_kgco2e',
    formula: 'emissions_kgco2e = kwh × grid_ef_kgco2e_per_kwh',
    status: 'implemented' },
  { id: 'ovl_cost', tier: 'overlays', label: 'Cost Overlay',
    shortDesc: 'cost = kwh × electricity price',
    detailPlain: 'Applies electricity prices to electricity outputs. Merges geo × year price data and computes cost for central estimate and P10/P50/P90 bands.',
    detailCode: 'src/models/cost.py → apply_cost_overlay(electricity_df, price_df)\nAdds: cost_usd, cost_p10/p50/p90_usd',
    formula: 'cost_usd = kwh × price_usd_per_kwh',
    status: 'implemented' },
  { id: 'ovl_reporting', tier: 'overlays', label: 'Reporting Module',
    shortDesc: 'Appendix tables, area aggregation, ICT totals',
    detailPlain: 'Produces study-aligned output tables: per product group (inventory, kWh, emissions for reference years 2015/2025/2035), aggregated by application area, and overall ICT-in-scope totals.',
    detailCode: 'src/models/reporting.py\ndef build_appendix_table(results_df, reference_years) → pd.DataFrame\ndef aggregate_by_application_area(...) → pd.DataFrame\ndef aggregate_total_ict(...) → pd.DataFrame\ndef build_full_report(...) → dict[str, pd.DataFrame]',
    status: 'implemented' },

  // ── Tier 5: Outputs ───────────────────────────────────────────────────
  { id: 'out_schema', tier: 'outputs', label: 'Output Schema',
    shortDesc: 'geo × segment × product × year → kWh + uncertainty',
    detailPlain: 'Every output cell carries: kwh_estimate, kwh_p10/p50/p90, confidence_tier (1/2/3), uncertainty_band, scenario_id, run_id, and source_ids. This is the locked contract — never changed without migration.',
    detailCode: 'OutputRow TypedDict: geo, segment, product, year, kwh_estimate, kwh_p10, kwh_p50, kwh_p90, confidence_tier, uncertainty_band, scenario_id, run_id, source_ids',
    status: 'implemented' },
  { id: 'out_duckdb', tier: 'outputs', label: 'DuckDB Gold Tables',
    shortDesc: 'data/gold/ict_demand.duckdb',
    detailPlain: 'DuckDB is the single source of truth for gold tables. Every table has lineage columns: source_id, ingestion_date, version, run_id. All writes go through the gold_writer module.',
    detailCode: 'Path: data/gold/ict_demand.duckdb\nLineage: source_id, ingestion_date, version, run_id\nWriter: src/data/gold_writer.py',
    status: 'implemented' },
  { id: 'out_api', tier: 'outputs', label: 'Frontend API',
    shortDesc: 'REST API → charts, exports, decision-support UI',
    detailPlain: 'FastAPI backend serves scenario runs, results, and health checks. Frontend polls run status and renders interactive charts (Recharts/Plotly), exports (CSV), and the Streamlit decision-support app.',
    detailCode: 'backend/api/routes/scenarios.py → list, get\nbackend/api/routes/runs.py → create, status, results\nFrontend: React + TypeScript + Vite',
    status: 'implemented' },
];

const PHASE0_NODES: FlowNodeDef[] = [
  { id: 'p0_synthetic', tier: 'phase0', label: 'Synthetic Engine',
    shortDesc: 'Shaped trajectory generator — deterministic via seed',
    detailPlain: 'Phase 0 bypass: generates shaped synthetic data directly from scenario parameters without real data loaders or model functions. Each scenario has a distinct curve shape (exponential, linear, hockey stick, capped). Adds emissions and cost columns using config values. All runs deterministic via seed.',
    detailCode: 'backend/synthetic.py → generate(scenario_id, geos, years, segments, seed, run_id)\n25 geos × 3 segments × 14 products × 16 years = ~17,000 rows\nTrajectory functions: _dc_trajectory(), _device_trajectory(), _network_trajectory()',
    status: 'phase0' },
  { id: 'p0_engine', tier: 'phase0', label: 'Scenario Engine',
    shortDesc: 'Orchestration + scenario dispatch',
    detailPlain: 'SyntheticEngine loads scenario definitions from the registry YAML and dispatches to the synthetic generator. Filters out grid_mix scenarios (not runnable). In Phase 1, this will dispatch to real model functions instead.',
    detailCode: 'backend/engine/synthetic_engine.py\nclass SyntheticEngine\ndef list_scenarios() → list[dict]\ndef get_scenario(scenario_id) → dict\ndef run(scenario_id, params) → pd.DataFrame',
    status: 'phase0' },
];

const EDGES: FlowEdgeDef[] = [
  // Sources → Loaders
  { from: 'src_eurostat', to: 'ldr_eurostat' },
  { from: 'src_borderstep', to: 'ldr_eurostat' },
  { from: 'src_iea', to: 'ldr_iea' },
  { from: 'src_itu', to: 'ldr_itu' },
  { from: 'src_comtrade', to: 'ldr_trade' },
  { from: 'src_dcbyte', to: 'ldr_dcbyte' },
  // Loaders → Gold Writer
  { from: 'ldr_eurostat', to: 'ldr_gold_writer' },
  { from: 'ldr_iea', to: 'ldr_gold_writer' },
  { from: 'ldr_itu', to: 'ldr_gold_writer' },
  { from: 'ldr_trade', to: 'ldr_gold_writer' },
  { from: 'ldr_dcbyte', to: 'ldr_gold_writer' },
  // Gold Writer → Models
  { from: 'ldr_gold_writer', to: 'mdl_devices', label: 'device gold' },
  { from: 'ldr_gold_writer', to: 'mdl_networks', label: 'network gold' },
  { from: 'ldr_gold_writer', to: 'mdl_datacentres', label: 'DC gold' },
  // Supporting → Models
  { from: 'mdl_inventory', to: 'mdl_devices' },
  { from: 'mdl_load_profile', to: 'mdl_devices' },
  { from: 'src_ref_params', to: 'mdl_devices', label: 'params' },
  { from: 'mdl_taxonomy', to: 'mdl_devices' },
  { from: 'mdl_taxonomy', to: 'mdl_networks' },
  { from: 'mdl_taxonomy', to: 'mdl_datacentres' },
  { from: 'mdl_schema', to: 'mdl_devices' },
  { from: 'mdl_schema', to: 'mdl_networks' },
  { from: 'mdl_schema', to: 'mdl_datacentres' },
  // Models → Overlays
  { from: 'mdl_devices', to: 'ovl_carbon' },
  { from: 'mdl_networks', to: 'ovl_carbon' },
  { from: 'mdl_datacentres', to: 'ovl_carbon' },
  { from: 'mdl_devices', to: 'ovl_cost' },
  { from: 'mdl_networks', to: 'ovl_cost' },
  { from: 'mdl_datacentres', to: 'ovl_cost' },
  { from: 'ovl_carbon', to: 'ovl_reporting' },
  { from: 'ovl_cost', to: 'ovl_reporting' },
  // Overlays → Outputs
  { from: 'ovl_reporting', to: 'out_schema' },
  { from: 'out_schema', to: 'out_duckdb' },
  { from: 'out_schema', to: 'out_api' },
  // Phase 0 bypass
  { from: 'src_scenarios', to: 'p0_engine', dashed: true },
  { from: 'src_grid_yaml', to: 'p0_synthetic', dashed: true },
  { from: 'p0_engine', to: 'p0_synthetic', dashed: true },
  { from: 'p0_synthetic', to: 'out_api', dashed: true, label: 'bypass' },
];

/* ═══════════════════════════════════════════════════════════════════════════
   LAYOUT — x,y positions for every node on the SVG canvas
   ═══════════════════════════════════════════════════════════════════════════ */

const NODE_W = 180;
const NODE_H = 90;
const CANVAS_W = 1600;
const CANVAS_H = 1300;

const LAYOUT: Record<string, { x: number; y: number }> = {
  // Tier 1: Sources — y=30
  src_eurostat:    { x: 20,   y: 30 },
  src_borderstep:  { x: 215,  y: 30 },
  src_iea:         { x: 410,  y: 30 },
  src_itu:         { x: 605,  y: 30 },
  src_comtrade:    { x: 800,  y: 30 },
  src_dcbyte:      { x: 995,  y: 30 },
  src_grid_yaml:   { x: 20,   y: 140 },
  src_ref_params:  { x: 215,  y: 140 },
  src_scenarios:   { x: 410,  y: 140 },
  src_geo_tiers:   { x: 605,  y: 140 },

  // Tier 2: Loaders — y=310
  ldr_eurostat:    { x: 80,   y: 310 },
  ldr_iea:         { x: 280,  y: 310 },
  ldr_itu:         { x: 480,  y: 310 },
  ldr_trade:       { x: 680,  y: 310 },
  ldr_dcbyte:      { x: 880,  y: 310 },
  ldr_gold_writer: { x: 480,  y: 430 },

  // Tier 3: Models — y=590
  mdl_inventory:   { x: 20,   y: 590 },
  mdl_load_profile:{ x: 215,  y: 590 },
  mdl_devices:     { x: 120,  y: 720 },
  mdl_networks:    { x: 440,  y: 720 },
  mdl_datacentres: { x: 760,  y: 720 },
  mdl_taxonomy:    { x: 440,  y: 590 },
  mdl_uncertainty: { x: 635,  y: 590 },
  mdl_schema:      { x: 830,  y: 590 },

  // Tier 4: Overlays — y=880
  ovl_carbon:      { x: 240,  y: 880 },
  ovl_cost:        { x: 540,  y: 880 },
  ovl_reporting:   { x: 390,  y: 990 },

  // Tier 5: Outputs — y=1130
  out_schema:      { x: 300,  y: 1130 },
  out_duckdb:      { x: 540,  y: 1130 },
  out_api:         { x: 780,  y: 1130 },

  // Phase 0 — right column
  p0_engine:       { x: 1300, y: 310 },
  p0_synthetic:    { x: 1300, y: 590 },
};

/* ═══════════════════════════════════════════════════════════════════════════
   GRAPH TRAVERSAL
   ═══════════════════════════════════════════════════════════════════════════ */

function getUpstream(nodeId: string, edges: FlowEdgeDef[]): Set<string> {
  const visited = new Set<string>();
  const queue = [nodeId];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const e of edges) {
      if (e.to === current && !visited.has(e.from)) {
        visited.add(e.from);
        queue.push(e.from);
      }
    }
  }
  return visited;
}

function getDownstream(nodeId: string, edges: FlowEdgeDef[]): Set<string> {
  const visited = new Set<string>();
  const queue = [nodeId];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const e of edges) {
      if (e.from === current && !visited.has(e.to)) {
        visited.add(e.to);
        queue.push(e.to);
      }
    }
  }
  return visited;
}

function getFlowPath(nodeId: string, edges: FlowEdgeDef[]): Set<string> {
  const up = getUpstream(nodeId, edges);
  const down = getDownstream(nodeId, edges);
  return new Set([...up, nodeId, ...down]);
}

function getFlowEdges(activeNodes: Set<string>, edges: FlowEdgeDef[]): Set<number> {
  const result = new Set<number>();
  edges.forEach((e, i) => {
    if (activeNodes.has(e.from) && activeNodes.has(e.to)) result.add(i);
  });
  return result;
}

/* ═══════════════════════════════════════════════════════════════════════════
   FLOW PRESETS
   ═══════════════════════════════════════════════════════════════════════════ */

interface FlowPreset {
  label: string;
  description: string;
  seedNodes: string[];
}

const FLOW_PRESETS: FlowPreset[] = [
  { label: 'All', description: 'Show all connections', seedNodes: [] },
  { label: 'Devices', description: 'Comtrade → stock-flow → devices → outputs',
    seedNodes: ['src_comtrade', 'ldr_trade', 'ldr_gold_writer', 'mdl_inventory', 'mdl_load_profile',
      'mdl_devices', 'mdl_taxonomy', 'mdl_schema', 'src_ref_params',
      'ovl_carbon', 'ovl_cost', 'ovl_reporting', 'out_schema', 'out_duckdb', 'out_api'] },
  { label: 'Networks', description: 'ITU → loaders → networks model → outputs',
    seedNodes: ['src_itu', 'ldr_itu', 'ldr_gold_writer', 'mdl_networks', 'mdl_taxonomy', 'mdl_schema',
      'ovl_carbon', 'ovl_cost', 'ovl_reporting', 'out_schema', 'out_duckdb', 'out_api'] },
  { label: 'Data Centres', description: 'Eurostat + DC Byte → DC model → outputs',
    seedNodes: ['src_eurostat', 'src_borderstep', 'src_dcbyte', 'ldr_eurostat', 'ldr_dcbyte',
      'ldr_gold_writer', 'mdl_datacentres', 'mdl_taxonomy', 'mdl_schema',
      'ovl_carbon', 'ovl_cost', 'ovl_reporting', 'out_schema', 'out_duckdb', 'out_api'] },
  { label: 'Phase 0', description: 'Synthetic bypass — scenarios → shaped curves → API',
    seedNodes: ['src_scenarios', 'src_grid_yaml', 'p0_engine', 'p0_synthetic', 'out_api'] },
];

/* ═══════════════════════════════════════════════════════════════════════════
   BEZIER PATH HELPER
   ═══════════════════════════════════════════════════════════════════════════ */

function bezierPath(fromId: string, toId: string): string {
  const from = LAYOUT[fromId];
  const to = LAYOUT[toId];
  if (!from || !to) return '';
  const x1 = from.x + NODE_W / 2;
  const y1 = from.y + NODE_H;
  const x2 = to.x + NODE_W / 2;
  const y2 = to.y;
  const dy = Math.abs(y2 - y1);
  const cp = Math.max(dy * 0.45, 40);
  return `M ${x1} ${y1} C ${x1} ${y1 + cp}, ${x2} ${y2 - cp}, ${x2} ${y2}`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════════════════════ */

function StatusBadge({ status }: { status: NodeStatus }) {
  const s = STATUS_STYLE[status];
  return (
    <span style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '0.04em', padding: '2px 6px',
      borderRadius: '3px', background: s.bg, color: s.color, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
      {s.label}
    </span>
  );
}

function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  const colors: Record<number, string> = { 1: 'var(--accent-active)', 2: 'var(--accent-amber)', 3: 'var(--accent-red)' };
  return (
    <span style={{ fontSize: '9px', fontWeight: 700, fontFamily: 'var(--font-mono)', padding: '1px 5px',
      borderRadius: '3px', border: `1px solid ${colors[tier]}40`, color: colors[tier], whiteSpace: 'nowrap' }}>
      T{tier}
    </span>
  );
}

function FormulaBox({ formula }: { formula: string }) {
  return (
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-secondary)',
      background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '4px',
      padding: '4px 8px', marginTop: '4px', lineHeight: 1.4, whiteSpace: 'pre-wrap' }}>
      {formula}
    </div>
  );
}

/* ── Canvas node card (rendered inside foreignObject) ──────────────────── */

function CanvasNode({ node, isActive, isSelected, isDimmed, onClick }: {
  node: FlowNodeDef; isActive: boolean; isSelected: boolean; isDimmed: boolean; onClick: () => void;
}) {
  const tier = TIER_META[node.tier];
  const isPhase0 = node.tier === 'phase0';
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      style={{
        width: NODE_W,
        height: NODE_H,
        background: 'var(--bg-surface)',
        border: `1.5px ${isPhase0 ? 'dashed' : 'solid'} ${isSelected ? tier.color : isActive ? tier.color : 'var(--border)'}`,
        borderRadius: '8px',
        padding: '8px 10px',
        cursor: 'pointer',
        textAlign: 'left',
        fontFamily: 'var(--font-sans)',
        transition: 'opacity 0.25s ease, border-color 0.2s ease, box-shadow 0.2s ease',
        opacity: isDimmed ? 0.15 : 1,
        boxShadow: isSelected
          ? `0 0 0 3px ${tier.color}30, 0 2px 12px rgba(0,0,0,0.12)`
          : isActive ? `0 0 0 2px ${tier.color}18, 0 1px 4px rgba(0,0,0,0.06)` : '0 1px 3px rgba(0,0,0,0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: '3px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
        <StatusBadge status={node.status} />
        {node.confidenceTier && <TierBadge tier={node.confidenceTier} />}
      </div>
      <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {node.label}
      </div>
      <div style={{ fontSize: '10px', color: 'var(--text-secondary)', lineHeight: 1.3,
        overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
        {node.shortDesc}
      </div>
      {/* Left accent bar */}
      <div style={{ position: 'absolute', left: 0, top: '6px', bottom: '6px', width: '3px',
        borderRadius: '0 2px 2px 0', background: tier.color, opacity: isSelected || isActive ? 1 : 0.3 }} />
    </button>
  );
}

/* ── Detail panel (slide-out right) ────────────────────────────────────── */

function DetailPanel({ node, onClose }: { node: FlowNodeDef; onClose: () => void }) {
  const [showCode, setShowCode] = useState(false);
  const tier = TIER_META[node.tier];
  return (
    <div style={{
      position: 'fixed', top: '52px', right: 0, bottom: 0, width: '380px', zIndex: 200,
      background: 'var(--bg-surface)', borderLeft: '1px solid var(--border)',
      boxShadow: '-4px 0 20px rgba(0,0,0,0.08)', display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
            <StatusBadge status={node.status} />
            {node.confidenceTier && <TierBadge tier={node.confidenceTier} />}
            <span style={{ fontSize: '10px', color: tier.color, fontWeight: 600 }}>{tier.label}</span>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer',
            fontSize: '18px', color: 'var(--text-muted)', lineHeight: 1, padding: '0 4px' }}>×</button>
        </div>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>{node.label}</h3>
      </div>

      <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '0' }}>
        {(['plain', 'code'] as const).map((mode) => (
          <button key={mode} onClick={() => setShowCode(mode === 'code')}
            style={{
              flex: 1, padding: '6px 0', fontSize: '11px', fontWeight: 600,
              background: (mode === 'code') === showCode ? 'var(--accent-soft)' : 'transparent',
              color: (mode === 'code') === showCode ? 'var(--accent-active)' : 'var(--text-muted)',
              border: '1px solid var(--border)', cursor: 'pointer',
              borderRadius: mode === 'plain' ? '4px 0 0 4px' : '0 4px 4px 0',
              borderLeft: mode === 'code' ? 'none' : undefined,
            }}>
            {mode === 'plain' ? 'Description' : 'Code Detail'}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
        {!showCode ? (
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.7 }}>
            {node.detailPlain}
          </p>
        ) : (
          <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '11px', lineHeight: 1.7,
            color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {node.detailCode || 'No code detail available.'}
          </pre>
        )}
        {node.formula && (
          <div style={{ marginTop: '16px' }}>
            <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.06em',
              textTransform: 'uppercase', marginBottom: '6px' }}>Key Formula</div>
            <FormulaBox formula={node.formula} />
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Tier band backgrounds for the SVG canvas ──────────────────────────── */

const TIER_BANDS: { tier: TierKey; y: number; h: number }[] = [
  { tier: 'sources',  y: 0,    h: 260 },
  { tier: 'loaders',  y: 270,  h: 280 },
  { tier: 'models',   y: 560,  h: 280 },
  { tier: 'overlays', y: 850,  h: 240 },
  { tier: 'outputs',  y: 1100, h: 140 },
];

/* ── Flow toolbar (presets + zoom controls) ────────────────────────────── */

function FlowToolbar({ activePreset, onPreset, zoom, onZoomIn, onZoomOut, onFit }: {
  activePreset: number; onPreset: (i: number) => void;
  zoom: number; onZoomIn: () => void; onZoomOut: () => void; onFit: () => void;
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      marginBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
      {/* Flow presets */}
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', alignSelf: 'center', marginRight: '4px' }}>
          Trace flow:
        </span>
        {FLOW_PRESETS.map((p, i) => (
          <button key={p.label} onClick={() => onPreset(i)} title={p.description}
            style={{
              padding: '5px 12px', fontSize: '11px', fontWeight: 600, borderRadius: '5px', cursor: 'pointer',
              border: activePreset === i ? '1.5px solid var(--accent)' : '1px solid var(--border)',
              background: activePreset === i ? 'var(--accent-soft)' : 'var(--bg-surface)',
              color: activePreset === i ? 'var(--accent-active)' : 'var(--text-secondary)',
              transition: 'all 0.15s ease',
            }}>
            {p.label}
          </button>
        ))}
      </div>
      {/* Zoom controls */}
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginRight: '6px' }}>
          {Math.round(zoom * 100)}%
        </span>
        {[{ label: '−', fn: onZoomOut }, { label: '+', fn: onZoomIn }, { label: 'Fit', fn: onFit }].map((b) => (
          <button key={b.label} onClick={b.fn}
            style={{ width: b.label === 'Fit' ? 'auto' : '28px', height: '28px', padding: '0 8px',
              fontSize: '12px', fontWeight: 600, borderRadius: '4px', cursor: 'pointer',
              border: '1px solid var(--border)', background: 'var(--bg-surface)', color: 'var(--text-secondary)' }}>
            {b.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Legend ─────────────────────────────────────────────────────────────── */

function Legend() {
  const items: { label: string; color: string; dashed?: boolean }[] = [
    { label: 'Sources', color: TIER_META.sources.color },
    { label: 'Loaders', color: TIER_META.loaders.color },
    { label: 'Models', color: TIER_META.models.color },
    { label: 'Overlays', color: TIER_META.overlays.color },
    { label: 'Outputs', color: TIER_META.outputs.color },
    { label: 'Phase 0 Bypass', color: TIER_META.phase0.color, dashed: true },
  ];
  return (
    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '12px', alignItems: 'center' }}>
      {items.map((it) => (
        <div key={it.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '14px', height: '14px', borderRadius: '3px',
            border: `2px ${it.dashed ? 'dashed' : 'solid'} ${it.color}`, background: `${it.color}15` }} />
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500 }}>{it.label}</span>
        </div>
      ))}
      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic', marginLeft: '8px' }}>
        Click any node to trace its flow
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   EXPORTED PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

export function Methodology() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activePresetIdx, setActivePresetIdx] = useState(0);
  const [zoom, setZoom] = useState(0.72);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  const allNodes = [...NODES, ...PHASE0_NODES];
  const allEdges = EDGES;

  /* Compute active flow nodes */
  const activeNodes: Set<string> | null = (() => {
    if (selectedId) return getFlowPath(selectedId, allEdges);
    const preset = FLOW_PRESETS[activePresetIdx];
    if (preset.seedNodes.length === 0) return null;
    return new Set(preset.seedNodes);
  })();

  const activeEdgeIdxs: Set<number> | null = activeNodes ? getFlowEdges(activeNodes, allEdges) : null;

  const selectedNode = allNodes.find((n) => n.id === selectedId) ?? null;

  const handleNodeClick = useCallback((id: string) => {
    setSelectedId((prev) => (prev === id ? null : id));
    setActivePresetIdx(0);
  }, []);

  const handlePreset = useCallback((i: number) => {
    setActivePresetIdx(i);
    setSelectedId(null);
  }, []);

  const handleCanvasClick = useCallback(() => {
    setSelectedId(null);
    setActivePresetIdx(0);
  }, []);

  /* Zoom handlers */
  const handleZoomIn = useCallback(() => setZoom((z) => Math.min(z + 0.1, 1.5)), []);
  const handleZoomOut = useCallback(() => setZoom((z) => Math.max(z - 0.1, 0.3)), []);
  const handleFit = useCallback(() => { setZoom(0.72); setPan({ x: 0, y: 0 }); }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.max(0.3, Math.min(1.5, z - e.deltaY * 0.001)));
  }, []);

  /* Pan handlers */
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning) return;
    setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
  }, [isPanning, panStart]);

  const handleMouseUp = useCallback(() => setIsPanning(false), []);

  /* Keyboard: Escape to deselect */
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { setSelectedId(null); setActivePresetIdx(0); }
  }, []);

  const tierNodes = (tier: TierKey) => NODES.filter((n) => n.tier === tier);

  return (
    <div style={{ padding: '24px', paddingRight: selectedNode ? '404px' : '24px', transition: 'padding-right 0.2s ease' }}
      onKeyDown={handleKeyDown} tabIndex={0}>
      <PageHeader
        title="Methodology & Data Model"
        subtitle="Interactive process flow — click any node to trace data through the pipeline"
      />

      <Legend />

      <FlowToolbar activePreset={activePresetIdx} onPreset={handlePreset}
        zoom={zoom} onZoomIn={handleZoomIn} onZoomOut={handleZoomOut} onFit={handleFit} />

      {/* Canvas container with pan/zoom */}
      <div
        style={{
          borderRadius: '12px', border: '1px solid var(--border)', overflow: 'hidden',
          background: 'radial-gradient(circle, var(--border) 0.8px, transparent 0.8px)',
          backgroundSize: '20px 20px',
          cursor: isPanning ? 'grabbing' : 'grab',
          position: 'relative',
          height: 'calc(100vh - 220px)',
          minHeight: '500px',
        }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleCanvasClick}
      >
        <div style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: '0 0',
          width: CANVAS_W,
          height: CANVAS_H,
          position: 'relative',
        }}>
          <svg width={CANVAS_W} height={CANVAS_H} style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 8" refX="9" refY="4" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 4 L 0 8 z" fill="var(--border-bright)" />
              </marker>
              <marker id="arrow-hl" viewBox="0 0 10 8" refX="9" refY="4" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 4 L 0 8 z" fill="var(--accent)" />
              </marker>
              <marker id="arrow-amber" viewBox="0 0 10 8" refX="9" refY="4" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 4 L 0 8 z" fill="var(--accent-amber)" />
              </marker>
            </defs>

            {/* Tier band backgrounds */}
            {TIER_BANDS.map((b) => {
              const meta = TIER_META[b.tier];
              return (
                <g key={b.tier}>
                  <rect x={0} y={b.y} width={CANVAS_W - 300} height={b.h} rx={10}
                    fill={meta.bg} stroke={`${meta.color}20`} strokeWidth={1} />
                  <text x={14} y={b.y + 18} fontSize={11} fontWeight={700} fill={meta.color}
                    fontFamily="var(--font-sans)" letterSpacing="0.04em">
                    {meta.label.toUpperCase()}
                  </text>
                </g>
              );
            })}

            {/* Phase 0 column background */}
            <rect x={1260} y={0} width={320} height={CANVAS_H} rx={10}
              fill={TIER_META.phase0.bg} stroke="var(--accent-amber)" strokeWidth={1.5}
              strokeDasharray="8 4" />
            <text x={1274} y={22} fontSize={11} fontWeight={700} fill="var(--accent-amber)"
              fontFamily="var(--font-sans)" letterSpacing="0.04em">
              PHASE 0 — SYNTHETIC BYPASS
            </text>

            {/* Edges */}
            {allEdges.map((edge, i) => {
              const d = bezierPath(edge.from, edge.to);
              if (!d) return null;
              const isHighlighted = activeEdgeIdxs === null || activeEdgeIdxs.has(i);
              const isDimmed = activeEdgeIdxs !== null && !activeEdgeIdxs.has(i);
              const isPhase0Edge = edge.dashed;
              return (
                <path key={i} d={d}
                  fill="none"
                  stroke={isHighlighted && isPhase0Edge ? 'var(--accent-amber)'
                    : isHighlighted ? 'var(--accent)' : 'var(--border-bright)'}
                  strokeWidth={isHighlighted && activeEdgeIdxs !== null ? 2.5 : 1.2}
                  strokeDasharray={isPhase0Edge ? '6 4' : undefined}
                  markerEnd={isHighlighted && isPhase0Edge ? 'url(#arrow-amber)'
                    : isHighlighted && activeEdgeIdxs !== null ? 'url(#arrow-hl)' : 'url(#arrow)'}
                  opacity={isDimmed ? 0.1 : 1}
                  style={{ transition: 'opacity 0.25s ease, stroke 0.25s ease, stroke-width 0.25s ease' }}
                />
              );
            })}

            {/* Edge labels */}
            {allEdges.map((edge, i) => {
              if (!edge.label) return null;
              const from = LAYOUT[edge.from];
              const to = LAYOUT[edge.to];
              if (!from || !to) return null;
              const mx = (from.x + NODE_W / 2 + to.x + NODE_W / 2) / 2;
              const my = (from.y + NODE_H + to.y) / 2;
              const isDimmed = activeEdgeIdxs !== null && !activeEdgeIdxs.has(i);
              return (
                <text key={`lbl-${i}`} x={mx} y={my - 4} fontSize={9} fill="var(--text-muted)"
                  textAnchor="middle" fontFamily="var(--font-sans)" fontWeight={500}
                  opacity={isDimmed ? 0.1 : 0.7}>
                  {edge.label}
                </text>
              );
            })}
          </svg>

          {/* Node cards (HTML over SVG) */}
          {allNodes.map((node) => {
            const pos = LAYOUT[node.id];
            if (!pos) return null;
            const isSelected = selectedId === node.id;
            const isActive = activeNodes === null || activeNodes.has(node.id);
            const isDimmed = activeNodes !== null && !activeNodes.has(node.id);
            return (
              <div key={node.id} style={{
                position: 'absolute', left: pos.x, top: pos.y,
                zIndex: isSelected ? 10 : isActive ? 5 : 1,
              }}>
                <CanvasNode node={node} isActive={isActive} isSelected={isSelected}
                  isDimmed={isDimmed} onClick={() => handleNodeClick(node.id)} />
              </div>
            );
          })}
        </div>
      </div>

      {/* Pipeline summary */}
      <Card style={{ marginTop: '16px' }}>
        <h3 style={{ margin: '0 0 8px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Pipeline Summary
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px' }}>
          {[
            { label: 'Data Sources', value: tierNodes('sources').length.toString(), sub: `${NODES.filter(n => n.tier === 'sources' && n.status === 'implemented').length} implemented` },
            { label: 'Loaders', value: tierNodes('loaders').length.toString(), sub: `${NODES.filter(n => n.tier === 'loaders' && n.status === 'implemented').length} implemented` },
            { label: 'Model Functions', value: tierNodes('models').length.toString(), sub: '3 tracks + 4 utilities' },
            { label: 'Overlays', value: tierNodes('overlays').length.toString(), sub: 'Carbon + Cost + Reporting' },
            { label: 'Outputs', value: tierNodes('outputs').length.toString(), sub: 'Schema → DuckDB → API' },
            { label: 'Connections', value: allEdges.length.toString(), sub: `${allEdges.filter(e => e.dashed).length} Phase 0 bypass` },
          ].map((kpi) => (
            <div key={kpi.label} style={{ padding: '10px', background: 'var(--bg-base)', borderRadius: '6px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{kpi.label}</div>
              <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', margin: '2px 0' }}>{kpi.value}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{kpi.sub}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Detail panel */}
      {selectedNode && <DetailPanel node={selectedNode} onClose={() => { setSelectedId(null); setActivePresetIdx(0); }} />}
    </div>
  );
}
