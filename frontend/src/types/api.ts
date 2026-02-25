// ============================================================
// Score & Scoring Types
// ============================================================

export interface ScoreResponse {
  title_id: number;
  title_name: string;
  overall_score: number;
  revenue_score?: number;
  growth_score?: number;
  platform_distribution_score?: number;
  stability_score?: number;
  ranking_frequency_score?: number;
  confidence_rating: 'A' | 'B' | 'C';
  global_potential_score?: number;
  genre_percentile?: number;
  calculated_at: string;
}

// ============================================================
// Trend Types
// ============================================================

export interface TrendDataPoint {
  period: string;
  revenue?: number;
  units_sold?: number;
  engagement_rate?: number;
  overall_score?: number;
}

export interface TrendResponse {
  title_id: number;
  title_name: string;
  data_points: TrendDataPoint[];
  growth_rate_3m?: number;
  growth_rate_6m?: number;
  growth_rate_12m?: number;
}

// ============================================================
// Genre Ranking Types
// ============================================================

export interface RankingEntry {
  rank: number;
  title_name?: string;
  title_id?: number;
  is_own_title: boolean;
  anonymous_label?: string;
  overall_score: number;
  genre_percentile: number;
}

export interface GenreRankingResponse {
  genre: string;
  total_titles: number;
  rankings: RankingEntry[];
  genre_avg_score?: number;
  genre_growth_rate?: number;
}

// ============================================================
// Affinity Types
// ============================================================

export interface AffinityTitle {
  title_id: number;
  title_name: string;
  affinity_score: number;
  shared_audience_pct?: number;
  publisher?: string;
}

export interface AffinityResponse {
  title_id: number;
  title_name: string;
  similar_titles: AffinityTitle[];
  affinity_basis?: string;
}

// ============================================================
// Global Potential Types
// ============================================================

export interface RegionPotential {
  region: string;
  region_label: string;
  potential_score: number;
  market_readiness?: number;
  estimated_audience_size?: number;
  recommended_platforms?: string[];
}

export interface GlobalPotentialResponse {
  title_id: number;
  title_name: string;
  global_potential_score: number;
  region_breakdown: RegionPotential[];
  recommended_markets?: string[];
  localization_notes?: string;
}

// ============================================================
// Alert Types
// ============================================================

export type AlertSeverity = 'critical' | 'warning' | 'info';
export type AlertType =
  | 'rank_drop'
  | 'revenue_spike'
  | 'engagement_drop'
  | 'competitor_surge'
  | 'milestone'
  | 'anomaly';

export interface AlertResponse {
  alert_id: number;
  title_id?: number;
  title_name?: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  message: string;
  detail?: string;
  created_at: string;
  read_at?: string;
  is_read: boolean;
  metadata?: Record<string, unknown>;
}

export interface AlertListResponse {
  alerts: AlertResponse[];
  total: number;
  page: number;
  page_size: number;
  unread_count: number;
}

// ============================================================
// Prediction Types
// ============================================================

export interface PredictionEntry {
  title_id: number;
  title_name: string;
  current_score: number;
  predicted_score_30d?: number;
  predicted_score_90d?: number;
  predicted_revenue_30d?: number;
  trend_direction: 'up' | 'down' | 'stable';
  confidence: number;
  key_factors?: string[];
}

export interface PredictionResponse {
  predictions: PredictionEntry[];
  generated_at: string;
  model_version?: string;
}

// ============================================================
// Upload Types
// ============================================================

export interface UploadResponse {
  upload_id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  rows_processed?: number;
  rows_failed?: number;
  created_at: string;
  completed_at?: string;
  errors?: string[];
}

// ============================================================
// Title Types
// ============================================================

export interface TitleResponse {
  title_id: number;
  title_name: string;
  publisher_id: number;
  genre: string;
  genre_label?: string;
  status: 'active' | 'hiatus' | 'completed';
  platform_ids?: number[];
  created_at: string;
  updated_at?: string;
}

// ============================================================
// Auth Types
// ============================================================

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

export interface PublisherInfo {
  publisher_id: number;
  publisher_name: string;
  tier: 'basic' | 'standard' | 'enterprise';
  title_count: number;
}

// ============================================================
// Pagination & Common Types
// ============================================================

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}
