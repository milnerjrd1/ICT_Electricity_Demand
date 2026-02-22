import { Activity, Zap } from 'lucide-react';
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
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginRight: '8px' }}>
        <Zap size={18} color="var(--accent-cyan)" />
        <span style={{ fontWeight: 700, fontSize: '14px', letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
          ICT ELECTRICITY
        </span>
        <span
          style={{
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--accent-cyan)',
            background: 'rgba(0,212,255,0.1)',
            border: '1px solid rgba(0,212,255,0.25)',
            borderRadius: '3px',
            padding: '1px 6px',
            letterSpacing: '0.08em',
          }}
        >
          DEMAND MODEL
        </span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Status indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {health && (
          <>
            <StatusPill label="ENGINE" value={health.engine.toUpperCase()} color="var(--accent-amber)" />
            <StatusPill label="MODEL" value={`v${health.model_version}`} color="var(--accent-cyan)" />
            <StatusPill label="DATA" value={health.data_vintage} color="var(--accent-green)" />
          </>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={13} color={health?.status === 'ok' ? 'var(--accent-green)' : 'var(--accent-red)'} />
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            {health?.status === 'ok' ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </header>
  );
}

function StatusPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <span style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>{label}</span>
      <span
        style={{
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          color,
          fontWeight: 600,
        }}
      >
        {value}
      </span>
    </div>
  );
}
