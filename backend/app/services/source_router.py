from dataclasses import dataclass
from typing import Dict, List, Optional

import structlog

from app.utils.field_catalog import FIELD_CATALOG, FieldDefinition

logger = structlog.get_logger()


@dataclass
class RoutedField:
    field_name: str
    route_type: str          # "direct_api" | "web_scrape"
    source_name: str         # e.g. "world_bank", "imf", "open_meteo"
    api_key: Optional[str]   # decrypted key if route_type == "direct_api"
    fallback_sources: List[str]
    requires_key: bool
    catalog_entry: FieldDefinition


class SourceRouter:
    """
    For every requested field, decide whether to hit a direct API
    (user has a valid key) or the Web Intelligence Engine (free scrape).
    """

    def route_fields(
        self,
        requested_fields: List[str],
        user_api_keys: Dict[str, str],  # service_name -> decrypted_key
    ) -> List[RoutedField]:
        routed: List[RoutedField] = []

        for field_name in requested_fields:
            entry = FIELD_CATALOG.get(field_name)
            if not entry:
                # Unknown field — try web scrape with a generic search
                logger.warning("unknown_field", field=field_name)
                entry = FieldDefinition(
                    field_name=field_name,
                    display_name=field_name.replace("_", " ").title(),
                    preferred_source="web_search",
                    fallback_sources=["web_search"],
                    requires_api_key=False,
                    api_key_service=None,
                    search_query_template="{entity} {field} {year}",
                    unit="",
                    category="economic",
                )

            preferred = entry.preferred_source
            key_service = entry.api_key_service

            # Check if the preferred source needs a key and user has it
            if entry.requires_api_key and key_service:
                key = user_api_keys.get(key_service)
                if key:
                    routed.append(RoutedField(
                        field_name=field_name,
                        route_type="direct_api",
                        source_name=preferred,
                        api_key=key,
                        fallback_sources=entry.fallback_sources,
                        requires_key=True,
                        catalog_entry=entry,
                    ))
                    logger.info("routed_to_api", field=field_name, source=preferred)
                    continue

            # No key or no key required — route to WIE
            # But some sources work without a key (World Bank, OECD, Open-Meteo)
            no_key_sources = {
                "world_bank", "imf", "oecd", "open_meteo",
                "rest_countries", "un_data", "fred",
            }
            if preferred in no_key_sources:
                routed.append(RoutedField(
                    field_name=field_name,
                    route_type="direct_api",
                    source_name=preferred,
                    api_key=None,
                    fallback_sources=entry.fallback_sources,
                    requires_key=False,
                    catalog_entry=entry,
                ))
                logger.info("routed_to_free_api", field=field_name, source=preferred)
            else:
                routed.append(RoutedField(
                    field_name=field_name,
                    route_type="web_scrape",
                    source_name=preferred,
                    api_key=None,
                    fallback_sources=entry.fallback_sources,
                    requires_key=entry.requires_api_key,
                    catalog_entry=entry,
                ))
                logger.info("routed_to_wie", field=field_name, source=preferred)

        return routed

    def get_entity_list(
        self,
        entity_scope: str,
        specific_entities: List[str],
    ) -> List[dict]:
        """Resolve entity scope to a list of country dicts with codes + coords."""
        from app.utils.geo_utils import SCOPE_COUNTRIES, ALL_COUNTRIES

        if entity_scope == "specific" and specific_entities:
            return [
                c for c in ALL_COUNTRIES
                if c["name"] in specific_entities
                or c["iso2"] in [e.upper() for e in specific_entities]
            ]
        elif entity_scope in SCOPE_COUNTRIES:
            codes = SCOPE_COUNTRIES[entity_scope]
            return [c for c in ALL_COUNTRIES if c["iso2"] in codes]
        else:
            # "world" — return all
            return ALL_COUNTRIES
