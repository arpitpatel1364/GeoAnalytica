"""
Data Normalizer — converts raw API/WIE results into the standard DataPoint schema.
Merge Engine — joins multiple field results on entity + timestamp.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


@dataclass
class NormalizedDataPoint:
    entity_name: str
    country_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    field_name: str
    field_value: Optional[float]
    timestamp: str
    source_type: str       # "api" | "web"
    source_name: str
    source_url: str
    confidence_score: float
    is_null: bool
    is_outlier: bool = False
    outlier_reason: Optional[str] = None
    conflicts: Optional[list] = None
    cluster_id: Optional[int] = None


class DataNormalizer:
    """
    Converts raw results from WIE or DirectAPIFetcher into normalized NormalizedDataPoint objects.
    """

    def normalize_wie_results(self, wie_results, entity_meta: Dict[str, dict]) -> List[NormalizedDataPoint]:
        """
        wie_results: List[WIEResult]
        entity_meta: {entity_name: {"iso2": ..., "lat": ..., "lon": ...}}
        """
        normalized = []
        for pt in wie_results:
            meta = entity_meta.get(pt.entity, {})
            normalized.append(NormalizedDataPoint(
                entity_name=pt.entity,
                country_code=meta.get("iso2"),
                latitude=meta.get("lat"),
                longitude=meta.get("lon"),
                field_name=pt.metric,
                field_value=pt.value,
                timestamp=str(pt.timestamp),
                source_type="web",
                source_name=pt.source_name,
                source_url=pt.source_url,
                confidence_score=pt.confidence,
                is_null=pt.is_null,
                conflicts=pt.conflicts if pt.conflicts else None,
            ))
        return normalized

    def normalize_direct_results(self, direct_results, entity_meta: Dict[str, dict]) -> List[NormalizedDataPoint]:
        """
        direct_results: List[DirectAPIResult]
        """
        normalized = []
        for pt in direct_results:
            meta = entity_meta.get(pt.entity, {})
            normalized.append(NormalizedDataPoint(
                entity_name=pt.entity,
                country_code=meta.get("iso2"),
                latitude=meta.get("lat"),
                longitude=meta.get("lon"),
                field_name=pt.metric,
                field_value=pt.value,
                timestamp=str(pt.timestamp),
                source_type="api",
                source_name=pt.source_name,
                source_url=pt.source_url,
                confidence_score=pt.confidence,
                is_null=pt.is_null,
                conflicts=None,
            ))
        return normalized


class MergeEngine:
    """
    Joins data points from multiple field sources on entity + timestamp.
    Applies user-defined filters. Flags null data points.
    """

    def merge(
        self,
        all_points: List[NormalizedDataPoint],
        filters: Optional[List[dict]] = None,
    ) -> List[NormalizedDataPoint]:
        """
        Combine all normalized data points, apply filters, return final list.
        Filters: [{"field": "inflation_rate", "operator": "gt", "value": 5.0}]
        """
        if not filters:
            return all_points

        # Build per-entity averages for filter evaluation
        field_entity_values: Dict[Tuple[str, str], List[float]] = {}
        for pt in all_points:
            if not pt.is_null and pt.field_value is not None:
                key = (pt.entity_name, pt.field_name)
                field_entity_values.setdefault(key, []).append(pt.field_value)

        entity_avgs: Dict[Tuple[str, str], float] = {
            k: sum(v) / len(v)
            for k, v in field_entity_values.items()
        }

        # Determine which entities pass all filters
        all_entities = {pt.entity_name for pt in all_points}
        passing_entities = set()

        for entity in all_entities:
            passes_all = True
            for f in filters:
                field = f.get("field")
                op = f.get("operator", "gt")
                threshold = float(f.get("value", 0))
                avg = entity_avgs.get((entity, field))

                if avg is None:
                    # Entity has no data for this filter field — exclude it
                    passes_all = False
                    break

                ops_map = {
                    "gt": lambda a, t: a > t,
                    "lt": lambda a, t: a < t,
                    "gte": lambda a, t: a >= t,
                    "lte": lambda a, t: a <= t,
                    "eq": lambda a, t: abs(a - t) < 0.001,
                    "neq": lambda a, t: abs(a - t) >= 0.001,
                }
                fn = ops_map.get(op, ops_map["gt"])
                if not fn(avg, threshold):
                    passes_all = False
                    break

            if passes_all:
                passing_entities.add(entity)

        filtered = [pt for pt in all_points if pt.entity_name in passing_entities]

        logger.info(
            "merge_complete",
            total_before=len(all_points),
            total_after=len(filtered),
            entities_passing=len(passing_entities),
        )
        return filtered
