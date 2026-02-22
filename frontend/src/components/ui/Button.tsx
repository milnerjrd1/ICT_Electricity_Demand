import type { CSSProperties, MouseEvent, ReactNode } from 'react';

interface ButtonProps {
  children: ReactNode;
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  style?: CSSProperties;
  type?: 'button' | 'submit' | 'reset';
}

const VARIANTS = {
  primary: {
    background: 'var(--accent-cyan)',
    color: '#0A0E1A',
    border: 'none',
    hoverBg: '#33DDFF',
  },
  secondary: {
    background: 'transparent',
    color: 'var(--accent-cyan)',
    border: '1px solid var(--accent-cyan)',
    hoverBg: 'rgba(0,212,255,0.08)',
  },
  danger: {
    background: 'transparent',
    color: 'var(--accent-red)',
    border: '1px solid var(--accent-red)',
    hoverBg: 'rgba(239,68,68,0.08)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    hoverBg: 'var(--bg-elevated)',
  },
};

const SIZES = {
  sm: { padding: '5px 12px', fontSize: '12px' },
  md: { padding: '8px 16px', fontSize: '13px' },
  lg: { padding: '10px 24px', fontSize: '14px' },
};

export function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  style,
  type = 'button',
}: ButtonProps) {
  const v = VARIANTS[variant];
  const s = SIZES[size];

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        ...s,
        background: v.background,
        color: v.color,
        border: v.border,
        borderRadius: '6px',
        fontFamily: 'var(--font-sans)',
        fontWeight: 600,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 0.15s ease',
        letterSpacing: '0.02em',
        ...style,
      }}
    >
      {loading && (
        <span
          style={{
            width: '12px',
            height: '12px',
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            display: 'inline-block',
            animation: 'spin 0.7s linear infinite',
          }}
        />
      )}
      {children}
    </button>
  );
}
