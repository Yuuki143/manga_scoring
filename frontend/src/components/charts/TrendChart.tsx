import React, { useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  TooltipProps,
} from 'recharts';
import type { TrendDataPoint } from '../../types/api';

interface TrendChartProps {
  data: TrendDataPoint[];
  showRevenue?: boolean;
  showEngagement?: boolean;
  showScore?: boolean;
  height?: number;
}

const TrendChart: React.FC<TrendChartProps> = ({
  data,
  showRevenue = true,
  showEngagement = true,
  showScore = false,
  height = 300,
}) => {
  const chartData = useMemo(() => {
    return data.map((d) => ({
      period: formatPeriod(d.period),
      revenue: d.revenue,
      engagement: d.engagement_rate !== undefined ? +(d.engagement_rate * 100).toFixed(1) : undefined,
      score: d.overall_score,
      units: d.units_sold,
    }));
  }, [data]);

  const hasRevenue = showRevenue && data.some((d) => d.revenue !== undefined);
  const hasEngagement = showEngagement && data.some((d) => d.engagement_rate !== undefined);
  const hasScore = showScore && data.some((d) => d.overall_score !== undefined);

  if (chartData.length === 0) {
    return (
      <div className="empty-state" style={{ height }}>
        <span style={{ fontSize: '2rem' }}>📈</span>
        <p>トレンドデータがありません</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0f3460" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#0f3460" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
        <XAxis
          dataKey="period"
          tick={{ fontSize: 11, fill: '#718096' }}
          axisLine={false}
          tickLine={false}
          dy={8}
        />
        {hasRevenue && (
          <YAxis
            yAxisId="revenue"
            orientation="left"
            tick={{ fontSize: 11, fill: '#718096' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => formatYen(v)}
            width={60}
          />
        )}
        {(hasEngagement || hasScore) && (
          <YAxis
            yAxisId="rate"
            orientation="right"
            tick={{ fontSize: 11, fill: '#718096' }}
            axisLine={false}
            tickLine={false}
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            width={45}
          />
        )}
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }}
          formatter={(value) => legendLabels[value] || value}
        />
        {hasRevenue && (
          <Bar
            yAxisId="revenue"
            dataKey="revenue"
            fill="#0f3460"
            fillOpacity={0.15}
            stroke="#0f3460"
            strokeWidth={0}
            radius={[3, 3, 0, 0]}
            name="revenue"
          />
        )}
        {hasRevenue && (
          <Line
            yAxisId="revenue"
            type="monotone"
            dataKey="revenue"
            stroke="#0f3460"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5, fill: '#0f3460' }}
            name="revenueLine"
          />
        )}
        {hasEngagement && (
          <Line
            yAxisId="rate"
            type="monotone"
            dataKey="engagement"
            stroke="#e94560"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5, fill: '#e94560' }}
            strokeDasharray="5 3"
            name="engagement"
          />
        )}
        {hasScore && (
          <Line
            yAxisId="rate"
            type="monotone"
            dataKey="score"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: '#22c55e' }}
            name="score"
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
};

// ============================================================
// Custom Tooltip
// ============================================================

const CustomTooltip: React.FC<TooltipProps<number, string>> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="custom-tooltip">
      <p className="custom-tooltip-label">{label}</p>
      {payload.map((entry) => {
        if (entry.name === 'revenueLine') return null; // skip duplicate
        const displayName = legendLabels[entry.name ?? ''] || entry.name;
        const formattedValue =
          entry.name === 'revenue'
            ? formatYen(entry.value as number)
            : entry.name === 'engagement'
            ? `${entry.value}%`
            : String(entry.value);
        return (
          <div key={entry.name} className="custom-tooltip-item">
            <span
              className="custom-tooltip-dot"
              style={{ background: entry.color }}
            />
            <span>{displayName}: {formattedValue}</span>
          </div>
        );
      })}
    </div>
  );
};

// ============================================================
// Helpers
// ============================================================

const legendLabels: Record<string, string> = {
  revenue: '売上',
  revenueLine: '売上(線)',
  engagement: 'エンゲージメント率',
  score: 'スコア',
  units: '販売数',
};

function formatPeriod(period: string): string {
  // Handle YYYY-MM format
  const match = period.match(/^(\d{4})-(\d{2})$/);
  if (match) {
    const month = parseInt(match[2], 10);
    return `${match[1].slice(2)}/${month}月`;
  }
  return period;
}

function formatYen(value: number): string {
  if (value >= 100000000) return `${(value / 100000000).toFixed(1)}億`;
  if (value >= 10000) return `${(value / 10000).toFixed(0)}万`;
  return String(value);
}

export default TrendChart;
