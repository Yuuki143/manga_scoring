# MMIP - Manga Market Intelligence Platform

マンガ市場インテリジェンスプラットフォーム — Link-U Group

出版社向けクロスプラットフォーム分析サービス。30以上のマンガ配信プラットフォームデータと出版社の匿名化売上データを統合し、5軸スコアリング・ヒット予測・ジャンルトレンド分析を提供。

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 / FastAPI / SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Frontend | React 18 / TypeScript / Recharts |
| Infrastructure | Docker Compose |

## Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Seed demo data (3 publishers, 40 titles, 12 months of data)
docker-compose exec backend python seed_data.py

# 3. Access
#    Swagger UI:  http://localhost:8000/docs
#    Dashboard:   http://localhost:3000
#    Login:       demo@shueisha-demo.jp / demo123
```

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # pydantic-settings configuration
│   ├── database.py           # SQLAlchemy session management
│   ├── models/               # 10 ORM models
│   ├── schemas/              # 12 Pydantic v2 request/response schemas
│   ├── api/v1/               # 8 RESTful endpoints
│   ├── scoring/              # 5-axis scoring engine + hit prediction
│   ├── auth/                 # JWT + API key auth, RBAC, audit log
│   ├── ingestion/            # CSV/Excel parser + data processor
│   └── services/             # Business logic layer
├── alembic/                  # Database migrations
├── seed_data.py              # Demo data generator
└── requirements.txt

frontend/
├── src/
│   ├── pages/                # Login, Dashboard, TitleDetail, GenreTrend, Alerts
│   ├── components/
│   │   ├── charts/           # TrendChart, RadarChart, HeatmapChart
│   │   ├── dashboard/        # ScoreCard
│   │   └── common/           # Header, Sidebar
│   ├── services/api.ts       # Axios API client
│   └── types/api.ts          # TypeScript type definitions
└── package.json
```

## API Endpoints

| Method | Endpoint | Description | Tier |
|--------|----------|-------------|------|
| GET | `/api/v1/titles/{id}/score` | 5-axis title score | Basic+ |
| GET | `/api/v1/titles/{id}/trend` | 12-month trend data | Pro+ |
| GET | `/api/v1/titles/{id}/affinity` | Similar titles | Pro+ |
| GET | `/api/v1/titles/{id}/global` | Overseas potential | Enterprise |
| GET | `/api/v1/genres/{genre}/ranking` | Genre ranking | Basic+ |
| GET | `/api/v1/alerts` | Alert notifications | Basic+ |
| GET | `/api/v1/trends/predictions` | Hit predictions | Pro+ |
| POST | `/api/v1/data/upload` | Sales data upload | Basic+ |

## 5-Axis Scoring Model

| Axis | Weight | Description |
|------|--------|-------------|
| Revenue Scale | 25% | Percentile rank of 12-month revenue |
| Growth Trend | 25% | Weighted 3/6/12-month growth rates |
| Platform Distribution | 20% | Multi-platform presence + Gini coefficient |
| Sales Stability | 15% | Inverse coefficient of variation |
| Ranking Frequency | 15% | Ranking appearances + best position |

## Data Ingestion

The parser supports CSV and Excel uploads with automatic detection of:
- Encoding: UTF-8, Shift-JIS, CP932
- Column headers: Japanese and English
- Date formats: `2026-01`, `2026/01/15`, `202601`, `2026年1月`
- Platform formats: Kindle, BookWalker, Cmoa, Renta!, GauGau, MangaONE

## Publisher Tiers

| Feature | Basic | Pro | Enterprise |
|---------|-------|-----|-----------|
| Overall Score | ○ | ○ | ○ |
| 5-Axis Detail | — | ○ | ○ |
| Genre Trends | Top 3 | All | All + Prediction |
| Competitor Benchmark | — | Anonymized | Detailed |
| Global Potential | — | Score only | Regional detail |
| Alerts | Breakout | 4 types | All + Custom |
| API Access | — | — | RESTful API |

## Development

```bash
# Backend only (without Docker)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend only
cd frontend
npm install
npm start
```

## License

Confidential — Link-U Group © 2026
