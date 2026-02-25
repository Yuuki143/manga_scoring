import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { genreApi } from '../services/api';
import type { GenreRankingResponse, RankingEntry } from '../types/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  TooltipProps,
} from 'recharts';

// Default genres if API doesn't return a list
const DEFAULT_GENRES = [
  { genre: 'action', label: 'アクション' },
  { genre: 'romance', label: '恋愛・ロマンス' },
  { genre: 'fantasy', label: 'ファンタジー' },
  { genre: 'scifi', label: 'SF' },
  { genre: 'horror', label: 'ホラー' },
  { genre: 'sports', label: 'スポーツ' },
  { genre: 'slice_of_life', label: '日常' },
  { genre: 'mystery', label: 'ミステリー' },
  { genre: 'comedy', label: 'コメディ' },
  { genre: 'drama', label: 'ドラマ' },
];

const GenreTrendPage: React.FC = () => {
  const [selectedGenre, setSelectedGenre] = useState<string>(DEFAULT_GENRES[0].genre);
  const [genreList, setGenreList] = useState<{ genre: string; label: string }[]>(DEFAULT_GENRES);
  const [rankingData, setRankingData] = useState<GenreRankingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Try to fetch genre list on mount
  useEffect(() => {
    const fetchGenres = async () => {
      try {
        const res = await genreApi.listGenres();
        if (res.data && res.data.length > 0) {
          setGenreList(res.data);
          setSelectedGenre(res.data[0].genre);
        }
      } catch {
        // Fall back to default genres
      }
    };
    fetchGenres();
  }, []);

  const fetchRanking = useCallback(async (genre: string) => {
    setLoading(true);
    setError(null);
    setRankingData(null);
    try {
      const res = await genreApi.getRanking(genre, 30);
      setRankingData(res.data);
    } catch (err) {
      setError(`${selectedGenreName(genre)} のランキングデータの読み込みに失敗しました。`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedGenre) {
      fetchRanking(selectedGenre);
    }
  }, [selectedGenre, fetchRanking]);

  const selectedGenreName = (genreId: string) => {
    return genreList.find((g) => g.genre === genreId)?.label || genreId;
  };

  // Chart data for top 10 entries
  const chartData = useMemo(() => {
    if (!rankingData) return [];
    return rankingData.rankings.slice(0, 10).map((entry) => ({
      name: entry.is_own_title
        ? entry.title_name || `タイトル #${entry.title_id}`
        : entry.anonymous_label || `競合 ${entry.rank}位`,
      score: Math.round(entry.overall_score),
      percentile: Math.round(entry.genre_percentile),
      isOwn: entry.is_own_title,
      rank: entry.rank,
    }));
  }, [rankingData]);

  const ownTitles = useMemo(
    () => rankingData?.rankings.filter((r) => r.is_own_title) ?? [],
    [rankingData]
  );

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">ジャンル分析</h1>
          <p className="page-subtitle">ジャンル内ランキングと市場動向</p>
        </div>
      </div>

      {/* Genre Selector */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-body" style={{ padding: '1.25rem' }}>
          <div style={pageStyles.selectorRow}>
            <div>
              <label style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)', fontFamily: '"Noto Sans JP", sans-serif', display: 'block', marginBottom: '0.5rem' }}>
                ジャンルを選択
              </label>
              <select
                className="form-select"
                value={selectedGenre}
                onChange={(e) => setSelectedGenre(e.target.value)}
                style={{ minWidth: '200px' }}
              >
                {genreList.map(({ genre, label }) => (
                  <option key={genre} value={genre}>{label}</option>
                ))}
              </select>
            </div>

            {rankingData && (
              <div style={pageStyles.genreStats}>
                <div style={pageStyles.genreStat}>
                  <span style={pageStyles.genreStatValue}>{rankingData.total_titles}</span>
                  <span style={pageStyles.genreStatLabel}>タイトル数</span>
                </div>
                {rankingData.genre_avg_score !== undefined && (
                  <div style={pageStyles.genreStat}>
                    <span style={pageStyles.genreStatValue}>
                      {Math.round(rankingData.genre_avg_score)}
                    </span>
                    <span style={pageStyles.genreStatLabel}>平均スコア</span>
                  </div>
                )}
                {rankingData.genre_growth_rate !== undefined && (
                  <div style={pageStyles.genreStat}>
                    <span
                      style={{
                        ...pageStyles.genreStatValue,
                        color:
                          rankingData.genre_growth_rate > 0
                            ? 'var(--color-score-high)'
                            : 'var(--color-score-low)',
                      }}
                    >
                      {rankingData.genre_growth_rate > 0 ? '+' : ''}
                      {rankingData.genre_growth_rate.toFixed(1)}%
                    </span>
                    <span style={pageStyles.genreStatLabel}>ジャンル成長率</span>
                  </div>
                )}
                <div style={pageStyles.genreStat}>
                  <span style={{ ...pageStyles.genreStatValue, color: 'var(--color-accent)' }}>
                    {ownTitles.length}
                  </span>
                  <span style={pageStyles.genreStatLabel}>自社タイトル</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner" />
          <span className="loading-text">ランキングデータを読み込み中...</span>
        </div>
      )}

      {error && !loading && (
        <div className="error-container">
          <div className="error-icon">⚠</div>
          <h2 className="error-title">読み込みエラー</h2>
          <p className="error-message">{error}</p>
          <button className="btn btn-primary" onClick={() => fetchRanking(selectedGenre)}>
            再試行
          </button>
        </div>
      )}

      {rankingData && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Score Bar Chart */}
          <div className="card">
            <div className="card-header">
              <div>
                <h2 className="card-title">トップ10 スコア比較</h2>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', fontFamily: '"Noto Sans JP", sans-serif' }}>
                  {selectedGenreName(selectedGenre)} ジャンル — 赤: 自社タイトル、青: 競合他社
                </p>
              </div>
            </div>
            <div className="card-body">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={chartData}
                    margin={{ top: 10, right: 20, left: 0, bottom: 40 }}
                    barSize={32}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 10, fill: '#718096' }}
                      axisLine={false}
                      tickLine={false}
                      angle={-25}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: '#718096' }}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 100]}
                    />
                    <Tooltip content={<GenreBarTooltip />} />
                    <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.isOwn ? '#e94560' : '#0f3460'}
                          fillOpacity={entry.isOwn ? 1 : 0.7}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state">チャートデータがありません</div>
              )}
            </div>
          </div>

          {/* Full Ranking Table */}
          <div className="card">
            <div className="card-header">
              <div>
                <h2 className="card-title">ジャンルランキング</h2>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', fontFamily: '"Noto Sans JP", sans-serif' }}>
                  競合タイトルは匿名化されています
                </p>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                全 {rankingData.total_titles} タイトル
              </span>
            </div>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>順位</th>
                    <th>タイトル</th>
                    <th>スコア</th>
                    <th>ジャンル内パーセンタイル</th>
                    <th>種別</th>
                  </tr>
                </thead>
                <tbody>
                  {rankingData.rankings.map((entry) => (
                    <RankingRow key={`${entry.rank}-${entry.title_id}`} entry={entry} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Own Titles Summary */}
          {ownTitles.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">自社タイトル まとめ</h2>
              </div>
              <div className="card-body">
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                    gap: '1rem',
                  }}
                >
                  {ownTitles.map((t) => (
                    <OwnTitleCard key={t.title_id} entry={t} total={rankingData.total_titles} />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {!rankingData && !loading && !error && (
        <div className="empty-state">
          <span className="empty-state-icon">📊</span>
          <p>ジャンルを選択してランキングを表示</p>
        </div>
      )}
    </div>
  );
};

// ============================================================
// Sub-components
// ============================================================

const RankingRow: React.FC<{ entry: RankingEntry }> = ({ entry }) => {
  const displayName = entry.is_own_title
    ? entry.title_name || `タイトル #${entry.title_id}`
    : entry.anonymous_label || `競合タイトル ${entry.rank}位`;

  const scoreColor =
    entry.overall_score >= 70
      ? 'var(--color-score-high)'
      : entry.overall_score >= 40
      ? 'var(--color-score-mid)'
      : 'var(--color-score-low)';

  return (
    <tr
      style={{
        background: entry.is_own_title ? 'rgba(233, 69, 96, 0.04)' : undefined,
      }}
    >
      <td>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            background: entry.rank <= 3 ? getRankBackground(entry.rank) : 'var(--color-surface-alt)',
            color: entry.rank <= 3 ? 'white' : 'var(--color-text-secondary)',
            fontSize: '0.75rem',
            fontWeight: 700,
          }}
        >
          {entry.rank}
        </span>
      </td>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {entry.is_own_title && (
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--color-accent)',
                flexShrink: 0,
              }}
            />
          )}
          <span
            style={{
              fontWeight: entry.is_own_title ? 600 : 400,
              color: entry.is_own_title ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
              fontFamily: entry.is_own_title ? '"Noto Sans JP", sans-serif' : undefined,
            }}
          >
            {displayName}
          </span>
        </div>
      </td>
      <td>
        <span style={{ fontWeight: 700, color: scoreColor, fontSize: '0.9375rem' }}>
          {Math.round(entry.overall_score)}
        </span>
      </td>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="progress-bar-track" style={{ width: '100px' }}>
            <div
              className="progress-bar-fill"
              style={{
                width: `${entry.genre_percentile}%`,
                background: scoreColor,
              }}
            />
          </div>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', minWidth: '40px' }}>
            {Math.round(entry.genre_percentile)}%
          </span>
        </div>
      </td>
      <td>
        {entry.is_own_title ? (
          <span className="badge badge-danger" style={{ fontSize: '0.625rem' }}>自社</span>
        ) : (
          <span className="badge badge-neutral" style={{ fontSize: '0.625rem' }}>競合</span>
        )}
      </td>
    </tr>
  );
};

