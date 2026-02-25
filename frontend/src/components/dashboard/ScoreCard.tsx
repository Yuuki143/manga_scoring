import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts';
import type { ScoreResponse, TrendDataPoint } from '../../types/api';

interface ScoreCardProps {
  score: ScoreResponse;
  trendData?: TrendDataPoint[];
}

const ScoreCard: React.FC<ScoreCardProps> = ({ score, trendData }) => {
  const navigate = useNavigate();

  const scoreColor = useMemo(() => {
    if (score.overall_score >= 70) return 'var(--color-score-high)';
    if (score.overall_score >= 40) return 'var(--color-score-mid)';
    return 'var(--color-score-low)';
  }, [score.overall_score]);

  const scoreBg = useMemo(() => {
    if (score.overall_score >= 70) return 'var(--color-score-high-bg)';
    if (score.overall_score >= 40) return 'var(--color-score-mid-bg)';
    return 'var(--color-score-low-bg)';
  }, [score.overall_score]);

  const confidenceClass = useMemo(() => {
    const map: Record<string, string> = {
      A: 'badge-confidence-a',
      B: 'badge-confidence-b',
      C: 'badge-confidence-c',
    };
    return map[score.confidence_rating] || 'badge-confidence-c';
  }, [score.confidence_rating]);

  const confidenceLabel = useMemo(() => {
    const map: Record<string, string> = {
      A: '信頼性 A',
      B: '信頼性 B',
      C: '信頼性 C',
    };
    return map[score.confidence_rating] || score.confidence_rating;
  }, [score.confidence_rating]);

  const sparklineData = useMemo(() => {
    if (!trendData || trendData.length === 0) return [];
    return trendData.slice(-6).map((d, i) => ({
      i,
      v: d.overall_score ?? d.revenue ?? 0,
    }));
  }, [trendData]);

  const handleClick = () => {
    navigate(`/title/${score.title_id}`);
  };

  const percentile = score.genre_percentile ?? 0;

  return (
    <div
      style={styles.card}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
      aria-label={`${score.title_name} - スコア ${score.overall_score}`}
    >
      {/* Header strip */}
      <div style={{ ...styles.headerStrip, background: scoreColor }} />

      <div style={styles.body}>
        {/* Title & Confidence */}
        <div style={styles.titleRow}>
          <h3 style={styles.titleName} title={score.title_name}>
            {score.title_name}
          </h3>
          <span className={`badge ${confidenceClass}`} style={{ flexShrink: 0 }}>
            {confidenceLabel}
          </span>
        </div>

        {/* Score Display */}
        <div style={styles.scoreSection}>
          <div style={{ ...styles.scoreCircle, background: scoreBg, borderColor: scoreColor }}>
            <span style={{ ...styles.scoreNumber, color: scoreColor }}>
              {Math.round(score.overall_score)}
            </span>
            <span style={styles.scoreMax}>/100</span>
          </div>

          {/* Sparkline */}
          <div style={styles.sparklineContainer}>
            {sparklineData.length > 1 ? (
              <ResponsiveContainer width="100%" height={48}>
                <LineChart data={sparklineData}>
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke={scoreColor}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={styles.noSparkline}>
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.6875rem' }}>
                  トレンドデータなし
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Score sub-metrics */}
        <div style={styles.metrics}>
          {score.revenue_score !== undefined && (
            <ScoreMetric label="売上" value={score.revenue_score} />
          )}
          {score.growth_score !== undefined && (
            <ScoreMetric label="成長" value={score.growth_score} />
          )}
          {score.stability_score !== undefined && (
            <ScoreMetric label="安定性" value={score.stability_score} />
          )}
        </div>

        {/* Genre percentile bar */}
        <div style={styles.percentileSection}>
          <div style={styles.percentileLabel}>
            <span style={styles.percentileLabelText}>ジャンル内順位</span>
            <span style={styles.percentileValue}>
              上位 {Math.round(100 - percentile)}%
            </span>
          </div>
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{
                width: `${percentile}%`,
                background: scoreColor,
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <span style={styles.footerDate}>
            {formatDate(score.calculated_at)}
          </span>
          <span style={styles.viewDetail}>詳細を見る →</span>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Sub-components
// ============================================================

const ScoreMetric: React.FC<{ label: string; value: number }> = ({ label, value }) => {
  const color = value >= 70 ? 'var(--color-score-high)' : value >= 40 ? 'var(--color-score-mid)' : 'var(--color-score-low)';
  return (
    <div style={metricStyles.item}>
      <span style={metricStyles.label}>{label}</span>
      <span style={{ ...metricStyles.value, color }}>{Math.round(value)}</span>
    </div>
  );
};

const metricStyles: Record<string, React.CSSProperties> = {
  item: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.125rem',
    flex: 1,
  },
  label: {
    fontSize: '0.625rem',
    color: 'var(--color-text-muted)',
    fontFamily: '"Noto Sans JP", sans-serif',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.04em',
  },
  value: {
    fontSize: '0.9375rem',
    fontWeight: 700,
  },
};

// ============================================================
// Helpers
// ============================================================

function formatDate(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return isoStr;
  }
}

// ============================================================
// Styles
// ============================================================

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: 'var(--color-surface)',
    borderRadius: 'var(--border-radius-lg)',
    border: '1px solid var(--color-border)',
    boxShadow: 'var(--shadow-sm)',
    cursor: 'pointer',
    transition: 'transform 200ms ease, box-shadow 200ms ease',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
  },
  headerStrip: {
    height: '3px',
    width: '100%',
  },
  body: {
    padding: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '0.5rem',
  },
  titleName: {
    fontSize: '0.9375rem',
    fontWeight: 700,
    color: 'var(--color-text-primary)',
    fontFamily: '"Noto Sans JP", sans-serif',
    lineHeight: 1.3,
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  scoreSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  scoreCircle: {
    width: '72px',
    height: '72px',
    borderRadius: '50%',
    border: '3px solid',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  scoreNumber: {
    fontSize: '1.375rem',
    fontWeight: 800,
    lineHeight: 1,
    letterSpacing: '-0.03em',
  },
  scoreMax: {
    fontSize: '0.625rem',
    color: 'var(--color-text-muted)',
    lineHeight: 1,
    marginTop: '0.125rem',
  },
  sparklineContainer: {
    flex: 1,
    height: '48px',
  },
  noSparkline: {
    height: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--color-surface-alt)',
    borderRadius: '6px',
  },
  metrics: {
    display: 'flex',
    gap: '0.5rem',
    padding: '0.75rem',
    background: 'var(--color-surface-alt)',
    borderRadius: '8px',
  },
  percentileSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.375rem',
  },
  percentileLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  percentileLabelText: {
    fontSize: '0.6875rem',
    color: 'var(--color-text-muted)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  percentileValue: {
    fontSize: '0.6875rem',
    fontWeight: 600,
    color: 'var(--color-text-secondary)',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '0.75rem',
    borderTop: '1px solid var(--color-border-light)',
  },
  footerDate: {
    fontSize: '0.6875rem',
    color: 'var(--color-text-muted)',
  },
  viewDetail: {
    fontSize: '0.6875rem',
    color: 'var(--color-accent)',
    fontWeight: 600,
  },
};

export default ScoreCard;
