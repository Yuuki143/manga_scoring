import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { alertApi } from '../services/api';
import { useNavigate } from 'react-router-dom';
import type { AlertResponse, AlertSeverity, AlertType } from '../types/api';

const PAGE_SIZE = 20;

const AlertsPage: React.FC = () => {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<'ALL' | AlertSeverity>('ALL');
  const [filterRead, setFilterRead] = useState<'ALL' | 'UNREAD' | 'READ'>('ALL');
  const [markingAllRead, setMarkingAllRead] = useState(false);

  const fetchAlerts = useCallback(async (pageNum: number) => {
    setLoading(true);
    setError(null);
    try {
      const unreadOnly = filterRead === 'UNREAD' ? true : undefined;
      const res = await alertApi.getAlerts(pageNum, PAGE_SIZE, unreadOnly);
      setAlerts(res.data.alerts);
      setTotal(res.data.total);
      setUnreadCount(res.data.unread_count);
    } catch (err) {
      setError('アラートデータの読み込みに失敗しました。');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filterRead]);

  useEffect(() => {
    fetchAlerts(page);
  }, [fetchAlerts, page]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [filterSeverity, filterRead]);

  const handleMarkRead = useCallback(async (alertId: number) => {
    try {
      await alertApi.markRead(alertId);
      setAlerts((prev) =>
        prev.map((a) =>
          a.alert_id === alertId ? { ...a, is_read: true, read_at: new Date().toISOString() } : a
        )
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error('Failed to mark alert as read:', err);
    }
  }, []);

  const handleMarkAllRead = useCallback(async () => {
    setMarkingAllRead(true);
    try {
      await alertApi.markAllRead();
      setAlerts((prev) =>
        prev.map((a) => ({
          ...a,
          is_read: true,
          read_at: a.read_at || new Date().toISOString(),
        }))
      );
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    } finally {
      setMarkingAllRead(false);
    }
  }, []);

  // Client-side severity filter
  const filteredAlerts = useMemo(() => {
    let result = [...alerts];
    if (filterSeverity !== 'ALL') {
      result = result.filter((a) => a.severity === filterSeverity);
    }
    if (filterRead === 'READ') {
      result = result.filter((a) => a.is_read);
    }
    return result;
  }, [alerts, filterSeverity, filterRead]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="page-title">アラート</h1>
          <p className="page-subtitle">重要な市場動向と異常検知通知</p>
        </div>
        {unreadCount > 0 && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleMarkAllRead}
            disabled={markingAllRead}
          >
            {markingAllRead ? (
              <>
                <span style={spinnerStyle} />
                処理中...
              </>
            ) : (
              <>
                <CheckAllIcon size={14} />
                すべて既読にする ({unreadCount})
              </>
            )}
          </button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <SeveritySummaryCard
          label="緊急"
          severity="critical"
          count={alerts.filter((a) => a.severity === 'critical' && !a.is_read).length}
          total={alerts.filter((a) => a.severity === 'critical').length}
          onClick={() => setFilterSeverity(filterSeverity === 'critical' ? 'ALL' : 'critical')}
          active={filterSeverity === 'critical'}
        />
        <SeveritySummaryCard
          label="警告"
          severity="warning"
          count={alerts.filter((a) => a.severity === 'warning' && !a.is_read).length}
          total={alerts.filter((a) => a.severity === 'warning').length}
          onClick={() => setFilterSeverity(filterSeverity === 'warning' ? 'ALL' : 'warning')}
          active={filterSeverity === 'warning'}
        />
        <SeveritySummaryCard
          label="情報"
          severity="info"
          count={alerts.filter((a) => a.severity === 'info' && !a.is_read).length}
          total={alerts.filter((a) => a.severity === 'info').length}
          onClick={() => setFilterSeverity(filterSeverity === 'info' ? 'ALL' : 'info')}
          active={filterSeverity === 'info'}
        />
        <div
          className="stat-card"
          style={{ cursor: 'pointer', border: filterRead === 'UNREAD' ? '2px solid var(--color-accent)' : undefined }}
          onClick={() => setFilterRead(filterRead === 'UNREAD' ? 'ALL' : 'UNREAD')}
        >
          <span className="stat-label">未読</span>
          <span className="stat-value" style={{ color: unreadCount > 0 ? 'var(--color-accent)' : undefined }}>
            {unreadCount}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontFamily: '"Noto Sans JP", sans-serif' }}>
            未読のみ表示
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <div style={pageStyles.filterBar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', fontFamily: '"Noto Sans JP", sans-serif' }}>
            フィルター:
          </span>
          {(['ALL', 'critical', 'warning', 'info'] as const).map((sev) => (
            <button
              key={sev}
              style={{
                ...pageStyles.filterChip,
                ...(filterSeverity === sev ? pageStyles.filterChipActive : {}),
                ...(sev !== 'ALL' ? { borderColor: getSeverityColor(sev), color: filterSeverity === sev ? 'white' : getSeverityColor(sev), background: filterSeverity === sev ? getSeverityColor(sev) : 'transparent' } : {}),
              }}
              onClick={() => setFilterSeverity(filterSeverity === sev ? 'ALL' : sev)}
            >
              {sev === 'ALL' ? 'すべて' : getSeverityLabel(sev)}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: '"Noto Sans JP", sans-serif' }}>
            {filteredAlerts.length} 件表示
          </span>
        </div>
      </div>

      {/* Alerts List */}
      {loading ? (
        <div className="loading-container">
          <div className="loading-spinner" />
          <span className="loading-text">アラートを読み込み中...</span>
        </div>
      ) : error ? (
        <div className="error-container">
          <div className="error-icon">⚠</div>
          <h2 className="error-title">読み込みエラー</h2>
          <p className="error-message">{error}</p>
          <button className="btn btn-primary" onClick={() => fetchAlerts(page)}>
            再試行
          </button>
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-icon">🔔</span>
          <p style={{ fontFamily: '"Noto Sans JP", sans-serif' }}>アラートはありません</p>
          {filterSeverity !== 'ALL' && (
            <button className="btn btn-ghost btn-sm" onClick={() => setFilterSeverity('ALL')}>
              フィルターをリセット
            </button>
          )}
        </div>
      ) : (
        <div className="card">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {filteredAlerts.map((alert, idx) => (
              <AlertItem
                key={alert.alert_id}
                alert={alert}
                onMarkRead={handleMarkRead}
                onTitleClick={alert.title_id ? () => navigate(`/title/${alert.title_id}`) : undefined}
                isLast={idx === filteredAlerts.length - 1}
              />
            ))}
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !loading && (
        <div className="pagination">
          <button
            className="pagination-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            ← 前
          </button>
          {getPaginationPages(page, totalPages).map((p, idx) =>
            p === '...' ? (
              <span key={`ellipsis-${idx}`} style={{ padding: '0.5rem 0.375rem', color: 'var(--color-text-muted)' }}>...</span>
            ) : (
              <button
                key={p}
                className={`pagination-btn ${page === p ? 'active' : ''}`}
                onClick={() => setPage(p as number)}
              >
                {p}
              </button>
            )
          )}
          <button
            className="pagination-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            次 →
          </button>
        </div>
      )}
    </div>
  );
};

// ============================================================
// Sub-components
// ============================================================

interface AlertItemProps {
  alert: AlertResponse;
  onMarkRead: (id: number) => void;
  onTitleClick?: () => void;
  isLast: boolean;
}

const AlertItem: React.FC<AlertItemProps> = ({ alert, onMarkRead, onTitleClick, isLast }) => {
  return (
    <div
      style={{
        ...itemStyles.container,
        borderBottom: isLast ? 'none' : '1px solid var(--color-border-light)',
        background: alert.is_read ? 'white' : 'rgba(233,69,96,0.02)',
      }}
    >
      {/* Severity indicator */}
      <div
        style={{
          ...itemStyles.severityBar,
          background: getSeverityColor(alert.severity),
          opacity: alert.is_read ? 0.3 : 1,
        }}
      />

      <div style={itemStyles.body}>
        {/* Top row */}
        <div style={itemStyles.topRow}>
          <div style={itemStyles.badges}>
            <span
              style={{
                ...itemStyles.severityBadge,
                background: getSeverityBg(alert.severity),
                color: getSeverityColor(alert.severity),
              }}
            >
              {getSeverityLabel(alert.severity)}
            </span>
            <span style={itemStyles.typeBadge}>
              {getAlertTypeLabel(alert.alert_type)}
            </span>
            {!alert.is_read && <span style={itemStyles.unreadDot} />}
          </div>
          <span style={itemStyles.timestamp}>{formatDateTime(alert.created_at)}</span>
        </div>

        {/* Message */}
        <p style={itemStyles.message}>{alert.message}</p>

        {/* Detail */}
        {alert.detail && (
          <p style={itemStyles.detail}>{alert.detail}</p>
        )}

        {/* Footer */}
        <div style={itemStyles.footer}>
          {alert.title_name && (
            <button
              style={itemStyles.titleLink}
              onClick={onTitleClick}
              disabled={!onTitleClick}
            >
              {alert.title_name} →
            </button>
          )}
          {!alert.is_read && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => onMarkRead(alert.alert_id)}
              style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', padding: '0.25rem 0.5rem' }}
            >
              <CheckIcon size={12} />
              既読にする
            </button>
          )}
          {alert.is_read && alert.read_at && (
            <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontFamily: '"Noto Sans JP", sans-serif' }}>
              既読: {formatDateTime(alert.read_at)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

const SeveritySummaryCard: React.FC<{
  label: string;
  severity: AlertSeverity;
  count: number;
  total: number;
  onClick: () => void;
  active: boolean;
}> = ({ label, severity, count, total, onClick, active }) => (
  <div
    className="stat-card"
    style={{
      cursor: 'pointer',
      border: active ? `2px solid ${getSeverityColor(severity)}` : undefined,
      transition: 'all 150ms',
    }}
    onClick={onClick}
  >
    <span className="stat-label" style={{ color: getSeverityColor(severity) }}>{label}</span>
    <span className="stat-value" style={{ color: getSeverityColor(severity) }}>{count}</span>
    <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontFamily: '"Noto Sans JP", sans-serif' }}>
      未読 / 合計 {total}
    </span>
  </div>
);

// ============================================================
// Icons
// ============================================================

const CheckAllIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const CheckIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

// ============================================================
// Helpers
// ============================================================

function getSeverityColor(severity: AlertSeverity | 'ALL'): string {
  const map: Record<string, string> = {
    critical: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6',
    ALL: '#6b7280',
  };
  return map[severity] || '#6b7280';
}

function getSeverityBg(severity: AlertSeverity): string {
  const map: Record<string, string> = {
    critical: '#fef2f2',
    warning: '#fffbeb',
    info: '#eff6ff',
  };
  return map[severity] || '#f3f4f6';
}

function getSeverityLabel(severity: AlertSeverity | 'ALL'): string {
  const map: Record<string, string> = {
    critical: '緊急',
    warning: '警告',
    info: '情報',
    ALL: 'すべて',
  };
  return map[severity] || severity;
}

function getAlertTypeLabel(type: AlertType): string {
  const map: Record<AlertType, string> = {
    rank_drop: 'ランク下落',
    revenue_spike: '売上急増',
    engagement_drop: 'エンゲージメント低下',
    competitor_surge: '競合急上昇',
    milestone: 'マイルストーン',
    anomaly: '異常検知',
  };
  return map[type] || type;
}

function formatDateTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'たった今';
    if (diffMins < 60) return `${diffMins}分前`;
    if (diffHours < 24) return `${diffHours}時間前`;
    if (diffDays < 7) return `${diffDays}日前`;

    return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return isoStr;
  }
}

