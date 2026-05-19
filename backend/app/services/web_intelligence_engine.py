"""
Web Intelligence Engine (WIE)
Full 8-step pipeline:
1. Query Decomposition
2. Search Execution (parallel)
3. Source Prioritization
4. Structured Data Extraction (Playwright + BS4)
5. Data Normalization
6. Conflict Resolution
7. Gap Detection
8. Result Assembly
"""
import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
import structlog
from bs4 import BeautifulSoup

from app.config import settings
from app.services.cache_service import cache
from app.utils.field_catalog import FIELD_CATALOG

logger = structlog.get_logger()

# Source trust ranking (higher = more trusted)
SOURCE_TRUST: Dict[str, int] = {
    "data.worldbank.org": 10,
    "imf.org": 9,
    "stats.oecd.org": 9,
    "data.un.org": 8,
    "fred.stlouisfed.org": 8,
    "en.wikipedia.org": 7,
    "tradingeconomics.com": 6,
    "macrotrends.net": 5,
    "ourworldindata.org": 6,
    "open-meteo.com": 8,
    "restcountries.com": 7,
}


@dataclass
class RawDataPoint:
    entity: str
    metric: str
    timestamp: str
    value: Optional[float]
    source_url: str
    source_name: str
    confidence: float  # 0.0 - 1.0
    raw_text: str = ""
    conflicts: List[dict] = field(default_factory=list)


@dataclass
class WIEResult:
    entity: str
    metric: str
    timestamp: str
    value: Optional[float]
    source_url: str
    source_name: str
    confidence: float
    is_null: bool
    conflicts: List[dict] = field(default_factory=list)


