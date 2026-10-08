import { Role } from '@relay/api-client';
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../../app/auth';
import { Button } from '../../components/button/Button';
import { TextField } from '../../components/field/Field';
import { copy } from '../../lib/copy';
import './auth-page.css';

export function LoginPage() {
  const { signIn, signOut } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ organization: 'acme', email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const session = await signIn(form.organization, form.email, form.password);
      if (session.user.role === Role.CUSTOMER) {
        await signOut();
        setError(copy.auth.customerInConsole);
        return;
      }
      navigate('/console/inbox/mine');
    } catch (e) {
      setError(e instanceof Error ? e.message : copy.errors.generic);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <form className="auth-page__card" onSubmit={(e) => void submit(e)}>
        <p className="auth-page__brand"><span className="auth-page__logo" aria-hidden="true">R</span>{copy.brand}</p>
        <h1 className="auth-page__title">{copy.auth.consoleTitle}</h1>
        <p className="auth-page__lead">{copy.auth.consoleLead}</p>
        {error && <p className="auth-page__error" role="alert">{error}</p>}
        <TextField label={copy.auth.organization} value={form.organization} required autoComplete="organization"
          onChange={(e) => setForm({ ...form, organization: e.target.value })} />
        <TextField label={copy.auth.email} type="email" value={form.email} required autoComplete="email"
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <TextField label={copy.auth.password} type="password" value={form.password} required autoComplete="current-password"
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <Button type="submit" variant="primary" block loading={busy}>{copy.auth.signIn}</Button>
        <p className="auth-page__hint">{copy.auth.demo}</p>
      </form>
    </main>
  );
}
