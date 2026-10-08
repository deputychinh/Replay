import { initials } from '../../lib/format';
import './avatar.css';

export function Avatar({ name, staff = false, size }: { name: string; staff?: boolean; size?: 'small' }) {
  const classes = ['avatar', staff && 'avatar--staff', size && `avatar--${size}`].filter(Boolean).join(' ');
  return <span className={classes} aria-hidden="true">{initials(name)}</span>;
}
