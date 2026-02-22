// Taxonomy utility — mirrors src/models/taxonomy.py LEGACY_SEGMENT_MAP
// Derives application_area and product_group from legacy (segment, product) pairs.
// All enrichment is client-side; no backend changes required.

import type { OutputRow } from '../types/schema';

// ── Application areas ────────────────────────────────────────────────────────

export const APPLICATION_AREAS = [
  'households',
  'workplace',
  'public_spaces',
  'datacentres',
  'telecom_networks',
] as const;

export type ApplicationArea = (typeof APPLICATION_AREAS)[number];

export const AREA_LABELS: Record<ApplicationArea, string> = {
  households:       'Households',
  workplace:        'Workplace',
  public_spaces:    'Public Spaces',
  datacentres:      'Data Centres',
  telecom_networks: 'Telecom Networks',
};

export const AREA_COLORS: Record<ApplicationArea, string> = {
  households:       '#00FF41',
  workplace:        '#00D4FF',
  public_spaces:    '#F59E0B',
  datacentres:      '#EF4444',
  telecom_networks: '#AA00FF',
};

// ── Legacy segment → application area mapping ────────────────────────────────

type LegacyKey = `${string}|${string}`;

interface TaxonomyMapping {
  application_area: ApplicationArea;
  product_group: string;
}

const LEGACY_MAP: Record<LegacyKey, TaxonomyMapping> = {
  // devices → households
  'devices|laptop':      { application_area: 'households',       product_group: 'laptop_hh' },
  'devices|desktop':     { application_area: 'households',       product_group: 'desktop_hh' },
  'devices|smartphone':  { application_area: 'households',       product_group: 'smartphone_hh' },
  'devices|tablet':      { application_area: 'households',       product_group: 'tablet_hh' },
  'devices|monitor':     { application_area: 'households',       product_group: 'monitor_hh' },
  // devices → workplace
  'devices|pc_notebook_wp': { application_area: 'workplace',    product_group: 'pc_notebook_wp' },
  'devices|printer_mfd_wp': { application_area: 'workplace',    product_group: 'printer_mfd_wp' },
  'devices|monitor_wp':     { application_area: 'workplace',    product_group: 'monitor_wp' },
  'devices|telephone_wp':   { application_area: 'workplace',    product_group: 'telephone_wp' },
  'devices|lan_port_wp':    { application_area: 'workplace',    product_group: 'lan_port_wp' },
  // networks → telecom_networks
  'networks|5g_base_station':     { application_area: 'telecom_networks', product_group: 'mobile_access_port' },
  'networks|4g_base_station':     { application_area: 'telecom_networks', product_group: 'mobile_access_port' },
  'networks|fixed_broadband_cpe': { application_area: 'telecom_networks', product_group: 'fixed_access_port' },
  'networks|core_network':        { application_area: 'telecom_networks', product_group: 'core_transport_port' },
  // datacentres → datacentres
  'datacentres|hyperscale':   { application_area: 'datacentres', product_group: 'cpu_unit' },
  'datacentres|sovereign':    { application_area: 'datacentres', product_group: 'cpu_unit' },
  'datacentres|colocation':   { application_area: 'datacentres', product_group: 'cpu_unit' },
  'datacentres|on_premises':  { application_area: 'datacentres', product_group: 'cpu_unit' },
  'datacentres|edge':         { application_area: 'datacentres', product_group: 'cpu_unit' },
  'datacentres|cpu_unit':     { application_area: 'datacentres', product_group: 'cpu_unit' },
  'datacentres|hdd_unit':     { application_area: 'datacentres', product_group: 'hdd_unit' },
  'datacentres|ssd_unit':     { application_area: 'datacentres', product_group: 'ssd_unit' },
  'datacentres|dc_port_unit': { application_area: 'datacentres', product_group: 'dc_port_unit' },
};

const SEGMENT_FALLBACK: Record<string, ApplicationArea> = {
  devices:     'households',
  networks:    'telecom_networks',
  datacentres: 'datacentres',
};

export function resolveApplicationArea(segment: string, product: string): ApplicationArea {
  const key: LegacyKey = `${segment}|${product}`;
  return LEGACY_MAP[key]?.application_area ?? SEGMENT_FALLBACK[segment] ?? 'households';
}

export function resolveProductGroup(segment: string, product: string): string {
  const key: LegacyKey = `${segment}|${product}`;
  return LEGACY_MAP[key]?.product_group ?? product;
}

// ── Row enrichment ────────────────────────────────────────────────────────────

export interface EnrichedRow extends OutputRow {
  application_area: ApplicationArea;
  product_group: string;
}

export function enrichRows(rows: OutputRow[]): EnrichedRow[] {
  return rows.map((r) => ({
    ...r,
    application_area: (r.application_area as ApplicationArea | undefined)
      ?? resolveApplicationArea(r.segment, r.product),
    product_group: r.product_group ?? resolveProductGroup(r.segment, r.product),
  }));
}

// ── Aggregation helpers ───────────────────────────────────────────────────────

/** Sum kwh_p50 (in TWh) grouped by application_area × year. */
export function aggregateByAreaYear(
  rows: EnrichedRow[],
): Record<number, Partial<Record<ApplicationArea, number>>> {
  const out: Record<number, Partial<Record<ApplicationArea, number>>> = {};
  for (const r of rows) {
    if (!out[r.year]) out[r.year] = {};
    out[r.year][r.application_area] =
      (out[r.year][r.application_area] ?? 0) + r.kwh_p50 / 1e9;
  }
  return out;
}

/** Sum kwh_p50 (in TWh) grouped by product_group × year for a given area. */
export function aggregateByProductYear(
  rows: EnrichedRow[],
  area: ApplicationArea,
): Record<number, Record<string, number>> {
  const out: Record<number, Record<string, number>> = {};
  for (const r of rows.filter((r) => r.application_area === area)) {
    if (!out[r.year]) out[r.year] = {};
    out[r.year][r.product_group] = (out[r.year][r.product_group] ?? 0) + r.kwh_p50 / 1e9;
  }
  return out;
}

/** Compute CAGR between two years for each application area. */
export function computeAreaCagr(
  byAreaYear: Record<number, Partial<Record<ApplicationArea, number>>>,
  fromYear: number,
  toYear: number,
): Partial<Record<ApplicationArea, number>> {
  const n = toYear - fromYear;
  if (n <= 0) return {};
  const result: Partial<Record<ApplicationArea, number>> = {};
  for (const area of APPLICATION_AREAS) {
    const start = byAreaYear[fromYear]?.[area] ?? 0;
    const end   = byAreaYear[toYear]?.[area]   ?? 0;
    if (start > 0) {
      result[area] = (end / start) ** (1 / n) - 1;
    }
  }
  return result;
}
