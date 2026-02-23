import { useEffect, useRef, useState } from 'react';
import {
  CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useCreateRun, useRunStatus, useScenarios } from '../api/hooks';
import { Card, KpiCard } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import type { RunResult } from '../types/schema';

// ── Published study data ──────────────────────────────────────────────────────
// Primary source:
//   Stobbe et al. (2025) "Power demand and carbon footprint of ICT in Germany
//   2010–2036", Fraunhofer IZM, Green ICT @ FMD project.
//   https://www.izm.fraunhofer.de/en/.../study-on-the-electricity-demand-and-carbon-footprint-of-ict-in-germany.html
//   Model version: ICT_CF_D_Mod_24-2 (as of 04/2024; study published 2025)
//
// Cross-checks:
//   Borderstep Institute (2023) "Rechenzentren und Energieverbrauch"
//   IEA Data Centres and Data Transmission Networks (2024)

interface StudyPoint { year: number; twh: number; low?: number; high?: number }
interface Study {
  id: string; label: string; shortLabel: string; color: string;
  geo: string; segment: string; description: string; points: StudyPoint[];
}

const STUDIES: Study[] = [
  {
    // Data centres: 7.5 TWh (2013) → 15 TWh (2023) → 27 TWh (2033)
    // Interpolated intermediate years from the continuous model trajectory.
    // Source: Stobbe et al. 2025, Fig. electricity demand use phase (ICT_CF_D_Mod_24-2)
    id: 'stobbe_2025_de_dc',
    label: 'Stobbe et al. 2025 — DE Data Centres',
    shortLabel: 'Stobbe et al. 2025 (DC)',
    color: '#F59E0B', geo: 'DE', segment: 'datacentres',
    description:
      'Stobbe et al. (2025) "Power demand and carbon footprint of ICT in Germany 2010–2036", ' +
      'Fraunhofer IZM. Bottom-up model (ICT_CF_D_Mod_24-2). Data centres only. ' +
      'Reported anchors: 7.5 TWh (2013), 15 TWh (2023), 27 TWh (2033).',
    points: [
      { year: 2013, twh:  7.5 },
      { year: 2018, twh: 11.0 },
      { year: 2020, twh: 12.5 },
      { year: 2022, twh: 14.0 },
      { year: 2023, twh: 15.0 },
      { year: 2025, twh: 17.5 },
      { year: 2028, twh: 22.0 },
      { year: 2030, twh: 24.5 },
      { year: 2033, twh: 27.0 },
    ],
  },
  {
    // Telecom networks: 5.2 TWh (2013) → 8.4 TWh (2023) → 10.3 TWh (2033)
    // Source: Stobbe et al. 2025
    id: 'stobbe_2025_de_networks',
    label: 'Stobbe et al. 2025 — DE Telecom Networks',
    shortLabel: 'Stobbe et al. 2025 (Networks)',
    color: '#06B6D4', geo: 'DE', segment: 'networks',
    description:
      'Stobbe et al. (2025) Fraunhofer IZM. Telecommunications networks electricity demand for Germany. ' +
      'Reported anchors: 5.2 TWh (2013), 8.4 TWh (2023), 10.3 TWh (2033). ' +
      'Growth driven by 4G/5G densification; partially offset by efficiency gains.',
    points: [
      { year: 2013, twh:  5.2 },
      { year: 2018, twh:  6.8 },
      { year: 2020, twh:  7.4 },
      { year: 2022, twh:  8.0 },
      { year: 2023, twh:  8.4 },
      { year: 2025, twh:  9.0 },
      { year: 2028, twh:  9.7 },
      { year: 2030, twh: 10.0 },
      { year: 2033, twh: 10.3 },
    ],
  },
  {
    // Households: ~19 TWh (2013) → ~13 TWh (2023) → ~15 TWh (2033)
    // Source: Stobbe et al. 2025
    id: 'stobbe_2025_de_devices',
    label: 'Stobbe et al. 2025 — DE Household Devices',
    shortLabel: 'Stobbe et al. 2025 (Devices)',
    color: '#EC4899', geo: 'DE', segment: 'devices',
    description:
      'Stobbe et al. (2025) Fraunhofer IZM. ICT electricity demand in German households. ' +
      'Reported anchors: ~19 TWh (2013), ~13 TWh (2023), ~15 TWh (2033). ' +
      'Decline driven by EU Ecodesign Directive; partial rebound from larger displays and AI devices.',
    points: [
      { year: 2013, twh: 19.0 },
      { year: 2018, twh: 15.5 },
      { year: 2020, twh: 14.5 },
      { year: 2022, twh: 13.5 },
      { year: 2023, twh: 13.0 },
      { year: 2025, twh: 13.2 },
      { year: 2028, twh: 14.0 },
      { year: 2030, twh: 14.5 },
      { year: 2033, twh: 15.0 },
    ],
  },
  {
    // Total ICT: ~50 TWh (2023) → ~72 TWh (2033)
    // Derived: DC + Networks + Households + other (work/public spaces)
    // Source: Stobbe et al. 2025
    id: 'stobbe_2025_de_total',
    label: 'Stobbe et al. 2025 — DE Total ICT',
    shortLabel: 'Stobbe et al. 2025 (Total ICT)',
    color: '#EF4444', geo: 'DE', segment: 'total_ict',
    description:
      'Stobbe et al. (2025) Fraunhofer IZM. Total ICT electricity demand for Germany across all segments ' +
      '(households, data centres, telecom networks, work, public spaces). ' +
      'Reported anchors: ~50 TWh (2023), ~72 TWh (2033). ' +
      'Note: "work" and "public spaces" segments are not modelled in this tool.',
    points: [
      { year: 2013, twh: 44.0 },
      { year: 2018, twh: 47.0 },
      { year: 2020, twh: 47.5 },
      { year: 2022, twh: 49.0 },
      { year: 2023, twh: 50.0 },
      { year: 2025, twh: 54.0 },
      { year: 2028, twh: 62.0 },
      { year: 2030, twh: 66.0 },
      { year: 2033, twh: 72.0 },
    ],
  },
  {
    // Cross-check: Borderstep 2023 (primary calibration anchor for this model)
    id: 'borderstep_2023_de_dc',
    label: 'Borderstep 2023 — DE Data Centres',
    shortLabel: 'Borderstep 2023 (cross-check)',
    color: '#10B981', geo: 'DE', segment: 'datacentres',
    description:
      'Borderstep Institute (2023) annual survey of German data centre energy consumption. ' +
      'Primary calibration anchor for this model. Shown here as a cross-check against Stobbe et al. 2025.',
    points: [
      { year: 2018, twh: 14.0, low: 12.5, high: 15.5 },
      { year: 2019, twh: 15.0, low: 13.5, high: 16.5 },
      { year: 2020, twh: 16.0, low: 14.5, high: 17.5 },
      { year: 2021, twh: 17.0, low: 15.5, high: 18.5 },
      { year: 2022, twh: 18.0, low: 16.5, high: 19.5 },
      { year: 2023, twh: 18.5, low: 17.0, high: 20.0 },
    ],
  },
  {
    // Cross-check: IEA 2024
    id: 'iea_2024_de_dc',
    label: 'IEA 2024 — DE Data Centres',
    shortLabel: 'IEA 2024 (cross-check)',
    color: '#8B5CF6', geo: 'DE', segment: 'datacentres',
    description:
      'IEA Data Centres and Data Transmission Networks (2024) top-down estimate for Germany. ' +
      'Shown as a cross-check against Stobbe et al. 2025.',
    points: [
      { year: 2018, twh: 13.5, low: 11.0, high: 16.0 },
      { year: 2020, twh: 15.5, low: 12.5, high: 18.5 },
      { year: 2022, twh: 19.2, low: 15.5, high: 23.0 },
    ],
  },
];

