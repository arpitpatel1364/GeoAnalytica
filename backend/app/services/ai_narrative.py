"""
AI Narrative Generator — calls Claude API to produce structured analysis narrative.
"""
import json
import re
from typing import Optional

import structlog
from anthropic import AsyncAnthropic

from app.config import settings

logger = structlog.get_logger()
client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a senior data analyst specializing in geopolitical and economic data.
You will receive a geospatial dataset analysis and must produce a structured narrative report.

Return ONLY a valid JSON object with NO surrounding text, markdown, or explanation:
{
  "summary": "2-3 paragraph executive summary of the key patterns and insights",
  "key_findings": [
    "Finding 1 — specific, quantified insight",
    "Finding 2 — specific, quantified insight",
    "Finding 3 — specific, quantified insight",
    "Finding 4 — specific, quantified insight",
    "Finding 5 — specific, quantified insight"
  ],
  "anomalies": [
    "Anomaly description with specific entity, value, and why it stands out",
    "Second anomaly if present"
  ],
  "data_quality_note": "Brief note on data confidence, source mix, and any significant gaps"
}

Guidelines:
- Be specific: cite country names, exact percentages, years
- Identify correlation patterns, outliers, regional clusters
- Highlight trends (rising, falling, volatile)
- Note data quality issues like high null rates or low-confidence sources
- Keep summary under 400 words total
- Each key finding must be one concrete, data-backed statement"""


def _build_context(
    analysis_result: dict,
    original_instruction: str,
    max_tokens: int = 6000,
) -> str:
    """Build a compact context string for the Claude prompt."""
    parts = [f"USER QUERY: {original_instruction}\n"]

    stats = analysis_result.get("stats_summary", {})
    if stats:
        parts.append("DESCRIPTIVE STATISTICS:")
        for field, s in list(stats.items())[:5]:
            def _fmt(v):
                return f"{v:.2f}" if v is not None and not isinstance(v, str) else str(v or 'N/A')
            parts.append(
                f"  {field}: mean={_fmt(s.get('mean'))}, "
                f"min={_fmt(s.get('min'))}, max={_fmt(s.get('max'))}, "
                f"std={_fmt(s.get('std'))}, null_rate={s.get('null_rate', 0):.1%}"
            )

    rankings = analysis_result.get("entity_rankings", [])
    if rankings:
        parts.append(f"\nTOP ENTITIES (by primary metric, top 15):")
        for r in rankings[:15]:
            parts.append(f"  #{r['rank']} {r['entity']}: {r.get('avg_value', 'N/A'):.2f}")

        if len(rankings) > 15:
            parts.append(f"  ... and {len(rankings) - 15} more entities")

    corr = analysis_result.get("correlation_matrix", {})
    if corr:
        parts.append("\nCORRELATION MATRIX (Pearson r):")
        fields = list(corr.keys())
        for i, f1 in enumerate(fields):
            for f2 in fields[i + 1:]:
                coef_data = corr.get(f1, {}).get(f2, {})
                coef = coef_data.get("coefficient")
                if coef is not None:
                    sig = " *" if coef_data.get("significant") else ""
                    parts.append(f"  {f1} vs {f2}: r={coef:.3f}{sig}")

    outliers = [
        pt for pt in analysis_result.get("data_points", [])
        if getattr(pt, "is_outlier", False)
    ]
    if outliers:
        parts.append(f"\nOUTLIERS DETECTED ({len(outliers)} total):")
        for pt in outliers[:10]:
            parts.append(
                f"  {pt.entity_name} {pt.field_name} {pt.timestamp}: "
                f"{pt.field_value:.2f} ({pt.outlier_reason})"
            )

    total_pts = len(analysis_result.get("data_points", []))
    null_count = sum(1 for pt in analysis_result.get("data_points", []) if getattr(pt, "is_null", False))
    web_count = sum(1 for pt in analysis_result.get("data_points", []) if getattr(pt, "source_type", "web") == "web")
    api_count = total_pts - null_count - web_count
    parts.append(f"\nDATA QUALITY:")
    parts.append(f"  Total points: {total_pts}")
    parts.append(f"  Null/missing: {null_count} ({null_count/total_pts:.1%} null rate)" if total_pts else "  No data points")
    parts.append(f"  From direct API: {api_count}")
    parts.append(f"  From web scrape: {web_count}")

    return "\n".join(parts)


async def generate_narrative(
    analysis_result: dict,
    original_instruction: str,
) -> dict:
    """
    Generate a structured narrative using Claude.
    Returns dict with summary, key_findings, anomalies, data_quality_note.
    Never raises — returns fallback on error.
    """
    fallback = {
        "summary": "Analysis complete. Review the charts and data table for detailed insights.",
        "key_findings": ["Data successfully fetched and analyzed.", "Review the visualization panels for patterns."],
        "anomalies": [],
        "data_quality_note": "Data sourced from public web sources. Verify critical values with primary sources.",
    }

    if not settings.ANTHROPIC_API_KEY:
        logger.warning("anthropic_key_missing_narrative")
        return fallback

    try:
        context = _build_context(analysis_result, original_instruction)

        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
        )

        raw = response.content[0].text.strip()

        # Extract JSON
        parsed = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]+\}", raw)
            if match:
                try:
                    parsed = json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        if not parsed:
            logger.error("narrative_json_parse_failed", raw=raw[:200])
            return fallback

        return {
            "summary": str(parsed.get("summary", fallback["summary"])),
            "key_findings": list(parsed.get("key_findings", fallback["key_findings"])),
            "anomalies": list(parsed.get("anomalies", [])),
            "data_quality_note": str(parsed.get("data_quality_note", fallback["data_quality_note"])),
        }

    except Exception as e:
        logger.error("narrative_generation_error", error=str(e))
        return fallback
