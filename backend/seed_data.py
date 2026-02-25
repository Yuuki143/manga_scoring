"""Seed script for MMIP demo data.

Creates 3 demo publishers, ~40 titles across multiple genres,
12 months of sales data, platform engagement data, pre-computed scores,
and sample alerts.

Usage:
    python -m seed_data
    # or from backend/:
    python seed_data.py
"""

import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine, Base
from app.models.publisher import Publisher, PublisherTier, DataProvisionFrequency
from app.models.user import User, UserRole
from app.models.title import Title, Genre, TitleStatus
from app.models.sales_data import SalesData, DataSource
from app.models.platform_data import PlatformData
from app.models.score import TitleScore, ConfidenceRating
from app.models.alert import Alert, AlertType, AlertSeverity, AlertRequiredTier
from app.models.genre_trend import GenreTrend, TrendingDirection
from app.auth.dependencies import get_password_hash

# ---------------------------------------------------------------------------
# Reproducible randomness
# ---------------------------------------------------------------------------
random.seed(42)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TODAY = date.today()
NOW_UTC = datetime.now(tz=timezone.utc)

PLATFORMS = [
    "Kindle",
    "BookWalker",
    "Cmoa",
    "Renta!",
    "めちゃコミック",
    "LINEマンガ",
    "ebookjapan",
    "GauGau",
]

# ---------------------------------------------------------------------------
# Publisher / title definitions
# ---------------------------------------------------------------------------

