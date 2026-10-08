import type { ButtonHTMLAttributes } from 'react';
import './button.css';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: 'small';
  loading?: boolean;
  block?: boolean;
}

export function Button({ variant = 'secondary', size, loading, block, className, disabled, children, ...rest }: Props) {
  const classes = [
    'button',
    `button--${variant}`,
    size && `button--${size}`,
    block && 'button--block',
    loading && 'button--loading',
    className,
  ].filter(Boolean);
  return (
    <button type="button" className={classes.join(' ')} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {children}
    </button>
  );
}
