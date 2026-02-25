import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../App';
import { alertApi } from '../../services/api';

const Header: React.FC = () => {
  const { publisher, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const res = await alertApi.getAlerts(1, 1);
        setUnreadCount(res.data.unread_count);
      } catch {
        // silently ignore
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const navItems = [
    { path: '/', label: 'ダッシュボード', icon: GridIcon },
    { path: '/genres', label: 'ジャンル分析', icon: ChartIcon },
    { path: '/alerts', label: 'アラート', icon: BellIcon, badge: unreadCount },
  ];

  return (
    <header style={styles.header}>
      <div style={styles.inner}>
        {/* Left: Nav links */}
        <nav style={styles.nav}>
          {navItems.map(({ path, label, icon: Icon, badge }) => {
            const isActive =
              path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);
            return (
              <Link
                key={path}
                to={path}
                style={{
                  ...styles.navLink,
                  ...(isActive ? styles.navLinkActive : {}),
                }}
              >
                <Icon size={16} />
                <span>{label}</span>
                {badge !== undefined && badge > 0 && (
                  <span style={styles.navBadge}>{badge > 99 ? '99+' : badge}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right: User menu */}
        <div style={styles.right}>
          {publisher && (
            <div style={styles.tierBadge}>
              <span style={getTierStyle(publisher.tier)}>
                {getTierLabel(publisher.tier)}
              </span>
            </div>
          )}

          <div style={styles.userMenuWrapper}>
            <button
              style={styles.userBtn}
              onClick={() => setDropdownOpen((v) => !v)}
              onBlur={() => setTimeout(() => setDropdownOpen(false), 150)}
            >
              <div style={styles.avatar}>
                {publisher?.publisher_name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div style={styles.userInfo}>
                <span style={styles.userName}>
                  {publisher?.publisher_name || 'ユーザー'}
                </span>
                <span style={styles.userMeta}>
                  {publisher?.title_count ?? 0} タイトル
                </span>
              </div>
              <ChevronIcon size={14} />
            </button>

            {dropdownOpen && (
              <div style={styles.dropdown}>
                <div style={styles.dropdownHeader}>
                  <p style={styles.dropdownName}>
                    {publisher?.publisher_name || 'ユーザー'}
                  </p>
                  <p style={styles.dropdownMeta}>
                    {publisher?.title_count ?? 0} タイトル登録済み
                  </p>
                </div>
                <hr style={styles.dropdownDivider} />
                <button style={styles.dropdownItem} onClick={handleLogout}>
                  <LogoutIcon size={15} />
                  ログアウト
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

// ============================================================
// Helper functions
// ============================================================

function getTierLabel(tier: string): string {
  const labels: Record<string, string> = {
    basic: 'ベーシック',
    standard: 'スタンダード',
    enterprise: 'エンタープライズ',
  };
  return labels[tier] || tier;
}

function getTierStyle(tier: string): React.CSSProperties {
  const styles: Record<string, React.CSSProperties> = {
    basic: { background: '#f3f4f6', color: '#6b7280', padding: '0.2rem 0.6rem', borderRadius: '9999px', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' },
    standard: { background: '#dbeafe', color: '#2563eb', padding: '0.2rem 0.6rem', borderRadius: '9999px', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' },
    enterprise: { background: 'linear-gradient(135deg, #fef3c7, #fde68a)', color: '#92400e', padding: '0.2rem 0.6rem', borderRadius: '9999px', fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' },
  };
  return styles[tier] || styles.basic;
}

// ============================================================
// Inline SVG Icons
// ============================================================

const GridIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
  </svg>
);

const ChartIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
  </svg>
);

const BellIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
);

const ChevronIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);

const LogoutIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
    <polyline points="16 17 21 12 16 7"/>
    <line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
);

// ============================================================
// Styles
// ============================================================

const styles: Record<string, React.CSSProperties> = {
  header: {
    position: 'fixed',
    top: 0,
    left: 'var(--sidebar-width)',
    right: 0,
    height: 'var(--header-height)',
    background: 'rgba(255,255,255,0.95)',
    backdropFilter: 'blur(8px)',
    borderBottom: '1px solid var(--color-border)',
    zIndex: 100,
    display: 'flex',
    alignItems: 'center',
  },
  inner: {
    width: '100%',
    padding: '0 2rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.25rem',
  },
  navLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.375rem',
    padding: '0.5rem 0.875rem',
    borderRadius: '8px',
    fontSize: '0.8125rem',
    fontWeight: 500,
    color: 'var(--color-text-secondary)',
    textDecoration: 'none',
    transition: 'all 150ms ease',
    position: 'relative',
  },
  navLinkActive: {
    background: 'rgba(233, 69, 96, 0.08)',
    color: 'var(--color-accent)',
  },
  navBadge: {
    background: 'var(--color-accent)',
    color: 'white',
    borderRadius: '9999px',
    fontSize: '0.625rem',
    fontWeight: 700,
    padding: '0.1rem 0.4rem',
    minWidth: '18px',
    textAlign: 'center',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  tierBadge: {
    display: 'flex',
    alignItems: 'center',
  },
  userMenuWrapper: {
    position: 'relative',
  },
  userBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.375rem 0.75rem 0.375rem 0.5rem',
    borderRadius: '8px',
    background: 'none',
    border: '1px solid var(--color-border)',
    cursor: 'pointer',
    color: 'var(--color-text-primary)',
    transition: 'all 150ms',
  },
  avatar: {
    width: '30px',
    height: '30px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #1a1a2e, #0f3460)',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.75rem',
    fontWeight: 700,
    flexShrink: 0,
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '0.125rem',
  },
  userName: {
    fontSize: '0.8125rem',
    fontWeight: 600,
    color: 'var(--color-text-primary)',
    lineHeight: 1,
  },
  userMeta: {
    fontSize: '0.6875rem',
    color: 'var(--color-text-muted)',
    lineHeight: 1,
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  dropdown: {
    position: 'absolute',
    top: 'calc(100% + 8px)',
    right: 0,
    background: 'white',
    border: '1px solid var(--color-border)',
    borderRadius: '10px',
    boxShadow: '0 10px 30px rgba(0,0,0,0.12)',
    minWidth: '200px',
    zIndex: 200,
    overflow: 'hidden',
  },
  dropdownHeader: {
    padding: '0.875rem 1rem',
    background: 'var(--color-surface-alt)',
  },
  dropdownName: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--color-text-primary)',
  },
  dropdownMeta: {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    marginTop: '0.125rem',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  dropdownDivider: {
    border: 'none',
    borderTop: '1px solid var(--color-border)',
    margin: 0,
  },
  dropdownItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    width: '100%',
    padding: '0.75rem 1rem',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '0.8125rem',
    color: 'var(--color-text-secondary)',
    textAlign: 'left',
    transition: 'background 150ms',
  },
};

export default Header;
