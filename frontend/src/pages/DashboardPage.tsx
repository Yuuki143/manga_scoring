import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { titleApi, predictionApi } from '../services/api';
import { useAuth } from '../App';
import ScoreCard from '../components/dashboard/ScoreCard';
import type { ScoreResponse, TrendDataPoint, PredictionEntry } from '../types/api';

interface TitleWithTrend {
  score: ScoreResponse;
  trend: TrendDataPoint[];
}

const DashboardPage: React.FC = () => {
  const { publisher } = useAuth();
  const [titlesData, setTitlesData] = useState<TitleWithTrend[]>([]);
  const [predictions, setPredictions] = useState<PredictionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'score' | 'name' | 'percentile'>('score');
  const [filterConfidence, setFilterConfidence] = useState<'ALL' | 'A' | 'B' | 'C'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch list of titles first
      const titlesRes = await titleApi.listTitles(1, 50);
      const titles = titlesRes.data;

      // Fetch scores and trends in parallel
      const scoresAndTrends = await Promise.allSettled(
        titles.map(async (t) => {
          const [scoreRes, trendRes] = await Promise.allSettled([
            titleApi.getScore(t.title_id),
            titleApi.getTrend(t.title_id, 6),
          ]);

          const score = scoreRes.status === 'fulfilled' ? scoreRes.value.data : null;
          const trend =
            trendRes.status === 'fulfilled' ? trendRes.value.data.data_points : [];

          return score ? { score, trend } : null;
        })
      );

      const validData = scoresAndTrends
        .filter(
          (r): r is PromiseFulfilledResult<TitleWithTrend | null> =>
            r.status === 'fulfilled' && r.value !== null
        )
        .map((r) => r.value!);

      setTitlesData(validData);

      // Fetch predictions
      try {
        const predRes = await predictionApi.getPredictions();
        const preds = Array.isArray(predRes.data) ? predRes.data : (predRes.data as any).predictions || [];
        setPredictions(preds.slice(0, 5));
      } catch {
        // predictions optional
      }
    } catch (err) {
      setError('ダッシュボードデータの読み込みに失敗しました。');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Compute summary stats
  const stats = useMemo(() => {
    if (titlesData.length === 0) return null;
    const scores = titlesData.map((t) => t.score.overall_score);
    const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
    const topPerformer = titlesData.reduce(
      (best, t) => (t.score.overall_score > best.score.overall_score ? t : best),
      titlesData[0]
    );
    const highScoreCount = scores.filter((s) => s >= 70).length;

    return {
      totalTitles: titlesData.length,
      avgScore: Math.round(avgScore),
      topPerformer: topPerformer.score.title_name,
      topScore: Math.round(topPerformer.score.overall_score),
      highScoreCount,
    };
  }, [titlesData]);

  // Filtered and sorted titles
  const filteredTitles = useMemo(() => {
    let result = [...titlesData];

    // Filter by search
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      result = result.filter((t) =>
        t.score.title_name.toLowerCase().includes(q)
      );
    }

    // Filter by confidence
    if (filterConfidence !== 'ALL') {
      result = result.filter(
        (t) => t.score.confidence_rating === filterConfidence
      );
    }

    // Sort
    result.sort((a, b) => {
      if (sortBy === 'score') return b.score.overall_score - a.score.overall_score;
      if (sortBy === 'name') return a.score.title_name.localeCompare(b.score.title_name, 'ja');
      if (sortBy === 'percentile') return (b.score.genre_percentile ?? 0) - (a.score.genre_percentile ?? 0);
      return 0;
    });

    return result;
  }, [titlesData, searchQuery, filterConfidence, sortBy]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <span className="loading-text">ダッシュボードを読み込み中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-icon">⚠</div>
        <h2 className="error-title">読み込みエラー</h2>
        <p className="error-message">{error}</p>
        <button className="btn btn-primary" onClick={fetchDashboardData}>
          再試行
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Page Header */}
      <div className="page-header" style={pageStyles.header}>
        <div>
          <h1 className="page-title">ダッシュボード</h1>
          <p className="page-subtitle">
            {publisher?.publisher_name} &mdash; タイトル パフォーマンス概要
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchDashboardData}>
          <RefreshIcon size={14} />
          更新
        </button>
      </div>

      {/* Summary Stats */}
      {stats && (
        <div className="grid-4" style={{ marginBottom: '2rem' }}>
          <div className="stat-card">
            <span className="stat-label">登録タイトル数</span>
            <span className="stat-value">{stats.totalTitles}</span>
            <span className="stat-change" style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
              アクティブタイトル
            </span>
          </div>
          <div className="stat-card">
            <span className="stat-label">平均スコア</span>
            <span
              className="stat-value"
              style={{
                color:
                  stats.avgScore >= 70
                    ? 'var(--color-score-high)'
                    : stats.avgScore >= 40
                    ? 'var(--color-score-mid)'
                    : 'var(--color-score-low)',
              }}
            >
              {stats.avgScore}
            </span>
            <span className="stat-change" style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
              全タイトル平均
            </span>
          </div>
          <div className="stat-card">
            <span className="stat-label">高スコアタイトル</span>
            <span className="stat-value" style={{ color: 'var(--color-score-high)' }}>
              {stats.highScoreCount}
            </span>
            <span className="stat-change positive">
              スコア 70+ ({Math.round((stats.highScoreCount / stats.totalTitles) * 100)}%)
            </span>
          </div>
          <div className="stat-card">
            <span className="stat-label">トップパフォーマー</span>
            <span
              style={{
                fontSize: '1rem',
                fontWeight: 700,
                color: 'var(--color-text-primary)',
                fontFamily: '"Noto Sans JP", sans-serif',
                lineHeight: 1.3,
                marginTop: '0.25rem',
              }}
            >
              {stats.topPerformer}
            </span>
            <span className="stat-change positive">スコア {stats.topScore}</span>
          </div>
        </div>
      )}

      {/* Predictions Banner */}
      {predictions.length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <div className="card-header">
            <div>
              <h2 className="card-title">予測アラート</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.125rem', fontFamily: '"Noto Sans JP", sans-serif' }}>
                今後30日間の動向予測
              </p>
            </div>
          </div>
          <div className="card-body" style={{ padding: '0' }}>
            <div style={{ overflowX: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>タイトル</th>
                    <th>現在スコア</th>
                    <th>30日後予測</th>
                    <th>トレンド</th>
                    <th>信頼度</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((p) => (
                    <tr key={p.title_id}>
                      <td style={{ fontWeight: 600, fontFamily: '"Noto Sans JP", sans-serif' }}>
                        {p.title_name}
                      </td>
                      <td>
                        <ScorePill value={p.current_score} />
                      </td>
                      <td>
                        {p.predicted_score_30d !== undefined ? (
                          <ScorePill value={p.predicted_score_30d} />
                        ) : '—'}
                      </td>
                      <td>
                        <TrendBadge direction={p.trend_direction} />
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div
                            style={{
                              width: `${p.confidence * 100}%`,
                              height: '6px',
                              background: 'var(--color-secondary)',
                              borderRadius: '3px',
                              maxWidth: '80px',
                              minWidth: '20px',
                            }}
                          />
                          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                            {Math.round(p.confidence * 100)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Title Grid */}
      <div>
        <div style={pageStyles.titleGridHeader}>
          <div>
            <h2 className="section-title">タイトル一覧</h2>
            <p className="section-subtitle">
              {filteredTitles.length} / {titlesData.length} タイトル表示中
            </p>
          </div>
          <div style={pageStyles.controls}>
            {/* Search */}
            <div style={{ position: 'relative' }}>
              <input
                className="form-input"
                placeholder="タイトル検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ paddingLeft: '2rem', width: '200px', fontSize: '0.8125rem' }}
              />
              <span style={pageStyles.searchIcon}>
                <SearchIcon size={14} />
              </span>
            </div>
            {/* Confidence Filter */}
            <select
              className="form-select"
              value={filterConfidence}
              onChange={(e) => setFilterConfidence(e.target.value as typeof filterConfidence)}
              style={{ fontSize: '0.8125rem' }}
            >
              <option value="ALL">全信頼性</option>
              <option value="A">信頼性 A</option>
              <option value="B">信頼性 B</option>
              <option value="C">信頼性 C</option>
            </select>
            {/* Sort */}
            <select
              className="form-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              style={{ fontSize: '0.8125rem' }}
            >
              <option value="score">スコア順</option>
              <option value="name">タイトル名順</option>
              <option value="percentile">ジャンル順位順</option>
            </select>
          </div>
        </div>

        {filteredTitles.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state-icon">📚</span>
            <p>タイトルが見つかりませんでした</p>
            <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
              検索条件を変更してお試しください
            </p>
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '1.25rem',
            }}
          >
            {filteredTitles.map(({ score, trend }) => (
              <ScoreCard key={score.title_id} score={score} trendData={trend} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================
// Sub-components
// ============================================================

const ScorePill: React.FC<{ value: number }> = ({ value }) => {
  const color =
    value >= 70
      ? 'var(--color-score-high)'
      : value >= 40
      ? 'var(--color-score-mid)'
      : 'var(--color-score-low)';
  const bg =
    value >= 70
      ? 'var(--color-score-high-bg)'
      : value >= 40
      ? 'var(--color-score-mid-bg)'
      : 'var(--color-score-low-bg)';

  return (
    <span
      style={{
        display: 'inline-block',
        padding: '0.2rem 0.6rem',
        borderRadius: '9999px',
        background: bg,
        color,
        fontWeight: 700,
        fontSize: '0.8125rem',
      }}
    >
      {Math.round(value)}
    </span>
  );
};

const TrendBadge: React.FC<{ direction: 'up' | 'down' | 'stable' }> = ({ direction }) => {
  const config = {
    up: { label: '上昇', color: 'var(--color-score-high)', bg: 'var(--color-score-high-bg)', icon: '↑' },
    down: { label: '下降', color: 'var(--color-score-low)', bg: 'var(--color-score-low-bg)', icon: '↓' },
    stable: { label: '横ばい', color: 'var(--color-text-muted)', bg: 'var(--color-confidence-c-bg)', icon: '→' },
  }[direction];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.25rem',
        padding: '0.2rem 0.6rem',
        borderRadius: '9999px',
        background: config.bg,
        color: config.color,
        fontWeight: 600,
        fontSize: '0.75rem',
        fontFamily: '"Noto Sans JP", sans-serif',
      }}
    >
      {config.icon} {config.label}
    </span>
  );
};

// ============================================================
// Icons
// ============================================================

const RefreshIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"/>
    <polyline points="1 20 1 14 7 14"/>
    <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
  </svg>
);

const SearchIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/>
    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

// ============================================================
// Styles
// ============================================================

const pageStyles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  titleGridHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: '1.25rem',
    flexWrap: 'wrap' as const,
    gap: '1rem',
  },
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    flexWrap: 'wrap' as const,
  },
  searchIcon: {
    position: 'absolute' as const,
    left: '0.625rem',
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--color-text-muted)',
    display: 'flex',
    alignItems: 'center',
    pointerEvents: 'none' as const,
  },
};

export default DashboardPage;