class WebIntelligenceEngine:
    def __init__(self):
        self.timeout = settings.SCRAPE_TIMEOUT_SECONDS
        self.http_timeout = settings.HTTP_REQUEST_TIMEOUT_SECONDS
        self.max_workers = settings.MAX_PARALLEL_SCRAPE_WORKERS

    # ─────────────────────────────────────────────────────────
    # STEP 1: Query Decomposition
    # ─────────────────────────────────────────────────────────
    def decompose_query(
        self,
        entities: List[dict],
        fields: List[str],
        time_start: str,
        time_end: str,
        granularity: str,
    ) -> List[dict]:
        """Build atomic search intents from query parameters."""
        intents = []
        years = list(range(int(time_start), int(time_end) + 1))

        for entity in entities:
            for field_name in fields:
                catalog = FIELD_CATALOG.get(field_name)
                display = catalog.display_name if catalog else field_name.replace("_", " ")
                search_template = (
                    catalog.search_query_template if catalog
                    else "{entity} {field} {year}"
                )

                if granularity == "annual":
                    # One search per entity covers the whole range
                    query_str = search_template.format(
                        entity=entity["name"],
                        field=display,
                        year=f"{time_start} {time_end}",
                    )
                    intents.append({
                        "entity": entity,
                        "field": field_name,
                        "display_field": display,
                        "years": years,
                        "query": query_str,
                        "granularity": granularity,
                    })
                else:
                    # Monthly/quarterly: search per year
                    for year in years:
                        query_str = search_template.format(
                            entity=entity["name"],
                            field=display,
                            year=year,
                        )
                        intents.append({
                            "entity": entity,
                            "field": field_name,
                            "display_field": display,
                            "years": [year],
                            "query": query_str,
                            "granularity": granularity,
                        })
        return intents

    # ─────────────────────────────────────────────────────────
    # STEP 2: Search Execution
    # ─────────────────────────────────────────────────────────
    async def search_web(self, query: str) -> List[dict]:
        """Execute a web search and return ranked result URLs."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cached = await cache.get_search_results(query_hash)
        if cached:
            return cached

        results = []

        # Try Brave Search API if key available
        if settings.BRAVE_API_KEY:
            try:
                results = await self._brave_search(query)
            except Exception as e:
                logger.warning("brave_search_failed", error=str(e))

        # Fallback: DuckDuckGo instant answers (HTML scrape)
        if not results:
            try:
                results = await self._duckduckgo_search(query)
            except Exception as e:
                logger.warning("ddg_search_failed", error=str(e))

        # Further fallback: construct known URLs directly
        if not results:
            results = self._construct_known_urls(query)

        # Cache for 2 hours
        await cache.set_search_results(query_hash, results, ttl_seconds=7200)
        return results

    async def _brave_search(self, query: str) -> List[dict]:
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 8},
                headers={"Accept": "application/json",
                         "X-Subscription-Token": settings.BRAVE_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {"url": r["url"], "title": r.get("title", ""), "snippet": r.get("description", "")}
                for r in data.get("web", {}).get("results", [])
            ]

    async def _duckduckgo_search(self, query: str) -> List[dict]:
        async with httpx.AsyncClient(
            timeout=self.http_timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; GeoAnalytica/1.0)"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
            )
            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            for a in soup.select(".result__a")[:8]:
                href = a.get("href", "")
                if href.startswith("http"):
                    results.append({"url": href, "title": a.get_text(), "snippet": ""})
            return results

    def _construct_known_urls(self, query: str) -> List[dict]:
        """Build known data portal URLs as fallback."""
        words = query.lower().split()
        urls = []

        if any(w in words for w in ["gdp", "inflation", "unemployment", "trade", "debt"]):
            urls.append({
                "url": "https://data.worldbank.org/indicator",
                "title": "World Bank Data",
                "snippet": "",
            })
            urls.append({
                "url": "https://www.imf.org/en/Data",
                "title": "IMF Data",
                "snippet": "",
            })

        if any(w in words for w in ["climate", "co2", "temperature", "emissions"]):
            urls.append({
                "url": "https://ourworldindata.org",
                "title": "Our World in Data",
                "snippet": "",
            })

        return urls

    # ─────────────────────────────────────────────────────────
    # STEP 3: Source Prioritization
    # ─────────────────────────────────────────────────────────
    def prioritize_sources(self, search_results: List[dict]) -> List[dict]:
        def trust_score(r: dict) -> int:
            url = r.get("url", "")
            for domain, score in SOURCE_TRUST.items():
                if domain in url:
                    return score
            return 1

        return sorted(search_results, key=trust_score, reverse=True)

    # ─────────────────────────────────────────────────────────
    # STEP 4: Data Extraction
    # ─────────────────────────────────────────────────────────
    async def extract_from_url(
        self,
        url: str,
        entity: str,
        field_name: str,
        years: List[int],
    ) -> List[RawDataPoint]:
        """Try multiple extraction strategies in order."""
        results: List[RawDataPoint] = []

        try:
            # Strategy A: Direct CSV/Excel download links
            if any(ext in url for ext in [".csv", ".xlsx", ".xls"]):
                results = await self._extract_csv(url, entity, field_name, years)
                if results:
                    return results

            # Strategy B: Known structured APIs
            if "data.worldbank.org" in url or "api.worldbank.org" in url:
                results = await self._extract_worldbank_api(entity, field_name, years)
                if results:
                    return results

            if "imf.org" in url:
                results = await self._extract_imf(entity, field_name, years)
                if results:
                    return results

            if "stats.oecd.org" in url or "data-explorer.oecd.org" in url:
                results = await self._extract_oecd(entity, field_name, years)
                if results:
                    return results

            # Strategy C: HTML table extraction via httpx + BS4
            html_results = await self._extract_html_tables(url, entity, field_name, years)
            if html_results:
                return html_results

            # Strategy D: NLP number extraction from page text
            text_results = await self._extract_from_text(url, entity, field_name, years)
            return text_results

        except asyncio.TimeoutError:
            logger.warning("extraction_timeout", url=url, entity=entity)
            return []
        except Exception as e:
            logger.warning("extraction_error", url=url, entity=entity, error=str(e))
            return []

    async def _extract_worldbank_api(
        self, entity: str, field_name: str, years: List[int]
    ) -> List[RawDataPoint]:
        """Use World Bank REST API (no key needed)."""
        from app.utils.field_catalog import FIELD_CATALOG
        catalog = FIELD_CATALOG.get(field_name)
        wb_indicator = catalog.world_bank_indicator if catalog else None
        if not wb_indicator:
            return []

        # Resolve country ISO2 code
        from app.utils.geo_utils import name_to_iso2
        iso2 = name_to_iso2(entity)
        if not iso2:
            return []

        year_start = min(years)
        year_end = max(years)

        url = (
            f"https://api.worldbank.org/v2/country/{iso2}/indicator/{wb_indicator}"
            f"?format=json&date={year_start}:{year_end}&per_page=100&mrv=100"
        )

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                if len(data) < 2 or not data[1]:
                    return []

                results = []
                for entry in data[1]:
                    val = entry.get("value")
                    year = str(entry.get("date", ""))
                    if year and int(year) in years:
                        results.append(RawDataPoint(
                            entity=entity,
                            metric=field_name,
                            timestamp=year,
                            value=float(val) if val is not None else None,
                            source_url=url,
                            source_name="World Bank API",
                            confidence=0.95,
                        ))
                return results
        except Exception as e:
            logger.warning("worldbank_api_error", entity=entity, field=field_name, error=str(e))
            return []

    async def _extract_imf(
        self, entity: str, field_name: str, years: List[int]
    ) -> List[RawDataPoint]:
        """Fetch from IMF World Economic Outlook data."""
        from app.utils.field_catalog import FIELD_CATALOG
        catalog = FIELD_CATALOG.get(field_name)
        imf_code = catalog.imf_code if catalog else None
        if not imf_code:
            return []

        from app.utils.geo_utils import name_to_iso3
        iso3 = name_to_iso3(entity)
        if not iso3:
            return []

        url = (
            f"https://www.imf.org/external/datamapper/api/v1/{imf_code}/{iso3}"
        )
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                if resp.status_code != 200:
                    return []
                data = resp.json()
                values = (
                    data.get("values", {})
                    .get(imf_code, {})
                    .get(iso3, {})
                )
                results = []
                for year_str, val in values.items():
                    try:
                        if int(year_str) in years:
                            results.append(RawDataPoint(
                                entity=entity,
                                metric=field_name,
                                timestamp=year_str,
                                value=float(val) if val is not None else None,
                                source_url=url,
                                source_name="IMF DataMapper",
                                confidence=0.92,
                            ))
                    except (ValueError, TypeError):
                        continue
                return results
        except Exception as e:
            logger.warning("imf_api_error", entity=entity, error=str(e))
            return []

    async def _extract_oecd(
        self, entity: str, field_name: str, years: List[int]
    ) -> List[RawDataPoint]:
        """Fetch from OECD Stats API (public, no key)."""
        from app.utils.field_catalog import FIELD_CATALOG
        catalog = FIELD_CATALOG.get(field_name)
        oecd_ds = catalog.oecd_dataset if catalog else None
        if not oecd_ds:
            return []

        from app.utils.geo_utils import name_to_iso3
        iso3 = name_to_iso3(entity)
        if not iso3:
            return []

        year_filter = "+".join(str(y) for y in years)
        url = f"https://stats.oecd.org/SDMX-JSON/data/{oecd_ds}/{iso3}.{year_filter}/all?contentType=csv"
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                return self._parse_csv_text(resp.text, entity, field_name, years, url, "OECD", 0.9)
        except Exception as e:
            logger.warning("oecd_error", entity=entity, error=str(e))
            return []

    async def _extract_csv(
        self, url: str, entity: str, field_name: str, years: List[int]
    ) -> List[RawDataPoint]:
        try:
            async with httpx.AsyncClient(
                timeout=self.http_timeout,
                headers={"User-Agent": "Mozilla/5.0"},
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                return self._parse_csv_text(resp.text, entity, field_name, years, url, url.split("/")[2], 0.85)
        except Exception as e:
            logger.warning("csv_extract_error", url=url, error=str(e))
            return []

    def _parse_csv_text(
        self,
        text: str,
        entity: str,
        field_name: str,
        years: List[int],
        source_url: str,
        source_name: str,
        confidence: float,
    ) -> List[RawDataPoint]:
        import io
        import csv
        results = []
        try:
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                # Try to find year column and value column
                year_val = None
                metric_val = None
                for key, val in row.items():
                    k_lower = key.lower().strip()
                    if k_lower in ("year", "date", "period", "time"):
                        try:
                            year_val = int(str(val).strip()[:4])
                        except ValueError:
                            pass
                    if field_name.lower() in k_lower or k_lower in ("value", "obs_value", "amount"):
                        cleaned = self._clean_number(str(val))
                        if cleaned is not None:
                            metric_val = cleaned

                if year_val and year_val in years and metric_val is not None:
                    results.append(RawDataPoint(
                        entity=entity,
                        metric=field_name,
                        timestamp=str(year_val),
                        value=metric_val,
                        source_url=source_url,
                        source_name=source_name,
                        confidence=confidence,
                    ))
        except Exception as e:
            logger.warning("csv_parse_error", error=str(e))
        return results

    async def _extract_html_tables(
        self, url: str, entity: str, field_name: str, years: List[int]
    ) -> List[RawDataPoint]:
        """Fetch HTML and extract tables using BS4."""
        try:
            async with httpx.AsyncClient(
                timeout=self.http_timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                return self._parse_html_tables(
                    resp.text, entity, field_name, years, url
                )
        except Exception as e:
            logger.warning("html_table_error", url=url, error=str(e))
            return []

    def _parse_html_tables(
        self,
        html: str,
        entity: str,
        field_name: str,
        years: List[int],
        url: str,
    ) -> List[RawDataPoint]:
        """Parse all tables from HTML and extract year+value pairs."""
        soup = BeautifulSoup(html, "lxml")
        results: List[RawDataPoint] = []

        # Check for JSON-LD structured data first
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                ld = json.loads(script.string or "{}")
                if isinstance(ld, dict) and "observation" in ld:
                    for obs in ld["observation"]:
                        try:
                            ts = str(obs.get("timePeriod", ""))[:4]
                            val = obs.get("obsValue")
                            if ts and val and int(ts) in years:
                                results.append(RawDataPoint(
                                    entity=entity,
                                    metric=field_name,
                                    timestamp=ts,
                                    value=float(val),
                                    source_url=url,
                                    source_name=url.split("/")[2],
                                    confidence=0.85,
                                ))
                        except (ValueError, TypeError, KeyError):
                            continue
            except Exception:
                continue

        if results:
            return results

        # Parse HTML tables
        domain = url.split("/")[2] if "/" in url else url
        trust = SOURCE_TRUST.get(domain, 1)
        confidence = min(0.5 + trust * 0.04, 0.9)

        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            rows = table.find_all("tr")

            for row in rows:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) < 2:
                    continue

                # Try to extract year from first column
                year_match = re.match(r"^(19|20)\d{2}", cells[0].strip())
                if not year_match:
                    continue
                year = int(year_match.group())
                if year not in years:
                    continue

                # Find numeric values in remaining cells
                for i, cell in enumerate(cells[1:], 1):
                    val = self._clean_number(cell)
                    if val is not None and abs(val) < 1e12:
                        results.append(RawDataPoint(
                            entity=entity,
                            metric=field_name,
                            timestamp=str(year),
                            value=val,
                            source_url=url,
                            source_name=domain,
                            confidence=confidence,
                        ))
                        break  # Take first valid numeric value per row

        return results

    async def _extract_from_text(
        self, url: str, entity: str, field_name: str, years: List[int]
    ) -> List[RawDataPoint]:
        """Last resort: NLP-style regex extraction from page text."""
        try:
            async with httpx.AsyncClient(
                timeout=self.http_timeout,
                headers={"User-Agent": "Mozilla/5.0"},
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, "lxml")
                text = soup.get_text(" ")
        except Exception:
            return []

        results: List[RawDataPoint] = []
        domain = url.split("/")[2] if "/" in url else url

        # Pattern: "2021: 8.3%" or "8.3% in 2021" or "2021 was 8.3"
        patterns = [
            r"(20\d{2})[:\s]+([+-]?\d{1,6}(?:[.,]\d{1,4})?)\s*%?",
            r"([+-]?\d{1,6}(?:[.,]\d{1,4})?)\s*%?\s+in\s+(20\d{2})",
            r"(20\d{2})\s+(?:was|is|:)\s+([+-]?\d{1,6}(?:[.,]\d{1,4})?)",
        ]

        found: Dict[int, List[float]] = {}
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                groups = match.groups()
                try:
                    if groups[0].startswith("20"):
                        year, raw_val = int(groups[0]), groups[1]
                    else:
                        raw_val, year = groups[0], int(groups[1])
                    val = self._clean_number(raw_val)
                    if val is not None and year in years:
                        found.setdefault(year, []).append(val)
                except (ValueError, TypeError):
                    continue

        for year, vals in found.items():
            # Take median to reduce noise
            vals.sort()
            median_val = vals[len(vals) // 2]
            results.append(RawDataPoint(
                entity=entity,
                metric=field_name,
                timestamp=str(year),
                value=median_val,
                source_url=url,
                source_name=domain,
                confidence=0.4,  # Low confidence for text extraction
                raw_text=f"Extracted from text — {len(vals)} mentions",
            ))

        return results

    # ─────────────────────────────────────────────────────────
    # STEP 5: Data Normalization (helper)
    # ─────────────────────────────────────────────────────────
    def _clean_number(self, raw: str) -> Optional[float]:
        """Parse a messy number string into a float."""
        if not raw:
            return None
        # Remove currency symbols, spaces, percentage
        cleaned = re.sub(r"[£$€¥₹%\s]", "", str(raw).strip())
        # Handle European decimal format: 1.234,56 -> 1234.56
        if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", cleaned):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
        # Handle K/M/B suffixes
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

    # ─────────────────────────────────────────────────────────
    # STEP 6: Conflict Resolution
    # ─────────────────────────────────────────────────────────
    def resolve_conflicts(
        self, raw_points: List[RawDataPoint]
    ) -> List[RawDataPoint]:
        """Group by entity+metric+year, keep highest-trust value, record conflicts."""
        grouped: Dict[Tuple, List[RawDataPoint]] = {}
        for pt in raw_points:
            key = (pt.entity, pt.metric, pt.timestamp)
            grouped.setdefault(key, []).append(pt)

        resolved = []
        for key, points in grouped.items():
            if len(points) == 1:
                resolved.append(points[0])
                continue
            # Sort by confidence desc
            points.sort(key=lambda p: p.confidence, reverse=True)
            winner = points[0]
            conflicts = [
                {
                    "source": p.source_name,
                    "value": p.value,
                    "confidence": p.confidence,
                    "url": p.source_url,
                }
                for p in points[1:]
                if p.value != winner.value
            ]
            winner.conflicts = conflicts
            resolved.append(winner)

        return resolved

    # ─────────────────────────────────────────────────────────
    # STEP 7: Gap Detection
    # ─────────────────────────────────────────────────────────
    def detect_gaps(
        self,
        resolved: List[RawDataPoint],
        entities: List[dict],
        fields: List[str],
        years: List[int],
    ) -> List[RawDataPoint]:
        """Fill in null placeholders for missing entity+field+year combos."""
        existing = {
            (p.entity, p.metric, p.timestamp)
            for p in resolved
            if p.value is not None
        }

        for entity in entities:
            for field_name in fields:
                for year in years:
                    key = (entity["name"], field_name, str(year))
                    if key not in existing:
                        resolved.append(RawDataPoint(
                            entity=entity["name"],
                            metric=field_name,
                            timestamp=str(year),
                            value=None,
                            source_url="",
                            source_name="not_found",
                            confidence=0.0,
                            raw_text="Gap detected — no source returned data",
                        ))
        return resolved

    # ─────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────
    async def fetch(
        self,
        entities: List[dict],
        fields: List[str],
        time_start: str,
        time_end: str,
        granularity: str = "annual",
        progress_callback: Optional[Callable] = None,
    ) -> List[WIEResult]:
        """
        Main WIE pipeline. Returns normalized, conflict-resolved, gap-detected data points.
        progress_callback(entity_name, field, count_done, count_total) called after each entity.
        """
        years = list(range(int(time_start), int(time_end) + 1))
        intents = self.decompose_query(entities, fields, time_start, time_end, granularity)

        all_raw: List[RawDataPoint] = []
        total = len(intents)
        done = 0

        # Process in parallel batches
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_intent(intent: dict) -> List[RawDataPoint]:
            nonlocal done
            entity = intent["entity"]
            field_name = intent["field"]
            intent_years = intent["years"]

            # Check cache first
            cached_pts = []
            for year in intent_years:
                c = await cache.get_datapoint(entity["name"], field_name, str(year))
                if c:
                    cached_pts.append(RawDataPoint(**c))

            if len(cached_pts) == len(intent_years):
                done += 1
                if progress_callback:
                    latest_val = None
                    valid_pts = [p for p in cached_pts if p.value is not None]
                    if valid_pts:
                        latest_val = sorted(valid_pts, key=lambda x: str(x.timestamp))[-1].value
                    await progress_callback(entity["name"], field_name, done, total, latest_value=latest_val)
                return cached_pts

            # Try World Bank API first (free, most reliable)
            pts = await self._extract_worldbank_api(entity["name"], field_name, intent_years)

            # Try IMF if WB didn't return data
            if not pts:
                pts = await self._extract_imf(entity["name"], field_name, intent_years)

            # If still no data, fall back to web search + extraction
            if not pts:
                async with semaphore:
                    search_results = await self.search_web(intent["query"])
                    ranked = self.prioritize_sources(search_results)
                    for result in ranked[:3]:  # Try top 3 URLs
                        pts = await self.extract_from_url(
                            result["url"], entity["name"], field_name, intent_years
                        )
                        if pts:
                            break

            # Cache results
            for pt in pts:
                if pt.value is not None:
                    await cache.set_datapoint(
                        entity["name"], field_name, pt.timestamp,
                        {
                            "entity": pt.entity,
                            "metric": pt.metric,
                            "timestamp": pt.timestamp,
                            "value": pt.value,
                            "source_url": pt.source_url,
                            "source_name": pt.source_name,
                            "confidence": pt.confidence,
                            "raw_text": pt.raw_text,
                            "conflicts": pt.conflicts,
                        },
                        ttl_seconds=settings.cache_ttl_annual_seconds,
                    )

            done += 1
            if progress_callback:
                try:
                    latest_val = None
                    valid_pts = [p for p in pts if p.value is not None]
                    if valid_pts:
                        latest_val = sorted(valid_pts, key=lambda x: str(x.timestamp))[-1].value
                    await progress_callback(entity["name"], field_name, done, total, latest_value=latest_val)
                except Exception:
                    pass

            return pts

        # Run all intents concurrently
        tasks = [process_intent(intent) for intent in intents]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results_nested:
            if isinstance(r, list):
                all_raw.extend(r)
            elif isinstance(r, Exception):
                logger.warning("intent_error", error=str(r))

        # Steps 6 & 7
        resolved = self.resolve_conflicts(all_raw)
        resolved = self.detect_gaps(resolved, entities, fields, years)

        # STEP 8: Assemble WIEResult objects
        final: List[WIEResult] = []
        for pt in resolved:
            final.append(WIEResult(
                entity=pt.entity,
                metric=pt.metric,
                timestamp=pt.timestamp,
                value=pt.value,
                source_url=pt.source_url,
                source_name=pt.source_name,
                confidence=pt.confidence,
                is_null=pt.value is None,
                conflicts=pt.conflicts,
            ))

        logger.info(
            "wie_complete",
            total=len(final),
            null_count=sum(1 for p in final if p.is_null),
        )
        return final
