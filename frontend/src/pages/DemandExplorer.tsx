import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useCreateRun, useRunStatus, useScenarios } from '../api/hooks';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import type { OutputRow, RunResult } from '../types/schema';

const ChoroplethMap = lazy(() => import('../components/charts/ChoroplethMap'));

const SEGMENT_COLORS: Record<string, string> = {
  datacentres: '#EF4444',
  networks: '#F59E0B',
  devices: '#10B981',
};

const ALL_GEOS = ['US', 'CN', 'DE', 'JP', 'GB', 'FR', 'IN', 'CA', 'AU', 'NL', 'IE', 'SG', 'KR', 'SE', 'BR', 'AE', 'SA', 'PL', 'MY', 'ZA'];

function RunWatcher({ runId, onDone }: { runId: string; onDone: (r: RunResult) => void }) {
  const { data } = useRunStatus(runId);
  const called = useRef(false);
  useEffect(() => {
    if (data?.status === 'done' && data.result && !called.current) {
      called.current = true;
      onDone(data.result);
    }
  }, [data, onDone]);
  return null;
}

export function DemandExplorer() {
  const { data: scenarioList } = useScenarios();
  const createRun = useCreateRun();
  const [scenarioId, setScenarioId] = useState('ai_base');
  const [selectedGeos, setSelectedGeos] = useState<string[]>(['US', 'CN', 'DE', 'JP', 'GB', 'IN', 'IE', 'NL', 'SG']);
  const [yearRange, setYearRange] = useState<[number, number]>([2020, 2035]);
  const [activeTab, setActiveTab] = useState<'map' | 'segment' | 'geo' | 'product'>('map');
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    createRun.mutate({ scenario_id: scenarioId, seed: 42 }, {
      onSuccess: (d) => setRunId(d.run_id),
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleScenarioChange = (id: string) => {
    setScenarioId(id);
    setResult(null);
    createRun.mutate({ scenario_id: id, seed: 42 }, { onSuccess: (d) => setRunId(d.run_id) });
  };

  const filteredRows: OutputRow[] = (result?.rows ?? []).filter((r) =>
    (selectedGeos.length === 0 || selectedGeos.includes(r.geo)) &&
    r.year >= yearRange[0] && r.year <= yearRange[1],
  );

  return (
    <div>
      <PageHeader title="DEMAND EXPLORER" subtitle="Drill down by geography · segment · product · year" accent="var(--accent-amber)" />
      {runId && <RunWatcher runId={runId} onDone={setResult} />}

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '20px', alignItems: 'start' }}>
        {/* Sidebar filters */}
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
            <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
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

        {/* Main content */}
        <div>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '0' }}>
            {(['map', 'segment', 'geo', 'product'] as const).map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                style={{ padding: '8px 16px', background: 'none', border: 'none', borderBottom: activeTab === tab ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                  color: activeTab === tab ? 'var(--accent-cyan)' : 'var(--text-secondary)', cursor: 'pointer',
                  fontSize: '12px', fontWeight: activeTab === tab ? 600 : 400, fontFamily: 'var(--font-sans)',
                  marginBottom: '-1px', transition: 'all 0.15s' }}>
                {tab === 'map' ? '🌍 World Map' : tab === 'segment' ? 'By Segment' : tab === 'geo' ? 'By Geography' : 'By Product'}
              </button>
            ))}
          </div>

          {createRun.isPending && !result && (
            <Card style={{ padding: '60px', textAlign: 'center' }}>
              <div style={{ width: '32px', height: '32px', border: '3px solid var(--border)', borderTopColor: 'var(--accent-cyan)',
                borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: 0 }}>Loading data...</p>
            </Card>
          )}

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

          {result && activeTab === 'segment' && (
            <SegmentChart rows={filteredRows} />
          )}

          {result && activeTab === 'geo' && (
            <GeoChart rows={filteredRows} selectedGeos={selectedGeos} />
          )}

          {result && activeTab === 'product' && (
            <ProductChart rows={filteredRows} />
          )}
        </div>
      </div>
    </div>
  );
}

function SegmentChart({ rows }: { rows: OutputRow[] }) {
  const byYear: Record<number, Record<string, number>> = {};
  for (const r of rows) {
    if (!byYear[r.year]) byYear[r.year] = { year: r.year };
    byYear[r.year][r.segment] = (byYear[r.year][r.segment] ?? 0) + r.kwh_p50 / 1e9;
  }
  const data = Object.values(byYear).sort((a, b) => a.year - b.year).map((pt) => {
    const r: Record<string, number> = { year: pt.year };
    for (const [k, v] of Object.entries(pt)) if (k !== 'year') r[k] = Math.round(v);
    return r;
  });

  return (
    <Card>
      <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>ICT Electricity by Segment</h3>
      <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>P50 · TWh</p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
          <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={60} />
          <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
            formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name)]} />
          {['datacentres', 'networks', 'devices'].map((seg) => (
            <Line key={seg} type="monotone" dataKey={seg} stroke={SEGMENT_COLORS[seg]} strokeWidth={2.5} dot={false} name={seg} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

function GeoChart({ rows, selectedGeos }: { rows: OutputRow[]; selectedGeos: string[] }) {
  const byYear: Record<number, Record<string, number>> = {};
  for (const r of rows) {
    if (!byYear[r.year]) byYear[r.year] = { year: r.year };
    byYear[r.year][r.geo] = (byYear[r.year][r.geo] ?? 0) + r.kwh_p50 / 1e9;
  }
  const data = Object.values(byYear).sort((a, b) => a.year - b.year).map((pt) => {
    const r: Record<string, number> = { year: pt.year };
    for (const [k, v] of Object.entries(pt)) if (k !== 'year') r[k] = Math.round(v * 10) / 10;
    return r;
  });

  const GEO_COLORS = ['#00D4FF', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#84CC16', '#EC4899', '#14B8A6'];

  return (
    <Card>
      <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>ICT Electricity by Geography</h3>
      <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>P50 · TWh</p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
          <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={60} />
          <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
            formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name)]} />
          {selectedGeos.slice(0, 10).map((geo, i) => (
            <Line key={geo} type="monotone" dataKey={geo} stroke={GEO_COLORS[i % GEO_COLORS.length]} strokeWidth={1.5} dot={false} name={geo} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

function ProductChart({ rows }: { rows: OutputRow[] }) {
  const products = [...new Set(rows.map((r) => r.product))].slice(0, 8);
  const byYear: Record<number, Record<string, number>> = {};
  for (const r of rows) {
    if (!byYear[r.year]) byYear[r.year] = { year: r.year };
    byYear[r.year][r.product] = (byYear[r.year][r.product] ?? 0) + r.kwh_p50 / 1e9;
  }
  const data = Object.values(byYear).sort((a, b) => a.year - b.year).map((pt) => {
    const r: Record<string, number> = { year: pt.year };
    for (const [k, v] of Object.entries(pt)) if (k !== 'year') r[k] = Math.round(v * 10) / 10;
    return r;
  });

  const PROD_COLORS = ['#00D4FF', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#84CC16'];

  return (
    <Card>
      <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>ICT Electricity by Product</h3>
      <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>P50 · TWh</p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
          <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={60} />
          <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
            formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name)]} />
          {products.map((prod, i) => (
            <Line key={prod} type="monotone" dataKey={prod} stroke={PROD_COLORS[i % PROD_COLORS.length]} strokeWidth={1.5} dot={false} name={prod} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
