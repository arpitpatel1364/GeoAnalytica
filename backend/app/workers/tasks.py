"""
Celery Tasks — full async query pipeline, alert checking, scheduled exports.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import structlog
from celery import Task

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


def run_async(coro):
    """Run an async coroutine from a sync Celery task.

    Always creates a fresh event loop per task invocation. Celery workers
    use threads/processes without a persistent event loop, so we must not
    reuse a potentially closed or foreign loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            # Cancel any remaining tasks to avoid resource leaks
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
            asyncio.set_event_loop(None)


async def _broadcast_progress(query_id: str, **kwargs):
    """Send WebSocket progress update."""
    try:
        from app.routers.websocket import manager
        await manager.send(query_id, {"type": "progress", **kwargs})
    except Exception as e:
        logger.warning("ws_broadcast_failed", error=str(e))


async def _run_query_pipeline(query_id: str):
    """Full async query pipeline."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.query import Query as QueryModel
    from app.models.result import Result, DataPoint
    from app.models.api_key import ApiKey
    from app.routers.websocket import manager
    from app.services.query_parser import parse_instruction
    from app.services.source_router import SourceRouter
    from app.services.web_intelligence_engine import WebIntelligenceEngine
    from app.services.direct_api_fetcher import DirectAPIFetcher
    from app.services.data_normalizer import DataNormalizer, NormalizedDataPoint
    from app.services.merge_engine import MergeEngine
    from app.services.analysis_engine import AnalysisEngine
    from app.services.ai_narrative import generate_narrative
    from app.services.encryption_service import decrypt_key
    from app.utils.geo_utils import ALL_COUNTRIES, name_to_iso2

    start_time = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Load query
        result = await db.execute(
            select(QueryModel).where(QueryModel.id == uuid.UUID(query_id))
        )
        query = result.scalar_one_or_none()
        if not query:
            logger.error("query_not_found", query_id=query_id)
            return

        query.status = "running"
        await db.commit()

        try:
            # ── STAGE 1: Parse ────────────────────────────────────
            await manager.send(query_id, {
                "type": "progress", "stage": "parsing",
                "status": "running", "percent": 5,
                "message": "Parsing your query with AI...",
            })

            spec = await parse_instruction(query.instruction_text)
            query.parsed_spec = spec.to_dict()
            await db.commit()

            if spec.error:
                raise ValueError(f"Query parsing failed: {spec.error_message}")

            await manager.send(query_id, {
                "type": "progress", "stage": "parsing",
                "status": "done", "percent": 15,
                "message": f"Parsed: {len(spec.fields)} fields, scope={spec.entity_scope}",
            })

            # ── STAGE 2: Route ────────────────────────────────────
            await manager.send(query_id, {
                "type": "progress", "stage": "routing",
                "status": "running", "percent": 18,
                "message": "Identifying data sources...",
            })

            # Load user's API keys
            key_result = await db.execute(
                select(ApiKey).where(
                    ApiKey.user_id == query.user_id,
                    ApiKey.is_valid == True,  # noqa: E712
                )
            )
            api_keys_db = key_result.scalars().all()
            user_api_keys: Dict[str, str] = {}
            for k in api_keys_db:
                try:
                    user_api_keys[k.service_name] = decrypt_key(k.encrypted_key)
                except Exception:
                    pass

            router = SourceRouter()
            routed_fields = router.route_fields(spec.fields, user_api_keys)
            entities = router.get_entity_list(spec.entity_scope, spec.entities)

            if not entities:
                raise ValueError("No entities resolved from query scope")

            entity_meta = {
                e["name"]: {"iso2": e.get("iso2"), "lat": e.get("lat"), "lon": e.get("lon")}
                for e in entities
            }

            await manager.send(query_id, {
                "type": "progress", "stage": "routing",
                "status": "done", "percent": 20,
                "message": f"Routing {len(routed_fields)} fields for {len(entities)} entities",
            })

            # ── STAGE 3: Fetch ────────────────────────────────────
            await manager.send(query_id, {
                "type": "progress", "stage": "fetching",
                "status": "running", "percent": 22,
                "message": f"Fetching data for {len(entities)} countries...",
            })

            wie = WebIntelligenceEngine()
            direct_fetcher = DirectAPIFetcher()
            normalizer = DataNormalizer()

            all_normalized: List[NormalizedDataPoint] = []
            done_count = 0
            total_fetch = len(entities) * len(routed_fields)

            async def progress_cb(entity_name, field, done, total):
                nonlocal done_count
                done_count = done
                percent = 22 + int((done_count / max(total_fetch, 1)) * 43)  # 22-65%

                # Broadcast country data point for live map coloring
                entity_pts = [
                    p for p in all_normalized
                    if p.entity_name == entity_name and p.field_name == field and not p.is_null
                ]
                if entity_pts:
                    latest = entity_pts[-1]
                    iso2 = entity_meta.get(entity_name, {}).get("iso2", "")
                    if iso2 and latest.field_value is not None:
                        await manager.send(query_id, {
                            "type": "country_data",
                            "country_code": iso2,
                            "value": latest.field_value,
                            "field": field,
                        })

                await manager.send(query_id, {
                    "type": "progress", "stage": "fetching",
                    "status": "running", "percent": percent,
                    "message": f"Fetched {entity_name} — {field}",
                    "country_count": done_count,
                })

            # Separate WIE and direct API fields
            wie_fields = [rf.field_name for rf in routed_fields if rf.route_type == "web_scrape"]
            direct_fields = {rf.field_name: rf for rf in routed_fields if rf.route_type == "direct_api"}

            # Fetch WIE fields
            if wie_fields:
                wie_results = await wie.fetch(
                    entities=entities,
                    fields=wie_fields,
                    time_start=spec.time_start,
                    time_end=spec.time_end,
                    granularity=spec.granularity,
                    progress_callback=progress_cb,
                )
                all_normalized.extend(normalizer.normalize_wie_results(wie_results, entity_meta))

            # Fetch direct API fields
            for field_name, routed in direct_fields.items():
                years = list(range(int(spec.time_start), int(spec.time_end) + 1))
                for entity in entities:
                    direct_results = await direct_fetcher.fetch(
                        service_name=routed.source_name,
                        api_key=routed.api_key or "",
                        entity=entity["name"],
                        field_name=field_name,
                        years=years,
                    )
                    all_normalized.extend(
                        normalizer.normalize_direct_results(direct_results, entity_meta)
                    )
                    # Increment here (caller owns count); progress_cb reads it
                    done_count += 1
                    await progress_cb(entity["name"], field_name, done_count, total_fetch)

            await manager.send(query_id, {
                "type": "progress", "stage": "fetching",
                "status": "done", "percent": 65,
                "message": f"Fetched {len(all_normalized)} data points",
            })

            # ── STAGE 4: Normalize + Merge ────────────────────────
            await manager.send(query_id, {
                "type": "progress", "stage": "normalizing",
                "status": "running", "percent": 67,
                "message": "Normalizing and merging data...",
            })

            merge_engine = MergeEngine()
            filters = [f.__dict__ if hasattr(f, '__dict__') else f for f in spec.filters]
            merged = merge_engine.merge(all_normalized, filters)

            await manager.send(query_id, {
                "type": "progress", "stage": "normalizing",
                "status": "done", "percent": 72,
                "message": f"{len(merged)} points after filtering",
            })

            # ── STAGE 5: Analyze ──────────────────────────────────
            await manager.send(query_id, {
                "type": "progress", "stage": "analyzing",
                "status": "running", "percent": 75,
                "message": "Running statistical analysis...",
            })

            engine = AnalysisEngine()
            primary_field = spec.fields[0] if spec.fields else None
            analysis = engine.run_all(merged, primary_field)
            analyzed_points = analysis["data_points"]

            await manager.send(query_id, {
                "type": "progress", "stage": "analyzing",
                "status": "done", "percent": 88,
                "message": f"Analysis complete — {analysis.get('outlier_count', 0)} outliers detected",
            })

            # ── STAGE 6: AI Narrative ─────────────────────────────
            await manager.send(query_id, {
                "type": "progress", "stage": "narrative",
                "status": "running", "percent": 90,
                "message": "Generating AI narrative summary...",
            })

            narrative = await generate_narrative(analysis, query.instruction_text)

            # ── Build GeoJSON ─────────────────────────────────────
            features = []
            entity_data: Dict[str, dict] = {}
            for pt in analyzed_points:
                if not pt.is_null and pt.latitude and pt.longitude:
                    if pt.entity_name not in entity_data:
                        entity_data[pt.entity_name] = {
                            "country_code": pt.country_code,
                            "lat": pt.latitude,
                            "lon": pt.longitude,
                            "fields": {},
                        }
                    entity_data[pt.entity_name]["fields"].setdefault(pt.field_name, []).append(pt.field_value)

            for entity_name, data in entity_data.items():
                avg_fields = {
                    f: sum(vals) / len(vals)
                    for f, vals in data["fields"].items()
                    if vals
                }
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [data["lon"], data["lat"]]},
                    "properties": {
                        "entity_name": entity_name,
                        "country_code": data["country_code"],
                        **avg_fields,
                    },
                })

            geojson = {"type": "FeatureCollection", "features": features}

            # ── Persist Result ────────────────────────────────────
            total_points = len(analyzed_points)
            null_count = sum(1 for p in analyzed_points if p.is_null)
            outlier_count = sum(1 for p in analyzed_points if p.is_outlier)

            db_result = Result(
                query_id=query.id,
                summary_text=narrative.get("summary"),
                key_findings=narrative.get("key_findings"),
                anomalies=narrative.get("anomalies"),
                data_quality_note=narrative.get("data_quality_note"),
                stats_summary=analysis.get("stats_summary"),
                correlation_matrix=analysis.get("correlation_matrix"),
                entity_rankings=analysis.get("entity_rankings"),
                geojson=geojson,
                total_points=total_points,
                null_count=null_count,
                outlier_count=outlier_count,
            )
            db.add(db_result)
            await db.flush()  # Get db_result.id

            # Persist DataPoints in batches
            BATCH_SIZE = 500
            for i in range(0, len(analyzed_points), BATCH_SIZE):
                batch = analyzed_points[i:i + BATCH_SIZE]
                for pt in batch:
                    dp = DataPoint(
                        result_id=db_result.id,
                        entity_name=pt.entity_name,
                        country_code=pt.country_code,
                        latitude=pt.latitude,
                        longitude=pt.longitude,
                        field_name=pt.field_name,
                        field_value=pt.field_value,
                        timestamp=pt.timestamp,
                        source_type=pt.source_type,
                        source_name=pt.source_name,
                        source_url=pt.source_url[:500] if pt.source_url else None,
                        confidence_score=pt.confidence_score,
                        is_null=pt.is_null,
                        is_outlier=pt.is_outlier,
                        outlier_reason=pt.outlier_reason,
                        conflicts=pt.conflicts,
                        cluster_id=pt.cluster_id,
                    )
                    db.add(dp)
                await db.flush()

            # Update query
            end_time = datetime.now(timezone.utc)
            query.status = "completed"
            query.completed_at = end_time
            query.duration_seconds = (end_time - start_time).total_seconds()
            query.data_point_count = total_points

            # Update project last_query_at (query_count already incremented on creation)
            from app.models.project import Project
            proj_result = await db.execute(
                select(Project).where(Project.id == query.project_id)
            )
            project = proj_result.scalar_one_or_none()
            if project:
                project.last_query_at = end_time

            await db.commit()

            # Broadcast completion
            await manager.send(query_id, {
                "type": "complete",
                "result_id": str(db_result.id),
                "percent": 100,
                "message": "Analysis complete!",
            })

            logger.info(
                "query_complete",
                query_id=query_id,
                points=total_points,
                duration=query.duration_seconds,
            )

        except Exception as e:
            logger.error("query_pipeline_error", query_id=query_id, error=str(e))
            query.status = "failed"
            query.error_message = str(e)
            await db.commit()
            await manager.send(query_id, {
                "type": "error",
                "message": f"Analysis failed: {str(e)}",
            })
            raise


@celery_app.task(bind=True, max_retries=3, name="app.workers.tasks.run_query_task")
def run_query_task(self, query_id: str):
    """Main query execution task."""
    try:
        run_async(_run_query_pipeline(query_id))
    except Exception as exc:
        logger.error("query_task_failed", query_id=query_id, error=str(exc))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 10)


@celery_app.task(name="app.workers.tasks.check_alerts_task")
def check_alerts_task():
    """Check all active alerts and send notifications if triggered."""
    async def _check():
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.alert import Alert, AlertHistory
        from app.models.result import DataPoint, Result
        from app.models.query import Query as QueryModel
        from app.models.user import User
        from app.services.alert_service import alert_service
        from app.config import settings

        async with AsyncSessionLocal() as db:
            alerts_result = await db.execute(
                select(Alert).where(Alert.is_active == True)  # noqa: E712
            )
            alerts = alerts_result.scalars().all()

            for alert in alerts:
                try:
                    # Get latest result for this query
                    result_q = await db.execute(
                        select(Result)
                        .where(Result.query_id == alert.query_id)
                        .order_by(Result.created_at.desc())
                        .limit(1)
                    )
                    result = result_q.scalar_one_or_none()
                    if not result:
                        continue

                    # Find matching data point (latest timestamp)
                    dp_q = await db.execute(
                        select(DataPoint)
                        .where(
                            DataPoint.result_id == result.id,
                            DataPoint.field_name == alert.metric_field,
                            DataPoint.entity_name == alert.entity_name,
                            DataPoint.is_null == False,  # noqa: E712
                        )
                        .order_by(DataPoint.timestamp.desc())
                        .limit(1)
                    )
                    dp = dp_q.scalar_one_or_none()
                    if not dp or dp.field_value is None:
                        continue

                    alert.last_checked_at = datetime.now(timezone.utc)
                    alert.last_value = dp.field_value

                    if alert_service.evaluate_condition(
                        alert.condition_operator, dp.field_value, alert.threshold_value
                    ):
                        alert.last_triggered_at = datetime.now(timezone.utc)
                        alert.trigger_count += 1

                        channels = []
                        if alert.notify_email:
                            # Load the alert owner's email properly
                            user_q = await db.execute(
                                select(User).where(User.id == alert.user_id)
                            )
                            alert_user = user_q.scalar_one_or_none()
                            user_email = alert_user.email if alert_user else ""

                            if user_email:
                                sent = await alert_service.send_email_notification(
                                    to_email=user_email,
                                    alert_name=alert.name,
                                    entity=alert.entity_name,
                                    metric=alert.metric_field,
                                    current_value=dp.field_value,
                                    threshold=alert.threshold_value,
                                    operator=alert.condition_operator,
                                    smtp_host=settings.SMTP_HOST,
                                    smtp_port=settings.SMTP_PORT,
                                    smtp_user=settings.SMTP_USER,
                                    smtp_password=settings.SMTP_PASSWORD,
                                    from_email=settings.SMTP_FROM_EMAIL,
                                    from_name=settings.SMTP_FROM_NAME,
                                )
                                if sent:
                                    channels.append("email")

                        if alert.notify_slack and alert.slack_webhook_url:
                            sent = await alert_service.send_slack_notification(
                                webhook_url=alert.slack_webhook_url,
                                alert_name=alert.name,
                                entity=alert.entity_name,
                                metric=alert.metric_field,
                                current_value=dp.field_value,
                                threshold=alert.threshold_value,
                                operator=alert.condition_operator,
                            )
                            if sent:
                                channels.append("slack")

                        history = AlertHistory(
                            alert_id=alert.id,
                            value_at_trigger=dp.field_value,
                            channels_notified=channels,
                            notification_status="sent" if channels else "failed",
                        )
                        db.add(history)

                    await db.commit()

                except Exception as e:
                    logger.error("alert_check_error", alert_id=str(alert.id), error=str(e))
                    await db.rollback()
                    continue

    run_async(_check())


@celery_app.task(name="app.workers.tasks.run_scheduled_exports_task")
def run_scheduled_exports_task():
    """Run all due scheduled exports and email results."""
    async def _run():
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.export import Export
        from app.models.result import Result
        from app.models.query import Query as QueryModel
        from app.services.export_service import ExportService
        from sqlalchemy.orm import selectinload
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email import encoders
        from app.config import settings

        now = datetime.now(timezone.utc)
        service = ExportService()

        INTERVALS = {
            "daily": 86400,
            "weekly": 604800,
            "monthly": 2592000,
        }

        async with AsyncSessionLocal() as db:
            exports_q = await db.execute(
                select(Export).where(
                    Export.is_scheduled == True,  # noqa: E712
                    Export.next_run_at <= now,
                    Export.schedule_email != None,  # noqa: E711
                )
            )
            due_exports = exports_q.scalars().all()

            for exp in due_exports:
                try:
                    result_q = await db.execute(
                        select(Result)
                        .where(Result.query_id == exp.query_id)
                        .options(selectinload(Result.data_points))
                    )
                    result = result_q.scalar_one_or_none()
                    if not result:
                        continue

                    query_q = await db.execute(
                        select(QueryModel).where(QueryModel.id == exp.query_id)
                    )
                    query = query_q.scalar_one_or_none()

                    fmt = exp.format
                    if fmt == "csv":
                        file_data = service.generate_csv(result)
                        mime_type = "text/csv"
                        ext = "csv"
                    elif fmt == "xlsx":
                        file_data = service.generate_xlsx(result, query)
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        ext = "xlsx"
                    elif fmt == "json":
                        file_data = service.generate_json(result)
                        mime_type = "application/json"
                        ext = "json"
                    else:
                        file_data = service.generate_csv(result)
                        mime_type = "text/csv"
                        ext = "csv"

                    # Send email with attachment
                    if settings.SMTP_USER and exp.schedule_email:
                        msg = MIMEMultipart()
                        msg["Subject"] = f"GeoAnalytica Scheduled Export — {now.strftime('%Y-%m-%d')}"
                        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
                        msg["To"] = exp.schedule_email
                        msg.attach(MIMEText(
                            f"Your scheduled GeoAnalytica export is attached.\n\nGenerated: {now.strftime('%Y-%m-%d %H:%M UTC')}",
                            "plain"
                        ))
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(file_data)
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f'attachment; filename="geoanalytica_export.{ext}"')
                        msg.attach(part)

                        await aiosmtplib.send(
                            msg,
                            hostname=settings.SMTP_HOST,
                            port=settings.SMTP_PORT,
                            username=settings.SMTP_USER,
                            password=settings.SMTP_PASSWORD,
                            start_tls=settings.SMTP_TLS,
                        )

                    # Update next_run_at
                    interval_secs = INTERVALS.get(exp.schedule_frequency or "weekly", 604800)
                    from datetime import timedelta
                    exp.next_run_at = now + timedelta(seconds=interval_secs)
                    exp.last_run_at = now
                    await db.commit()

                except Exception as e:
                    logger.error("scheduled_export_error", export_id=str(exp.id), error=str(e))
                    continue

    run_async(_run())