function getPaginationPages(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | '...')[] = [1];
  if (current > 3) pages.push('...');
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i);
  }
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
}

// ============================================================
// Styles
// ============================================================

const spinnerStyle: React.CSSProperties = {
  width: '12px',
  height: '12px',
  border: '2px solid rgba(0,0,0,0.2)',
  borderTopColor: 'currentColor',
  borderRadius: '50%',
  display: 'inline-block',
  animation: 'spin 0.8s linear infinite',
};

const pageStyles: Record<string, React.CSSProperties> = {
  filterBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '1.25rem',
    flexWrap: 'wrap' as const,
    gap: '0.75rem',
  },
  filterChip: {
    padding: '0.3rem 0.75rem',
    borderRadius: '9999px',
    fontSize: '0.75rem',
    fontWeight: 500,
    border: '1px solid var(--color-border)',
    background: 'white',
    color: 'var(--color-text-secondary)',
    cursor: 'pointer',
    transition: 'all 150ms',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  filterChipActive: {
    background: 'var(--color-primary)',
    borderColor: 'var(--color-primary)',
    color: 'white',
  },
};

const itemStyles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'stretch',
    transition: 'background 150ms',
  },
  severityBar: {
    width: '4px',
    flexShrink: 0,
  },
  body: {
    flex: 1,
    padding: '1rem 1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  topRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '0.5rem',
    flexWrap: 'wrap' as const,
  },
  badges: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.375rem',
  },
  severityBadge: {
    display: 'inline-block',
    padding: '0.2rem 0.6rem',
    borderRadius: '9999px',
    fontSize: '0.625rem',
    fontWeight: 700,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.04em',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  typeBadge: {
    display: 'inline-block',
    padding: '0.2rem 0.6rem',
    borderRadius: '6px',
    fontSize: '0.625rem',
    fontWeight: 600,
    background: 'var(--color-surface-alt)',
    color: 'var(--color-text-secondary)',
    border: '1px solid var(--color-border)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  unreadDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    background: 'var(--color-accent)',
    flexShrink: 0,
  },
  timestamp: {
    fontSize: '0.6875rem',
    color: 'var(--color-text-muted)',
    whiteSpace: 'nowrap' as const,
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  message: {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: 'var(--color-text-primary)',
    fontFamily: '"Noto Sans JP", sans-serif',
    lineHeight: 1.5,
  },
  detail: {
    fontSize: '0.8125rem',
    color: 'var(--color-text-secondary)',
    fontFamily: '"Noto Sans JP", sans-serif',
    lineHeight: 1.5,
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: '0.25rem',
  },
  titleLink: {
    background: 'none',
    border: 'none',
    color: 'var(--color-accent)',
    fontSize: '0.75rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: '"Noto Sans JP", sans-serif',
    padding: 0,
    transition: 'opacity 150ms',
  },
};

export default AlertsPage;
