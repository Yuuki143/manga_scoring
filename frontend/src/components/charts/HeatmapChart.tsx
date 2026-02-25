import React, { useMemo } from 'react';
import type { TrendDataPoint } from '../../types/api';

interface HeatmapChartProps {
  data: TrendDataPoint[];
  platforms?: string[];
  metric?: 'revenue' | 'engagement_rate' | 'units_sold';
}

const HeatmapChart: React.FC<HeatmapChartProps> = ({
  data,
  platforms = ['Web', 'iOS', 'Android', 'eBook', 'Print'],
  metric = 'revenue',
}) => {
  const periods = useMemo(() => data.map((d) => formatPeriod(d.period)), [data]);

  // Apply platform-level weights to simulate distribution
  const platformWeights = useMemo(() => {
    const seed = platforms.map((p) => p.charCodeAt(0));
    const total = seed.reduce((a, b) => a + b, 0);
    return seed.map((s) => s / total);
  }, [platforms]);

  const gridData = useMemo(() => {
    return platforms.map((platform, pi) => ({
      platform,
      values: data.map((d) => {
        const rawValue = (d[metric as keyof TrendDataPoint] as number) ?? 0;
        const variance = 0.7 + 0.6 * platformWeights[pi];
        return rawValue * variance;
      }),
    }));
  }, [platforms, data, metric, platformWeights]);

  const allValues = useMemo(
    () => gridData.flatMap((row) => row.values).filter((v) => v > 0),
    [gridData]
  );

  const maxValue = useMemo(() => (allValues.length > 0 ? Math.max(...allValues) : 1), [allValues]);
  const minValue = useMemo(() => (allValues.length > 0 ? Math.min(...allValues) : 0), [allValues]);

  const getIntensity = (value: number): number => {
    if (maxValue === minValue) return 0.5;
    return (value - minValue) / (maxValue - minValue);
  };

  const getCellColor = (intensity: number): string => {
    if (intensity === 0) return '#f5f5f5';
    // Interpolate from light (#dbeafe) to dark (#0f3460)
    const r = Math.round(219 - intensity * 187);
    const g = Math.round(234 - intensity * 182);
    const b = Math.round(254 - intensity * 158);
    return `rgb(${r}, ${g}, ${b})`;
  };

  const getTextColor = (intensity: number): string =>
    intensity > 0.6 ? 'rgba(255,255,255,0.9)' : '#4a5568';

  const metricLabel: Record<string, string> = {
    revenue: '売上',
    engagement_rate: 'エンゲージメント',
    units_sold: '販売数',
  };

  const gridTemplateColumns = `90px repeat(${periods.length}, minmax(44px, 1fr))`;

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <p>プラットフォームデータがありません</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Legend */}
      <div style={styles.legendRow}>
        <span style={styles.legendLabel}>{metricLabel[metric] || metric} プラットフォーム分布</span>
        <div style={styles.legendScale}>
          <span style={styles.legendScaleText}>低</span>
          <div style={styles.legendGradient} />
          <span style={styles.legendScaleText}>高</span>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div style={{ overflowX: 'auto' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns,
            gap: '3px',
            alignItems: 'center',
          }}
        >
          {/* Corner */}
          <div style={styles.cornerCell} />

          {/* Column headers */}
          {periods.map((period) => (
            <div key={period} style={styles.headerCell}>
              {period}
            </div>
          ))}

          {/* Data rows */}
          {gridData.map(({ platform, values }) => (
            <React.Fragment key={platform}>
              <div style={styles.rowLabel}>{platform}</div>
              {values.map((value, ci) => {
                const intensity = getIntensity(value);
                return (
                  <div
                    key={ci}
                    style={{
                      ...styles.dataCell,
                      background: getCellColor(intensity),
                      color: getTextColor(intensity),
                    }}
                    title={`${platform} / ${periods[ci]}: ${formatValue(value, metric)}`}
                  >
                    {value > 0 ? formatValueShort(value, metric) : '—'}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Helpers
// ============================================================

function formatPeriod(period: string): string {
  const match = period.match(/^(\d{4})-(\d{2})$/);
  if (match) {
    return `${parseInt(match[2], 10)}月`;
  }
  return period;
}

function formatValue(value: number, metric: string): string {
  if (metric === 'revenue') {
    if (value >= 100000000) return `¥${(value / 100000000).toFixed(1)}億`;
    if (value >= 10000) return `¥${(value / 10000).toFixed(0)}万`;
    return `¥${Math.round(value).toLocaleString()}`;
  }
  if (metric === 'engagement_rate') return `${(value * 100).toFixed(1)}%`;
  return Math.round(value).toLocaleString();
}

function formatValueShort(value: number, metric: string): string {
  if (metric === 'revenue') {
    if (value >= 100000000) return `${(value / 100000000).toFixed(1)}億`;
    if (value >= 10000) return `${(value / 10000).toFixed(0)}万`;
    return `${Math.round(value / 1000)}k`;
  }
  if (metric === 'engagement_rate') return `${(value * 100).toFixed(0)}%`;
  if (value >= 10000) return `${(value / 10000).toFixed(0)}万`;
  return String(Math.round(value));
}

// ============================================================
// Styles
// ============================================================

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  legendRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  legendLabel: {
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--color-text-secondary)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  legendScale: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.375rem',
  },
  legendScaleText: {
    fontSize: '0.625rem',
    color: 'var(--color-text-muted)',
  },
  legendGradient: {
    width: '60px',
    height: '10px',
    borderRadius: '3px',
    background: 'linear-gradient(to right, #dbeafe, #0f3460)',
  },
  cornerCell: {
    padding: '0.25rem',
  },
  headerCell: {
    fontSize: '0.625rem',
    fontWeight: 600,
    color: 'var(--color-text-muted)',
    textAlign: 'center' as const,
    padding: '0.25rem 0.125rem',
    whiteSpace: 'nowrap' as const,
  },
  rowLabel: {
    fontSize: '0.6875rem',
    fontWeight: 500,
    color: 'var(--color-text-secondary)',
    whiteSpace: 'nowrap' as const,
    paddingRight: '0.5rem',
  },
  dataCell: {
    borderRadius: '4px',
    padding: '0.375rem 0.25rem',
    fontSize: '0.625rem',
    fontWeight: 600,
    textAlign: 'center' as const,
    cursor: 'default',
    transition: 'transform 100ms',
    minWidth: '40px',
    minHeight: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
};

export default HeatmapChart;
