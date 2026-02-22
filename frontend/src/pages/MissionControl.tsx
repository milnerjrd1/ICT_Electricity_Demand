import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../api/client';
import { useRunStatus, useScenarios } from '../api/hooks';
import { KpiCard } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { useScenarioStore } from '../store/scenarioStore';
import type { RunResult } from '../types/schema';

const SCENARIO_COLORS: Record<string, string> = {
  ai_base: '#00D4FF',
  ai_high: '#EF4444',
  ai_low: '#10B981',
  ai_stress: '#8B5CF6',
  sovereignty_push: '#F59E0B',
  grid_constrained: '#6B7280',
  efficiency_breakthrough: '#06B6D4',
};

const ALL_SCENARIOS = Object.keys(SCENARIO_COLORS);

export function MissionControl() {
  const { data: scenarioList } = useScenarios();
  const { activeScenarioId, setActivePage } = useScenarioStore();

  const [runIds, setRunIds] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, RunResult>>({});
  const bootstrapped = useRef(false);

  useEffect(() => { setActivePage('mission-control'); }, [setActivePage]);

  // Bootstrap: fire all 7 runs concurrently via Promise.all.
  // Cannot use a shared useMutation instance — calling .mutate() multiple times
  // on one instance cancels the previous call, so only the last onSuccess fires.
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;

    Promise.all(
      ALL_SCENARIOS.map((sid) =>
        api.post<{ run_id: string }>('/runs', { scenario_id: sid, seed: 42 })
          .then((data) => ({ sid, run_id: data.run_id }))
      )
    ).then((pairs) => {
      const ids: Record<string, string> = {};
      for (const { sid, run_id } of pairs) ids[sid] = run_id;
      setRunIds(ids);
    }).catch((err) => {
      console.error('Failed to bootstrap scenario runs:', err);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const runIdList = Object.entries(runIds);
  const isLoading = Object.keys(results).length < ALL_SCENARIOS.length;

  return (
    <div>
      <PageHeader
        title="MISSION CONTROL"
        subtitle="Global ICT electricity demand · all scenarios · P10/P50/P90 uncertainty"
        actions={
          isLoading ? (
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              {Object.keys(results).length}/{ALL_SCENARIOS.length} scenarios loaded...
            </span>
          ) : undefined
        }
      />

      {runIdList.map(([sid, runId]) => (
        <RunPoller
          key={runId}
          runId={runId}
          onDone={(result) => {
            setResults((prev) => ({ ...prev, [sid]: result }));
          }}
        />
      ))}

      <MissionControlContent
        results={results}
        activeScenarioId={activeScenarioId}
        scenarioList={scenarioList ?? []}
      />
    </div>
  );
}

function RunPoller({
  runId,
  onDone,
}: {
  runId: string;
  scenarioId?: string;
  onDone: (result: RunResult) => void;
}) {
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

function MissionControlContent({
  results,
  activeScenarioId,
  scenarioList,
}: {
  results: Record<string, RunResult>;
  activeScenarioId: string;
  scenarioList: { id: string; label: string; color: string }[];
}) {
  const activeResult = results[activeScenarioId];
  const summary = activeResult?.summary;

  // Build fan chart data
  const fanData = useMemo(() => {
    const byYear: Record<number, Record<string, { p50: number; p10: number; p90: number }>> = {};
    for (const [sid, result] of Object.entries(results)) {
      for (const row of result.rows) {
        if (!byYear[row.year]) byYear[row.year] = {};
        if (!byYear[row.year][sid]) byYear[row.year][sid] = { p50: 0, p10: 0, p90: 0 };
        byYear[row.year][sid].p50 += row.kwh_p50 / 1e9;
        byYear[row.year][sid].p10 += row.kwh_p10 / 1e9;
        byYear[row.year][sid].p90 += row.kwh_p90 / 1e9;
      }
    }
    return Object.entries(byYear)
      .sort(([a], [b]) => Number(a) - Number(b))
      .map(([year, scens]) => {
        const pt: Record<string, number> = { year: Number(year) };
        for (const [sid, v] of Object.entries(scens)) {
          pt[`${sid}_p50`] = Math.round(v.p50);
          pt[`${sid}_p10`] = Math.round(v.p10);
          pt[`${sid}_p90`] = Math.round(v.p90);
        }
        return pt;
      });
  }, [results]);

  const nLoaded = Object.keys(results).length;
  const nTotal = ALL_SCENARIOS.length;

  if (nLoaded === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px' }}>
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              border: '3px solid var(--border)',
              borderTopColor: 'var(--accent-cyan)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 16px',
            }}
          />
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: '0 0 6px' }}>
            Running scenario engine...
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '11px', fontFamily: 'var(--font-mono)', margin: 0 }}>
            {nLoaded}/{nTotal} scenarios complete
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* KPI strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <KpiCard
          label="Total ICT Electricity"
          value={summary ? `${summary.total_twh.toLocaleString()} TWh` : '—'}
          sub={`Year ${summary?.latest_year ?? '—'} · ${activeScenarioId.replace(/_/g, ' ').toUpperCase()}`}
          accent="var(--accent-cyan)"
        />
        <KpiCard
          label="Data Centre Share"
          value={summary ? `${(summary.dc_share * 100).toFixed(1)}%` : '—'}
          sub={`${summary?.dc_twh.toLocaleString() ?? '—'} TWh`}
          accent="var(--accent-red)"
        />
        <KpiCard
          label="Carbon Emissions"
          value={summary ? `${summary.total_emissions_mtco2e.toLocaleString()} MtCO₂e` : '—'}
          sub="ICT sector total"
          accent="var(--accent-amber)"
        />
        <KpiCard
          label="Geographies"
          value={summary ? `${summary.n_geos}` : '—'}
          sub="countries & regions"
          accent="var(--accent-green)"
        />
      </div>

      {/* Fan chart */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '20px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Global ICT Electricity Demand — All Scenarios
            </h3>
            <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--text-secondary)' }}>
              P50 trajectories · P10/P90 band shown for active scenario
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {Object.entries(SCENARIO_COLORS).map(([sid, color]) => (
              <div key={sid} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <div style={{ width: '20px', height: '2px', background: color, opacity: sid === activeScenarioId ? 1 : 0.5 }} />
                <span style={{ fontSize: '10px', color: sid === activeScenarioId ? color : 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {sid.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
        </div>

        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={fanData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="year"
              tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v.toLocaleString()}`}
              width={65}
              label={{ value: 'TWh', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 11, dy: 20 }}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-bright)',
                borderRadius: '6px',
                fontSize: '12px',
              }}
              labelStyle={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}
              itemStyle={{ color: 'var(--text-secondary)' }}
              formatter={(value, name) => [
                `${Number(value).toLocaleString()} TWh`,
                String(name).replace('_p50', '').replace(/_/g, ' '),
              ]}
            />

            {/* P10/P90 band for active scenario */}
            {fanData.length > 0 && fanData[0][`${activeScenarioId}_p90`] !== undefined && (
              <Area
                type="monotone"
                dataKey={`${activeScenarioId}_p90`}
                stroke="none"
                fill={SCENARIO_COLORS[activeScenarioId] ?? '#00D4FF'}
                fillOpacity={0.08}
                legendType="none"
              />
            )}

            {/* P50 lines for all scenarios */}
            {Object.entries(SCENARIO_COLORS).map(([sid, color]) => (
              <Line
                key={sid}
                type="monotone"
                dataKey={`${sid}_p50`}
                stroke={color}
                strokeWidth={sid === activeScenarioId ? 2.5 : 1.5}
                dot={false}
                strokeOpacity={sid === activeScenarioId ? 1 : 0.45}
                legendType="none"
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Segment breakdown + scenario cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <SegmentBreakdown result={activeResult} />
        <ScenarioCards scenarioList={scenarioList} results={results} activeId={activeScenarioId} />
      </div>
    </>
  );
}

function SegmentBreakdown({ result }: { result: RunResult | undefined }) {
  const segmentData = useMemo(() => {
    if (!result) return [];
    const byYearSeg: Record<number, Record<string, number>> = {};
    for (const row of result.rows) {
      if (!byYearSeg[row.year]) byYearSeg[row.year] = {};
      byYearSeg[row.year][row.segment] = (byYearSeg[row.year][row.segment] ?? 0) + row.kwh_p50 / 1e9;
    }
    return Object.entries(byYearSeg)
      .sort(([a], [b]) => Number(a) - Number(b))
      .map(([year, segs]) => ({ year: Number(year), ...segs }));
  }, [result]);

  const SEG_COLORS: Record<string, string> = {
    datacentres: '#EF4444',
    networks: '#F59E0B',
    devices: '#10B981',
  };

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '20px',
      }}
    >
      <h3 style={{ margin: '0 0 4px', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
        Demand by Segment
      </h3>
      <p style={{ margin: '0 0 16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
        Active scenario · P50 · TWh
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={segmentData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
          <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={50} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', borderRadius: '6px', fontSize: '11px' }}
            formatter={(v, name) => [`${Number(v).toLocaleString()} TWh`, String(name)]}
          />
          {['datacentres', 'networks', 'devices'].map((seg) => (
            <Area key={seg} type="monotone" dataKey={seg} stackId="1" stroke={SEG_COLORS[seg]} fill={SEG_COLORS[seg]} fillOpacity={0.6} strokeWidth={1.5} />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function ScenarioCards({
  scenarioList,
  results,
  activeId,
}: {
  scenarioList: { id: string; label: string; color: string }[];
  results: Record<string, RunResult>;
  activeId: string;
}) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '20px',
        overflowY: 'auto',
        maxHeight: '320px',
      }}
    >
      <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
        Scenario Outcomes — {results[Object.keys(results)[0]]?.summary?.latest_year ?? '2035'}
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {scenarioList.map((sc) => {
          const r = results[sc.id];
          const color = SCENARIO_COLORS[sc.id] ?? sc.color ?? '#9CA3AF';
          const twh = r?.summary?.total_twh;
          const isActive = sc.id === activeId;
          return (
            <div
              key={sc.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 12px',
                background: isActive ? `${color}12` : 'var(--bg-elevated)',
                border: `1px solid ${isActive ? `${color}40` : 'var(--border)'}`,
                borderLeft: `3px solid ${color}`,
                borderRadius: '6px',
              }}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: isActive ? color : 'var(--text-primary)' }}>
                  {sc.label}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{sc.id}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color }}>
                  {twh != null ? `${twh.toLocaleString()} TWh` : '—'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>total ICT</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