PUBLISHER_DEFS = [
    {
        "name": "Shueisha Demo",
        "slug": "shueisha-demo",
        "tier": PublisherTier.ENTERPRISE,
        "contact_email": "contact@shueisha-demo.jp",
        "data_provision_frequency": DataProvisionFrequency.WEEKLY,
        "user_email": "demo@shueisha-demo.jp",
        "user_full_name": "Shueisha Demo Admin",
        "titles": [
            # Shonen / Action heavy (15 titles)
            {
                "name": "鬼神の刃 外伝",
                "name_en": "Demon Blade Chronicles",
                "genre": Genre.ACTION,
                "author": "田中 勇樹",
                "start_date": date(2021, 4, 1),
                "has_anime": True,
                "anime_start_date": date(2023, 1, 8),
                "status": TitleStatus.ONGOING,
                "pattern": "ANIME_BOOST",
            },
            {
                "name": "呪術廻戦記 零編",
                "name_en": "Jujutsu Chronicles: Zero",
                "genre": Genre.FANTASY,
                "author": "佐藤 光",
                "start_date": date(2020, 10, 5),
                "has_anime": True,
                "anime_start_date": date(2022, 4, 3),
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "超人学園NEXT",
                "name_en": "Hero Academy NEXT",
                "genre": Genre.SHONEN,
                "author": "山田 翔",
                "start_date": date(2019, 7, 15),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "ワンサイドバトル 新章",
                "name_en": "One-Side Battle: New Arc",
                "genre": Genre.ACTION,
                "author": "伊藤 賢二",
                "start_date": date(2022, 1, 10),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "転生勇者の逆襲",
                "name_en": "The Reborn Hero's Counterattack",
                "genre": Genre.ISEKAI,
                "author": "鈴木 誠",
                "start_date": date(2021, 9, 20),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "剣神道場 最強伝説",
                "name_en": "Sword God Dojo: Legend of the Strongest",
                "genre": Genre.ACTION,
                "author": "中村 刃",
                "start_date": date(2020, 3, 1),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "少年革命家マサト",
                "name_en": "Masato the Young Revolutionary",
                "genre": Genre.SHONEN,
                "author": "加藤 武",
                "start_date": date(2023, 6, 5),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "闇の帝国 反乱軍",
                "name_en": "Dark Empire: The Rebels",
                "genre": Genre.FANTASY,
                "author": "林 蒼太",
                "start_date": date(2019, 11, 12),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.COMPLETED,
                "pattern": "DECLINING",
            },
            {
                "name": "神速の剣士 新世界篇",
                "name_en": "Lightning Swordsman: New World Arc",
                "genre": Genre.ACTION,
                "author": "渡辺 鋼",
                "start_date": date(2022, 8, 22),
                "has_anime": True,
                "anime_start_date": date(2024, 7, 14),
                "status": TitleStatus.ONGOING,
                "pattern": "ANIME_BOOST",
            },
            {
                "name": "海賊王への航海録",
                "name_en": "Voyage to the Pirate King",
                "genre": Genre.SHONEN,
                "author": "小林 海斗",
                "start_date": date(2020, 5, 18),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "無限界突破 覚醒編",
                "name_en": "Limitless: Awakening Arc",
                "genre": Genre.SHONEN,
                "author": "上田 力",
                "start_date": date(2021, 2, 7),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "龍脈の守護者",
                "name_en": "Guardian of the Dragon Vein",
                "genre": Genre.FANTASY,
                "author": "松本 龍",
                "start_date": date(2023, 3, 19),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "悪魔狩り少年隊",
                "name_en": "Devil Hunter Boys",
                "genre": Genre.ACTION,
                "author": "井上 鬼人",
                "start_date": date(2018, 9, 3),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.COMPLETED,
                "pattern": "DECLINING",
            },
            {
                "name": "最後の魔法使い 番外編",
                "name_en": "The Last Mage: Side Stories",
                "genre": Genre.FANTASY,
                "author": "木村 魔法",
                "start_date": date(2022, 12, 1),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "天空武術大会 頂上決戦",
                "name_en": "Sky Martial Arts Tournament: Summit Battle",
                "genre": Genre.SHONEN,
                "author": "大野 天翔",
                "start_date": date(2021, 7, 26),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
        ],
    },
    {
        "name": "Kodansha Demo",
        "slug": "kodansha-demo",
        "tier": PublisherTier.PRO,
        "contact_email": "contact@kodansha-demo.jp",
        "data_provision_frequency": DataProvisionFrequency.MONTHLY,
        "user_email": "demo@kodansha-demo.jp",
        "user_full_name": "Kodansha Demo Admin",
        "titles": [
            # Seinen / Mystery heavy (13 titles)
            {
                "name": "進撃の巨城 新世界",
                "name_en": "Attack on Fortress: New World",
                "genre": Genre.SEINEN,
                "author": "赤木 壁",
                "start_date": date(2020, 4, 7),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "名探偵コダン 事件簿",
                "name_en": "Great Detective Kodan: Case Files",
                "genre": Genre.MYSTERY,
                "author": "青山 謙二",
                "start_date": date(2019, 9, 14),
                "has_anime": True,
                "anime_start_date": date(2021, 10, 9),
                "status": TitleStatus.ONGOING,
                "pattern": "ANIME_BOOST",
            },
            {
                "name": "深夜食堂 続章",
                "name_en": "Midnight Diner: Continued",
                "genre": Genre.SLICE_OF_LIFE,
                "author": "安倍 夜",
                "start_date": date(2021, 1, 8),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "社畜の逆転劇",
                "name_en": "Office Drone's Reversal",
                "genre": Genre.COMEDY,
                "author": "藤田 勤太",
                "start_date": date(2022, 5, 16),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "霧の中の殺意 完全版",
                "name_en": "Murderous Intent in the Fog: Complete Edition",
                "genre": Genre.MYSTERY,
                "author": "黒沢 霧子",
                "start_date": date(2020, 8, 30),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.COMPLETED,
                "pattern": "STEADY",
            },
            {
                "name": "ゴルゴタ特殊捜査班",
                "name_en": "Golgotha Special Investigations",
                "genre": Genre.MYSTERY,
                "author": "白石 捜",
                "start_date": date(2021, 11, 3),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "機動戦士ガウラム 星間戦争",
                "name_en": "Mobile Soldier Gawram: Interstellar War",
                "genre": Genre.SCI_FI,
                "author": "土田 宇宙",
                "start_date": date(2019, 6, 10),
                "has_anime": True,
                "anime_start_date": date(2022, 7, 4),
                "status": TitleStatus.ONGOING,
                "pattern": "ANIME_BOOST",
            },
            {
                "name": "人形遣いの殺人",
                "name_en": "The Puppeteer's Murder",
                "genre": Genre.MYSTERY,
                "author": "桐島 操",
                "start_date": date(2023, 2, 14),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "終末ダーウィン 進化の果て",
                "name_en": "Doomsday Darwin: Edge of Evolution",
                "genre": Genre.SEINEN,
                "author": "原田 進化",
                "start_date": date(2020, 12, 21),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "腐海の探偵 蟲の囁き",
                "name_en": "Rot Sea Detective: Whispers of Insects",
                "genre": Genre.HORROR,
                "author": "宮野 腐",
                "start_date": date(2022, 9, 9),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "昭和刑事 太陽のもとで",
                "name_en": "Showa Detective: Under the Sun",
                "genre": Genre.MYSTERY,
                "author": "三上 昭男",
                "start_date": date(2018, 3, 5),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.COMPLETED,
                "pattern": "DECLINING",
            },
            {
                "name": "AIの目覚め 意識という名の迷宮",
                "name_en": "AI Awakening: Labyrinth Called Consciousness",
                "genre": Genre.SCI_FI,
                "author": "高橋 知能",
                "start_date": date(2023, 8, 28),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "未来都市の孤独",
                "name_en": "Solitude in the Future City",
                "genre": Genre.SEINEN,
                "author": "村上 未来",
                "start_date": date(2021, 5, 17),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
        ],
    },
    {
        "name": "Shogakukan Demo",
        "slug": "shogakukan-demo",
        "tier": PublisherTier.BASIC,
        "contact_email": "contact@shogakukan-demo.jp",
        "data_provision_frequency": DataProvisionFrequency.MONTHLY,
        "user_email": "demo@shogakukan-demo.jp",
        "user_full_name": "Shogakukan Demo Admin",
        "titles": [
            # Variety (12 titles)
            {
                "name": "スラムダンク再起 新世代",
                "name_en": "Slam Dunk Revival: New Generation",
                "genre": Genre.SPORTS,
                "author": "長谷川 桜木",
                "start_date": date(2021, 10, 4),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "花より花嫁 恋愛模様",
                "name_en": "Flowers Before the Bride: Love's Tapestry",
                "genre": Genre.ROMANCE,
                "author": "花田 桜子",
                "start_date": date(2022, 2, 14),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "ポケモンアドベンチャー 翡翠編",
                "name_en": "Pocket Adventure: Jade Arc",
                "genre": Genre.KODOMO,
                "author": "池田 翡翠",
                "start_date": date(2020, 7, 6),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "異世界居酒屋 旅人の酒",
                "name_en": "Isekai Tavern: Traveler's Brew",
                "genre": Genre.ISEKAI,
                "author": "笹本 居酒",
                "start_date": date(2021, 6, 21),
                "has_anime": True,
                "anime_start_date": date(2023, 4, 2),
                "status": TitleStatus.ONGOING,
                "pattern": "ANIME_BOOST",
            },
            {
                "name": "猫と私の下宿生活",
                "name_en": "My Cat and I: Boarding House Life",
                "genre": Genre.SLICE_OF_LIFE,
                "author": "田村 猫助",
                "start_date": date(2023, 1, 9),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "百合の園で待ってる",
                "name_en": "Waiting in the Lily Garden",
                "genre": Genre.GL,
                "author": "西村 百合",
                "start_date": date(2022, 7, 18),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "野球少年 夢の甲子園",
                "name_en": "Baseball Boy: Dream of Koshien",
                "genre": Genre.SPORTS,
                "author": "松井 球道",
                "start_date": date(2019, 4, 1),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.COMPLETED,
                "pattern": "DECLINING",
            },
            {
                "name": "幽霊屋敷の少女",
                "name_en": "Girl in the Haunted Mansion",
                "genre": Genre.HORROR,
                "author": "怪談 幽子",
                "start_date": date(2022, 10, 31),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "お嬢様と執事の恋",
                "name_en": "The Lady and the Butler's Love",
                "genre": Genre.JOSEI,
                "author": "藤原 雅子",
                "start_date": date(2021, 3, 8),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "ハッカー少女 電脳戦記",
                "name_en": "Hacker Girl: Cyberspace Battle",
                "genre": Genre.SCI_FI,
                "author": "電脳 ハル",
                "start_date": date(2023, 5, 15),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "GROWING",
            },
            {
                "name": "推し活男子 アイドル道",
                "name_en": "Fan Boy: The Idol Path",
                "genre": Genre.COMEDY,
                "author": "沢田 推男",
                "start_date": date(2022, 4, 4),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
            {
                "name": "茶道部の謎解き",
                "name_en": "Tea Ceremony Club Mysteries",
                "genre": Genre.MYSTERY,
                "author": "茶木 亭主",
                "start_date": date(2020, 9, 7),
                "has_anime": False,
                "anime_start_date": None,
                "status": TitleStatus.ONGOING,
                "pattern": "STEADY",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Revenue base amounts per publisher tier (monthly, per title, per platform)
# ---------------------------------------------------------------------------
TIER_BASE_REVENUE = {
    PublisherTier.ENTERPRISE: 800_000,
    PublisherTier.PRO: 400_000,
    PublisherTier.BASIC: 150_000,
}

TIER_BASE_UNITS = {
    PublisherTier.ENTERPRISE: 12_000,
    PublisherTier.PRO: 6_000,
    PublisherTier.BASIC: 2_500,
}


# ---------------------------------------------------------------------------
# Revenue generation helpers
# ---------------------------------------------------------------------------


def _month_dates(months_back: int) -> tuple[date, date]:
    """Return (period_start, period_end) for *months_back* months ago."""
    # Start from first of the month, months_back months ago
    first_of_current = TODAY.replace(day=1)
    target_month = first_of_current - timedelta(days=months_back * 30)
    period_start = target_month.replace(day=1)
    # Last day of that month
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1, day=1) - timedelta(days=1)
    return period_start, period_end


def _platform_subset(n: int) -> list[str]:
    """Return a reproducible random subset of *n* platforms."""
    return random.sample(PLATFORMS, n)


def _generate_monthly_multipliers(pattern: str, anime_start_date: date | None) -> list[float]:
    """Generate 12 monthly revenue multipliers (index 0 = 12 months ago, 11 = last month).

    Patterns:
        STEADY       – ~±5% variation around 1.0
        GROWING      – +5–15% compound monthly growth
        DECLINING    – -5–10% compound monthly decline
        ANIME_BOOST  – spike at anime_start_date then gradual return to 1.0
    """
    multipliers = []

    if pattern == "STEADY":
        for _ in range(12):
            multipliers.append(1.0 + random.uniform(-0.05, 0.05))

    elif pattern == "GROWING":
        monthly_growth = random.uniform(0.05, 0.15)
        val = random.uniform(0.5, 0.8)  # start lower
        for _ in range(12):
            val *= (1.0 + monthly_growth)
            multipliers.append(val + random.uniform(-0.03, 0.03))

    elif pattern == "DECLINING":
        monthly_decline = random.uniform(0.05, 0.10)
        val = random.uniform(1.0, 1.4)  # start higher
        for _ in range(12):
            val *= (1.0 - monthly_decline)
            multipliers.append(max(0.05, val + random.uniform(-0.02, 0.02)))

    elif pattern == "ANIME_BOOST":
        # Compute which of the 12 months (0-indexed from 12 months ago) the
        # anime started, then apply a large spike at that point.
        base = [1.0 + random.uniform(-0.05, 0.05) for _ in range(12)]

        if anime_start_date is not None:
            for i in range(12):
                period_start, _ = _month_dates(11 - i)
                # Check if anime_start_date falls within 2 months of period_start
                delta_days = (anime_start_date - period_start).days
                if 0 <= delta_days < 60:
                    # Peak spike: 2.0–3.0x
                    base[i] = random.uniform(2.0, 3.0)
                elif 60 <= delta_days < 120:
                    # Elevated for 2 months after peak
                    base[i] = random.uniform(1.4, 2.0)
                elif -90 < delta_days < 0:
                    # Pre-anime buzz
                    base[i] = random.uniform(1.1, 1.5)
        multipliers = base

    else:
        multipliers = [1.0] * 12

    return multipliers


# ---------------------------------------------------------------------------
# Score computation helpers
# ---------------------------------------------------------------------------


def _compute_scores_for_title(
    title: Title,
    monthly_revenues: list[float],
    n_platforms: int,
    all_titles_revenue: list[float],
    genre_revenues: list[float],
) -> dict:
    """Compute pre-seeded scores using the MMIP 5-axis weighting.

    This mirrors the ScoringEngine logic but works directly on the seed data
    without requiring a live database query loop.

    Weights:
        revenue           25 %
        growth            25 %
        platform_dist     20 %
        stability         15 %
        ranking_frequency 15 %
    """
    # --- Revenue score (25%): percentile among all titles ---
    total_revenue = sum(monthly_revenues)
    if all_titles_revenue:
        below = sum(1 for r in all_titles_revenue if r < total_revenue)
        revenue_score = (below / len(all_titles_revenue)) * 100.0
    else:
        revenue_score = 50.0

    # --- Growth score (25%): weighted 3/6/12-month growth ---
    def _sum_recent(n: int) -> float:
        return sum(monthly_revenues[max(0, 12 - n):])

    def _sum_prior(n: int) -> float:
        start = max(0, 12 - 2 * n)
        end = max(0, 12 - n)
        return sum(monthly_revenues[start:end])

    def _growth_rate(current: float, prior: float) -> float:
        if prior == 0:
            return 0.0
        return (current - prior) / prior

    gr_3m = _growth_rate(_sum_recent(3), _sum_prior(3))
    gr_6m = _growth_rate(_sum_recent(6), _sum_prior(6))
    gr_12m = _growth_rate(sum(monthly_revenues), _sum_prior(12))
    weighted_growth = 0.5 * gr_3m + 0.3 * gr_6m + 0.2 * gr_12m
    # Sigmoid-like normalisation centred at 0% growth
    import math
    sigmoid_val = 1.0 / (1.0 + math.exp(-weighted_growth / 0.30))
    growth_score = sigmoid_val * 100.0

    # --- Platform distribution score (20%) ---
    platform_count_norm = min(n_platforms / 10.0, 1.0)
    # Simulate slight revenue concentration variation
    gini_approx = random.uniform(0.1, 0.4)
    platform_score = (platform_count_norm * 0.6 + (1.0 - gini_approx) * 0.4) * 100.0

    # --- Stability score (15%): inverse coefficient of variation ---
    if len(monthly_revenues) >= 3 and sum(monthly_revenues) > 0:
        mean_rev = sum(monthly_revenues) / len(monthly_revenues)
        if mean_rev > 0:
            variance = sum((r - mean_rev) ** 2 for r in monthly_revenues) / len(monthly_revenues)
            std_dev = variance ** 0.5
            cv = std_dev / mean_rev
            stability_score = max(0.0, (1.0 - cv) * 100.0)
        else:
            stability_score = 50.0
    else:
        stability_score = 50.0

    # --- Ranking frequency score (15%): use platform data quality proxy ---
    # For seed data, simulate ranking based on revenue percentile
    rank_appearances = int(revenue_score * 1.2)  # proxy
    best_rank = max(1, int(101 - revenue_score))
    freq_norm = min(rank_appearances / 100.0, 1.0)
    pos_score = max(0.0, (101 - best_rank) / 100.0)
    ranking_score = (freq_norm * 0.6 + pos_score * 0.4) * 100.0

    # --- Overall composite ---
    overall = (
        0.25 * revenue_score
        + 0.25 * growth_score
        + 0.20 * platform_score
        + 0.15 * stability_score
        + 0.15 * ranking_score
    )
    overall = max(0.0, min(100.0, overall))

    # --- Confidence rating ---
    # All 5 axes have data (we generate full 12 months), so A is appropriate
    confidence = ConfidenceRating.A

    # --- Genre percentile ---
    if genre_revenues:
        below_genre = sum(1 for r in genre_revenues if r < total_revenue)
        genre_percentile = (below_genre / len(genre_revenues)) * 100.0
    else:
        genre_percentile = 100.0

    return {
        "overall_score": round(overall, 2),
        "revenue_score": round(revenue_score, 2),
        "growth_score": round(growth_score, 2),
        "platform_distribution_score": round(platform_score, 2),
        "stability_score": round(stability_score, 2),
        "ranking_frequency_score": round(ranking_score, 2),
        "confidence_rating": confidence,
        "genre_percentile": round(genre_percentile, 2),
        "global_potential_score": round(random.uniform(40.0, 90.0) if title.has_anime else random.uniform(20.0, 70.0), 2),
    }


# ---------------------------------------------------------------------------
# GenreTrend helpers
# ---------------------------------------------------------------------------

GENRE_TREND_CONFIGS = {
    Genre.ACTION: {"growth_base": 0.08, "direction": TrendingDirection.UP},
    Genre.SHONEN: {"growth_base": 0.05, "direction": TrendingDirection.UP},
    Genre.FANTASY: {"growth_base": 0.06, "direction": TrendingDirection.UP},
    Genre.SEINEN: {"growth_base": 0.02, "direction": TrendingDirection.STABLE},
    Genre.MYSTERY: {"growth_base": 0.04, "direction": TrendingDirection.UP},
    Genre.ISEKAI: {"growth_base": 0.09, "direction": TrendingDirection.UP},
    Genre.SLICE_OF_LIFE: {"growth_base": 0.01, "direction": TrendingDirection.STABLE},
    Genre.COMEDY: {"growth_base": 0.03, "direction": TrendingDirection.STABLE},
    Genre.SCI_FI: {"growth_base": 0.07, "direction": TrendingDirection.UP},
    Genre.SPORTS: {"growth_base": -0.02, "direction": TrendingDirection.DOWN},
    Genre.ROMANCE: {"growth_base": 0.04, "direction": TrendingDirection.STABLE},
    Genre.HORROR: {"growth_base": 0.05, "direction": TrendingDirection.UP},
    Genre.GL: {"growth_base": 0.06, "direction": TrendingDirection.UP},
    Genre.JOSEI: {"growth_base": 0.01, "direction": TrendingDirection.STABLE},
    Genre.KODOMO: {"growth_base": -0.01, "direction": TrendingDirection.STABLE},
    Genre.BL: {"growth_base": 0.05, "direction": TrendingDirection.UP},
}


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------


def seed() -> None:
    """Create all demo data if the database is empty."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # --- Guard: skip if data already exists ---
        existing = db.query(Publisher).filter(Publisher.slug == "shueisha-demo").first()
        if existing is not None:
            print("Seed data already exists. Skipping.")
            return

        print("Starting seed data creation...")

        # ---------------------------------------------------------------
        # Track per-genre total revenues for genre-percentile calculation
        # ---------------------------------------------------------------
        all_title_revenues: dict[int, float] = {}   # title_id -> total_revenue (filled later)
        genre_revenues: dict[str, list[float]] = {}  # genre -> [total_revenues]

        # ---------------------------------------------------------------
        # First pass: create publishers, users, titles, and collect
        # revenue totals for post-processing score computation
        # ---------------------------------------------------------------
        created_publishers: list[Publisher] = []
        created_titles: list[tuple[Title, list[float], int]] = []  # (title, monthly_revs, n_plats)

        for pub_def in PUBLISHER_DEFS:
            print(f"  Creating publisher: {pub_def['name']}")

            publisher = Publisher(
                name=pub_def["name"],
                slug=pub_def["slug"],
                tier=pub_def["tier"],
                contact_email=pub_def["contact_email"],
                api_key=f"demo-api-key-{pub_def['slug']}",
                is_active=True,
                data_provision_frequency=pub_def["data_provision_frequency"],
            )
            db.add(publisher)
            db.flush()  # get publisher.id

            # Demo user for this publisher
            user = User(
                email=pub_def["user_email"],
                hashed_password=get_password_hash("demo123"),
                full_name=pub_def["user_full_name"],
                publisher_id=publisher.id,
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(user)

            created_publishers.append(publisher)

            base_revenue = TIER_BASE_REVENUE[pub_def["tier"]]
            base_units = TIER_BASE_UNITS[pub_def["tier"]]

            for title_def in pub_def["titles"]:
                print(f"    Creating title: {title_def['name']}")

                title = Title(
                    name=title_def["name"],
                    name_en=title_def.get("name_en"),
                    publisher_id=publisher.id,
                    genre=title_def["genre"],
                    author=title_def["author"],
                    status=title_def["status"],
                    start_date=title_def["start_date"],
                    end_date=title_def.get("end_date"),
                    has_anime=title_def["has_anime"],
                    anime_start_date=title_def.get("anime_start_date"),
                    is_active=True,
                )
                db.add(title)
                db.flush()

                # Choose platforms for this title (4–7 platforms)
                n_platforms = random.randint(4, 7)
                platforms_for_title = _platform_subset(n_platforms)

                # Generate growth multipliers for 12 months
                multipliers = _generate_monthly_multipliers(
                    title_def["pattern"],
                    title_def.get("anime_start_date"),
                )

                # Per-title revenue seed (vary within tier band)
                title_revenue_seed = base_revenue * random.uniform(0.6, 1.4)
                title_units_seed = base_units * random.uniform(0.6, 1.4)

                monthly_revenues: list[float] = []

                for month_idx in range(12):
                    period_start, period_end = _month_dates(11 - month_idx)
                    multiplier = multipliers[month_idx]

                    # Distribute revenue evenly across platforms with slight noise
                    for platform in platforms_for_title:
                        platform_factor = random.uniform(0.8, 1.2)
                        revenue = (
                            (title_revenue_seed / n_platforms)
                            * multiplier
                            * platform_factor
                        )
                        units = int(
                            (title_units_seed / n_platforms)
                            * multiplier
                            * platform_factor
                        )
                        revenue = round(revenue, 2)
                        units = max(1, units)

                        sd = SalesData(
                            title_id=title.id,
                            publisher_id=publisher.id,
                            platform_name=platform,
                            period_start=period_start,
                            period_end=period_end,
                            revenue=revenue,
                            units_sold=units,
                            data_source=DataSource.PUBLISHER,
                        )
                        db.add(sd)

                    # Monthly total revenue for this title
                    monthly_total = (
                        title_revenue_seed * multiplier
                        * random.uniform(0.95, 1.05)
                    )
                    monthly_revenues.append(monthly_total)

                    # Platform engagement data (monthly snapshot per platform)
                    for platform in platforms_for_title:
                        engagement = random.uniform(0.25, 0.85)
                        retention = random.uniform(0.30, 0.75)
                        comment_vol = int(random.uniform(50, 5000) * multiplier)
                        sentiment = random.uniform(-0.2, 0.9)
                        ranking_pos = max(1, int(random.uniform(1, 150) / multiplier))

                        pd_row = PlatformData(
                            title_id=title.id,
                            platform_name=platform,
                            period_date=period_start,
                            first_episode_engagement=round(engagement, 4),
                            retention_rate=round(retention, 4),
                            comment_volume=comment_vol,
                            comment_sentiment=round(sentiment, 4),
                            ranking_position=ranking_pos,
                            page_views=int(random.uniform(10_000, 500_000) * multiplier),
                            unique_readers=int(random.uniform(2_000, 100_000) * multiplier),
                        )
                        db.add(pd_row)

                created_titles.append((title, monthly_revenues, n_platforms))

                # Accumulate for percentile calculation
                genre_key = title_def["genre"].value
                total_rev = sum(monthly_revenues)
                all_title_revenues[title.id] = total_rev
                genre_revenues.setdefault(genre_key, []).append(total_rev)

        db.flush()

        # ---------------------------------------------------------------
        # Second pass: compute and insert TitleScores
        # ---------------------------------------------------------------
        print("  Computing title scores...")
        all_revenues_list = list(all_title_revenues.values())

        for title, monthly_revenues, n_platforms in created_titles:
            genre_key = title.genre.value
            genre_rev_list = [
                r for tid, r in all_title_revenues.items()
                if tid != title.id and any(
                    t.id == tid and t.genre.value == genre_key
                    for t, _, __ in created_titles
                )
            ]

            scores = _compute_scores_for_title(
                title,
                monthly_revenues,
                n_platforms,
                all_revenues_list,
                genre_rev_list,
            )

            # One score snapshot per title, calculated "today"
            ts = TitleScore(
                title_id=title.id,
                calculated_at=NOW_UTC,
                overall_score=scores["overall_score"],
                revenue_score=scores["revenue_score"],
                growth_score=scores["growth_score"],
                platform_distribution_score=scores["platform_distribution_score"],
                stability_score=scores["stability_score"],
                ranking_frequency_score=scores["ranking_frequency_score"],
                confidence_rating=scores["confidence_rating"],
                global_potential_score=scores["global_potential_score"],
                genre_percentile=scores["genre_percentile"],
            )
            db.add(ts)

        # ---------------------------------------------------------------
        # Create Alerts
        # ---------------------------------------------------------------
        print("  Creating alerts...")

        # Map publisher name -> Publisher object
        pub_map: dict[str, Publisher] = {p.name: p for p in created_publishers}
        # Map title name -> Title object
        title_map: dict[str, Title] = {t.name: t for t, _, __ in created_titles}

        # Breakout alert for Shueisha's top anime-boosted title
        breakout_title = title_map.get("鬼神の刃 外伝")
        if breakout_title:
            alert1 = Alert(
                publisher_id=pub_map["Shueisha Demo"].id,
                title_id=breakout_title.id,
                alert_type=AlertType.BREAKOUT,
                severity=AlertSeverity.CRITICAL,
                message=(
                    "「鬼神の刃 外伝」が先月比 +280% の売上急増を記録しました。"
                    " アニメ放映開始による爆発的な需要増が確認されています。"
                    " 増刷および海外ライセンス交渉の開始を推奨します。"
                ),
                data={
                    "growth_pct": 280.0,
                    "trigger": "anime_start",
                    "platform_leaders": ["Kindle", "BookWalker"],
                    "recommended_action": "increase_print_run",
                },
                is_read=False,
                required_tier=AlertRequiredTier.BASIC,
            )
            db.add(alert1)

        # Anime impact alert for Kodansha
        anime_title = title_map.get("名探偵コダン 事件簿")
        if anime_title:
            alert2 = Alert(
                publisher_id=pub_map["Kodansha Demo"].id,
                title_id=anime_title.id,
                alert_type=AlertType.ANIME_IMPACT,
                severity=AlertSeverity.WARNING,
                message=(
                    "「名探偵コダン 事件簿」アニメ放映終了から3ヶ月が経過し、"
                    " 売上が放映前水準に戻りつつあります。"
                    " 後続コンテンツの投入でモメンタムを維持することを検討してください。"
                ),
                data={
                    "anime_end_months_ago": 3,
                    "sales_trend": "normalizing",
                    "peak_multiplier": 2.7,
                },
                is_read=False,
                required_tier=AlertRequiredTier.BASIC,
            )
            db.add(alert2)

        # Genre trend alert for rising Action/Shonen genre (Shueisha)
        alert3 = Alert(
            publisher_id=pub_map["Shueisha Demo"].id,
            title_id=None,
            alert_type=AlertType.GENRE_TREND,
            severity=AlertSeverity.INFO,
            message=(
                "ACTIONジャンルが過去3ヶ月で +8% の成長を示しています。"
                " 現在、同社ポートフォリオの Action タイトル比率は市場平均を上回っています。"
                " 新規 Action タイトルの早期立ち上げが有効な可能性があります。"
            ),
            data={
                "genre": "ACTION",
                "growth_rate_3m": 0.08,
                "portfolio_share": 0.27,
                "market_share": 0.21,
            },
            is_read=False,
            required_tier=AlertRequiredTier.BASIC,
        )
        db.add(alert3)

        # Overseas demand alert (Enterprise tier) for Shueisha
        overseas_title = title_map.get("呪術廻戦記 零編")
        if overseas_title:
            alert4 = Alert(
                publisher_id=pub_map["Shueisha Demo"].id,
                title_id=overseas_title.id,
                alert_type=AlertType.OVERSEAS_DEMAND,
                severity=AlertSeverity.WARNING,
                message=(
                    "「呪術廻戦記 零編」に対して北米・欧州のデジタルプラットフォームから"
                    " 強い需要シグナルが検出されています。"
                    " 英語・フランス語ライセンスの交渉を優先することを推奨します。"
                ),
                data={
                    "regions": ["North America", "Europe"],
                    "demand_index": 87.3,
                    "recommended_languages": ["en", "fr"],
                },
                is_read=False,
                required_tier=AlertRequiredTier.ENTERPRISE,
            )
            db.add(alert4)

        # Competitor movement alert (PRO tier) for Kodansha
        alert5 = Alert(
            publisher_id=pub_map["Kodansha Demo"].id,
            title_id=None,
            alert_type=AlertType.COMPETITOR_MOVEMENT,
            severity=AlertSeverity.INFO,
            message=(
                "競合他社がMYSTERYジャンルで過去2ヶ月以内に3タイトルを新規投入しました。"
                " 現在のミステリータイトルの認知向上施策の強化を推奨します。"
            ),
            data={
                "genre": "MYSTERY",
                "competitor_new_titles": 3,
                "window_months": 2,
            },
            is_read=False,
            required_tier=AlertRequiredTier.PRO,
        )
        db.add(alert5)

        # Breakout alert for Shogakukan's growing GL title
        gl_title = title_map.get("百合の園で待ってる")
        if gl_title:
            alert6 = Alert(
                publisher_id=pub_map["Shogakukan Demo"].id,
                title_id=gl_title.id,
                alert_type=AlertType.BREAKOUT,
                severity=AlertSeverity.WARNING,
                message=(
                    "「百合の園で待ってる」が直近2ヶ月で読者数 +42% を記録し、"
                    " GLジャンル内で急速にシェアを拡大しています。"
                    " プロモーション強化によりブレイクアウトを加速できる可能性があります。"
                ),
                data={
                    "reader_growth_pct": 42.0,
                    "genre_rank_change": -8,
                    "platforms_trending": ["LINEマンガ", "ebookjapan"],
                },
                is_read=True,
                required_tier=AlertRequiredTier.BASIC,
            )
            db.add(alert6)

        # ---------------------------------------------------------------
        # Create GenreTrend data (12 months for major genres)
        # ---------------------------------------------------------------
        print("  Creating genre trend data...")

        active_genres = set()
        for pub_def in PUBLISHER_DEFS:
            for td in pub_def["titles"]:
                active_genres.add(td["genre"])

        for genre_enum in active_genres:
            config_entry = GENRE_TREND_CONFIGS.get(genre_enum, {
                "growth_base": 0.02,
                "direction": TrendingDirection.STABLE,
            })
            base_growth = config_entry["growth_base"]
            direction = config_entry["direction"]

            # Count titles in this genre across all publishers
            title_count = sum(
                1
                for pub_def in PUBLISHER_DEFS
                for td in pub_def["titles"]
                if td["genre"] == genre_enum
            )

            for month_idx in range(12):
                period_start, _ = _month_dates(11 - month_idx)
                # Add some temporal variation
                growth_variation = random.uniform(-0.02, 0.02)
                period_growth = base_growth + growth_variation
                # Trend direction can shift slightly
                if period_growth > 0.04:
                    period_direction = TrendingDirection.UP
                elif period_growth < -0.01:
                    period_direction = TrendingDirection.DOWN
                else:
                    period_direction = TrendingDirection.STABLE

                gt = GenreTrend(
                    genre=genre_enum.value,
                    period_date=period_start,
                    growth_rate=round(period_growth, 4),
                    title_count=title_count,
                    avg_engagement=round(random.uniform(0.35, 0.72), 4),
                    avg_revenue=round(
                        TIER_BASE_REVENUE[PublisherTier.BASIC] * random.uniform(0.8, 2.5),
                        2,
                    ),
                    trending_direction=period_direction,
                )
                db.add(gt)

        # ---------------------------------------------------------------
        # Commit everything
        # ---------------------------------------------------------------
        print("  Committing all data to database...")
        db.commit()
        print("Seed data created successfully!")
        print()

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        n_publishers = db.query(Publisher).count()
        n_users = db.query(User).count()
        n_titles = db.query(Title).count()
        n_sales = db.query(SalesData).count()
        n_platform = db.query(PlatformData).count()
        n_scores = db.query(TitleScore).count()
        n_alerts = db.query(Alert).count()
        n_trends = db.query(GenreTrend).count()

        print("Database summary:")
        print(f"  Publishers  : {n_publishers}")
        print(f"  Users       : {n_users}")
        print(f"  Titles      : {n_titles}")
        print(f"  SalesData   : {n_sales}")
        print(f"  PlatformData: {n_platform}")
        print(f"  TitleScores : {n_scores}")
        print(f"  Alerts      : {n_alerts}")
        print(f"  GenreTrends : {n_trends}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
