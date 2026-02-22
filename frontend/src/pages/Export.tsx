import { Download, FileText, Table } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useCreateRun, useRunStatus, useScenarios } from '../api/hooks';
import { Button } from '../components/ui/Button';
import { Card, KpiCard } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import type { OutputRow, RunResult } from '../types/schema';

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

function rowsToCsv(rows: OutputRow[], summary = false): string {
  if (summary) {
    const byYearSeg: Record<string, { twh: number; emissions: number; cost: number }> = {};
    for (const r of rows) {
      const key = `${r.scenario_id}|${r.geo}|${r.segment}|${r.year}`;
      if (!byYearSeg[key]) byYearSeg[key] = { twh: 0, emissions: 0, cost: 0 };
      byYearSeg[key].twh += r.kwh_p50 / 1e9;
      byYearSeg[key].emissions += (r.emissions_kgco2e ?? 0);
      byYearSeg[key].cost += (r.cost_usd ?? 0);
    }
    const header = 'scenario_id,geo,segment,year,twh_p50,emissions_mtco2e,cost_usd_bn\n';
    const lines = Object.entries(byYearSeg).map(([key, v]) => {
      const [sid, geo, seg, yr] = key.split('|');
      return `${sid},${geo},${seg},${yr},${v.twh.toFixed(2)},${v.emissions.toFixed(4)},${v.cost.toFixed(4)}`;
    });
    return header + lines.join('\n');
  }

  const header = 'scenario_id,geo,segment,product,year,kwh_p10,kwh_p50,kwh_p90,confidence_tier,uncertainty_band,emissions_kgco2e,cost_usd,run_id\n';
  const lines = rows.map((r) =>
    `${r.scenario_id},${r.geo},${r.segment},${r.product},${r.year},${r.kwh_p10.toFixed(0)},${r.kwh_p50.toFixed(0)},${r.kwh_p90.toFixed(0)},${r.confidence_tier},${r.uncertainty_band},${(r.emissions_kgco2e ?? 0).toFixed(4)},${(r.cost_usd ?? 0).toFixed(4)},${r.run_id}`,
  );
  return header + lines.join('\n');
}

function downloadCsv(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function Export() {
  const { data: scenarioList } = useScenarios();
  const createRun = useCreateRun();
  const [scenarioId, setScenarioId] = useState('ai_base');
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [previewPage, setPreviewPage] = useState(0);
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
    setScenarioId(id); setResult(null); setPreviewPage(0);
    setIsLoading(true);
    createRun.mutateAsync({ scenario_id: id, seed: 42 })
      .then((d) => setRunId(d.run_id))
      .catch(() => setIsLoading(false));
  }, [createRun]);

  const rows = result?.rows ?? [];
  const PAGE_SIZE = 50;
  const pageRows = rows.slice(previewPage * PAGE_SIZE, (previewPage + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(rows.length / PAGE_SIZE);

  const s = result?.summary;

  return (
    <div>
      <PageHeader title="EXPORT" subtitle="Download model outputs · CSV · filtered by scenario" accent="var(--accent-purple)" />
      {runId && <RunWatcher runId={runId} onDone={(r) => { setResult(r); setIsLoading(false); }} />}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'flex-end' }}>
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Scenario</label>
          <select value={scenarioId} onChange={(e) => handleScenarioChange(e.target.value)}
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px',
              color: 'var(--text-primary)', padding: '7px 12px', fontSize: '12px', fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
            {(scenarioList ?? []).map((sc) => <option key={sc.id} value={sc.id} style={{ background: 'var(--bg-elevated)' }}>{sc.label}</option>)}
          </select>
        </div>
      </div>

      {/* KPIs */}
      {s && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '20px' }}>
          <KpiCard label="Total Rows" value={rows.length.toLocaleString()} sub="output cells" accent="var(--accent-cyan)" />
          <KpiCard label="Geographies" value={s.n_geos.toString()} sub="countries & regions" accent="var(--accent-green)" />
          <KpiCard label="Total ICT TWh" value={s.total_twh.toLocaleString()} sub={`Year ${s.latest_year}`} accent="var(--accent-amber)" />
          <KpiCard label="Emissions" value={`${s.total_emissions_mtco2e.toLocaleString()} MtCO₂e`} sub={`Year ${s.latest_year}`} accent="var(--accent-red)" />
        </div>
      )}

      {/* Download buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <Card accent="var(--accent-cyan)" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <Table size={20} color="var(--accent-cyan)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: '0 0 4px', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Full Dataset</h3>
              <p style={{ margin: '0 0 12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                All rows · geo × segment × product × year · P10/P50/P90 · emissions · cost
              </p>
              <Button
                onClick={() => rows.length && downloadCsv(rowsToCsv(rows), `ict_demand_${scenarioId}_full.csv`)}
                disabled={!rows.length}
                loading={isLoading}
              >
                <Download size={13} />
                Download Full CSV ({rows.length.toLocaleString()} rows)
              </Button>
            </div>
          </div>
        </Card>

        <Card accent="var(--accent-green)" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <FileText size={20} color="var(--accent-green)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: '0 0 4px', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Summary Dataset</h3>
              <p style={{ margin: '0 0 12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                Aggregated by geo × segment × year · TWh P50 · emissions · cost
              </p>
              <Button
                variant="secondary"
                onClick={() => rows.length && downloadCsv(rowsToCsv(rows, true), `ict_demand_${scenarioId}_summary.csv`)}
                disabled={!rows.length}
                loading={isLoading}
              >
                <Download size={13} />
                Download Summary CSV
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Data preview */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Data Preview</h3>
            <p style={{ margin: '2px 0 0', fontSize: '11px', color: 'var(--text-secondary)' }}>
              Showing {previewPage * PAGE_SIZE + 1}–{Math.min((previewPage + 1) * PAGE_SIZE, rows.length)} of {rows.length.toLocaleString()} rows
            </p>
          </div>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <Button size="sm" variant="ghost" onClick={() => setPreviewPage(Math.max(0, previewPage - 1))} disabled={previewPage === 0}>←</Button>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{previewPage + 1} / {totalPages}</span>
            <Button size="sm" variant="ghost" onClick={() => setPreviewPage(Math.min(totalPages - 1, previewPage + 1))} disabled={previewPage >= totalPages - 1}>→</Button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['scenario', 'geo', 'segment', 'product', 'year', 'TWh P50', 'confidence', 'emissions MtCO₂e', 'cost USD bn'].map((h) => (
                  <th key={h} style={{ padding: '7px 8px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '10px', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)' }}>
                  <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>{r.scenario_id}</td>
                  <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontWeight: 600 }}>{r.geo}</td>
                  <td style={{ padding: '6px 8px', color: 'var(--text-secondary)' }}>{r.segment}</td>
                  <td style={{ padding: '6px 8px', color: 'var(--text-muted)' }}>{r.product}</td>
                  <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{r.year}</td>
                  <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>{(r.kwh_p50 / 1e9).toFixed(2)}</td>
                  <td style={{ padding: '6px 8px', textAlign: 'center' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '12px',
                      color: r.confidence_tier === 1 ? '#10B981' : r.confidence_tier === 2 ? '#F59E0B' : '#EF4444' }}>
                      T{r.confidence_tier}
                    </span>
                  </td>
                  <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{(r.emissions_kgco2e ?? 0).toFixed(3)}</td>
                  <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{(r.cost_usd ?? 0).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