const OwnTitleCard: React.FC<{ entry: RankingEntry; total: number }> = ({ entry, total }) => {
  const scoreColor =
    entry.overall_score >= 70
      ? 'var(--color-score-high)'
      : entry.overall_score >= 40
      ? 'var(--color-score-mid)'
      : 'var(--color-score-low)';

  const displayName = entry.title_name || `タイトル #${entry.title_id}`;

  return (
    <div
      style={{
        padding: '1rem',
        background: 'var(--color-surface-alt)',
        borderRadius: '10px',
        border: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.625rem',
      }}
    >
      <p
        style={{
          fontSize: '0.875rem',
          fontWeight: 700,
          color: 'var(--color-text-primary)',
          fontFamily: '"Noto Sans JP", sans-serif',
          lineHeight: 1.3,
        }}
      >
        {displayName}
      </p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: '"Noto Sans JP", sans-serif' }}>
          {entry.rank}位 / {total}中
        </span>
        <span style={{ fontSize: '1.25rem', fontWeight: 800, color: scoreColor }}>
          {Math.round(entry.overall_score)}
        </span>
      </div>
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{
            width: `${entry.genre_percentile}%`,
            background: scoreColor,
          }}
        />
      </div>
      <span style={{ fontSize: '0.625rem', color: 'var(--color-text-muted)', textAlign: 'right', fontFamily: '"Noto Sans JP", sans-serif' }}>
        上位 {Math.round(100 - entry.genre_percentile)}%
      </span>
    </div>
  );
};

