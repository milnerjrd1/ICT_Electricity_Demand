import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  accent?: string;
}

export function PageHeader({ title, subtitle, actions, accent = 'var(--accent)' }: PageHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        marginBottom: '28px',
        paddingBottom: '20px',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
        <div style={{ width: '3px', borderRadius: '2px', background: accent, alignSelf: 'stretch', minHeight: '28px', flexShrink: 0 }} />
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: '20px',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.01em',
              lineHeight: 1.25,
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <p style={{ margin: '5px 0 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>{actions}</div>}
    </div>
  );
}
