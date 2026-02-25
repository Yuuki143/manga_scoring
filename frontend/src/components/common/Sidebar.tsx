import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../App';

const Sidebar: React.FC = () => {
  const { publisher } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const navItems = [
    {
      group: 'メイン',
      items: [
        { path: '/', label: 'ダッシュボード', sublabel: 'Dashboard', icon: GridIcon },
        { path: '/genres', label: 'ジャンル分析', sublabel: 'Genre Analysis', icon: ChartBarIcon },
        { path: '/alerts', label: 'アラート', sublabel: 'Alerts', icon: BellIcon },
      ],
    },
  ];

  return (
    <aside
      style={{
        ...styles.sidebar,
        width: collapsed ? '64px' : 'var(--sidebar-width)',
      }}
    >
      {/* Brand */}
      <div style={styles.brand}>
        <div style={styles.logoContainer}>
          <div style={styles.logoMark}>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" fill="#e94560" />
              <text x="16" y="22" textAnchor="middle" fill="white" fontSize="16" fontWeight="700">M</text>
            </svg>
          </div>
          {!collapsed && (
            <div style={styles.brandText}>
              <span style={styles.brandName}>MMIP</span>
              <span style={styles.brandSub}>マーケット分析</span>
            </div>
          )}
        </div>
        <button
          style={styles.collapseBtn}
          onClick={() => setCollapsed((v) => !v)}
          title={collapsed ? 'サイドバーを開く' : 'サイドバーを閉じる'}
        >
          {collapsed ? <ChevronRightIcon size={14} /> : <ChevronLeftIcon size={14} />}
        </button>
      </div>

      {/* Navigation */}
      <nav style={styles.nav}>
        {navItems.map(({ group, items }) => (
          <div key={group} style={styles.navGroup}>
            {!collapsed && (
              <span style={styles.navGroupLabel}>{group}</span>
            )}
            {items.map(({ path, label, sublabel, icon: Icon }) => {
              const isActive =
                path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(path);
              return (
                <Link
                  key={path}
                  to={path}
                  style={{
                    ...styles.navItem,
                    ...(isActive ? styles.navItemActive : {}),
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  }}
                  title={collapsed ? label : undefined}
                >
                  <span
                    style={{
                      ...styles.navIcon,
                      color: isActive ? 'var(--color-accent)' : 'var(--color-text-muted)',
                    }}
                  >
                    <Icon size={18} />
                  </span>
                  {!collapsed && (
                    <span style={styles.navLabels}>
                      <span style={styles.navLabel}>{label}</span>
                      <span style={styles.navSublabel}>{sublabel}</span>
                    </span>
                  )}
                  {isActive && !collapsed && <span style={styles.activeIndicator} />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Publisher Info */}
      {!collapsed && publisher && (
        <div style={styles.publisherCard}>
          <div style={styles.publisherHeader}>
            <div style={styles.publisherAvatar}>
              {publisher.publisher_name.charAt(0).toUpperCase()}
            </div>
            <div style={styles.publisherInfo}>
              <p style={styles.publisherName}>{publisher.publisher_name}</p>
              <p style={styles.publisherTier}>{getTierLabel(publisher.tier)}</p>
            </div>
          </div>
          <div style={styles.publisherStats}>
            <div style={styles.publisherStat}>
              <span style={styles.publisherStatValue}>{publisher.title_count}</span>
              <span style={styles.publisherStatLabel}>タイトル</span>
            </div>
            <div style={styles.publisherStatDivider} />
            <div style={styles.publisherStat}>
              <span style={styles.publisherStatValue}>
                {publisher.tier === 'enterprise' ? '★' : publisher.tier === 'standard' ? '◆' : '●'}
              </span>
              <span style={styles.publisherStatLabel}>プラン</span>
            </div>
          </div>
        </div>
      )}

      {/* Version */}
      {!collapsed && (
        <div style={styles.version}>
          <span>MMIP v1.0</span>
        </div>
      )}
    </aside>
  );
};

// ============================================================
// Helper
// ============================================================

function getTierLabel(tier: string): string {
  const labels: Record<string, string> = {
    basic: 'ベーシックプラン',
    standard: 'スタンダードプラン',
    enterprise: 'エンタープライズ',
  };
  return labels[tier] || tier;
}

// ============================================================
// Icons
// ============================================================

const GridIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
  </svg>
);

const ChartBarIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
    <line x1="2" y1="20" x2="22" y2="20"/>
  </svg>
);

const BellIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
);

const ChevronLeftIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6"/>
  </svg>
);

const ChevronRightIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6"/>
  </svg>
);

// ============================================================
// Styles
// ============================================================

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    position: 'fixed',
    top: 0,
    left: 0,
    height: '100vh',
    background: 'var(--color-primary)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 200,
    transition: 'width 200ms ease',
    overflow: 'hidden',
    borderRight: '1px solid rgba(255,255,255,0.05)',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '1.25rem 1rem',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
    minHeight: 'var(--header-height)',
  },
  logoContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    overflow: 'hidden',
  },
  logoMark: {
    flexShrink: 0,
  },
  brandText: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  brandName: {
    color: 'white',
    fontSize: '1.25rem',
    fontWeight: 700,
    letterSpacing: '-0.02em',
    lineHeight: 1,
    whiteSpace: 'nowrap',
  },
  brandSub: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: '0.625rem',
    marginTop: '0.25rem',
    whiteSpace: 'nowrap',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  collapseBtn: {
    color: 'rgba(255,255,255,0.4)',
    background: 'rgba(255,255,255,0.05)',
    border: 'none',
    borderRadius: '6px',
    padding: '0.375rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all 150ms',
  },
  nav: {
    flex: 1,
    padding: '1rem 0.75rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
    overflowY: 'auto',
    overflowX: 'hidden',
  },
  navGroup: {
    marginBottom: '0.5rem',
  },
  navGroupLabel: {
    display: 'block',
    fontSize: '0.625rem',
    fontWeight: 700,
    color: 'rgba(255,255,255,0.25)',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    padding: '0 0.5rem',
    marginBottom: '0.375rem',
    whiteSpace: 'nowrap',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.625rem 0.75rem',
    borderRadius: '8px',
    textDecoration: 'none',
    color: 'rgba(255,255,255,0.65)',
    fontSize: '0.875rem',
    transition: 'all 150ms ease',
    position: 'relative',
    overflow: 'hidden',
    whiteSpace: 'nowrap',
  },
  navItemActive: {
    background: 'rgba(233, 69, 96, 0.15)',
    color: 'white',
  },
  navIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  navLabels: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.1rem',
    overflow: 'hidden',
  },
  navLabel: {
    fontWeight: 500,
    lineHeight: 1.2,
    fontFamily: '"Noto Sans JP", sans-serif',
    fontSize: '0.8125rem',
  },
  navSublabel: {
    fontSize: '0.625rem',
    color: 'rgba(255,255,255,0.3)',
    lineHeight: 1,
  },
  activeIndicator: {
    position: 'absolute',
    right: 0,
    top: '50%',
    transform: 'translateY(-50%)',
    width: '3px',
    height: '60%',
    background: 'var(--color-accent)',
    borderRadius: '3px 0 0 3px',
  },
  publisherCard: {
    margin: '0 0.75rem 0.75rem',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '10px',
    padding: '1rem',
    border: '1px solid rgba(255,255,255,0.07)',
  },
  publisherHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.625rem',
    marginBottom: '0.75rem',
  },
  publisherAvatar: {
    width: '32px',
    height: '32px',
    borderRadius: '8px',
    background: 'linear-gradient(135deg, #e94560, #c73652)',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.875rem',
    fontWeight: 700,
    flexShrink: 0,
  },
  publisherInfo: {
    overflow: 'hidden',
    flex: 1,
  },
  publisherName: {
    color: 'white',
    fontSize: '0.8125rem',
    fontWeight: 600,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  publisherTier: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: '0.625rem',
    marginTop: '0.125rem',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  publisherStats: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  publisherStat: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.125rem',
    flex: 1,
  },
  publisherStatValue: {
    color: 'white',
    fontSize: '1rem',
    fontWeight: 700,
    lineHeight: 1,
  },
  publisherStatLabel: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: '0.625rem',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  publisherStatDivider: {
    width: '1px',
    height: '24px',
    background: 'rgba(255,255,255,0.1)',
  },
  version: {
    padding: '0.75rem 1.25rem',
    color: 'rgba(255,255,255,0.2)',
    fontSize: '0.625rem',
    borderTop: '1px solid rgba(255,255,255,0.05)',
    whiteSpace: 'nowrap',
  },
};

export default Sidebar;
