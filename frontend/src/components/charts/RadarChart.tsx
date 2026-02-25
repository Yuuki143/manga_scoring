import React from 'react';
import {
  RadarChart as RechartsRadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
  TooltipProps,
} from 'recharts';
import type { ScoreResponse } from '../../types/api';

interface RadarChartProps {
  score: ScoreResponse;
  height?: number;
  showLegend?: boolean;
}

interface RadarDataPoint {
  axis: string;
  axisJP: string;
  value: number;
  fullMark: number;
}

const ScoreRadarChart: React.FC<RadarChartProps> = ({
  score,
  height = 320,
  showLegend = true,
}) => {
  const data: RadarDataPoint[] = [
    {
      axis: 'Revenue',
      axisJP: '売上',
      value: score.revenue_score ?? 0,
      fullMark: 100,
    },
    {
      axis: 'Growth',
      axisJP: '成長性',
      value: score.growth_score ?? 0,
      fullMark: 100,
    },
    {
      axis: 'Platform',
      axisJP: 'プラットフォーム',
      value: score.platform_distribution_score ?? 0,
      fullMark: 100,
    },
    {
      axis: 'Stability',
      axisJP: '安定性',
      value: score.stability_score ?? 0,
      fullMark: 100,
    },
    {
      axis: 'Ranking',
      axisJP: 'ランキング',
      value: score.ranking_frequency_score ?? 0,
      fullMark: 100,
    },
  ];

  const hasData = data.some((d) => d.value > 0);

  if (!hasData) {
    return (
      <div className="empty-state" style={{ height }}>
        <span style={{ fontSize: '2rem' }}>📊</span>
        <p>スコアデータが不足しています</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsRadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <defs>
          <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#e94560" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#e94560" stopOpacity={0.05} />
          </radialGradient>
        </defs>
        <PolarGrid
          stroke="rgba(0,0,0,0.08)"
          gridType="polygon"
        />
        <PolarAngleAxis
          dataKey="axisJP"
          tick={{ fontSize: 12, fill: '#4a5568', fontFamily: '"Noto Sans JP", sans-serif' }}
          tickLine={false}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickCount={6}
        />
        <Tooltip content={<RadarTooltip />} />
        <Radar
          name={score.title_name}
          dataKey="value"
          stroke="#e94560"
          strokeWidth={2.5}
          fill="url(#radarFill)"
          dot={{ r: 4, fill: '#e94560', strokeWidth: 0 }}
          activeDot={{ r: 6, fill: '#e94560', stroke: 'white', strokeWidth: 2 }}
        />
        {showLegend && (
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
          />
        )}
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
};

// ============================================================
// Custom Tooltip
// ============================================================

const RadarTooltip: React.FC<TooltipProps<number, string>> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) return null;

  const item = payload[0];
  const data = item.payload as RadarDataPoint;

  const color =
    data.value >= 70
      ? 'var(--color-score-high)'
      : data.value >= 40
      ? 'var(--color-score-mid)'
      : 'var(--color-score-low)';

  return (
    <div className="custom-tooltip">
      <p className="custom-tooltip-label">{data.axisJP}</p>
      <div className="custom-tooltip-item">
        <span className="custom-tooltip-dot" style={{ background: color }} />
        <span style={{ color }}>
          {Math.round(data.value)} / 100
        </span>
      </div>
    </div>
  );
};

export default ScoreRadarChart;
