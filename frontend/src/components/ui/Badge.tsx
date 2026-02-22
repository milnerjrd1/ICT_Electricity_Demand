import type { CSSProperties, ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  color?: string;
  style?: CSSProperties;
}

export function Badge({ children, color = 'var(--accent-cyan)', style }: BadgeProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        fontSize: '10px',
        fontFamily: 'var(--font-mono)',
        fontWeight: 600,
        letterSpacing: '0.08em',
        color,
        background: `${color}18`,
        border: `1px solid ${color}40`,
        borderRadius: '4px',
        padding: '2px 8px',
        ...style,
      }}
    >
      {children}
    </span>
  );
}
