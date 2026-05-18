"""
Confidence Scorer — assigns confidence scores to data points
based on source type, extraction method, and data completeness.
"""
from typing import Optional


SOURCE_BASE_SCORES = {
    "World Bank API": 0.95,
    "World Bank": 0.95,
    "IMF DataMapper": 0.92,
    "IMF": 0.92,
    "OECD": 0.90,
    "Open-Meteo": 0.90,
    "REST Countries": 0.85,
    "Alpha Vantage": 0.93,
    "NewsAPI": 0.88,
    "UN Data": 0.88,
    "FRED": 0.90,
    "Wikipedia": 0.70,
    "Trading Economics": 0.65,
    "Macrotrends": 0.62,
    "Our World in Data": 0.75,
    "web_search": 0.45,
    "not_found": 0.0,
}

DOMAIN_SCORES = {
    "data.worldbank.org": 0.92,
    "api.worldbank.org": 0.95,
    "imf.org": 0.92,
    "stats.oecd.org": 0.90,
    "data.un.org": 0.88,
    "fred.stlouisfed.org": 0.90,
    "en.wikipedia.org": 0.70,
    "tradingeconomics.com": 0.65,
    "macrotrends.net": 0.62,
    "ourworldindata.org": 0.75,
    "open-meteo.com": 0.90,
    "restcountries.com": 0.85,
}


def score_from_source(
    source_name: str,
    source_url: Optional[str] = None,
    extraction_method: str = "api",
    has_conflicts: bool = False,
    is_null: bool = False,
) -> float:
    """
    Compute a confidence score between 0.0 and 1.0.
    
    Parameters
    ----------
    source_name: str — name of the data source
    source_url: str — URL of the data source (for domain scoring)
    extraction_method: str — "api" | "csv" | "html_table" | "text_nlp"
    has_conflicts: bool — whether conflicting values were found
    is_null: bool — whether the value is missing
    """
    if is_null:
        return 0.0

    # Start with source base score
    score = SOURCE_BASE_SCORES.get(source_name, 0.5)

    # Try domain matching if source_name not in catalog
    if score == 0.5 and source_url:
        for domain, domain_score in DOMAIN_SCORES.items():
            if domain in source_url:
                score = domain_score
                break

    # Adjust for extraction method
    method_adjustments = {
        "api": 0.0,          # No adjustment — authoritative
        "csv": -0.03,        # Slight penalty — parsed file
        "html_table": -0.10, # HTML table extraction — less reliable
        "json_ld": -0.05,    # Structured data on page — pretty reliable
        "text_nlp": -0.25,   # NLP extraction from text — least reliable
    }
    score += method_adjustments.get(extraction_method, -0.15)

    # Penalty for conflicting values
    if has_conflicts:
        score -= 0.08

    # Clamp to [0.0, 1.0]
    return round(max(0.0, min(1.0, score)), 4)


def get_confidence_label(score: float) -> str:
    if score >= 0.8:
        return "High"
    elif score >= 0.5:
        return "Medium"
    elif score > 0.0:
        return "Low"
    else:
        return "No data"


def get_confidence_css_class(score: float) -> str:
    if score >= 0.8:
        return "conf-high"
    elif score >= 0.5:
        return "conf-medium"
    elif score > 0.0:
        return "conf-low"
    else:
        return "conf-null"
