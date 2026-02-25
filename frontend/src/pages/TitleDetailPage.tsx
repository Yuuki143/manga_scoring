import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { titleApi } from '../services/api';
import { useAuth } from '../App';
import TrendChart from '../components/charts/TrendChart';
import ScoreRadarChart from '../components/charts/RadarChart';
import HeatmapChart from '../components/charts/HeatmapChart';
import type {
  ScoreResponse,
  TrendResponse,
  AffinityResponse,
  GlobalPotentialResponse,
} from '../types/api';

const TitleDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { publisher } = useAuth();
  const titleId = parseInt(id ?? '0', 10);

  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [trend, setTrend] = useState<TrendResponse | null>(null);
  const [affinity, setAffinity] = useState<AffinityResponse | null>(null);
  const [global, setGlobal] = useState<GlobalPotentialResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'trend' | 'platform' | 'affinity' | 'global'>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isEnterprise = publisher?.tier === 'enterprise';

  const fetchData = useCallback(async () => {
    if (!titleId) return;
    setLoading(true);
    setError(null);

    try {
      const [scoreRes, trendRes] = await Promise.all([
        titleApi.getScore(titleId),
        titleApi.getTrend(titleId, 12),
      ]);
      setScore(scoreRes.data);
      setTrend(trendRes.data);

      // Fetch optional data
      const [affinityRes, globalRes] = await Promise.allSettled([
        titleApi.getAffinity(titleId),
        isEnterprise ? titleApi.getGlobal(titleId) : Promise.reject(new Error('Not enterprise')),
      ]);

      if (affinityRes.status === 'fulfilled') setAffinity(affinityRes.value.data);
      if (globalRes.status === 'fulfilled') setGlobal(globalRes.value.data);
    } catch (err) {
      setError('タイトル詳細データの読み込みに失敗しました。');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [titleId, isEnterprise]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <span className="loading-text">タイトル詳細を読み込み中...</span>
      </div>
    );
  }

  if (error || !score) {
    return (
      <div className="error-container">
        <div className="error-icon">⚠</div>
        <h2 className="error-title">読み込みエラー</h2>
        <p className="error-message">{error || 'タイトルが見つかりませんでした。'}</p>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary" onClick={() => navigate(-1)}>
            ← 戻る
          </button>
          <button className="btn btn-primary" onClick={fetchData}>
            再試行
          </button>
        </div>
      </div>
    );
  }

  const scoreColor =
    score.overall_score >= 70
      ? 'var(--color-score-high)'
      : score.overall_score >= 40
      ? 'var(--color-score-mid)'
      : 'var(--color-score-low)';

  const tabs = [
    { id: 'overview', label: '概要' },
    { id: 'trend', label: 'トレンド' },
    { id: 'platform', label: 'プラットフォーム' },
    { id: 'affinity', label: '類似タイトル' },
    ...(isEnterprise ? [{ id: 'global', label: 'グローバル展開' }] : []),
  ] as const;

  return (
    <div>
      {/* Breadcrumb */}
      <div style={pageStyles.breadcrumb}>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => navigate('/')}
          style={{ paddingLeft: 0 }}
        >
          ← ダッシュボード
        </button>
        <span style={{ color: 'var(--color-text-muted)' }}>/</span>
        <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8125rem' }}>
          タイトル詳細
        </span>
      </div>

      {/* Title Hero Section */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={pageStyles.heroBody}>
          <div style={pageStyles.heroLeft}>
            <div style={pageStyles.titleMark}>
              {score.title_name.charAt(0)}
            </div>
            <div>
              <h1 style={pageStyles.titleName}>{score.title_name}</h1>
              <div style={pageStyles.titleMeta}>
                <span
                  className={`badge badge-confidence-${score.confidence_rating.toLowerCase()}`}
                  style={{ fontSize: '0.6875rem' }}
                >
                  信頼性 {score.confidence_rating}
                </span>
                {score.genre_percentile !== undefined && (
                  <span style={pageStyles.metaBadge}>
                    ジャンル内 上位 {Math.round(100 - score.genre_percentile)}%
                  </span>
                )}
                <span style={pageStyles.metaDate}>
                  更新: {formatDate(score.calculated_at)}
                </span>
              </div>
            </div>
          </div>

          {/* Score display */}
          <div style={pageStyles.heroRight}>
            <div style={{ ...pageStyles.bigScoreCircle, borderColor: scoreColor, background: `${scoreColor}10` }}>
              <span style={{ ...pageStyles.bigScoreNum, color: scoreColor }}>
                {Math.round(score.overall_score)}
              </span>
              <span style={pageStyles.bigScoreLabel}>総合スコア</span>
            </div>

            {/* Sub scores */}
            <div style={pageStyles.subScores}>
              {[
                { label: '売上', value: score.revenue_score },
                { label: '成長性', value: score.growth_score },
                { label: 'プラットフォーム', value: score.platform_distribution_score },
                { label: '安定性', value: score.stability_score },
                { label: 'ランキング', value: score.ranking_frequency_score },
              ]
                .filter((s) => s.value !== undefined)
                .map((s) => (
                  <SubScorePill key={s.label} label={s.label} value={s.value!} />
                ))}
            </div>
          </div>
        </div>
      </div>

      {/* Growth Rates Banner */}
      {trend && (trend.growth_rate_3m !== undefined || trend.growth_rate_6m !== undefined) && (
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          {trend.growth_rate_3m !== undefined && (
            <GrowthCard label="3ヶ月成長率" value={trend.growth_rate_3m} />
          )}
          {trend.growth_rate_6m !== undefined && (
            <GrowthCard label="6ヶ月成長率" value={trend.growth_rate_6m} />
          )}
          {trend.growth_rate_12m !== undefined && (
            <GrowthCard label="12ヶ月成長率" value={trend.growth_rate_12m} />
          )}
        </div>
      )}

      {/* Tabs */}
      <div style={pageStyles.tabBar}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            style={{
              ...pageStyles.tabBtn,
              ...(activeTab === tab.id ? pageStyles.tabBtnActive : {}),
            }}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={pageStyles.tabContent}>
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid-2">
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">スコアレーダー</h2>
              </div>
              <div className="card-body">
                <ScoreRadarChart score={score} height={300} />
              </div>
            </div>
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">売上トレンド（6ヶ月）</h2>
              </div>
              <div className="card-body">
                {trend ? (
                  <TrendChart
                    data={trend.data_points.slice(-6)}
                    showRevenue={true}
                    showEngagement={true}
                    height={280}
                  />
                ) : (
                  <div className="empty-state">データなし</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Trend Tab */}
        {activeTab === 'trend' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="card">
              <div className="card-header">
                <div>
                  <h2 className="card-title">売上・エンゲージメントトレンド</h2>
                  <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', fontFamily: '"Noto Sans JP", sans-serif' }}>
                    過去12ヶ月の推移
                  </p>
                </div>
              </div>
              <div className="card-body">
                {trend ? (
                  <TrendChart
                    data={trend.data_points}
                    showRevenue={true}
                    showEngagement={true}
                    height={350}
                  />
                ) : (
                  <div className="empty-state">トレンドデータがありません</div>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2 className="card-title">スコア推移</h2>
              </div>
              <div className="card-body">
                {trend ? (
                  <TrendChart
                    data={trend.data_points}
                    showRevenue={false}
                    showEngagement={false}
                    showScore={true}
                    height={250}
                  />
                ) : (
                  <div className="empty-state">データなし</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Platform Tab */}
        {activeTab === 'platform' && (
          <div className="card">
            <div className="card-header">
              <div>
                <h2 className="card-title">プラットフォーム分布</h2>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', fontFamily: '"Noto Sans JP", sans-serif' }}>
                  各プラットフォームの売上・エンゲージメント分布
                </p>
              </div>
            </div>
            <div className="card-body">
              {trend && trend.data_points.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                  <div>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '1rem', fontFamily: '"Noto Sans JP", sans-serif', color: 'var(--color-text-secondary)' }}>
                      売上ヒートマップ
                    </h3>
                    <HeatmapChart
                      data={trend.data_points}
                      platforms={['Web', 'iOS', 'Android', 'eBook', 'Print']}
                      metric="revenue"
                    />
                  </div>
                  <hr className="divider" style={{ margin: '0' }} />
                  <div>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '1rem', fontFamily: '"Noto Sans JP", sans-serif', color: 'var(--color-text-secondary)' }}>
                      エンゲージメントヒートマップ
                    </h3>
                    <HeatmapChart
                      data={trend.data_points}
                      platforms={['Web', 'iOS', 'Android', 'eBook', 'Print']}
                      metric="engagement_rate"
                    />
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <p>プラットフォームデータがありません</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Affinity Tab */}
        {activeTab === 'affinity' && (
          <div className="card">
            <div className="card-header">
              <div>
                <h2 className="card-title">類似タイトル</h2>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', fontFamily: '"Noto Sans JP", sans-serif' }}>
                  {affinity?.affinity_basis || '読者層の重複に基づく類似度分析'}
                </p>
              </div>
            </div>
            <div className="card-body">
              {affinity && affinity.similar_titles.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {affinity.similar_titles.map((t, i) => (
                    <div key={t.title_id} style={affinityStyles.item}>
                      <div style={affinityStyles.rank}>{i + 1}</div>
                      <div style={affinityStyles.info}>
                        <p style={affinityStyles.titleName}>{t.title_name}</p>
                        {t.publisher && (
                          <p style={affinityStyles.publisher}>{t.publisher}</p>
                        )}
                      </div>
                      <div style={affinityStyles.right}>
                        {t.shared_audience_pct !== undefined && (
                          <div style={affinityStyles.audienceBar}>
                            <span style={affinityStyles.audienceLabel}>
                              共有読者 {Math.round(t.shared_audience_pct * 100)}%
                            </span>
                            <div className="progress-bar-track" style={{ width: '80px' }}>
                              <div
                                className="progress-bar-fill"
                                style={{
                                  width: `${t.shared_audience_pct * 100}%`,
                                  background: 'var(--color-secondary)',
                                }}
                              />
                            </div>
                          </div>
                        )}
                        <div style={affinityStyles.affinityScore}>
                          <span style={affinityStyles.affinityNum}>
                            {Math.round(t.affinity_score * 100)}%
                          </span>
                          <span style={affinityStyles.affinityLabel}>類似度</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <p>類似タイトルデータがありません</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Global Tab (Enterprise only) */}
        {activeTab === 'global' && isEnterprise && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {global ? (
              <>
                <div className="card">
                  <div className="card-header">
                    <div>
                      <h2 className="card-title">グローバル展開ポテンシャル</h2>
                      <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                        海外市場への展開可能性分析
                      </p>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--color-accent)' }}>
                        {Math.round(global.global_potential_score)}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', display: 'block' }}>
                        グローバルスコア
                      </span>
                    </div>
                  </div>
                  <div className="card-body">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      {global.region_breakdown.map((region) => (
                        <div key={region.region} style={globalStyles.regionRow}>
                          <div style={globalStyles.regionInfo}>
                            <p style={globalStyles.regionLabel}>{region.region_label}</p>
                            {region.recommended_platforms && region.recommended_platforms.length > 0 && (
                              <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                                {region.recommended_platforms.map((p) => (
                                  <span key={p} style={globalStyles.platformTag}>{p}</span>
                                ))}
                              </div>
                            )}
                          </div>
                          <div style={globalStyles.regionScores}>
                            {region.market_readiness !== undefined && (
                              <div style={globalStyles.scoreItem}>
                                <span style={globalStyles.scoreItemLabel}>市場準備度</span>
                                <span style={globalStyles.scoreItemValue}>
                                  {Math.round(region.market_readiness)}
                                </span>
                              </div>
                            )}
                            <div style={globalStyles.scoreItem}>
                              <span style={globalStyles.scoreItemLabel}>ポテンシャル</span>
                              <span
                                style={{
                                  ...globalStyles.scoreItemValue,
                                  color:
                                    region.potential_score >= 70
                                      ? 'var(--color-score-high)'
                                      : region.potential_score >= 40
                                      ? 'var(--color-score-mid)'
                                      : 'var(--color-score-low)',
                                }}
                              >
                                {Math.round(region.potential_score)}
                              </span>
                            </div>
                          </div>
                          <div style={{ flex: 1, maxWidth: '120px' }}>
                            <div className="progress-bar-track">
                              <div
                                className="progress-bar-fill"
                                style={{
                                  width: `${region.potential_score}%`,
                                  background:
                                    region.potential_score >= 70
                                      ? 'var(--color-score-high)'
                                      : region.potential_score >= 40
                                      ? 'var(--color-score-mid)'
                                      : 'var(--color-score-low)',
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {global.localization_notes && (
                      <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--color-surface-alt)', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                        <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '0.375rem' }}>
                          ローカライゼーションノート
                        </p>
                        <p style={{ fontSize: '0.875rem', color: 'var(--color-text-primary)', fontFamily: '"Noto Sans JP", sans-serif', lineHeight: 1.6 }}>
                          {global.localization_notes}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {global.recommended_markets && global.recommended_markets.length > 0 && (
                  <div className="card">
                    <div className="card-header">
                      <h2 className="card-title">推奨市場</h2>
                    </div>
                    <div className="card-body">
                      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                        {global.recommended_markets.map((market) => (
                          <span key={market} className="badge badge-info" style={{ fontSize: '0.8125rem', padding: '0.375rem 0.875rem' }}>
                            {market}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <p>グローバルデータがありません</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================
// Sub-components
// ============================================================

const SubScorePill: React.FC<{ label: string; value: number }> = ({ label, value }) => {
  const color =
    value >= 70 ? 'var(--color-score-high)' : value >= 40 ? 'var(--color-score-mid)' : 'var(--color-score-low)';
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.125rem',
        padding: '0.5rem 0.75rem',
        background: 'var(--color-surface-alt)',
        borderRadius: '8px',
        border: '1px solid var(--color-border)',
        minWidth: '70px',
      }}
    >
      <span style={{ fontSize: '1.125rem', fontWeight: 700, color }}>{Math.round(value)}</span>
      <span style={{ fontSize: '0.625rem', color: 'var(--color-text-muted)', fontFamily: '"Noto Sans JP", sans-serif', textAlign: 'center', lineHeight: 1.2 }}>
        {label}
      </span>
    </div>
  );
};

const GrowthCard: React.FC<{ label: string; value: number }> = ({ label, value }) => {
  const isPositive = value > 0;
  const color = isPositive ? 'var(--color-score-high)' : value < 0 ? 'var(--color-score-low)' : 'var(--color-text-muted)';
  return (
    <div
      style={{
        background: 'white',
        border: '1px solid var(--color-border)',
        borderRadius: '10px',
        padding: '0.875rem 1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
        flex: 1,
        minWidth: '140px',
      }}
    >
      <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontFamily: '"Noto Sans JP", sans-serif' }}>
        {label}
      </span>
      <span style={{ fontSize: '1.5rem', fontWeight: 800, color, letterSpacing: '-0.03em' }}>
        {isPositive ? '+' : ''}{value.toFixed(1)}%
      </span>
    </div>
  );
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

const pageStyles: Record<string, React.CSSProperties> = {
  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '1.5rem',
  },
  heroBody: {
    padding: '1.5rem',
    display: 'flex',
    gap: '1.5rem',
    alignItems: 'flex-start',
    flexWrap: 'wrap' as const,
  },
  heroLeft: {
    display: 'flex',
    gap: '1rem',
    alignItems: 'flex-start',
    flex: 1,
    minWidth: '250px',
  },
  titleMark: {
    width: '56px',
    height: '56px',
    borderRadius: '12px',
    background: 'linear-gradient(135deg, #1a1a2e, #0f3460)',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '1.5rem',
    fontWeight: 700,
    flexShrink: 0,
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  titleName: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: 'var(--color-text-primary)',
    fontFamily: '"Noto Sans JP", sans-serif',
    letterSpacing: '-0.02em',
    lineHeight: 1.2,
    marginBottom: '0.5rem',
  },
  titleMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    flexWrap: 'wrap' as const,
  },
  metaBadge: {
    fontSize: '0.6875rem',
    color: 'var(--color-text-secondary)',
    background: 'var(--color-surface-alt)',
    border: '1px solid var(--color-border)',
    borderRadius: '9999px',
    padding: '0.2rem 0.6rem',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  metaDate: {
    fontSize: '0.6875rem',
    color: 'var(--color-text-muted)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  heroRight: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '1rem',
  },
  bigScoreCircle: {
    width: '100px',
    height: '100px',
    borderRadius: '50%',
    border: '4px solid',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.125rem',
  },
  bigScoreNum: {
    fontSize: '2rem',
    fontWeight: 800,
    lineHeight: 1,
    letterSpacing: '-0.04em',
  },
  bigScoreLabel: {
    fontSize: '0.5625rem',
    color: 'var(--color-text-muted)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  subScores: {
    display: 'flex',
    gap: '0.5rem',
    flexWrap: 'wrap' as const,
    justifyContent: 'center',
    maxWidth: '400px',
  },
  tabBar: {
    display: 'flex',
    gap: '0.25rem',
    borderBottom: '2px solid var(--color-border)',
    marginBottom: '1.5rem',
    overflowX: 'auto' as const,
  },
  tabBtn: {
    padding: '0.625rem 1.125rem',
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    marginBottom: '-2px',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: 500,
    color: 'var(--color-text-muted)',
    whiteSpace: 'nowrap' as const,
    transition: 'all 150ms',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  tabBtnActive: {
    borderBottomColor: 'var(--color-accent)',
    color: 'var(--color-accent)',
    fontWeight: 600,
  },
  tabContent: {
    animation: 'fadeIn 200ms ease-out',
  },
};

const affinityStyles: Record<string, React.CSSProperties> = {
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    padding: '0.875rem 1rem',
    background: 'var(--color-surface-alt)',
    borderRadius: '10px',
    border: '1px solid var(--color-border)',
  },
  rank: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    background: 'var(--color-primary)',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.75rem',
    fontWeight: 700,
    flexShrink: 0,
  },
  info: {
    flex: 1,
  },
  titleName: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--color-text-primary)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  publisher: {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    marginTop: '0.125rem',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  audienceBar: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '0.25rem',
  },
  audienceLabel: {
    fontSize: '0.625rem',
    color: 'var(--color-text-muted)',
    whiteSpace: 'nowrap' as const,
  },
  affinityScore: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  affinityNum: {
    fontSize: '1.125rem',
    fontWeight: 800,
    color: 'var(--color-accent)',
  },
  affinityLabel: {
    fontSize: '0.5625rem',
    color: 'var(--color-text-muted)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
};

const globalStyles: Record<string, React.CSSProperties> = {
  regionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '1.5rem',
    padding: '0.875rem',
    background: 'var(--color-surface-alt)',
    borderRadius: '10px',
    border: '1px solid var(--color-border)',
    flexWrap: 'wrap' as const,
  },
  regionInfo: {
    flex: 1,
    minWidth: '150px',
  },
  regionLabel: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--color-text-primary)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  regionScores: {
    display: 'flex',
    gap: '1.5rem',
  },
  scoreItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.125rem',
  },
  scoreItemLabel: {
    fontSize: '0.5625rem',
    color: 'var(--color-text-muted)',
    fontFamily: '"Noto Sans JP", sans-serif',
  },
  scoreItemValue: {
    fontSize: '1.125rem',
    fontWeight: 700,
    color: 'var(--color-text-primary)',
  },
  platformTag: {
    fontSize: '0.625rem',
    background: '#e0e7ff',
    color: '#4338ca',
    borderRadius: '4px',
    padding: '0.125rem 0.5rem',
    fontWeight: 500,
  },
};

export default TitleDetailPage;
