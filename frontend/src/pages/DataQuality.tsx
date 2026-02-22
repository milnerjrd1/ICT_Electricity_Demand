import { useEffect, useRef, useState } from 'react';
import { useCreateRun, useRunStatus, useScenarios } from '../api/hooks';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import type { OutputRow, RunResult } from '../types/schema';

const TIER_META = {
  1: { label: 'TIER 1 — HIGH', color: '#10B981', band: '±10%', desc: 'Official statistics / regulator data. >80% segment coverage. 3+ independent sources agree within 15%.' },
  2: { label: 'TIER 2 — MEDIUM', color: '#F59E0B', band: '±20%', desc: 'Industry reports / surveys. 40–80% coverage. 2 sources agree within 25%.' },
  3: { label: 'TIER 3 — LOW', color: '#EF4444', band: '±35%', desc: 'Estimates / proxies. <40% coverage or single source. High sensitivity to assumptions.' },
} as const;

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

export function DataQuality() {
  const { data: scenarioList } = useScenarios();
  const createRun = useCreateRun();
  const [scenarioId, setScenarioId] = useState('ai_base');
  const [year, setYear] = useState(2035);
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    createRun.mutateAsync({ scenario_id: scenarioId, seed: 42 })
      .then((d) => setRunId(d.run_id))
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const yearRows: OutputRow[] = (result?.rows ?? []).filter((r) => r.year === year);

  // Tier stats
  const tierStats = ([1, 2, 3] as const).map((tier) => {
    const rows = yearRows.filter((r) => r.confidence_tier === tier);
    return {
      tier,
      count: rows.length,
      twh: rows.reduce((s, r) => s + r.kwh_p50 / 1e9, 0),
    };
  });

  // Heatmap: geo × segment → avg confidence tier
  const geos = [...new Set(yearRows.map((r) => r.geo))].sort();
  const segments = ['datacentres', 'networks', 'devices'];
  const heatmap: Record<string, Record<string, number>> = {};
  for (const r of yearRows) {
    if (!heatmap[r.geo]) heatmap[r.geo] = {};
    if (!heatmap[r.geo][r.segment]) heatmap[r.geo][r.segment] = r.confidence_tier;
  }

  // Geo confidence ranking
  const geoConf = geos.map((geo) => {
    const rows = yearRows.filter((r) => r.geo === geo);
    const avg = rows.reduce((s, r) => s + r.confidence_tier, 0) / (rows.length || 1);
    return { geo, avg };
  }).sort((a, b) => a.avg - b.avg);

  const tierColor = (t: number) => t <= 1.5 ? '#10B981' : t <= 2.5 ? '#F59E0B' : '#EF4444';

  return (
    <div>
      <PageHeader title="DATA QUALITY" subtitle="Confidence tiers · source coverage · uncertainty bands" accent="var(--accent-green)" />
      {runId && <RunWatcher runId={runId} onDone={(r) => setResult(r)} />}

      {/* Controls */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'center' }}>
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Scenario</label>
          <select value={scenarioId} onChange={(e) => {
            setScenarioId(e.target.value); setResult(null);
            createRun.mutateAsync({ scenario_id: e.target.value, seed: 42 })
              .then((d) => setRunId(d.run_id))
              .catch(() => {});
          }} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px',
            color: 'var(--text-primary)', padding: '7px 12px', fontSize: '12px', fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
            {(scenarioList ?? []).map((s) => <option key={s.id} value={s.id} style={{ background: 'var(--bg-elevated)' }}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Year</label>
          <select value={year} onChange={(e) => setYear(Number(e.target.value))}
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px',
              color: 'var(--text-primary)', padding: '7px 12px', fontSize: '12px', fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
            {Array.from({ length: 16 }, (_, i) => 2020 + i).map((y) => (
              <option key={y} value={y} style={{ background: 'var(--bg-elevated)' }}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Tier cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
        {tierStats.map(({ tier, count, twh }) => {
          const meta = TIER_META[tier];
          return (
            <Card key={tier} accent={meta.color}>
              <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.12em', color: meta.color, marginBottom: '8px' }}>
                {meta.label}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '26px', fontWeight: 700, color: meta.color, marginBottom: '4px' }}>
                {count.toLocaleString()} cells
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                {Math.round(twh).toLocaleString()} TWh · uncertainty {meta.band}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.55, borderTop: `1px solid ${meta.color}22`, paddingTop: '8px' }}>
                {meta.desc}
              </div>
            </Card>
          );
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        {/* Heatmap */}
        <Card>
          <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Confidence Heatmap — Geography × Segment
          </h3>
          <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>Average confidence tier · {year}</p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
              <thead>
                <tr>
                  <th style={{ padding: '6px 8px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '10px' }}>GEO</th>
                  {segments.map((seg) => (
                    <th key={seg} style={{ padding: '6px 8px', textAlign: 'center', color: 'var(--text-muted)', fontWeight: 600, fontSize: '10px', letterSpacing: '0.06em' }}>
                      {seg.toUpperCase()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {geos.slice(0, 20).map((geo) => (
                  <tr key={geo} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '5px 8px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>{geo}</td>
                    {segments.map((seg) => {
                      const t = heatmap[geo]?.[seg] ?? null;
                      const bg = t === 1 ? 'rgba(16,185,129,0.15)' : t === 2 ? 'rgba(245,158,11,0.15)' : t === 3 ? 'rgba(239,68,68,0.15)' : 'transparent';
                      const col = t === 1 ? '#10B981' : t === 2 ? '#F59E0B' : t === 3 ? '#EF4444' : 'var(--text-muted)';
                      return (
                        <td key={seg} style={{ padding: '5px 8px', textAlign: 'center', background: bg }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: col, fontSize: '12px' }}>
                            {t ?? '—'}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Geo confidence ranking */}
        <Card>
          <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Average Confidence Tier by Geography
          </h3>
          <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>Lower = better data quality</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '340px', overflowY: 'auto' }}>
            {geoConf.map(({ geo, avg }) => (
              <div key={geo} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)', width: '36px', flexShrink: 0 }}>{geo}</span>
                <div style={{ flex: 1, height: '8px', background: 'var(--bg-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${((avg - 1) / 2) * 100}%`, background: tierColor(avg), borderRadius: '4px', transition: 'width 0.3s' }} />
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: tierColor(avg), width: '28px', textAlign: 'right' }}>
                  {avg.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Methodology */}
      <Card>
        <h3 style={{ margin: '0 0 12px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Confidence Tier Methodology
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {['Factor', 'Tier 1 — High', 'Tier 2 — Medium', 'Tier 3 — Low'].map((h, i) => (
                <th key={h} style={{ padding: '8px', textAlign: 'left', color: i === 0 ? 'var(--text-muted)' : TIER_META[(i) as 1 | 2 | 3]?.color ?? 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ['Source quality', 'Official stats / regulator', 'Industry reports / surveys', 'Estimates / expert judgment'],
              ['Coverage', '>80% of segment', '40–80% covered', '<40% or pure proxy'],
              ['Triangulation', '3+ sources within 15%', '2 sources within 25%', 'Single source or >25% divergence'],
              ['Uncertainty band', '±10%', '±20%', '±35%'],
            ].map(([factor, ...vals]) => (
              <tr key={factor} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '8px', color: 'var(--text-secondary)', fontWeight: 600 }}>{factor}</td>
                {vals.map((v, i) => (
                  <td key={i} style={{ padding: '8px', color: 'var(--text-muted)' }}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
