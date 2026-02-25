import axios, { AxiosError } from 'axios';
import type {
  ScoreResponse,
  TrendResponse,
  AffinityResponse,
  GlobalPotentialResponse,
  GenreRankingResponse,
  AlertListResponse,
  AlertResponse,
  PredictionResponse,
  UploadResponse,
  AuthTokenResponse,
  PublisherInfo,
  TitleResponse,
} from '../types/api';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach JWT token if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('mmip_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 globally
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('mmip_token');
      localStorage.removeItem('mmip_publisher');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============================================================
// Title API
// ============================================================

export const titleApi = {
  getScore: (titleId: number) =>
    api.get<ScoreResponse>(`/titles/${titleId}/score`),

  getTrend: (titleId: number, months?: number) =>
    api.get<TrendResponse>(`/titles/${titleId}/trend`, {
      params: months ? { months } : undefined,
    }),

  getAffinity: (titleId: number) =>
    api.get<AffinityResponse>(`/titles/${titleId}/affinity`),

  getGlobal: (titleId: number) =>
    api.get<GlobalPotentialResponse>(`/titles/${titleId}/global`),

  getTitle: (titleId: number) =>
    api.get<TitleResponse>(`/titles/${titleId}`),

  listTitles: (page?: number, pageSize?: number) =>
    api.get<TitleResponse[]>('/titles', { params: { page, page_size: pageSize } }),
};

// ============================================================
// Genre API
// ============================================================

export const genreApi = {
  getRanking: (genre: string, limit?: number) =>
    api.get<GenreRankingResponse>(`/genres/${genre}/ranking`, {
      params: limit ? { limit } : undefined,
    }),

  listGenres: () =>
    api.get<{ genre: string; label: string }[]>('/genres'),
};

// ============================================================
// Alert API
// ============================================================

export const alertApi = {
  getAlerts: (page?: number, pageSize?: number, unreadOnly?: boolean) =>
    api.get<AlertListResponse>('/alerts', {
      params: { page, page_size: pageSize, unread_only: unreadOnly },
    }),

  markRead: (alertId: number) =>
    api.patch<AlertResponse>(`/alerts/${alertId}/read`),

  markAllRead: () =>
    api.patch('/alerts/read-all'),
};

// ============================================================
// Prediction API
// ============================================================

export const predictionApi = {
  getPredictions: () =>
    api.get<PredictionResponse>('/trends/predictions'),
};

// ============================================================
// Upload API
// ============================================================

export const uploadApi = {
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<UploadResponse>('/data/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getUploadStatus: (uploadId: string) =>
    api.get<UploadResponse>(`/data/upload/${uploadId}`),
};

// ============================================================
// Auth API
// ============================================================

export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthTokenResponse>(
      '/auth/token',
      new URLSearchParams({ username: email, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),

  getPublisherInfo: () =>
    api.get<PublisherInfo>('/auth/me'),

  logout: () => {
    localStorage.removeItem('mmip_token');
    localStorage.removeItem('mmip_publisher');
  },
};

export default api;
