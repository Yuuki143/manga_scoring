"""Sales-data file parsers for the MMIP ingestion pipeline.

Supports CSV and Excel uploads from multiple digital manga distribution
platforms.  Column names may be in English or Japanese; the parser
normalises them before returning structured records ready for DB insertion.
"""

import logging
from datetime import date, datetime
from io import BytesIO
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform-specific column name mappings
# ---------------------------------------------------------------------------

# Each entry maps a logical field name to a list of known header strings
# (case-insensitive matching is applied at parse time).
_PLATFORM_MAPPINGS: dict[str, dict[str, list[str]]] = {
    "default": {
        "title": ["title", "作品名", "タイトル", "title_name", "manga_title", "series"],
        "revenue": [
            "revenue",
            "売上",
            "売上金額",
            "sales_amount",
            "amount",
            "gross_revenue",
            "net_revenue",
            "earnings",
        ],
        "units": [
            "units",
            "部数",
            "販売部数",
            "units_sold",
            "quantity",
            "copies",
            "count",
            "sales_count",
        ],
        "platform": [
            "platform",
            "プラットフォーム",
            "配信先",
            "store",
            "channel",
            "distribution_channel",
        ],
        "period": [
            "period",
            "期間",
            "対象期間",
            "date",
            "月",
            "report_period",
            "reporting_period",
            "month",
            "year_month",
        ],
    },
    "kindle": {
        "title": ["title", "asin_title", "book_title"],
        "revenue": ["royalties_earned", "revenue", "net_royalties"],
        "units": ["units_sold", "units_refunded", "net_units_sold"],
        "platform": ["marketplace"],
        "period": ["reporting_date", "report_date", "month"],
    },
    "bookwalker": {
        "title": ["タイトル", "作品名", "title"],
        "revenue": ["売上金額", "revenue", "amount"],
        "units": ["販売部数", "units", "quantity"],
        "platform": ["プラットフォーム", "platform"],
        "period": ["対象期間", "period", "月"],
    },
    "cmoa": {
        "title": ["タイトル名", "作品名", "title"],
        "revenue": ["売上", "売上金額", "revenue"],
        "units": ["販売数", "部数", "units"],
        "platform": ["サービス", "platform"],
        "period": ["集計期間", "期間", "month"],
    },
    "renta": {
        "title": ["作品名", "タイトル", "title"],
        "revenue": ["売上金額", "売上", "revenue"],
        "units": ["購入数", "部数", "units"],
        "platform": ["サイト名", "platform"],
        "period": ["集計月", "対象月", "period"],
    },
}


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m",          # 2024-03
    "%Y/%m",          # 2024/03
    "%Y-%m-%d",       # 2024-03-15
    "%Y/%m/%d",       # 2024/03/15
    "%d/%m/%Y",       # 15/03/2024
    "%m/%d/%Y",       # 03/15/2024
    "%Y%m",           # 202403
    "%Y年%m月",       # 2024年03月
    "%Y年%m月%d日",   # 2024年03月15日
]


