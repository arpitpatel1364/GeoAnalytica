"""
Direct API Fetcher — handles Pro-tier data sources with user-provided keys.
Each service returns a list of normalized RawDataPoint objects.
"""
import asyncio
from dataclasses import dataclass
from typing import List, Optional

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class DirectAPIResult:
    entity: str
    metric: str
    timestamp: str
    value: Optional[float]
    source_name: str
    source_url: str
    confidence: float
    is_null: bool


@dataclass
class APITestResult:
    success: bool
    message: str
    rate_limit_info: Optional[dict] = None


async def test_api_key_connection(service_name: str, api_key: str) -> APITestResult:
    """Test whether an API key is valid for the given service."""
    testers = {
        "alpha_vantage": _test_alpha_vantage,
        "newsapi": _test_newsapi,
        "openweathermap": _test_openweathermap,
        "serpapi": _test_serpapi,
        "brave_search": _test_brave,
        "mapbox": _test_mapbox,
    }
    tester = testers.get(service_name)
    if not tester:
        return APITestResult(success=False, message=f"Unknown service: {service_name}")
    try:
        return await tester(api_key)
    except Exception as e:
        return APITestResult(success=False, message=f"Test failed: {str(e)}")


async def _test_alpha_vantage(key: str) -> APITestResult:
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={key}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        data = r.json()
        if "Error Message" in data or "Note" in data:
            return APITestResult(success=False, message="Invalid key or rate limited")
        return APITestResult(success=True, message="Connected — 25 requests/minute available",
                             rate_limit_info={"requests_per_minute": 25, "requests_per_day": 500})


async def _test_newsapi(key: str) -> APITestResult:
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={key}&pageSize=1"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        data = r.json()
        if data.get("status") != "ok":
            return APITestResult(success=False, message=data.get("message", "Invalid key"))
        return APITestResult(success=True, message="Connected — 100 requests/day (free tier)",
                             rate_limit_info={"requests_per_day": 100})


async def _test_openweathermap(key: str) -> APITestResult:
    url = f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={key}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        data = r.json()
        if data.get("cod") != 200 and r.status_code != 200:
            return APITestResult(success=False, message=data.get("message", "Invalid key"))
        return APITestResult(success=True, message="Connected — 60 calls/minute (free tier)",
                             rate_limit_info={"calls_per_minute": 60})


async def _test_serpapi(key: str) -> APITestResult:
    url = f"https://serpapi.com/account.json?api_key={key}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return APITestResult(success=False, message="Invalid API key")
        data = r.json()
        return APITestResult(
            success=True,
            message=f"Connected — {data.get('searches_per_month', 'N/A')} searches/month",
            rate_limit_info={"plan": data.get("plan_name")},
        )


async def _test_brave(key: str) -> APITestResult:
    url = "https://api.search.brave.com/res/v1/web/search"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            url,
            params={"q": "test", "count": 1},
            headers={"X-Subscription-Token": key, "Accept": "application/json"},
        )
        if r.status_code != 200:
            return APITestResult(success=False, message="Invalid API key")
        return APITestResult(success=True, message="Connected — Brave Search API",
                             rate_limit_info={"requests_per_month": 2000})


async def _test_mapbox(key: str) -> APITestResult:
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/London.json?access_token={key}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return APITestResult(success=False, message="Invalid Mapbox token")
        return APITestResult(success=True, message="Connected — Mapbox API",
                             rate_limit_info={"requests_per_month": 100000})


