import { Role } from '@relay/api-client';
import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useAuth } from '../../app/auth';
import { Button } from '../../components/button/Button';
import { TextField } from '../../components/field/Field';
import { copy } from '../../lib/copy';
import './portal.css';

export function PortalAuthPage({ mode }: { mode: 'sign-in' | 'sign-up' }) {
  const { org = '' } = useParams();
  const { signIn, register, signOut } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', full_name: '', company: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const signUp = mode === 'sign-up';

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const session = signUp
        ? await register({ organization: org, ...form, company: form.company || null })
        : await signIn(org, form.email, form.password);
      if (session.user.role !== Role.CUSTOMER) {
        await signOut();
        navigate('/login');
        return;
      }
      navigate(`/portal/${org}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : copy.errors.generic);
    } finally {
      setBusy(false);
    }
  };

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });
  return (
    <main className="portal portal--centered">
      <form className="portal__card" onSubmit={(e) => void submit(e)}>
        <p className="portal__brand">{copy.auth.portalTitle(org)}</p>
        <h1 className="portal__title">{signUp ? copy.auth.portalSignUp : copy.auth.signIn}</h1>
        <p className="portal__lead">{signUp ? copy.auth.portalSignUpLead : copy.auth.portalLead}</p>
        {error && <p className="portal__error" role="alert">{error}</p>}
        {signUp && <TextField label={copy.auth.fullName} value={form.full_name} required autoComplete="name" onChange={set('full_name')} />}
        {signUp && <TextField label={`${copy.auth.company} (${copy.common.optional})`} value={form.company} autoComplete="organization" onChange={set('company')} />}
        <TextField label={copy.auth.email} type="email" value={form.email} required autoComplete="email" onChange={set('email')} />
        <TextField label={copy.auth.password} type="password" value={form.password} required minLength={signUp ? 8 : undefined}
          autoComplete={signUp ? 'new-password' : 'current-password'} onChange={set('password')} />
        <Button type="submit" variant="primary" block loading={busy}>{signUp ? copy.auth.portalSignUp : copy.auth.signIn}</Button>
        <p className="portal__lead">
          {signUp ? copy.auth.haveAccount : copy.auth.noAccount}{' '}
          <Link to={`/portal/${org}/${signUp ? 'sign-in' : 'sign-up'}`}>{signUp ? copy.auth.signIn : copy.auth.portalSignUp}</Link>
        </p>
        {!signUp && <p className="portal__hint">{copy.auth.portalDemo}</p>}
      </form>
    </main>
  );
}
