import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useCreateRun, useRunStatus, useScenarios } from '../api/hooks';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { useScenarioStore } from '../store/scenarioStore';
import type { RunResult } from '../types/schema';
import {
  APPLICATION_AREAS, AREA_COLORS, AREA_LABELS, aggregateByAreaYear, enrichRows,
} from '../utils/taxonomy';
import type { ApplicationArea } from '../utils/taxonomy';

function SliderField({ label, description, value, min, max, step, format, onChange }: {
  label: string; description: string; value: number; min: number; max: number;
  step: number; format: (v: number) => string; onChange: (v: number) => void;
}) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
        <div>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px' }}>{description}</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
          {format(value)}
        </span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: '100%', height: '4px', cursor: 'pointer' }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{format(min)}</span>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{format(max)}</span>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.12em', color: 'var(--accent-cyan)',
      textTransform: 'uppercase', marginBottom: '12px', marginTop: '20px',
      paddingBottom: '6px', borderBottom: '1px solid var(--border)' }}>
      {children}
    </div>
  );
}

function RunWatcher({ runId, onDone }: { runId: string; onDone: (r: RunResult) => void }) {
  const { data } = useRunStatus(runId);
  const called = useRef(false);
  // Stable ref so the effect only re-fires when data changes, not on every
  // parent render that recreates the inline onDone arrow function.
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

function KpiMini({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ background: 'var(--bg-surface)', border: `1px solid ${color}33`,
      borderTop: `2px solid ${color}`, borderRadius: '6px', padding: '12px 14px' }}>
      <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function buildYearlyComparison(allResults: { label: string; result: RunResult }[]) {
  const byYear: Record<number, Record<string, number>> = {};
  for (const { label, result } of allResults) {
    for (const row of result.rows) {
      if (!byYear[row.year]) byYear[row.year] = { year: row.year };
      byYear[row.year][label] = (byYear[row.year][label] ?? 0) + row.kwh_p50 / 1e9;
    }
  }
  return Object.values(byYear).sort((a, b) => a.year - b.year).map((pt) => {
    const r: Record<string, number> = { year: pt.year };
    for (const [k, v] of Object.entries(pt)) if (k !== 'year') r[k] = Math.round(v);
    return r;
  });
}

function buildDelta(result: RunResult, baseline: RunResult) {
  const base: Record<number, number> = {};
  for (const row of baseline.rows) base[row.year] = (base[row.year] ?? 0) + row.kwh_p50 / 1e9;
  const res: Record<number, number> = {};
  for (const row of result.rows) res[row.year] = (res[row.year] ?? 0) + row.kwh_p50 / 1e9;
  return Object.entries(res).sort(([a], [b]) => Number(a) - Number(b)).map(([year, twh]) => {
    const b = base[Number(year)] ?? 1;
    return { year: Number(year), delta_pct: Math.round(((twh - b) / b) * 1000) / 10 };
  });
}

function buildDcUncertainty(result: RunResult) {
  const by: Record<number, { p10: number; p50: number; p90: number }> = {};
  for (const row of result.rows.filter((r) => r.segment === 'datacentres')) {
    if (!by[row.year]) by[row.year] = { p10: 0, p50: 0, p90: 0 };
    by[row.year].p10 += row.kwh_p10 / 1e9;
    by[row.year].p50 += row.kwh_p50 / 1e9;
    by[row.year].p90 += row.kwh_p90 / 1e9;
  }
  return Object.entries(by).sort(([a], [b]) => Number(a) - Number(b)).map(([year, v]) => ({
    year: Number(year), p10: Math.round(v.p10), p50: Math.round(v.p50), p90: Math.round(v.p90),
  }));
}

function ResultsPanel({ result, baselineResult, savedScenarios }: {
  result: RunResult;
  baselineResult: RunResult | null;
  savedScenarios: { label: string; color: string; result: RunResult | null }[];
}) {
  const s = result.summary;
  const allResults = [
    { label: result.model_card.scenario_id, color: '#00D4FF', result },
    ...savedScenarios.filter((sc) => sc.result).map((sc) => ({ label: sc.label, color: sc.color, result: sc.result! })),
  ];
  const compData = buildYearlyComparison(allResults);
  const deltaData = baselineResult ? buildDelta(result, baselineResult) : [];
  const dcData = buildDcUncertainty(result);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        <KpiMini label="Total ICT" value={`${s.total_twh.toLocaleString()} TWh`} color="var(--accent-cyan)" />
        <KpiMini label="DC Share" value={`${(s.dc_share * 100).toFixed(1)}%`} color="var(--accent-red)" />
        <KpiMini label="Emissions" value={`${s.total_emissions_mtco2e.toLocaleString()} MtCO₂e`} color="var(--accent-amber)" />
      </div>

      <Card>
        <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Scenario Comparison — Total ICT Electricity</h3>
        <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>P50 · TWh · selected years</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={compData.filter((d) => [2013,2018,2023,2025,2027,2030,2033,2035].includes(d.year))} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={55} tickFormatter={(v) => `${v}`} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
              formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name)]} />
            {allResults.map((r) => (
              <Bar key={r.label} dataKey={r.label} fill={r.color} radius={[3, 3, 0, 0]} maxBarSize={40} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Delta vs AI Base — %</h3>
        <p style={{ margin: '0 0 12px', fontSize: '11px', color: 'var(--text-secondary)' }}>
          {baselineResult ? 'Positive = higher demand than AI Base baseline' : 'Loading baseline…'}
        </p>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart
            data={deltaData.length > 0 ? deltaData.filter((d) => [2013,2018,2023,2025,2027,2030,2033,2035].includes(d.year)) : []}
            margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={45} tickFormatter={(v) => `${v}%`} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
              formatter={(v) => [`${Number(v).toFixed(1)}%`, 'Delta vs AI Base']} />
            <Bar dataKey="delta_pct" radius={[2, 2, 0, 0]} maxBarSize={40}>
              {(deltaData.filter((d) => [2013,2018,2023,2025,2027,2030,2033,2035].includes(d.year))).map((entry, i) => (
                <Cell key={i} fill={entry.delta_pct >= 0 ? 'var(--accent-red)' : 'var(--accent-green)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Data Centre Electricity — P10 / P50 / P90</h3>
        <p style={{ margin: '0 0 12px', fontSize: '11px', color: 'var(--text-secondary)' }}>Uncertainty band · TWh</p>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={dcData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={55} />
            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
              formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name)]} />
            <Line type="monotone" dataKey="p90" stroke="rgba(239,68,68,0.3)" strokeWidth={1} dot={false} strokeDasharray="4 2" name="P90" />
            <Line type="monotone" dataKey="p50" stroke="var(--accent-red)" strokeWidth={2.5} dot={false} name="P50" />
            <Line type="monotone" dataKey="p10" stroke="rgba(239,68,68,0.3)" strokeWidth={1} dot={false} strokeDasharray="4 2" name="P10" />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <h3 style={{ margin: '0 0 12px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Key Outputs — {s.latest_year}</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {['Segment', 'TWh', 'Share', 'Emissions MtCO₂e'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--text-muted)', fontWeight: 600, fontSize: '10px', letterSpacing: '0.08em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              { seg: 'Data Centres', twh: s.dc_twh, share: s.dc_share, color: 'var(--accent-red)' },
              { seg: 'Devices', twh: s.devices_twh, share: s.devices_twh / s.total_twh, color: 'var(--accent-green)' },
              { seg: 'Networks', twh: s.networks_twh, share: s.networks_twh / s.total_twh, color: 'var(--accent-amber)' },
            ].map((row) => (
              <tr key={row.seg} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '8px', color: row.color, fontWeight: 600 }}>{row.seg}</td>
                <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{row.twh.toLocaleString()}</td>
                <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>{(row.share * 100).toFixed(1)}%</td>
                <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{(s.total_emissions_mtco2e * row.share).toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <AreaBreakdownPanel result={result} baselineResult={baselineResult} />

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <Badge color="var(--accent-cyan)">v{result.model_card.model_version}</Badge>
        <Badge color="var(--accent-green)">{result.model_card.engine}</Badge>
        <Badge color="var(--text-muted)">seed:{result.model_card.seed}</Badge>
        <Badge color="var(--text-muted)">hash:{result.model_card.assumptions_hash}</Badge>
      </div>
    </div>
  );
}

function AreaBreakdownPanel({ result, baselineResult }: { result: RunResult; baselineResult: RunResult | null }) {
  const endYear = result.summary.latest_year;

  const areaShares = useMemo(() => {
    const enriched = enrichRows(result.rows);
    const byAreaYear = aggregateByAreaYear(enriched);
    const totalTwh = APPLICATION_AREAS.reduce((s, a) => s + (byAreaYear[endYear]?.[a] ?? 0), 0);
    return APPLICATION_AREAS.map((area) => {
      const twh = byAreaYear[endYear]?.[area] ?? 0;
      return { area, twh, share: totalTwh > 0 ? twh / totalTwh : 0 };
    }).sort((a, b) => b.twh - a.twh);
  }, [result, endYear]);

  const baselineTwhByArea = useMemo(() => {
    if (!baselineResult) return null;
    const enriched = enrichRows(baselineResult.rows);
    const byAreaYear = aggregateByAreaYear(enriched);
    const map: Partial<Record<ApplicationArea, number>> = {};
    for (const area of APPLICATION_AREAS) {
      map[area] = byAreaYear[endYear]?.[area] ?? 0;
    }
    return map;
  }, [baselineResult, endYear]);

  const barData = areaShares.map(({ area, twh }) => ({
    area: AREA_LABELS[area],
    twh: Math.round(twh * 10) / 10,
    baseline_twh: baselineTwhByArea ? Math.round((baselineTwhByArea[area] ?? 0) * 10) / 10 : null,
    color: AREA_COLORS[area],
  }));

  return (
    <Card>
      <h3 style={{ margin: '0 0 2px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
        Area Breakdown — {endYear}
      </h3>
      <p style={{ margin: '0 0 14px', fontSize: '11px', color: 'var(--text-secondary)' }}>
        TWh · Fraunhofer taxonomy{baselineResult ? ' · grey = AI Base' : ''}
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={barData} layout="vertical" margin={{ top: 0, right: 50, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
            axisLine={false} tickLine={false} tickFormatter={(v) => `${v}`} />
          <YAxis type="category" dataKey="area"
            tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-sans)' }}
            axisLine={false} tickLine={false} width={115} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
            formatter={(v, name) => [
              `${Number(v).toFixed(1)} TWh`,
              name === 'twh' ? 'Current' : 'AI Base',
            ]}
          />
          {baselineResult && (
            <Bar dataKey="baseline_twh" fill="rgba(156,163,175,0.35)" radius={[0, 3, 3, 0]} barSize={6} />
          )}
          <Bar dataKey="twh" radius={[0, 4, 4, 0]} barSize={baselineResult ? 14 : 20}>
            {barData.map((d) => <Cell key={d.area} fill={d.color} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function ScenarioBuilder() {
  const { data: scenarioList } = useScenarios();
  const { activeScenarioId, activeParams, isStale, setActiveScenarioId, updateParam,
    setCurrentRunId, savedScenarios, saveScenario, removeScenario } = useScenarioStore();
  const createRun = useCreateRun();
  const [currentRunId, setLocalRunId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [saveLabel, setSaveLabel] = useState('');
  const [showSaveInput, setShowSaveInput] = useState(false);
  const [latestResult, setLatestResult] = useState<RunResult | null>(null);
  const [baselineResult, setBaselineResult] = useState<RunResult | null>(null);
  const [baselineRunId, setBaselineRunId] = useState<string | null>(null);
  const baselineLoaded = useRef(false);

  useEffect(() => {
    if (baselineLoaded.current) return;
    baselineLoaded.current = true;
    createRun.mutateAsync({ scenario_id: 'ai_base', seed: 42 })
      .then((d) => setBaselineRunId(d.run_id))
      .catch(() => { /* baseline failure is non-fatal */ });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRun = useCallback(async () => {
    setIsRunning(true);
    try {
      const d = await createRun.mutateAsync(activeParams);
      setLocalRunId(d.run_id);
      setCurrentRunId(d.run_id);
    } catch {
      setIsRunning(false);
    }
  }, [activeParams, createRun, setCurrentRunId]);

  const handleSave = () => {
    if (!latestResult || !saveLabel.trim()) return;
    saveScenario(saveLabel.trim(), activeParams, latestResult);
    setSaveLabel(''); setShowSaveInput(false);
  };

  return (
    <div>
      <PageHeader title="SCENARIO BUILDER" subtitle="Configure assumptions · run model · compare outcomes" accent="var(--accent-green)" />
      {baselineRunId && (
        <RunWatcher runId={baselineRunId} onDone={(r) => {
          setBaselineResult(r);
        }} />
      )}
      {currentRunId && (
        <RunWatcher runId={currentRunId} onDone={(r) => {
          setLatestResult(r);
          setIsRunning(false);
        }} />
      )}
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '20px', alignItems: 'start' }}>
        {/* Left: controls */}
        <div>
          <Card style={{ padding: '20px' }}>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', display: 'block', marginBottom: '6px' }}>BASE SCENARIO</label>
              <select value={activeScenarioId} onChange={(e) => setActiveScenarioId(e.target.value)}
                style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '6px',
                  color: 'var(--text-primary)', padding: '8px 12px', fontSize: '13px', fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
                {(scenarioList ?? []).map((s) => (
                  <option key={s.id} value={s.id} style={{ background: 'var(--bg-elevated)' }}>{s.label}</option>
                ))}
              </select>
            </div>
            {isStale && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px',
                background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '6px', marginBottom: '16px' }}>
                <span style={{ fontSize: '14px' }}>⚠</span>
                <span style={{ fontSize: '12px', color: 'var(--accent-amber)' }}>Results stale — click Run to update</span>
              </div>
            )}
            <SectionLabel>Data Centres</SectionLabel>
            <SliderField label="AI Growth Rate" description="annual" value={activeParams.ai_growth_rate ?? 0.20}
              min={0} max={1} step={0.01} format={(v) => `${(v * 100).toFixed(0)}%`} onChange={(v) => updateParam('ai_growth_rate', v)} />
            <SliderField label="PUE Improvement" description="annual" value={activeParams.pue_improvement_rate ?? 0.02}
              min={0} max={0.15} step={0.005} format={(v) => `${(v * 100).toFixed(1)}%`} onChange={(v) => updateParam('pue_improvement_rate', v)} />
            <SliderField label="DC Utilisation" description="multiplier" value={activeParams.utilisation_multiplier ?? 1.0}
              min={0.5} max={2.0} step={0.05} format={(v) => `${v.toFixed(2)}×`} onChange={(v) => updateParam('utilisation_multiplier', v)} />
            <SectionLabel>Devices</SectionLabel>
            <SliderField label="Lifespan Multiplier" description="vs baseline" value={activeParams.avg_lifespan_multiplier ?? 1.0}
              min={0.5} max={2.0} step={0.05} format={(v) => `${v.toFixed(2)}×`} onChange={(v) => updateParam('avg_lifespan_multiplier', v)} />
            <SectionLabel>Networks</SectionLabel>
            <SliderField label="Power Efficiency" description="factor" value={activeParams.power_efficiency_factor ?? 1.0}
              min={0.5} max={1.5} step={0.05} format={(v) => `${v.toFixed(2)}×`} onChange={(v) => updateParam('power_efficiency_factor', v)} />
            <div style={{ marginTop: '20px', display: 'flex', gap: '8px' }}>
              <Button onClick={handleRun} loading={isRunning} disabled={isRunning} style={{ flex: 1, justifyContent: 'center' }}>
                {isRunning ? 'Running...' : '▶ RUN SCENARIO'}
              </Button>
            </div>
            {latestResult && (
              <div style={{ marginTop: '12px' }}>
                {showSaveInput ? (
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <input value={saveLabel} onChange={(e) => setSaveLabel(e.target.value)} placeholder="Scenario name..."
                      onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                      style={{ flex: 1, background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '6px',
                        color: 'var(--text-primary)', padding: '6px 10px', fontSize: '12px', fontFamily: 'var(--font-sans)' }} />
                    <Button size="sm" onClick={handleSave} disabled={!saveLabel.trim()}>Save</Button>
                    <Button size="sm" variant="ghost" onClick={() => setShowSaveInput(false)}>✕</Button>
                  </div>
                ) : (
                  <Button variant="secondary" size="sm" onClick={() => setShowSaveInput(true)}
                    disabled={savedScenarios.length >= 4} style={{ width: '100%', justifyContent: 'center' }}>
                    + Save Scenario {savedScenarios.length >= 4 ? '(max 4)' : ''}
                  </Button>
                )}
              </div>
            )}
          </Card>
          {savedScenarios.length > 0 && (
            <Card style={{ marginTop: '12px', padding: '16px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '12px' }}>SAVED SCENARIOS</div>
              {savedScenarios.map((sc) => (
                <div key={sc.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 10px', background: 'var(--bg-elevated)', borderLeft: `3px solid ${sc.color}`,
                  borderRadius: '4px', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: sc.color }} />
                    <span style={{ fontSize: '12px', color: 'var(--text-primary)' }}>{sc.label}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: sc.color }}>
                      {sc.result?.summary?.total_twh?.toLocaleString()} TWh
                    </span>
                    <button onClick={() => removeScenario(sc.id)}
                      style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '14px', padding: '0 2px' }}>✕</button>
                  </div>
                </div>
              ))}
            </Card>
          )}
        </div>
        {/* Right: results */}
        <div>
          {latestResult ? (
            <ResultsPanel result={latestResult} baselineResult={baselineResult} savedScenarios={savedScenarios} />
          ) : (
            <Card style={{ padding: '60px 20px', textAlign: 'center' }}>
              <div style={{ fontSize: '32px', marginBottom: '12px', opacity: 0.3 }}>▶</div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
                Configure assumptions and click <strong>RUN SCENARIO</strong> to see results
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
