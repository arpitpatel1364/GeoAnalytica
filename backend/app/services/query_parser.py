import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

import structlog
from anthropic import AsyncAnthropic

from app.config import settings

logger = structlog.get_logger()

client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a geospatial data query parser. The user will describe what data they want to analyze.
You must parse their request and return ONLY a valid JSON object — no preamble, no markdown, no explanation.

Return exactly this structure:
{
  "fields": ["field_name_1", "field_name_2"],
  "entities": ["Country1", "Country2"],
  "entity_scope": "specific|world|g7|g20|brics|eu|africa|asia|sea|middle_east|americas",
  "time_start": "2015",
  "time_end": "2023",
  "granularity": "annual|quarterly|monthly",
  "filters": [
    {"field": "inflation_rate", "operator": "gt", "value": 5.0}
  ],
  "custom_computation": "description of any custom scoring or ranking needed, or null",
  "output_preference": "table|map|chart|all",
  "error": false,
  "error_message": null
}

Field name mapping (use these exact names):
- GDP → gdp_usd
- GDP per capita → gdp_per_capita
- GDP growth → gdp_growth_rate
- Inflation → inflation_rate
- Unemployment → unemployment_rate
- Current account balance → current_account_balance_pct_gdp
- Government debt → government_debt_pct_gdp
- Trade balance → trade_balance_usd
- FDI → fdi_inflows_usd
- Exchange rate → exchange_rate_usd
- Population → population
- Population growth → population_growth_rate
- Life expectancy → life_expectancy
- Literacy rate → literacy_rate
- HDI → hdi_index
- Urbanization → urbanization_rate
- CO2 emissions → co2_emissions_per_capita
- Temperature anomaly → temperature_anomaly
- Renewable energy → renewable_energy_share
- Political stability → political_stability_index
- News sentiment → news_sentiment_score
- Stock index → stock_index_level

For entity_scope: if user says specific countries, list them in "entities" and set scope to "specific".
If user says a region/group (Africa, G20, etc.) set scope accordingly and leave entities empty.
For filters, operator must be one of: gt, lt, gte, lte, eq, neq.
If you cannot parse the request, set error=true and describe in error_message.
Return ONLY the JSON. No other text."""


@dataclass
class ParsedFilter:
    field: str
    operator: str
    value: float


@dataclass
class ParsedQuerySpec:
    fields: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    entity_scope: str = "world"
    time_start: str = "2018"
    time_end: str = "2023"
    granularity: str = "annual"
    filters: List[ParsedFilter] = field(default_factory=list)
    custom_computation: Optional[str] = None
    output_preference: str = "all"
    error: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "fields": self.fields,
            "entities": self.entities,
            "entity_scope": self.entity_scope,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "granularity": self.granularity,
            "filters": [
                {"field": f.field, "operator": f.operator, "value": f.value}
                for f in self.filters
            ],
            "custom_computation": self.custom_computation,
            "output_preference": self.output_preference,
            "error": self.error,
            "error_message": self.error_message,
        }


def _extract_json(text: str) -> Optional[dict]:
    """Try to extract JSON from text that may have surrounding content."""
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in text
    patterns = [
        r"```json\s*([\s\S]+?)\s*```",
        r"```\s*([\s\S]+?)\s*```",
        r"(\{[\s\S]+\})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


async def parse_instruction(instruction_text: str) -> ParsedQuerySpec:
    """
    Parse a natural language query instruction into a structured ParsedQuerySpec.
    Never raises — returns error spec on failure.
    """
    try:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": instruction_text}],
        )

        raw_text = response.content[0].text
        parsed_json = _extract_json(raw_text)

        if not parsed_json:
            logger.error("query_parser_json_extract_failed", raw=raw_text[:200])
            return ParsedQuerySpec(
                error=True,
                error_message="Failed to extract JSON from Claude response",
            )

        # Build spec
        filters = []
        for f in parsed_json.get("filters", []):
            try:
                filters.append(ParsedFilter(
                    field=str(f["field"]),
                    operator=str(f["operator"]),
                    value=float(f["value"]),
                ))
            except (KeyError, ValueError, TypeError):
                pass

        spec = ParsedQuerySpec(
            fields=parsed_json.get("fields", ["gdp_per_capita"]),
            entities=parsed_json.get("entities", []),
            entity_scope=parsed_json.get("entity_scope", "world"),
            time_start=str(parsed_json.get("time_start", "2018")),
            time_end=str(parsed_json.get("time_end", "2023")),
            granularity=parsed_json.get("granularity", "annual"),
            filters=filters,
            custom_computation=parsed_json.get("custom_computation"),
            output_preference=parsed_json.get("output_preference", "all"),
            error=bool(parsed_json.get("error", False)),
            error_message=parsed_json.get("error_message"),
        )

        # Ensure at least one field
        if not spec.fields:
            spec.fields = ["gdp_per_capita"]

        logger.info(
            "query_parsed",
            fields=spec.fields,
            scope=spec.entity_scope,
            time=f"{spec.time_start}-{spec.time_end}",
        )
        return spec

    except Exception as e:
        logger.error("query_parser_exception", error=str(e))
        return ParsedQuerySpec(
            error=True,
            error_message=f"Query parser error: {str(e)}",
        )
