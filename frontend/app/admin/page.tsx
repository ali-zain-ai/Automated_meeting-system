'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { adminLogin } from '@/lib/api';
import { Sparkles, Lock, ArrowRight } from 'lucide-react';
import styles from './page.module.css';

export default function AdminLogin() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;

    setLoading(true);
    setError('');

    try {
      const res = await adminLogin(password);
      // Store token in localStorage
      localStorage.setItem('admin_token', res.token);
      router.push('/admin/dashboard');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.loginCard + ' card-elevated animate-fade-in-up'}>
        <div className={styles.logo}>
          <Sparkles size={28} />
          <span>MindFuelByAli</span>
        </div>
        
        <h1 className={styles.title}>Admin Access</h1>

        {error && (
          <div className={styles.errorBanner + ' animate-fade-in'}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className="form-group">
            <label className="form-label" htmlFor="password">
              <Lock size={14} style={{ display: 'inline', verticalAlign: 'text-bottom' }} />
              {' '}Password
            </label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter admin password"
              required
            />
          </div>

          <button
            type="submit"
            className={styles.submitBtn + ' btn btn-primary btn-lg'}
            disabled={loading || !password}
          >
            {loading ? (
              <div className="spinner" />
            ) : (
              <>
                Login <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
