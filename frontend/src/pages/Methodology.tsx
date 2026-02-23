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

const TIER_ORDER: TierKey[] = ['sources', 'loaders', 'models', 'overlays', 'outputs'];

/* ═══════════════════════════════════════════════════════════════════════════
   PLACEHOLDER — nodes, edges, components appended below
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
      padding: '4px 8px', marginTop: '6px', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
      {formula}
    </div>
  );
}

function FlowNodeCard({ node, selected, onClick }: { node: FlowNodeDef; selected: boolean; onClick: () => void }) {
  const tier = TIER_META[node.tier];
  const isPhase0 = node.tier === 'phase0';
  return (
    <button
      onClick={onClick}
      style={{
        background: 'var(--bg-surface)',
        border: `1.5px ${isPhase0 ? 'dashed' : 'solid'} ${selected ? tier.color : 'var(--border)'}`,
        borderRadius: '8px',
        padding: '12px 14px',
        width: '200px',
        minHeight: '80px',
        cursor: 'pointer',
        textAlign: 'left',
        fontFamily: 'var(--font-sans)',
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
        boxShadow: selected ? `0 0 0 3px ${tier.color}20, 0 2px 8px rgba(0,0,0,0.08)` : '0 1px 3px rgba(0,0,0,0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        flexShrink: 0,
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        <StatusBadge status={node.status} />
        {node.confidenceTier && <TierBadge tier={node.confidenceTier} />}
      </div>
      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.3 }}>
        {node.label}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
        {node.shortDesc}
      </div>
      {node.formula && <FormulaBox formula={node.formula} />}
      {/* Left accent bar */}
      <div style={{ position: 'absolute', left: 0, top: '8px', bottom: '8px', width: '3px',
        borderRadius: '0 2px 2px 0', background: tier.color, opacity: selected ? 1 : 0.4 }} />
    </button>
  );
}

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
      {/* Header */}
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

      {/* Toggle */}
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

      {/* Content */}
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

function TierRow({ tierKey, nodes, selectedId, onSelect }: {
  tierKey: TierKey; nodes: FlowNodeDef[]; selectedId: string | null; onSelect: (id: string) => void;
}) {
  const meta = TIER_META[tierKey];
  return (
    <div style={{ background: meta.bg, borderRadius: '10px', padding: '16px 20px', border: `1px solid ${meta.color}20` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: meta.color, flexShrink: 0 }} />
        <span style={{ fontSize: '11px', fontWeight: 700, color: meta.color, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          {meta.label}
        </span>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>— {nodes.length} nodes</span>
      </div>
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        {nodes.map((n) => (
          <FlowNodeCard key={n.id} node={n} selected={selectedId === n.id} onClick={() => onSelect(n.id)} />
        ))}
      </div>
    </div>
  );
}

function DownArrow() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
      <svg width="20" height="28" viewBox="0 0 20 28">
        <line x1="10" y1="0" x2="10" y2="22" stroke="var(--border-bright)" strokeWidth="1.5" />
        <polygon points="5,20 10,28 15,20" fill="var(--border-bright)" />
      </svg>
    </div>
  );
}

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
    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '20px' }}>
      {items.map((it) => (
        <div key={it.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '14px', height: '14px', borderRadius: '3px',
            border: `2px ${it.dashed ? 'dashed' : 'solid'} ${it.color}`, background: `${it.color}15` }} />
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500 }}>{it.label}</span>
        </div>
      ))}
      <div style={{ marginLeft: '8px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        {(['implemented', 'stub', 'config', 'phase0'] as NodeStatus[]).map((s) => (
          <StatusBadge key={s} status={s} />
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   EXPORTED PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

export function Methodology() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const allNodes = [...NODES, ...PHASE0_NODES];
  const selectedNode = allNodes.find((n) => n.id === selectedId) ?? null;

  const handleSelect = useCallback((id: string) => {
    setSelectedId((prev) => (prev === id ? null : id));
  }, []);

  const tierNodes = (tier: TierKey) => NODES.filter((n) => n.tier === tier);

  return (
    <div style={{ padding: '24px', paddingRight: selectedNode ? '404px' : '24px', transition: 'padding-right 0.2s ease' }}>
      <PageHeader
        title="Methodology & Data Model"
        subtitle="Interactive pipeline map — click any node to explore data sources, model functions, and outputs"
      />

      <Legend />

      {/* Dot-grid background wrapper */}
      <div style={{
        background: 'radial-gradient(circle, var(--border) 0.8px, transparent 0.8px)',
        backgroundSize: '20px 20px',
        borderRadius: '12px',
        padding: '24px',
        border: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {TIER_ORDER.map((tier, i) => (
            <div key={tier}>
              <TierRow tierKey={tier} nodes={tierNodes(tier)} selectedId={selectedId} onSelect={handleSelect} />
              {i < TIER_ORDER.length - 1 && <DownArrow />}
            </div>
          ))}

          {/* Phase 0 bypass track */}
          <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '2px dashed var(--accent-amber)' }}>
            <TierRow tierKey="phase0" nodes={PHASE0_NODES} selectedId={selectedId} onSelect={handleSelect} />
            <div style={{ marginTop: '10px', padding: '10px 16px', background: 'rgba(237,139,0,0.06)',
              borderRadius: '6px', border: '1px dashed var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '11px', color: 'var(--accent-amber)', fontWeight: 600 }}>⚠</span>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                <strong>Phase 0 bypass active.</strong> The synthetic engine generates shaped trajectories directly from scenario parameters,
                bypassing real data loaders and model functions. When Phase 1 loaders are implemented, this track will be replaced by the main pipeline above.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Edge summary card */}
      <Card style={{ marginTop: '24px' }}>
        <h3 style={{ margin: '0 0 8px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Pipeline Summary
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {[
            { label: 'Data Sources', value: tierNodes('sources').length.toString(), sub: `${NODES.filter(n => n.tier === 'sources' && n.status === 'implemented').length} implemented` },
            { label: 'Loaders', value: tierNodes('loaders').length.toString(), sub: `${NODES.filter(n => n.tier === 'loaders' && n.status === 'implemented').length} implemented` },
            { label: 'Model Functions', value: tierNodes('models').length.toString(), sub: '3 segment tracks + 4 utilities' },
            { label: 'Overlays', value: tierNodes('overlays').length.toString(), sub: 'Carbon + Cost + Reporting' },
            { label: 'Outputs', value: tierNodes('outputs').length.toString(), sub: 'Schema → DuckDB → API' },
            { label: 'Connections', value: EDGES.length.toString(), sub: `${EDGES.filter(e => e.dashed).length} Phase 0 bypass` },
          ].map((kpi) => (
            <div key={kpi.label} style={{ padding: '12px', background: 'var(--bg-base)', borderRadius: '6px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{kpi.label}</div>
              <div style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', margin: '4px 0 2px' }}>{kpi.value}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{kpi.sub}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Detail panel */}
      {selectedNode && <DetailPanel node={selectedNode} onClose={() => setSelectedId(null)} />}
    </div>
  );
}
