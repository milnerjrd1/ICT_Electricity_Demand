import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useCreateRun, useRunStatus, useScenarios } from '../api/hooks';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import type { RunResult } from '../types/schema';
import {
  APPLICATION_AREAS, AREA_COLORS, AREA_LABELS,
  aggregateByAreaYear, aggregateByProductYear, computeAreaCagr, enrichRows,
} from '../utils/taxonomy';
import type { ApplicationArea, EnrichedRow } from '../utils/taxonomy';

const ChoroplethMap = lazy(() => import('../components/charts/ChoroplethMap'));

const ALL_GEOS = ['US', 'DE', 'JP', 'GB', 'IE', 'NL', 'SG', 'AE'];
const GEO_COLORS = ['#00D4FF', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#84CC16', '#EC4899', '#14B8A6'];
const PROD_COLORS = ['#00D4FF', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#84CC16'];

const TOOLTIP_STYLE = { background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' };
const AXIS_TICK = { fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' };

function RunWatcher({ runId, onDone }: { runId: string; onDone: (r: RunResult) => void }) {
  const { data } = useRunStatus(runId);
  const called = useRef(false);
  const onDoneRef = useRef(onDone);
  useEffect(() => { onDoneRef.current = onDone; });
  useEffect(() => {
    if (data?.status === 'done' && data.result && !called.current) {
      called.current = true;
      onDoneRef.current(data.result);
    }
  }, [data]);
  return null;
}

export function DemandExplorer() {
  const { data: scenarioList } = useScenarios();
  const createRun = useCreateRun();
  const [scenarioId, setScenarioId] = useState('ai_base');
  const [selectedGeos, setSelectedGeos] = useState<string[]>(['US', 'DE', 'JP', 'GB', 'IE', 'NL', 'SG', 'AE']);
  const [yearRange, setYearRange] = useState<[number, number]>([2020, 2035]);
  const [activeTab, setActiveTab] = useState<'map' | 'area' | 'change' | 'drilldown' | 'geo'>('area');
  const [drillArea, setDrillArea] = useState<ApplicationArea>('datacentres');
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    setIsLoading(true);
    createRun.mutateAsync({ scenario_id: scenarioId, seed: 42 })
      .then((d) => setRunId(d.run_id))
      .catch(() => setIsLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleScenarioChange = useCallback((id: string) => {
    setScenarioId(id);
    setResult(null);
    setIsLoading(true);
    createRun.mutateAsync({ scenario_id: id, seed: 42 })
      .then((d) => setRunId(d.run_id))
      .catch(() => setIsLoading(false));
  }, [createRun]);

  const enriched = useMemo(() => enrichRows(result?.rows ?? []), [result]);

  const filteredEnriched = useMemo(
    () => enriched.filter((r) =>
      (selectedGeos.length === 0 || selectedGeos.includes(r.geo)) &&
      r.year >= yearRange[0] && r.year <= yearRange[1],
    ),
    [enriched, selectedGeos, yearRange],
  );

  const byAreaYear = useMemo(() => aggregateByAreaYear(filteredEnriched), [filteredEnriched]);
  const endYear = yearRange[1];
  const startYear = Math.max(yearRange[0], 2024);

  const areaKpis = useMemo(() => {
    const cagr = computeAreaCagr(byAreaYear, startYear, endYear);
    const totalTwh = APPLICATION_AREAS.reduce((s, a) => s + (byAreaYear[endYear]?.[a] ?? 0), 0);
    return APPLICATION_AREAS.map((area) => {
      const twh = byAreaYear[endYear]?.[area] ?? 0;
      return { area, twh, share: totalTwh > 0 ? twh / totalTwh : 0, cagr: cagr[area] };
    });
  }, [byAreaYear, endYear, startYear]);

  const TABS = [
    { id: 'area' as const,      label: '📊 By Area' },
    { id: 'change' as const,    label: '📈 Change' },
    { id: 'drilldown' as const, label: '🔍 Drill-down' },
    { id: 'geo' as const,       label: '�� By Geography' },
    { id: 'map' as const,       label: '🌍 World Map' },
  ];

  return (
    <div>
      <PageHeader title="DEMAND EXPLORER" subtitle="Fraunhofer taxonomy · 5 application areas · product group drill-down" accent="var(--accent-amber)" />
      {runId && <RunWatcher key={runId} runId={runId} onDone={(r) => { setResult(r); setIsLoading(false); }} />}

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '20px', alignItems: 'start' }}>
        <Card style={{ padding: '16px' }}>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '12px', fontWeight: 700 }}>FILTERS</div>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Scenario</label>
            <select value={scenarioId} onChange={(e) => handleScenarioChange(e.target.value)}
              style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '6px',
                color: 'var(--text-primary)', padding: '7px 10px', fontSize: '12px', fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
              {(scenarioList ?? []).map((s) => (
                <option key={s.id} value={s.id} style={{ background: 'var(--bg-elevated)' }}>{s.label}</option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              Year Range: {yearRange[0]}–{yearRange[1]}
            </label>
            <input type="range" min={2020} max={2035} value={yearRange[0]}
              onChange={(e) => setYearRange([Number(e.target.value), yearRange[1]])}
              style={{ width: '100%', marginBottom: '4px' }} />
            <input type="range" min={2020} max={2035} value={yearRange[1]}
              onChange={(e) => setYearRange([yearRange[0], Number(e.target.value)])}
              style={{ width: '100%' }} />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              Geographies ({selectedGeos.length}/{ALL_GEOS.length})
            </label>
            <div style={{ maxHeight: '260px', overflowY: 'auto' }}>
              {ALL_GEOS.map((geo) => (
                <label key={geo} style={{ display: 'flex', alignItems: 'center', gap: '7px', padding: '3px 0', cursor: 'pointer' }}>
                  <input type="checkbox" checked={selectedGeos.includes(geo)}
                    onChange={(e) => setSelectedGeos(e.target.checked ? [...selectedGeos, geo] : selectedGeos.filter((g) => g !== geo))}
                    style={{ accentColor: 'var(--accent-cyan)' }} />
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{geo}</span>
                </label>
              ))}
            </div>
          </div>
        </Card>

        <div>
          {result && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px', marginBottom: '16px' }}>
              {areaKpis.map(({ area, twh, share, cagr }) => (
                <button key={area} onClick={() => { setDrillArea(area); setActiveTab('drilldown'); }}
                  style={{ background: 'var(--bg-surface)', border: `1px solid ${AREA_COLORS[area]}33`,
                    borderTop: `2px solid ${AREA_COLORS[area]}`, borderRadius: '6px', padding: '10px 12px',
                    cursor: 'pointer', textAlign: 'left' }}>
                  <div style={{ fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '4px', textTransform: 'uppercase' }}>
                    {AREA_LABELS[area]}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: AREA_COLORS[area] }}>
                    {twh >= 1 ? `${Math.round(twh)} TWh` : '<1 TWh'}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{(share * 100).toFixed(1)}%</span>
                    {cagr != null && (
                      <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: cagr >= 0 ? '#EF4444' : '#10B981' }}>
                        {cagr >= 0 ? '+' : ''}{(cagr * 100).toFixed(1)}%/yr
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '2px', marginBottom: '16px', borderBottom: '1px solid var(--border)' }}>
            {TABS.map(({ id, label }) => (
              <button key={id} onClick={() => setActiveTab(id)}
                style={{ padding: '8px 14px', background: 'none', border: 'none',
                  borderBottom: activeTab === id ? '2px solid var(--accent-amber)' : '2px solid transparent',
                  color: activeTab === id ? 'var(--accent-amber)' : 'var(--text-secondary)', cursor: 'pointer',
                  fontSize: '12px', fontWeight: activeTab === id ? 600 : 400, fontFamily: 'var(--font-sans)',
                  marginBottom: '-1px', transition: 'all 0.15s' }}>
                {label}
              </button>
            ))}
          </div>

          {isLoading && !result && (
            <Card style={{ padding: '60px', textAlign: 'center' }}>
              <div style={{ width: '32px', height: '32px', border: '3px solid var(--border)', borderTopColor: 'var(--accent-amber)',
                borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: 0 }}>Loading data...</p>
            </Card>
          )}

          {result && activeTab === 'area' && <AreaChart rows={filteredEnriched} yearRange={yearRange} />}
          {result && activeTab === 'change' && <ChangeChart byAreaYear={byAreaYear} fromYear={startYear} toYear={endYear} />}
          {result && activeTab === 'drilldown' && (
            <DrilldownChart rows={filteredEnriched} activeArea={drillArea} onAreaChange={setDrillArea} yearRange={yearRange} />
          )}
          {result && activeTab === 'geo' && <GeoChart rows={filteredEnriched} selectedGeos={selectedGeos} />}
          {result && activeTab === 'map' && (
            <Card style={{ padding: '16px' }}>
              <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                ICT Electricity Intensity — {yearRange[1]}
              </h3>
              <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>Total ICT TWh by geography</p>
              <Suspense fallback={<div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>Loading map...</div>}>
                <ChoroplethMap rows={result.rows} year={yearRange[1]} />
              </Suspense>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function AreaChart({ rows, yearRange }: { rows: EnrichedRow[]; yearRange: [number, number] }) {
  const byAreaYear = useMemo(() => aggregateByAreaYear(rows), [rows]);
  const years = useMemo(
    () => [...new Set(rows.map((r) => r.year))].sort((a, b) => a - b).filter((y) => y >= yearRange[0] && y <= yearRange[1]),
    [rows, yearRange],
  );
  const data = years.map((year) => {
    const pt: Record<string, number> = { year };
    for (const area of APPLICATION_AREAS) pt[area] = Math.round((byAreaYear[year]?.[area] ?? 0) * 10) / 10;
    return pt;
  });

  return (
    <Card>
      <h3 style={{ margin: '0 0 2px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>ICT Electricity by Application Area</h3>
      <p style={{ margin: '0 0 12px', fontSize: '11px', color: 'var(--text-secondary)' }}>P50 · TWh · click a KPI card to drill down into product groups</p>
      <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginBottom: '12px' }}>
        {APPLICATION_AREAS.map((area) => (
          <div key={area} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '14px', height: '3px', background: AREA_COLORS[area], borderRadius: '2px' }} />
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{AREA_LABELS[area]}</span>
          </div>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="year" tick={AXIS_TICK} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={55}
            label={{ value: 'TWh', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 10, dy: 20 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE}
            formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, AREA_LABELS[name as ApplicationArea] ?? String(name)]} />
          {APPLICATION_AREAS.map((area) => (
            <Line key={area} type="monotone" dataKey={area} stroke={AREA_COLORS[area]} strokeWidth={2.5} dot={false} name={area} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

function ChangeChart({
  byAreaYear, fromYear, toYear,
}: {
  byAreaYear: Record<number, Partial<Record<ApplicationArea, number>>>;
  fromYear: number;
  toYear: number;
}) {
  const data = useMemo(() => {
    const cagr = computeAreaCagr(byAreaYear, fromYear, toYear);
    return APPLICATION_AREAS.map((area) => ({
      area: AREA_LABELS[area],
      cagr_pct: cagr[area] != null ? Math.round(cagr[area]! * 1000) / 10 : 0,
      delta_twh: Math.round(((byAreaYear[toYear]?.[area] ?? 0) - (byAreaYear[fromYear]?.[area] ?? 0)) * 10) / 10,
      color: AREA_COLORS[area],
    })).sort((a, b) => b.cagr_pct - a.cagr_pct);
  }, [byAreaYear, fromYear, toYear]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
      <Card>
        <h3 style={{ margin: '0 0 2px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>CAGR by Application Area</h3>
        <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>{fromYear}→{toYear} · compound annual growth rate</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ ...AXIS_TICK, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
            <YAxis type="category" dataKey="area" tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-sans)' }} axisLine={false} tickLine={false} width={110} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${Number(v).toFixed(1)}%/yr`, 'CAGR']} />
            <Bar dataKey="cagr_pct" radius={[0, 3, 3, 0]}>
              {data.map((d) => <Cell key={d.area} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
      <Card>
        <h3 style={{ margin: '0 0 2px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Absolute Change by Area</h3>
        <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>{fromYear}→{toYear} · TWh delta</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ ...AXIS_TICK, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v} TWh`} />
            <YAxis type="category" dataKey="area" tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-sans)' }} axisLine={false} tickLine={false} width={110} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${Number(v).toLocaleString()} TWh`, 'Δ TWh']} />
            <Bar dataKey="delta_twh" radius={[0, 3, 3, 0]}>
              {data.map((d) => <Cell key={d.area} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}

function DrilldownChart({
  rows, activeArea, onAreaChange, yearRange,
}: {
  rows: EnrichedRow[];
  activeArea: ApplicationArea;
  onAreaChange: (a: ApplicationArea) => void;
  yearRange: [number, number];
}) {
  const byProductYear = useMemo(() => aggregateByProductYear(rows, activeArea), [rows, activeArea]);
  const years = useMemo(
    () => [...new Set(rows.map((r) => r.year))].sort((a, b) => a - b).filter((y) => y >= yearRange[0] && y <= yearRange[1]),
    [rows, yearRange],
  );
  const products = useMemo(
    () => [...new Set(rows.filter((r) => r.application_area === activeArea).map((r) => r.product_group))],
    [rows, activeArea],
  );
  const data = years.map((year) => {
    const pt: Record<string, number> = { year };
    for (const pg of products) pt[pg] = Math.round((byProductYear[year]?.[pg] ?? 0) * 10) / 10;
    return pt;
  });

  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0, fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Product Group Breakdown</h3>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {APPLICATION_AREAS.map((area) => (
            <button key={area} onClick={() => onAreaChange(area)}
              style={{ padding: '4px 10px', borderRadius: '4px',
                border: `1px solid ${area === activeArea ? AREA_COLORS[area] : 'var(--border)'}`,
                background: area === activeArea ? `${AREA_COLORS[area]}18` : 'transparent',
                color: area === activeArea ? AREA_COLORS[area] : 'var(--text-muted)',
                fontSize: '11px', cursor: 'pointer', fontFamily: 'var(--font-sans)', fontWeight: area === activeArea ? 600 : 400 }}>
              {AREA_LABELS[area]}
            </button>
          ))}
        </div>
      </div>
      <p style={{ margin: '0 0 12px', fontSize: '11px', color: 'var(--text-secondary)' }}>
        P50 · TWh · {AREA_LABELS[activeArea]}
        {activeArea === 'public_spaces' && (
          <span style={{ color: 'var(--text-muted)', marginLeft: '8px' }}>(no synthetic products mapped — available in Phase 1)</span>
        )}
      </p>
      {products.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
          No product groups available for this area in the current scenario.
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {products.map((pg, i) => (
              <div key={pg} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: PROD_COLORS[i % PROD_COLORS.length] }} />
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{pg.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="year" tick={AXIS_TICK} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
              <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={55}
                label={{ value: 'TWh', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 10, dy: 20 }} />
              <Tooltip contentStyle={TOOLTIP_STYLE}
                formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name).replace(/_/g, ' ')]} />
              {products.map((pg, i) => (
                <Line key={pg} type="monotone" dataKey={pg} stroke={PROD_COLORS[i % PROD_COLORS.length]} strokeWidth={2} dot={false} name={pg} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </Card>
  );
}

function GeoChart({ rows, selectedGeos }: { rows: EnrichedRow[]; selectedGeos: string[] }) {
  const byYear: Record<number, Record<string, number>> = {};
  for (const r of rows) {
    if (!byYear[r.year]) byYear[r.year] = { year: r.year };
    byYear[r.year][r.geo] = (byYear[r.year][r.geo] ?? 0) + r.kwh_p50 / 1e9;
  }
  const data = Object.values(byYear).sort((a, b) => a.year - b.year).map((pt) => {
    const rec: Record<string, number> = { year: pt.year };
    for (const [k, v] of Object.entries(pt)) if (k !== 'year') rec[k] = Math.round(v * 10) / 10;
    return rec;
  });

  return (
    <Card>
      <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>ICT Electricity by Geography</h3>
      <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>P50 · TWh · all application areas combined</p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="year" tick={AXIS_TICK} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={55} />
          <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name)]} />
          {selectedGeos.slice(0, 10).map((geo, i) => (
            <Line key={geo} type="monotone" dataKey={geo} stroke={GEO_COLORS[i % GEO_COLORS.length]} strokeWidth={1.5} dot={false} name={geo} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