class DirectAPIFetcher:
    """Fetch data from direct API integrations."""

    async def fetch(
        self,
        service_name: str,
        api_key: str,
        entity: str,
        field_name: str,
        years: List[int],
    ) -> List[DirectAPIResult]:
        fetchers = {
            "alpha_vantage": self._fetch_alpha_vantage,
            "newsapi": self._fetch_newsapi,
            "openweathermap": self._fetch_openweathermap,
            "world_bank": self._fetch_world_bank_direct,
            "imf": self._fetch_imf_direct,
            "open_meteo": self._fetch_open_meteo,
            "rest_countries": self._fetch_rest_countries,
        }
        fetcher = fetchers.get(service_name)
        if not fetcher:
            logger.warning("unknown_direct_api", service=service_name)
            return []
        try:
            return await fetcher(api_key, entity, field_name, years)
        except Exception as e:
            logger.error("direct_api_fetch_error", service=service_name, entity=entity, error=str(e))
            return []

    async def _fetch_world_bank_direct(
        self, api_key: str, entity: str, field_name: str, years: List[int]
    ) -> List[DirectAPIResult]:
        from app.utils.field_catalog import FIELD_CATALOG
        from app.utils.geo_utils import name_to_iso2
        catalog = FIELD_CATALOG.get(field_name)
        indicator = catalog.world_bank_indicator if catalog else None
        if not indicator:
            return []
        iso2 = name_to_iso2(entity)
        if not iso2:
            return []
        year_start, year_end = min(years), max(years)
        url = (
            f"https://api.worldbank.org/v2/country/{iso2}/indicator/{indicator}"
            f"?format=json&date={year_start}:{year_end}&per_page=100"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url)
            if r.status_code != 200 or len(r.json()) < 2:
                return []
            data = r.json()[1] or []
            return [
                DirectAPIResult(
                    entity=entity,
                    metric=field_name,
                    timestamp=str(d["date"]),
                    value=float(d["value"]) if d.get("value") is not None else None,
                    source_name="World Bank",
                    source_url=url,
                    confidence=0.95,
                    is_null=d.get("value") is None,
                )
                for d in data
                if d.get("date") and int(d["date"]) in years
            ]

    async def _fetch_imf_direct(
        self, api_key: str, entity: str, field_name: str, years: List[int]
    ) -> List[DirectAPIResult]:
        from app.utils.field_catalog import FIELD_CATALOG
        from app.utils.geo_utils import name_to_iso3
        catalog = FIELD_CATALOG.get(field_name)
        imf_code = catalog.imf_code if catalog else None
        if not imf_code:
            return []
        iso3 = name_to_iso3(entity)
        if not iso3:
            return []
        url = f"https://www.imf.org/external/datamapper/api/v1/{imf_code}/{iso3}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, headers={"Accept": "application/json"})
            if r.status_code != 200:
                return []
            data = r.json()
            values = data.get("values", {}).get(imf_code, {}).get(iso3, {})
            return [
                DirectAPIResult(
                    entity=entity,
                    metric=field_name,
                    timestamp=yr,
                    value=float(v) if v is not None else None,
                    source_name="IMF",
                    source_url=url,
                    confidence=0.92,
                    is_null=v is None,
                )
                for yr, v in values.items()
                if int(yr) in years
            ]

    async def _fetch_open_meteo(
        self, api_key: str, entity: str, field_name: str, years: List[int]
    ) -> List[DirectAPIResult]:
        from app.utils.geo_utils import name_to_coords
        coords = name_to_coords(entity)
        if not coords:
            return []
        lat, lon = coords
        year_start, year_end = min(years), max(years)
        url = (
            f"https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={year_start}-01-01&end_date={year_end}-12-31"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=UTC"
        )
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            data = r.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            temps_max = daily.get("temperature_2m_max", [])
            results = []
            yearly_data: dict = {}
            for i, date in enumerate(dates):
                yr = int(date[:4])
                if yr in years:
                    yearly_data.setdefault(yr, [])
                    val = temps_max[i] if i < len(temps_max) else None
                    if val is not None:
                        yearly_data[yr].append(val)
            for yr, vals in yearly_data.items():
                avg = sum(vals) / len(vals) if vals else None
                results.append(DirectAPIResult(
                    entity=entity,
                    metric=field_name,
                    timestamp=str(yr),
                    value=avg,
                    source_name="Open-Meteo",
                    source_url=url,
                    confidence=0.9,
                    is_null=avg is None,
                ))
            return results

    async def _fetch_rest_countries(
        self, api_key: str, entity: str, field_name: str, years: List[int]
    ) -> List[DirectAPIResult]:
        url = f"https://restcountries.com/v3.1/name/{entity}?fullText=true"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            data = r.json()
            if not data:
                return []
            country = data[0]
            field_map = {
                "population": country.get("population"),
                "area_sq_km": country.get("area"),
            }
            value = field_map.get(field_name)
            if value is None:
                return []
            return [
                DirectAPIResult(
                    entity=entity,
                    metric=field_name,
                    timestamp=str(yr),
                    value=float(value),
                    source_name="REST Countries",
                    source_url=url,
                    confidence=0.85,
                    is_null=False,
                )
                for yr in years
            ]

    async def _fetch_alpha_vantage(
        self, api_key: str, entity: str, field_name: str, years: List[int]
    ) -> List[DirectAPIResult]:
        # Alpha Vantage economic indicators
        indicator_map = {
            "gdp_usd": "REAL_GDP",
            "inflation_rate": "INFLATION",
            "unemployment_rate": "UNEMPLOYMENT",
        }
        av_func = indicator_map.get(field_name)
        if not av_func or entity.lower() not in ("united states", "usa", "us"):
            return []
        url = f"https://www.alphavantage.co/query?function={av_func}&apikey={api_key}&interval=annual"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url)
            data = r.json()
            entries = data.get("data", [])
            return [
                DirectAPIResult(
                    entity=entity,
                    metric=field_name,
                    timestamp=e["date"][:4],
                    value=float(e["value"]) if e.get("value") not in (None, ".") else None,
                    source_name="Alpha Vantage",
                    source_url=url,
                    confidence=0.93,
                    is_null=e.get("value") in (None, "."),
                )
                for e in entries
                if int(e["date"][:4]) in years
            ]

    async def _fetch_newsapi(
        self, api_key: str, entity: str, field_name: str, years: List[int]
    ) -> List[DirectAPIResult]:
        url = (
            f"https://newsapi.org/v2/everything"
            f"?q={entity}&language=en&sortBy=publishedAt&pageSize=100&apiKey={api_key}"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            data = r.json()
            articles = data.get("articles", [])
            yearly: dict = {}
            for a in articles:
                yr_str = (a.get("publishedAt") or "")[:4]
                try:
                    yr = int(yr_str)
                    if yr in years:
                        yearly[yr] = yearly.get(yr, 0) + 1
                except ValueError:
                    continue
            return [
                DirectAPIResult(
                    entity=entity,
                    metric=field_name,
                    timestamp=str(yr),
                    value=float(count),
                    source_name="NewsAPI",
                    source_url=url,
                    confidence=0.88,
                    is_null=False,
                )
                for yr, count in yearly.items()
            ]
