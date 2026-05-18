"""
Analysis Engine — runs statistical analysis on normalized data points.
All computations use numpy/scipy/scikit-learn.
"""
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
from scipy import stats

logger = structlog.get_logger()


class AnalysisEngine:

    # ─────────────────────────────────────────────────────────
    # Descriptive Statistics
    # ─────────────────────────────────────────────────────────
    def descriptive_stats(self, data_points) -> dict:
        """
        Returns per-field stats: mean, median, std, min, max, q25, q75,
        count, null_count, null_rate.
        """
        by_field: Dict[str, List[float]] = defaultdict(list)
        nulls_by_field: Dict[str, int] = defaultdict(int)
        total_by_field: Dict[str, int] = defaultdict(int)

        for pt in data_points:
            total_by_field[pt.field_name] += 1
            if pt.is_null or pt.field_value is None:
                nulls_by_field[pt.field_name] += 1
            else:
                by_field[pt.field_name].append(pt.field_value)

        result = {}
        for field, values in by_field.items():
            arr = np.array(values)
            null_count = nulls_by_field[field]
            total = total_by_field[field]
            result[field] = {
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "q25": float(np.percentile(arr, 25)),
                "q75": float(np.percentile(arr, 75)),
                "count": len(values),
                "null_count": null_count,
                "null_rate": round(null_count / total, 4) if total else 0.0,
                "range": float(np.max(arr) - np.min(arr)),
                "skewness": float(stats.skew(arr)) if len(arr) > 2 else 0.0,
                "kurtosis": float(stats.kurtosis(arr)) if len(arr) > 3 else 0.0,
            }

        return result

    # ─────────────────────────────────────────────────────────
    # Outlier Detection
    # ─────────────────────────────────────────────────────────
    def detect_outliers(self, data_points) -> list:
        """
        Mark outliers using IQR method and Z-score.
        Returns modified data_points with is_outlier and outlier_reason set.
        """
        by_field: Dict[str, List[float]] = defaultdict(list)
        for pt in data_points:
            if not pt.is_null and pt.field_value is not None:
                by_field[pt.field_name].append(pt.field_value)

        # Compute IQR and Z-score thresholds per field
        thresholds = {}
        for field, values in by_field.items():
            arr = np.array(values)
            q1, q3 = np.percentile(arr, 25), np.percentile(arr, 75)
            iqr = q3 - q1
            mean, std = np.mean(arr), np.std(arr)
            thresholds[field] = {
                "iqr_lower": q1 - 1.5 * iqr,
                "iqr_upper": q3 + 1.5 * iqr,
                "mean": mean,
                "std": std,
            }

        for pt in data_points:
            if pt.is_null or pt.field_value is None:
                continue
            t = thresholds.get(pt.field_name)
            if not t:
                continue

            val = pt.field_value
            reasons = []

            if val < t["iqr_lower"] or val > t["iqr_upper"]:
                reasons.append("IQR")

            if t["std"] > 0:
                z = abs((val - t["mean"]) / t["std"])
                if z > 3:
                    reasons.append("Z-score")

            if reasons:
                pt.is_outlier = True
                pt.outlier_reason = "+".join(reasons)

        return data_points

    # ─────────────────────────────────────────────────────────
    # Trend Analysis
    # ─────────────────────────────────────────────────────────
    def compute_trends(self, data_points) -> dict:
        """
        Per entity per field:
        - values list, years list
        - moving_avg_3yr
        - yoy_growth_rates
        - trend_direction ("up"/"down"/"flat")
        - cagr
        """
        by_entity_field: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)
        for pt in data_points:
            if not pt.is_null and pt.field_value is not None:
                key = (pt.entity_name, pt.field_name)
                by_entity_field[key][pt.timestamp] = pt.field_value

        trends = {}
        for (entity, field), year_vals in by_entity_field.items():
            sorted_years = sorted(year_vals.keys())
            values = [year_vals[y] for y in sorted_years]

            if len(values) < 2:
                continue

            # YoY growth rates
            yoy = []
            for i in range(1, len(values)):
                prev = values[i - 1]
                curr = values[i]
                if prev and prev != 0:
                    yoy.append(round((curr - prev) / abs(prev) * 100, 2))
                else:
                    yoy.append(None)

            # Moving average (3-year window)
            arr = np.array(values, dtype=float)
            ma3 = []
            for i in range(len(arr)):
                window = arr[max(0, i - 1): i + 2]
                ma3.append(round(float(np.mean(window)), 4))

            # CAGR
            first_val = values[0]
            last_val = values[-1]
            n_years = len(values) - 1
            if first_val and first_val > 0 and last_val > 0 and n_years > 0:
                cagr = round((pow(last_val / first_val, 1 / n_years) - 1) * 100, 4)
            else:
                cagr = None

            # Trend direction using linear regression slope
            if len(values) >= 3:
                x = np.arange(len(values))
                slope, _, r_value, _, _ = stats.linregress(x, arr)
                if abs(slope) < 0.01 * np.mean(np.abs(arr)) if np.mean(np.abs(arr)) > 0 else 0.001:
                    direction = "flat"
                elif slope > 0:
                    direction = "up"
                else:
                    direction = "down"
                r_squared = round(r_value ** 2, 4)
            else:
                direction = "up" if values[-1] > values[0] else "down"
                r_squared = None

            key_str = f"{entity}|{field}"
            trends[key_str] = {
                "entity": entity,
                "field": field,
                "years": sorted_years,
                "values": values,
                "moving_avg_3yr": ma3,
                "yoy_growth_rates": yoy,
                "trend_direction": direction,
                "cagr": cagr,
                "r_squared": r_squared,
            }

        return trends

    # ─────────────────────────────────────────────────────────
    # Correlation Matrix
    # ─────────────────────────────────────────────────────────
    def correlate_fields(self, data_points) -> dict:
        """
        Pearson correlation between each pair of fields across all entities+years.
        Returns {field1: {field2: coefficient}}.
        """
        # Build pivot: {(entity, timestamp): {field: value}}
        pivot: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)
        for pt in data_points:
            if not pt.is_null and pt.field_value is not None:
                pivot[(pt.entity_name, pt.timestamp)][pt.field_name] = pt.field_value

        all_fields = list({pt.field_name for pt in data_points if not pt.is_null})
        if len(all_fields) < 2:
            return {}

        # Build aligned arrays
        field_vectors: Dict[str, List[float]] = {f: [] for f in all_fields}
        for row in pivot.values():
            if all(f in row for f in all_fields):
                for f in all_fields:
                    field_vectors[f].append(row[f])

        if not any(field_vectors.values()):
            return {}

        matrix = {}
        for f1 in all_fields:
            matrix[f1] = {}
            for f2 in all_fields:
                v1 = np.array(field_vectors[f1])
                v2 = np.array(field_vectors[f2])
                if len(v1) > 2 and len(v2) > 2 and np.std(v1) > 0 and np.std(v2) > 0:
                    corr, p_value = stats.pearsonr(v1, v2)
                    matrix[f1][f2] = {
                        "coefficient": round(float(corr), 4),
                        "p_value": round(float(p_value), 6),
                        "significant": p_value < 0.05,
                        "n": len(v1),
                    }
                else:
                    matrix[f1][f2] = {"coefficient": None, "p_value": None, "significant": False, "n": 0}

        return matrix

    # ─────────────────────────────────────────────────────────
    # Entity Rankings
    # ─────────────────────────────────────────────────────────
    def rank_entities(self, data_points, primary_field: str) -> list:
        """
        Rank entities by average value of primary_field descending.
        Returns list of {entity, avg_value, rank, country_code}.
        """
        entity_vals: Dict[str, List[float]] = defaultdict(list)
        entity_meta: Dict[str, dict] = {}
        for pt in data_points:
            if pt.field_name == primary_field and not pt.is_null and pt.field_value is not None:
                entity_vals[pt.entity_name].append(pt.field_value)
                entity_meta[pt.entity_name] = {"country_code": pt.country_code}

        rankings = []
        for entity, vals in entity_vals.items():
            avg = float(np.mean(vals))
            rankings.append({
                "entity": entity,
                "avg_value": round(avg, 4),
                "country_code": entity_meta[entity].get("country_code"),
            })

        rankings.sort(key=lambda x: x["avg_value"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return rankings

    # ─────────────────────────────────────────────────────────
    # Geospatial Clustering
    # ─────────────────────────────────────────────────────────
    def geospatial_cluster(self, data_points, n_clusters: int = 5) -> list:
        """
        KMeans clustering on (lat, lon, normalized_value).
        Assigns cluster_id to each data point.
        """
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler

            valid = [
                pt for pt in data_points
                if not pt.is_null
                and pt.latitude is not None
                and pt.longitude is not None
                and pt.field_value is not None
            ]

            if len(valid) < n_clusters:
                return data_points

            X = np.array([
                [pt.latitude, pt.longitude, pt.field_value]
                for pt in valid
            ])
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            k = min(n_clusters, len(valid))
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X_scaled)

            valid_ids = {id(pt) for pt in valid}
            valid_map = {id(pt): pt for pt in valid}
            label_map = {id(pt): int(labels[i]) for i, pt in enumerate(valid)}

            for pt in data_points:
                if id(pt) in label_map:
                    pt.cluster_id = label_map[id(pt)]

        except Exception as e:
            logger.warning("clustering_failed", error=str(e))

        return data_points

    # ─────────────────────────────────────────────────────────
    # Run All
    # ─────────────────────────────────────────────────────────
    def run_all(self, data_points, primary_field: Optional[str] = None) -> dict:
        """Convenience method: run all analyses and return combined dict."""
        if not data_points:
            return {}

        if not primary_field:
            fields = [pt.field_name for pt in data_points if not pt.is_null]
            primary_field = fields[0] if fields else None

        data_points = self.detect_outliers(data_points)
        data_points = self.geospatial_cluster(data_points)

        return {
            "stats_summary": self.descriptive_stats(data_points),
            "entity_rankings": self.rank_entities(data_points, primary_field) if primary_field else [],
            "trends": self.compute_trends(data_points),
            "correlation_matrix": self.correlate_fields(data_points),
            "outlier_count": sum(1 for pt in data_points if pt.is_outlier),
            "data_points": data_points,
        }