interface DeviationRow {
  studyId: string; studyLabel: string; geo: string; segment: string; year: number;
  studyTwh: number; studyLow?: number; studyHigh?: number;
  modelTwh: number | null; deviation: number | null; withinRange: boolean | null;
}

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

const TOOLTIP_STYLE = { background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' };
const AXIS_TICK = { fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' };
const fmt = (v: number | null) => v === null ? '\u2014' : v.toFixed(1) + ' TWh';
const fmtDev = (v: number | null) => v === null ? '\u2014' : (v >= 0 ? '+' : '') + (v * 100).toFixed(1) + '%';

// Model segment lines shown on chart — one per modelled segment
const MODEL_SEGMENTS: { key: string; label: string; segment: string; color: string }[] = [
  { key: 'model_datacentres', label: 'Model — Data Centres (P50)', segment: 'datacentres', color: '#F59E0B' },
  { key: 'model_networks',    label: 'Model — Networks (P50)',     segment: 'networks',    color: '#06B6D4' },
  { key: 'model_devices',     label: 'Model — Devices (P50)',      segment: 'devices',     color: '#EC4899' },
];

type GeoFilter = 'DE' | 'ALL';
const GEO_TABS: { id: GeoFilter; label: string }[] = [
  { id: 'DE', label: 'Germany (DE)' },
  { id: 'ALL', label: 'All segments' },
];

export function BenchmarkComparison() {
  const { data: scenarioList } = useScenarios();
  const createRun = useCreateRun();
  const [scenarioId, setScenarioId] = useState('ai_base');
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeStudyIds, setActiveStudyIds] = useState<Set<string>>(
    new Set(['stobbe_2025_de_dc', 'stobbe_2025_de_networks', 'stobbe_2025_de_devices', 'borderstep_2023_de_dc'])
  );
  const [focusGeo, setFocusGeo] = useState<GeoFilter>('DE');
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    setIsLoading(true);
    createRun.mutateAsync({ scenario_id: scenarioId, seed: 42 })
      .then((d) => setRunId(d.run_id))
      .catch(() => setIsLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleScenarioChange = (id: string) => {
    setScenarioId(id);
    setResult(null);
    setIsLoading(true);
    createRun.mutateAsync({ scenario_id: id, seed: 42 })
      .then((d) => setRunId(d.run_id))
      .catch(() => setIsLoading(false));
  };

  const getModelTwh = (geo: string, segment: string, year: number): number | null => {
    if (!result) return null;
    const rows = result.rows.filter((r) =>
      r.year === year &&
      (segment === 'total_ict' ? true : r.segment === segment) &&
      (geo === 'GLOBAL' ? true : r.geo === geo)
    );
    if (rows.length === 0) return null;
    return rows.reduce((s, r) => s + r.kwh_p50, 0) / 1e9;
  };

  // Collect all years present in model output for DE
  const modelYears: number[] = result
    ? Array.from(new Set(result.rows.filter((r) => r.geo === 'DE').map((r) => r.year))).sort()
    : [];

  const deviationRows: DeviationRow[] = STUDIES.flatMap((study) =>
    study.points.map((pt) => {
      const modelTwh = getModelTwh(study.geo, study.segment, pt.year);
      const deviation = modelTwh !== null ? (modelTwh - pt.twh) / pt.twh : null;
      const withinRange =
        modelTwh !== null && pt.low !== undefined && pt.high !== undefined
          ? modelTwh >= pt.low && modelTwh <= pt.high
          : null;
      return { studyId: study.id, studyLabel: study.shortLabel, geo: study.geo, segment: study.segment, year: pt.year, studyTwh: pt.twh, studyLow: pt.low, studyHigh: pt.high, modelTwh, deviation, withinRange };
    })
  );

  const visibleStudies = STUDIES.filter((s) => focusGeo === 'ALL' || s.geo === focusGeo);
  const studyYears = Array.from(new Set(visibleStudies.flatMap((s) => s.points.map((p) => p.year)))).sort();
  const chartYears = Array.from(new Set([...studyYears, ...modelYears])).sort();

  const chartData = chartYears.map((year) => {
    const row: Record<string, number | null | undefined> = { year };
    for (const study of visibleStudies) {
      if (!activeStudyIds.has(study.id)) continue;
      const pt = study.points.find((p) => p.year === year);
      row[study.id] = pt ? pt.twh : null;
    }
    const modelGeo = focusGeo === 'ALL' ? 'GLOBAL' : 'DE';
    for (const ms of MODEL_SEGMENTS) {
      row[ms.key] = getModelTwh(modelGeo, ms.segment, year);
    }
    return row;
  });

  const de2023ModelDC  = getModelTwh('DE', 'datacentres', 2023);
  const de2023ModelNet = getModelTwh('DE', 'networks',    2023);
  const de2023ModelDev = getModelTwh('DE', 'devices',     2023);
  const nWithin = deviationRows.filter((r) => r.withinRange === true).length;
  const nChecked = deviationRows.filter((r) => r.withinRange !== null).length;

  const toggleStudy = (id: string) =>
    setActiveStudyIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const btnStyle = (active: boolean) => ({
    padding: '6px 14px', borderRadius: '6px', border: '1px solid',
    borderColor: active ? 'var(--accent)' : 'var(--border)',
    background: active ? 'var(--accent-soft)' : 'var(--bg-elevated)',
    color: active ? 'var(--accent-active)' : 'var(--text-secondary)',
    fontSize: '12px', fontWeight: active ? 600 : 400, cursor: 'pointer',
  });

  return (
    <div>
      {runId && <RunWatcher runId={runId} onDone={(r) => { setResult(r); setIsLoading(false); }} />}

      <PageHeader
        title="Benchmark Comparison"
        subtitle="Model output vs Stobbe et al. 2025 (Fraunhofer IZM) — Power demand and carbon footprint of ICT in Germany 2010–2036"
        accent="#F59E0B"
        actions={
          <select
            value={scenarioId}
            onChange={(e) => handleScenarioChange(e.target.value)}
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '12px', padding: '6px 10px', cursor: 'pointer' }}
          >
            {(scenarioList ?? [{ id: 'ai_base', label: 'AI Base' }]).map((s) => (
              <option key={s.id} value={s.id}>{s.label ?? s.id}</option>
            ))}
          </select>
        }
      />

      {/* KPI row — model 2023 vs Stobbe 2023 per segment */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <KpiCard
          label="DE Data Centres 2023"
          value={de2023ModelDC !== null ? `${de2023ModelDC.toFixed(1)} TWh` : isLoading ? '\u2026' : '\u2014'}
          sub="Model P50 vs Stobbe 15.0 TWh"
          accent={de2023ModelDC !== null ? (Math.abs((de2023ModelDC - 15.0) / 15.0) <= 0.15 ? '#10B981' : '#F59E0B') : '#00D4FF'}
        />
        <KpiCard
          label="DE Networks 2023"
          value={de2023ModelNet !== null ? `${de2023ModelNet.toFixed(1)} TWh` : isLoading ? '\u2026' : '\u2014'}
          sub="Model P50 vs Stobbe 8.4 TWh"
          accent={de2023ModelNet !== null ? (Math.abs((de2023ModelNet - 8.4) / 8.4) <= 0.15 ? '#10B981' : '#F59E0B') : '#00D4FF'}
        />
        <KpiCard
          label="DE Devices 2023"
          value={de2023ModelDev !== null ? `${de2023ModelDev.toFixed(1)} TWh` : isLoading ? '\u2026' : '\u2014'}
          sub="Model P50 vs Stobbe 13.0 TWh"
          accent={de2023ModelDev !== null ? (Math.abs((de2023ModelDev - 13.0) / 13.0) <= 0.15 ? '#10B981' : '#F59E0B') : '#00D4FF'}
        />
        <KpiCard
          label="Points within study range"
          value={nChecked > 0 ? `${nWithin} / ${nChecked}` : isLoading ? '\u2026' : '\u2014'}
          sub="Model P50 within published lo/hi"
          accent={nChecked > 0 && nWithin === nChecked ? '#10B981' : '#F59E0B'}
        />
      </div>

      {/* Geo filter */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        {GEO_TABS.map((tab) => (
          <button key={tab.id} onClick={() => setFocusGeo(tab.id)} style={btnStyle(focusGeo === tab.id)}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Chart + study panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: '20px', marginBottom: '24px' }}>
        <Card>
          <div style={{ marginBottom: '14px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '3px' }}>Model vs Published Estimates</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Solid = model P50 · Dashed = published central estimate · Toggle studies in panel →</div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="year" tick={AXIS_TICK} />
              <YAxis tick={AXIS_TICK} tickFormatter={(v) => `${v}T`} width={50} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((value: number | undefined, name: string | undefined) => {
                  const study = STUDIES.find((s) => s.id === name);
                  const modelSeg = MODEL_SEGMENTS.find((ms) => ms.key === name);
                  const label = study ? study.shortLabel : modelSeg ? modelSeg.label : String(name);
                  return [`${value != null ? Number(value).toFixed(1) : '\u2014'} TWh`, label];
                }) as any}
              />
              {MODEL_SEGMENTS.map((ms) => (
                <Line key={ms.key} dataKey={ms.key} name={ms.key} stroke={ms.color} strokeWidth={2.5} dot={{ r: 4, fill: ms.color }} connectNulls type="monotone" />
              ))}
              {visibleStudies.filter((s) => activeStudyIds.has(s.id)).map((study) => (
                <Line key={study.id} dataKey={study.id} name={study.id} stroke={study.color} strokeWidth={1.5} strokeDasharray="5 3" dot={{ r: 3, fill: study.color }} connectNulls type="monotone" />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '14px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Studies</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {/* Model segment entries */}
            <div style={{ paddingBottom: '8px', marginBottom: '8px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>This model · {scenarioId}</div>
              {MODEL_SEGMENTS.map((ms) => (
                <div key={ms.key} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '3px 0' }}>
                  <div style={{ width: '20px', height: '3px', background: ms.color, borderRadius: '2px', flexShrink: 0 }} />
                  <div style={{ fontSize: '11px', fontWeight: 600, color: ms.color }}>{ms.label.replace('Model \u2014 ', '')}</div>
                </div>
              ))}
            </div>
            {STUDIES.map((study) => {
              const active = activeStudyIds.has(study.id);
              const dimmed = focusGeo !== 'ALL' && study.geo !== focusGeo;
              return (
                <button
                  key={study.id}
                  onClick={() => toggleStudy(study.id)}
                  style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', background: 'none', border: 'none', padding: '5px 0', cursor: 'pointer', opacity: dimmed ? 0.3 : 1, textAlign: 'left' }}
                >
                  <div style={{ width: '20px', height: '2px', marginTop: '8px', borderBottom: `2px dashed ${active ? study.color : 'var(--border)'}`, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: active ? 600 : 400, color: active ? 'var(--text-primary)' : 'var(--text-muted)', lineHeight: 1.35 }}>{study.shortLabel}</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{study.geo} · {study.segment.replace('_', ' ')}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Deviation table */}
      <Card style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '16px' }}>Point-by-point deviation table</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Study', 'Geo', 'Segment', 'Year', 'Study (TWh)', 'Range', 'Model P50', 'Deviation', 'In range?'].map((h) => (
                  <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '10px', letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {deviationRows.map((row, i) => {
                const devColor = row.deviation === null ? 'var(--text-muted)' : Math.abs(row.deviation) <= 0.10 ? '#10B981' : Math.abs(row.deviation) <= 0.20 ? '#F59E0B' : '#EF4444';
                const inRangeColor = row.withinRange === null ? 'var(--text-muted)' : row.withinRange ? '#10B981' : '#EF4444';
                return (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'var(--bg-elevated)' }}>
                    <td style={{ padding: '8px 10px', color: 'var(--text-primary)', fontWeight: 500 }}>{row.studyLabel}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{row.geo}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-secondary)' }}>{row.segment.replace('_', ' ')}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{row.year}</td>
                    <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-primary)' }}>{fmt(row.studyTwh)}</td>
                    <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      {row.studyLow !== undefined && row.studyHigh !== undefined ? `${row.studyLow.toFixed(1)}–${row.studyHigh.toFixed(1)}` : '—'}
                    </td>
                    <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-primary)' }}>{isLoading ? '…' : fmt(row.modelTwh)}</td>
                    <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: devColor, fontWeight: 600 }}>{isLoading ? '…' : fmtDev(row.deviation)}</td>
                    <td style={{ padding: '8px 10px', fontWeight: 600, color: inRangeColor }}>{isLoading ? '…' : row.withinRange === null ? '—' : row.withinRange ? '✓' : '✗'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Study cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {STUDIES.map((study) => (
          <Card key={study.id} accent={study.color}>
            <div style={{ fontSize: '10px', fontWeight: 700, color: study.color, marginBottom: '6px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{study.shortLabel}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '10px' }}>{study.description}</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 6px', color: 'var(--text-muted)' }}>{study.geo}</span>
              <span style={{ fontSize: '10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 6px', color: 'var(--text-muted)' }}>{study.segment.replace('_', ' ')}</span>
              <span style={{ fontSize: '10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 6px', color: 'var(--text-muted)' }}>{study.points.length} data points</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
