import type { CSSProperties, ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  style?: CSSProperties;
  accent?: string;
  className?: string;
}

export function Card({ children, style, accent, className }: CardProps) {
  return (
    <div
      className={className}
      style={{
        background: 'var(--bg-surface)',
        border: `1px solid ${accent ? `${accent}33` : 'var(--border)'}`,
        borderTop: accent ? `2px solid ${accent}` : undefined,
        borderRadius: '8px',
        padding: '20px',
        ...style,
      }}
    >
      {children}
    </div>
  );
}

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
  icon?: ReactNode;
}

export function KpiCard({ label, value, sub, accent = 'var(--accent-cyan)', icon }: KpiCardProps) {
  return (
    <Card accent={accent}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, textTransform: 'uppercase' }}>
          {label}
        </span>
        {icon && <span style={{ color: accent, opacity: 0.7 }}>{icon}</span>}
      </div>
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '28px',
          fontWeight: 700,
          color: accent,
          margin: '8px 0 4px',
          letterSpacing: '-0.02em',
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{sub}</div>
      )}
    </Card>
  );
}
