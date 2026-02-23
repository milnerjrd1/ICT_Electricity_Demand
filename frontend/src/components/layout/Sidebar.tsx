import { BarChart2, BookOpen, Database, Download, GitBranch, Home, Layers, Shield } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', icon: Home, label: 'Mission Control' },
  { to: '/scenarios', icon: Layers, label: 'Scenario Builder' },
  { to: '/explorer', icon: BarChart2, label: 'Demand Explorer' },
  { to: '/quality', icon: Shield, label: 'Data Quality' },
  { to: '/export', icon: Download, label: 'Export' },
  { to: '/guide', icon: BookOpen, label: 'Scenario Guide' },
  { to: '/methodology', icon: GitBranch, label: 'Methodology' },
];

export function Sidebar() {
  return (
    <nav
      style={{
        width: '220px',
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        position: 'fixed',
        top: '52px',
        bottom: 0,
        left: 0,
        display: 'flex',
        flexDirection: 'column',
        padding: '20px 0 16px',
        zIndex: 90,
      }}
    >
      <div style={{ padding: '0 16px 14px', borderBottom: '1px solid var(--border)', marginBottom: '8px' }}>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600, textTransform: 'uppercase' }}>
          Navigation
        </span>
      </div>

      {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          style={({ isActive }) => ({
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '9px 16px',
            margin: '1px 8px',
            borderRadius: '6px',
            textDecoration: 'none',
            fontSize: '13px',
            fontWeight: isActive ? 600 : 400,
            color: isActive ? 'var(--accent-active)' : 'var(--text-secondary)',
            background: isActive ? 'var(--accent-soft)' : 'transparent',
            borderLeft: isActive ? `2px solid var(--accent)` : '2px solid transparent',
            transition: 'background 0.12s ease, color 0.12s ease',
          })}
        >
          <Icon size={15} />
          {label}
        </NavLink>
      ))}

      <div style={{ flex: 1 }} />

      <div
        style={{
          margin: '0 12px',
          padding: '12px',
          background: 'var(--bg-elevated)',
          borderRadius: '6px',
          border: '1px solid var(--border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
          <Database size={11} color="var(--accent-amber)" />
          <span style={{ fontSize: '10px', color: 'var(--accent-amber)', fontWeight: 600, letterSpacing: '0.06em' }}>
            Phase 0
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
          Synthetic data active. Real loaders in Phase 1.
        </p>
      </div>
    </nav>
  );
}
