"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("queries_today", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queries_today_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── projects ──────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("query_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_query_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    # ── queries ───────────────────────────────────────────────
    op.create_table(
        "queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instruction_text", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="natural"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("parsed_spec", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("data_point_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_queries_project_id", "queries", ["project_id"])
    op.create_index("ix_queries_user_id", "queries", ["user_id"])
    op.create_index("ix_queries_status", "queries", ["status"])

    # ── results ───────────────────────────────────────────────
    op.create_table(
        "results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("query_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("queries.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("key_findings", postgresql.JSONB(), nullable=True),
        sa.Column("anomalies", postgresql.JSONB(), nullable=True),
        sa.Column("data_quality_note", sa.Text(), nullable=True),
        sa.Column("stats_summary", postgresql.JSONB(), nullable=True),
        sa.Column("correlation_matrix", postgresql.JSONB(), nullable=True),
        sa.Column("entity_rankings", postgresql.JSONB(), nullable=True),
        sa.Column("geojson", postgresql.JSONB(), nullable=True),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("null_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outlier_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_results_query_id", "results", ["query_id"])

    # ── data_points ───────────────────────────────────────────
    op.create_table(
        "data_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("result_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_name", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(10), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("field_value", sa.Float(), nullable=True),
        sa.Column("timestamp", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(10), nullable=False, server_default="web"),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("is_null", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_outlier", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("outlier_reason", sa.String(50), nullable=True),
        sa.Column("conflicts", postgresql.JSONB(), nullable=True),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_data_points_result_id", "data_points", ["result_id"])
    op.create_index("ix_data_points_country_code", "data_points", ["country_code"])
    op.create_index("ix_data_points_field_name", "data_points", ["field_name"])
    op.create_index("ix_data_points_timestamp", "data_points", ["timestamp"])

    # ── datasources ───────────────────────────────────────────
    op.create_table(
        "datasources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("columns", postgresql.JSONB(), nullable=True),
        sa.Column("preview", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_datasources_project_id", "datasources", ["project_id"])

    # ── api_keys ──────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("key_preview", sa.String(20), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_info", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "service_name", name="uq_api_keys_user_service"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # ── alerts ────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("metric_field", sa.String(100), nullable=False),
        sa.Column("entity_name", sa.String(255), nullable=False),
        sa.Column("condition_operator", sa.String(10), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("check_frequency", sa.String(20), nullable=False,
                  server_default="daily"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_email", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_slack", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("slack_webhook_url", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_value", sa.Float(), nullable=True),
        sa.Column("trigger_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_is_active", "alerts", ["is_active"])

    # ── alert_history ─────────────────────────────────────────
    op.create_table(
        "alert_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("value_at_trigger", sa.Float(), nullable=True),
        sa.Column("channels_notified", postgresql.JSONB(), nullable=True),
        sa.Column("notification_status", sa.String(20), nullable=False,
                  server_default="sent"),
    )
    op.create_index("ix_alert_history_alert_id", "alert_history", ["alert_id"])

    # ── exports ───────────────────────────────────────────────
    op.create_table(
        "exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("schedule_frequency", sa.String(20), nullable=True),
        sa.Column("schedule_email", sa.String(255), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_scheduled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("public_token", sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_exports_user_id", "exports", ["user_id"])
    op.create_index("ix_exports_query_id", "exports", ["query_id"])

    # ── audit_log ─────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ── refresh_tokens ────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("audit_log")
    op.drop_table("exports")
    op.drop_table("alert_history")
    op.drop_table("alerts")
    op.drop_table("api_keys")
    op.drop_table("datasources")
    op.drop_table("data_points")
    op.drop_table("results")
    op.drop_table("queries")
    op.drop_table("projects")
    op.drop_table("users")
