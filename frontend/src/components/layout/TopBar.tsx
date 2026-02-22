import { Activity } from 'lucide-react';
import { useHealth } from '../../api/hooks';

export function TopBar() {
  const { data: health } = useHealth();

  return (
    <header
      style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        height: '52px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: '16px',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}
    >
      {/* Wordmark — "Deloitte" text + green dot placeholder */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginRight: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '2px' }}>
          <span style={{ fontWeight: 700, fontSize: '18px', color: 'var(--text-primary)', letterSpacing: '-0.02em', fontFamily: 'var(--font-sans)' }}>
            Deloitte
          </span>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', display: 'inline-block', marginLeft: '1px', marginBottom: '3px', flexShrink: 0 }} />
        </div>
        <div style={{ width: '1px', height: '20px', background: 'var(--border)' }} />
        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.02em' }}>
          ICT Electricity Demand Model
        </span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Status indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {health && (
          <>
            <StatusPill label="Engine" value={health.engine} />
            <StatusPill label="Model" value={`v${health.model_version}`} />
            <StatusPill label="Data" value={health.data_vintage} />
          </>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px',
          padding: '4px 10px', borderRadius: '20px',
          background: health?.status === 'ok' ? 'var(--accent-soft)' : '#FEE2E2',
          border: `1px solid ${health?.status === 'ok' ? '#C6E090' : '#FECACA'}`,
        }}>
          <Activity size={11} color={health?.status === 'ok' ? 'var(--accent-active)' : 'var(--accent-red)'} />
          <span style={{ fontSize: '11px', fontWeight: 600, fontFamily: 'var(--font-mono)',
            color: health?.status === 'ok' ? 'var(--accent-active)' : 'var(--accent-red)' }}>
            {health?.status === 'ok' ? 'Live' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  );
}

function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>{label}</span>
      <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontWeight: 600 }}>
        {value}
      </span>
    </div>
  );
}
