"""
Data Extractors — helper utilities for parsing various file formats.
"""
import io
import re
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


def extract_number(text: str) -> Optional[float]:
    """Extract the first valid number from a string."""
    if not text:
        return None
    text = str(text).strip()
    # Remove currency symbols and percentage
    cleaned = re.sub(r"[£$€¥₹%\s,]", "", text)
    # Handle K/M/B/T suffixes
    multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    for suffix, mult in multipliers.items():
        if cleaned.upper().endswith(suffix):
            try:
                return float(cleaned[:-1]) * mult
            except ValueError:
                return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_csv_bytes(data: bytes, encoding: str = "utf-8") -> List[Dict[str, str]]:
    """Parse CSV bytes into a list of row dicts."""
    import csv
    try:
        text = data.decode(encoding, errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        logger.warning("csv_parse_error", error=str(e))
        return []


def extract_tables_from_html(html: str) -> List[List[List[str]]]:
    """
    Extract all tables from HTML as list of tables,
    where each table is a list of rows, each row is a list of cell strings.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = []
            for cell in tr.find_all(["td", "th"]):
                cells.append(cell.get_text(strip=True))
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def find_year_value_pairs(
    rows: List[List[str]],
    year_col: Optional[int] = None,
    value_col: Optional[int] = None,
) -> Dict[int, float]:
    """
    Given table rows, auto-detect year and value columns
    and return a dict of {year: value}.
    """
    result = {}
    if not rows:
        return result

    # Try to detect header row
    header = rows[0] if rows else []
    year_col_idx = year_col
    value_col_idx = value_col

    if year_col_idx is None:
        for i, h in enumerate(header):
            if h.lower() in ("year", "date", "period", "time"):
                year_col_idx = i
                break

    for row in rows[1:] if header else rows:
        if len(row) < 2:
            continue
        # Try first column as year
        try:
            year = int(str(row[year_col_idx if year_col_idx is not None else 0]).strip()[:4])
            if not (1900 <= year <= 2100):
                continue
        except (ValueError, IndexError):
            continue

        # Try remaining columns for a valid number
        for i, cell in enumerate(row):
            if i == (year_col_idx or 0):
                continue
            val = extract_number(cell)
            if val is not None:
                result[year] = val
                break

    return result


def extract_json_ld(html: str) -> List[dict]:
    """Extract all JSON-LD structured data from an HTML page."""
    import json
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            results.append(data)
        except (json.JSONDecodeError, Exception):
            continue
    return results


def clean_entity_name(name: str) -> str:
    """Normalize an entity name for matching."""
    # Remove common variations
    replacements = {
        "united states of america": "United States",
        "usa": "United States",
        "uk": "United Kingdom",
        "great britain": "United Kingdom",
        "south korea": "South Korea",
        "republic of korea": "South Korea",
        "north korea": "North Korea",
        "democratic people's republic of korea": "North Korea",
        "taiwan, province of china": "Taiwan",
        "hong kong sar": "Hong Kong",
        "czech republic": "Czech Republic",
        "czechia": "Czech Republic",
        "türkiye": "Turkey",
        "türkiye (turkey)": "Turkey",
        "côte d'ivoire": "Ivory Coast",
    }
    normalized = name.strip().lower()
    return replacements.get(normalized, name.strip())
