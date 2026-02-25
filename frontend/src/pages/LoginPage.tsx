import React, { useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { authApi } from '../services/api';
import { useAuth } from '../App';

interface LocationState {
  from?: { pathname: string };
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const state = location.state as LocationState;
  const from = state?.from?.pathname || '/';

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!email.trim() || !password.trim()) {
        setError('メールアドレスとパスワードを入力してください。');
        return;
      }
      setLoading(true);
      setError(null);

      try {
        const res = await authApi.login(email.trim(), password);
        const { access_token } = res.data;
        await login(access_token);
        navigate(from, { replace: true });
      } catch (err: unknown) {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosErr.response?.status === 401) {
          setError('メールアドレスまたはパスワードが正しくありません。');
        } else if (axiosErr.response?.data?.detail) {
          setError(axiosErr.response.data.detail);
        } else {
          setError('ログインに失敗しました。もう一度お試しください。');
        }
      } finally {
        setLoading(false);
      }
    },
    [email, password, login, navigate, from]
  );

  return (
    <div style={styles.container}>
      {/* Background decorations */}
      <div style={styles.bgDecor1} />
      <div style={styles.bgDecor2} />

      <div style={styles.card} className="fade-in">
        {/* Logo / Brand */}
        <div style={styles.brandSection}>
          <div style={styles.logoMark}>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" fill="#e94560" />
              <text x="16" y="22" textAnchor="middle" fill="white" fontSize="16" fontWeight="700">M</text>
            </svg>
          </div>
          <div>
            <h1 style={styles.brandName}>MMIP</h1>
            <p style={styles.brandSubtitle}>マンガ市場インテリジェンス</p>
          </div>
        </div>

        <div style={styles.divider} />

        <div style={styles.formSection}>
          <h2 style={styles.formTitle}>ログイン</h2>
          <p style={styles.formSubtitle}>出版社アカウントでサインインしてください</p>

          {error && (
            <div style={styles.errorBanner} role="alert">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"/>
                <path d="M7.002 11a1 1 0 112 0 1 1 0 01-2 0zM7.1 4.995a.905.905 0 111.8 0l-.35 3.507a.552.552 0 01-1.1 0L7.1 4.995z"/>
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={styles.form} noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="email">
                メールアドレス
              </label>
              <input
                id="email"
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="publisher@example.co.jp"
                autoComplete="username"
                autoFocus
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">
                パスワード
              </label>
              <div style={styles.passwordWrapper}>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  disabled={loading}
                  required
                  style={{ paddingRight: '2.75rem' }}
                />
                <button
                  type="button"
                  style={styles.showPasswordBtn}
                  onClick={() => setShowPassword((v) => !v)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'パスワードを隠す' : 'パスワードを表示'}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
                      <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem' }}
            >
              {loading ? (
                <>
                  <span
                    style={{
                      width: '16px',
                      height: '16px',
                      border: '2px solid rgba(255,255,255,0.3)',
                      borderTopColor: 'white',
                      borderRadius: '50%',
                      display: 'inline-block',
                      animation: 'spin 0.8s linear infinite',
                    }}
                  />
                  ログイン中...
                </>
              ) : (
                'ログイン'
              )}
            </button>
          </form>
        </div>

        <div style={styles.footer}>
          <p style={styles.footerText}>
            Manga Market Intelligence Platform &copy; 2025
          </p>
          <p style={styles.footerSubtext}>
            本システムは許可された出版社のみご利用いただけます
          </p>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #1a1a2e 0%, #0f3460 60%, #1a1a2e 100%)',
    padding: '2rem',
    position: 'relative',
    overflow: 'hidden',
  },
  bgDecor1: {
    position: 'absolute',
    top: '-10%',
    right: '-5%',
    width: '500px',
    height: '500px',
    borderRadius: '50%',
    background: 'rgba(233, 69, 96, 0.08)',
    pointerEvents: 'none',
  },
  bgDecor2: {
    position: 'absolute',
    bottom: '-15%',
    left: '-8%',
    width: '600px',
    height: '600px',
    borderRadius: '50%',
    background: 'rgba(15, 52, 96, 0.5)',
    pointerEvents: 'none',
  },
  card: {
    background: 'white',
    borderRadius: '16px',
    boxShadow: '0 25px 60px rgba(0,0,0,0.3)',
    width: '100%',
    maxWidth: '420px',
    overflow: 'hidden',
    position: 'relative',
    zIndex: 1,
  },
  brandSection: {
    background: '#1a1a2e',
    padding: '2rem',
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  logoMark: {
    flexShrink: 0,
  },
  brandName: {
    fontSize: '1.5rem',
    fontWeight: '700',
    color: 'white',
    letterSpacing: '-0.02em',
    lineHeight: 1,
  },
  brandSubtitle: {
    fontSize: '0.75rem',
    color: 'rgba(255,255,255,0.5)',
    marginTop: '0.25rem',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  divider: {
    height: '3px',
    background: 'linear-gradient(90deg, #e94560, #0f3460)',
  },
  formSection: {
    padding: '2rem',
  },
  formTitle: {
    fontSize: '1.375rem',
    fontWeight: '700',
    color: '#1a1a2e',
    marginBottom: '0.375rem',
    letterSpacing: '-0.02em',
  },
  formSubtitle: {
    fontSize: '0.8125rem',
    color: '#718096',
    marginBottom: '1.5rem',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.75rem 1rem',
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    color: '#ef4444',
    fontSize: '0.8125rem',
    marginBottom: '1.25rem',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.125rem',
  },
  passwordWrapper: {
    position: 'relative',
  },
  showPasswordBtn: {
    position: 'absolute',
    right: '0.75rem',
    top: '50%',
    transform: 'translateY(-50%)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#718096',
    display: 'flex',
    alignItems: 'center',
    padding: '0.25rem',
    borderRadius: '4px',
    transition: 'color 150ms',
  },
  footer: {
    padding: '1rem 2rem 1.5rem',
    textAlign: 'center' as const,
    borderTop: '1px solid #f0f1f5',
  },
  footerText: {
    fontSize: '0.75rem',
    color: '#9ca3af',
  },
  footerSubtext: {
    fontSize: '0.6875rem',
    color: '#d1d5db',
    marginTop: '0.25rem',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
};

export default LoginPage;
