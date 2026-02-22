import type { CSSProperties, ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  color?: string;
  style?: CSSProperties;
}

export function Badge({ children, color = 'var(--accent)', style }: BadgeProps) {
  const isToken = color.startsWith('var(');
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        fontSize: '11px',
        fontFamily: 'var(--font-sans)',
        fontWeight: 600,
        letterSpacing: '0.02em',
        color: isToken ? 'var(--accent-active)' : color,
        background: isToken ? 'var(--accent-soft)' : `${color}18`,
        border: isToken ? '1px solid #C6E090' : `1px solid ${color}40`,
        borderRadius: '4px',
        padding: '2px 8px',
        ...style,
      }}
    >
      {children}
    </span>
  );
}
