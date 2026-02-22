// API schema types — mirrors backend/models.py Pydantic models
// In production these would be generated from /api/v1/openapi.json

export type RunStatus = 'queued' | 'running' | 'done' | 'failed';

export interface OutputRow {
  geo: string;
  segment: string;
  product: string;
  year: number;
  kwh_estimate: number;
  kwh_p10: number;
  kwh_p50: number;
  kwh_p90: number;
  confidence_tier: 1 | 2 | 3;
  uncertainty_band: number;
  scenario_id: string;
  run_id: string;
  source_ids: string[];
  emissions_kgco2e: number | null;
  cost_usd: number | null;
}

export interface ModelCard {
  model_version: string;
  data_vintage: string;
  engine: string;
  scenario_id: string;
  assumptions_hash: string;
  seed: number;
  test_status: string;
  inputs_summary: Record<string, unknown>;
}

export interface RunResult {
  run_id: string;
  status: RunStatus;
  model_card: ModelCard;
  rows: OutputRow[];
  summary: RunSummary;
}

export interface RunSummary {
  scenario_id: string;
  latest_year: number;
  total_twh: number;
  dc_twh: number;
  dc_share: number;
  devices_twh: number;
  networks_twh: number;
  total_emissions_mtco2e: number;
  total_cost_usd_bn: number;
  n_geos: number;
  confidence_tier_distribution: Record<string, number>;
}

export interface RunResponse {
  run_id: string;
  status: RunStatus;
}

export interface RunStatusResponse {
  run_id: string;
  status: RunStatus;
  progress: number;
  result: RunResult | null;
  error: string | null;
}

export interface ScenarioMeta {
  id: string;
  family: string;
  label: string;
  description: string;
  color: string;
}

export interface ScenarioDetail extends ScenarioMeta {
  params: Record<string, unknown>;
  assumption_ranges: Record<string, unknown>;
}

export interface ScenarioParams {
  scenario_id: string;
  label?: string;
  pue_improvement_rate?: number;
  utilisation_multiplier?: number;
  ai_growth_rate?: number;
  hyperscale_share?: number;
  avg_lifespan_multiplier?: number;
  device_shipment_growth?: number;
  power_efficiency_factor?: number;
  grid_carbon_2035_target?: number | null;
  geos?: string[] | null;
  years?: number[] | null;
  segments?: string[] | null;
  seed?: number;
}

export interface DemandSummary {
  scenario_id: string;
  year: number;
  total_twh: number;
  dc_twh: number;
  dc_share: number;
  devices_twh: number;
  networks_twh: number;
  total_emissions_mtco2e: number;
  total_cost_usd_bn: number;
  n_geos: number;
  confidence_tier_distribution: Record<string, number>;
}

export interface HealthResponse {
  status: string;
  model_version: string;
  data_vintage: string;
  engine: string;
}
