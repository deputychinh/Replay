import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import './field.css';

interface Wrapper {
  label: string;
  hint?: string;
  error?: string;
  hideLabel?: boolean;
}

function Shell({ id, label, hint, error, hideLabel, children }: Wrapper & { id: string; children: ReactNode }) {
  return (
    <div className={`field${error ? ' field--invalid' : ''}`}>
      <label className={`field__label${hideLabel ? ' field__label--hidden' : ''}`} htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && <p className="field__hint" id={`${id}-hint`}>{hint}</p>}
      {error && <p className="field__error" id={`${id}-error`} role="alert">{error}</p>}
    </div>
  );
}

const describedBy = (id: string, hint?: string, error?: string) =>
  [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined;

export function TextField({ label, hint, error, hideLabel, ...input }: Wrapper & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error} hideLabel={hideLabel}>
      <input id={id} className="field__control" aria-invalid={Boolean(error)} aria-describedby={describedBy(id, hint, error)} {...input} />
    </Shell>
  );
}

export function TextArea({ label, hint, error, hideLabel, ...input }: Wrapper & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error} hideLabel={hideLabel}>
      <textarea id={id} className="field__control field__control--area" aria-describedby={describedBy(id, hint, error)} {...input} />
    </Shell>
  );
}

export function SelectField({
  label, hint, error, hideLabel, options, ...select
}: Wrapper & SelectHTMLAttributes<HTMLSelectElement> & { options: { value: string; label: string }[] }) {
  const id = useId();
  return (
    <Shell id={id} label={label} hint={hint} error={error} hideLabel={hideLabel}>
      <select id={id} className="field__control field__control--select" aria-describedby={describedBy(id, hint, error)} {...select}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </Shell>
  );
}