def _parse_date_flexible(value: Any) -> date | None:
    """Try to parse *value* into a :class:`~datetime.date`.

    Supports a wide variety of string formats and numeric YYYYMM integers.
    Returns ``None`` if parsing fails.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    # pandas Timestamp
    if isinstance(value, pd.Timestamp):
        return value.date()

    # Python datetime / date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()

    # Numeric YYYYMM (e.g. 202403)
    if text.isdigit():
        if len(text) == 6:
            try:
                return datetime.strptime(text, "%Y%m").date()
            except ValueError:
                pass
        if len(text) == 8:
            try:
                return datetime.strptime(text, "%Y%m%d").date()
            except ValueError:
                pass

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def _period_to_date_range(period_date: date) -> tuple[date, date]:
    """Return the (period_start, period_end) for a monthly period date.

    If the date is already a specific day, returns (date, date).
    Otherwise returns first and last day of the month.
    """
    import calendar

    if period_date.day == 1:
        # Treat as month-level period
        last_day = calendar.monthrange(period_date.year, period_date.month)[1]
        return (period_date, date(period_date.year, period_date.month, last_day))
    return (period_date, period_date)


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------


class SalesDataParser:
    """Parse sales data from CSV or Excel uploads.

    Supports multiple platform-specific column layouts and normalises the
    data into a list of dicts suitable for direct DB insertion.
    """

    # Expose for external introspection / testing
    PLATFORM_MAPPINGS = _PLATFORM_MAPPINGS

    # ---------------------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------------------

    def parse(
        self,
        file_content: bytes,
        filename: str,
        publisher_id: int,
    ) -> dict:
        """Parse *file_content* and return structured sales records.

        Args:
            file_content: Raw bytes of the uploaded CSV or Excel file.
            filename: Original filename used to detect file type.
            publisher_id: ID of the uploading publisher (stamped on each record).

        Returns:
            A dict with keys:

            * ``"records"`` – list of dicts with keys:
              ``title_name``, ``platform_name``, ``period_start``,
              ``period_end``, ``revenue``, ``units_sold``, ``publisher_id``
            * ``"errors"`` – list of human-readable error strings
            * ``"format_detected"`` – the platform format key that was matched
        """
        errors: list[str] = []

        # --- Load file into DataFrame ---
        try:
            df = self._load_file(file_content, filename)
        except Exception as exc:
            return {
                "records": [],
                "errors": [f"Failed to read file '{filename}': {exc}"],
                "format_detected": "unknown",
            }

        if df.empty:
            return {
                "records": [],
                "errors": ["File contains no data rows."],
                "format_detected": "unknown",
            }

        # --- Normalise column names ---
        df.columns = [str(c).strip() for c in df.columns]

        # --- Detect platform format ---
        format_detected = self._detect_format(df.columns.tolist())

        # --- Map columns ---
        mapping = _PLATFORM_MAPPINGS.get(format_detected, _PLATFORM_MAPPINGS["default"])
        col_map = self._build_column_map(df.columns.tolist(), mapping)

        missing = [field for field in ("title", "revenue", "units", "period")
                   if field not in col_map]
        if missing:
            return {
                "records": [],
                "errors": [
                    f"Could not identify required columns: {missing}. "
                    f"Available columns: {df.columns.tolist()}"
                ],
                "format_detected": format_detected,
            }

        # --- Parse rows ---
        records: list[dict] = []
        for idx, row in df.iterrows():
            row_num = idx + 2  # 1-based, accounting for header row
            try:
                record, row_errors = self._parse_row(
                    row, col_map, publisher_id, row_num
                )
                if row_errors:
                    errors.extend(row_errors)
                if record is not None:
                    records.append(record)
            except Exception as exc:
                errors.append(f"Row {row_num}: Unexpected error – {exc}")

        return {
            "records": records,
            "errors": errors,
            "format_detected": format_detected,
        }

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _load_file(self, file_content: bytes, filename: str) -> pd.DataFrame:
        """Read *file_content* into a DataFrame based on *filename* extension."""
        lower_name = filename.lower()
        buf = BytesIO(file_content)

        if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
            return pd.read_excel(buf, dtype=str)

        if lower_name.endswith(".csv"):
            # Try UTF-8 first, then Shift-JIS for Japanese files
            for encoding in ("utf-8-sig", "utf-8", "shift_jis", "cp932"):
                try:
                    buf.seek(0)
                    return pd.read_csv(buf, dtype=str, encoding=encoding)
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            raise ValueError("Unable to decode CSV with any supported encoding.")

        # Attempt CSV as a fallback for unknown extensions
        try:
            buf.seek(0)
            return pd.read_csv(buf, dtype=str)
        except Exception:
            raise ValueError(
                f"Unsupported file type for '{filename}'. "
                "Please upload a .csv, .xlsx, or .xls file."
            )

    def _detect_format(self, columns: list[str]) -> str:
        """Return the best-matching platform format key for *columns*.

        Scores each platform mapping by counting matched column aliases and
        returns the key with the highest score.  Falls back to ``"default"``.
        """
        columns_lower = {c.lower() for c in columns}
        best_format = "default"
        best_score = 0

        for platform, field_map in _PLATFORM_MAPPINGS.items():
            if platform == "default":
                continue
            score = 0
            for aliases in field_map.values():
                if any(alias.lower() in columns_lower for alias in aliases):
                    score += 1
            if score > best_score:
                best_score = score
                best_format = platform

        # Only use a specific platform format if at least 2 fields matched
        if best_score < 2:
            return "default"
        return best_format

    def _build_column_map(
        self,
        columns: list[str],
        mapping: dict[str, list[str]],
    ) -> dict[str, str]:
        """Return ``{logical_field: actual_column_name}`` for *columns*.

        Matching is case-insensitive.
        """
        columns_lower_map = {c.lower(): c for c in columns}
        result: dict[str, str] = {}
        for field, aliases in mapping.items():
            for alias in aliases:
                actual = columns_lower_map.get(alias.lower())
                if actual is not None:
                    result[field] = actual
                    break
        return result

    def _parse_row(
        self,
        row: pd.Series,
        col_map: dict[str, str],
        publisher_id: int,
        row_num: int,
    ) -> tuple[dict | None, list[str]]:
        """Parse a single DataFrame row into a record dict.

        Returns ``(record_or_None, list_of_errors)``.  If the row has
        critical errors (e.g. missing title), the record is None but errors
        are still returned so that callers know the row was skipped.
        """
        row_errors: list[str] = []

        # --- Title ---
        title_raw = row.get(col_map["title"], "")
        if pd.isna(title_raw) or str(title_raw).strip() == "":
            row_errors.append(f"Row {row_num}: Missing title – row skipped.")
            return None, row_errors
        title_name = str(title_raw).strip()

        # --- Platform ---
        platform_name: str | None = None
        if "platform" in col_map:
            platform_raw = row.get(col_map["platform"], "")
            if not pd.isna(platform_raw) and str(platform_raw).strip():
                platform_name = str(platform_raw).strip()

        # --- Period ---
        period_raw = row.get(col_map["period"], "")
        period_date = _parse_date_flexible(period_raw)
        if period_date is None:
            row_errors.append(
                f"Row {row_num}: Could not parse date '{period_raw}' – row skipped."
            )
            return None, row_errors
        period_start, period_end = _period_to_date_range(period_date)

        # --- Revenue ---
        revenue_raw = row.get(col_map["revenue"], "")
        revenue = self._parse_numeric(revenue_raw)
        if revenue is None:
            row_errors.append(
                f"Row {row_num}: Invalid revenue value '{revenue_raw}' – defaulting to 0."
            )
            revenue = 0.0
        elif revenue < 0:
            row_errors.append(
                f"Row {row_num}: Negative revenue '{revenue_raw}' – defaulting to 0."
            )
            revenue = 0.0

        # --- Units sold ---
        units_raw = row.get(col_map["units"], "")
        units = self._parse_numeric(units_raw)
        if units is None:
            row_errors.append(
                f"Row {row_num}: Invalid units value '{units_raw}' – defaulting to 0."
            )
            units = 0
        elif units < 0:
            row_errors.append(
                f"Row {row_num}: Negative units '{units_raw}' – defaulting to 0."
            )
            units = 0

        record = {
            "title_name": title_name,
            "platform_name": platform_name,
            "period_start": period_start,
            "period_end": period_end,
            "revenue": float(revenue),
            "units_sold": int(units),
            "publisher_id": publisher_id,
        }
        return record, row_errors

    @staticmethod
    def _parse_numeric(value: Any) -> float | None:
        """Parse *value* to a float, stripping currency symbols and commas.

        Returns ``None`` if the value cannot be parsed.
        """
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        # Remove common currency symbols, thousands separators
        for char in ("¥", "￥", "$", "€", "£", ",", " ", "\u00a0"):
            text = text.replace(char, "")
        if text == "" or text == "-":
            return None
        try:
            return float(text)
        except ValueError:
            return None