// ============================================================
// Custom Tooltip
// ============================================================

const GenreBarTooltip: React.FC<TooltipProps<number, string>> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0].payload;
  return (
    <div className="custom-tooltip">
      <p className="custom-tooltip-label">{label}</p>
      <div className="custom-tooltip-item">
        <span className="custom-tooltip-dot" style={{ background: data.isOwn ? '#e94560' : '#0f3460' }} />
        <span>スコア: {data.score}</span>
      </div>
      <div className="custom-tooltip-item">
        <span className="custom-tooltip-dot" style={{ background: 'transparent' }} />
        <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem' }}>
          {data.isOwn ? '自社タイトル' : '競合タイトル'} ({data.rank}位)
        </span>
      </div>
    </div>
  );
};

// ============================================================
// Helpers
// ============================================================

function getRankBackground(rank: number): string {
  if (rank === 1) return '#f59e0b';
  if (rank === 2) return '#9ca3af';
  if (rank === 3) return '#b45309';
  return 'var(--color-surface-alt)';
}

// ============================================================
// Styles
// ============================================================

const pageStyles: Record<string, React.CSSProperties> = {
  selectorRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap' as const,
    gap: '1rem',
  },
  genreStats: {
    display: 'flex',
    gap: '2rem',
    alignItems: 'center',
  },
  genreStat: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.125rem',
  },
  genreStatValue: {
    fontSize: '1.5rem',
    fontWeight: 800,
    color: 'var(--color-text-primary)',
    letterSpacing: '-0.03em',
    lineHeight: 1,
  },
  genreStatLabel: {
    fontSize: '0.625rem',
    color: 'var(--color-text-muted)',
    fontFamily: '"Noto Sans JP", sans-serif',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.04em',
    fontWeight: 600,
  },
};

export default GenreTrendPage;
