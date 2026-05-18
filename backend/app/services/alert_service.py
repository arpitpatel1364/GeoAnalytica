"""
Alert Service — evaluates alert conditions and sends notifications.
"""
import json
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class AlertService:

    def evaluate_condition(
        self,
        operator: str,
        current_value: float,
        threshold: float,
    ) -> bool:
        ops = {
            "gt": current_value > threshold,
            "lt": current_value < threshold,
            "gte": current_value >= threshold,
            "lte": current_value <= threshold,
            "eq": abs(current_value - threshold) < 0.0001,
            "neq": abs(current_value - threshold) >= 0.0001,
        }
        return ops.get(operator, False)

    async def send_email_notification(
        self,
        to_email: str,
        alert_name: str,
        entity: str,
        metric: str,
        current_value: float,
        threshold: float,
        operator: str,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        from_name: str,
        app_base_url: str = "",
    ) -> bool:
        try:
            import aiosmtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"GeoAnalytica Alert: {alert_name} Triggered"
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email

            html_body = f"""
            <html><body style="font-family: -apple-system, sans-serif; background: #0d1117; color: #e6edf3; padding: 24px;">
            <div style="max-width: 560px; margin: 0 auto; background: #161b22; border-radius: 12px; padding: 32px; border: 1px solid #30363d;">
              <div style="display: flex; align-items: center; margin-bottom: 24px;">
                <span style="font-size: 24px; font-weight: 700; color: #2f81f7;">⬡ GeoAnalytica</span>
              </div>
              <h2 style="color: #f85149; margin: 0 0 16px;">Alert Triggered: {alert_name}</h2>
              <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                <tr><td style="padding: 8px 0; color: #8b949e;">Entity</td><td style="color: #e6edf3; font-weight: 600;">{entity}</td></tr>
                <tr><td style="padding: 8px 0; color: #8b949e;">Metric</td><td style="color: #e6edf3;">{metric.replace("_", " ").title()}</td></tr>
                <tr><td style="padding: 8px 0; color: #8b949e;">Condition</td><td style="color: #e6edf3;">{operator} {threshold}</td></tr>
                <tr><td style="padding: 8px 0; color: #8b949e;">Current Value</td><td style="color: #f85149; font-size: 20px; font-weight: 700;">{current_value:.2f}</td></tr>
                <tr><td style="padding: 8px 0; color: #8b949e;">Triggered At</td><td style="color: #e6edf3;">{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</td></tr>
              </table>
              <a href="{app_base_url or settings.APP_BASE_URL}/alerts" style="display: inline-block; background: #2f81f7; color: white; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-weight: 500;">View Alert Dashboard →</a>
              <p style="margin-top: 24px; font-size: 12px; color: #484f58;">GeoAnalytica — Global data, decoded.</p>
            </div>
            </body></html>
            """

            msg.attach(MIMEText(html_body, "html"))

            await aiosmtplib.send(
                msg,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_password,
                use_tls=False,
                start_tls=True,
            )
            logger.info("alert_email_sent", to=to_email, alert=alert_name)
            return True
        except Exception as e:
            logger.error("alert_email_failed", error=str(e))
            return False

    async def send_slack_notification(
        self,
        webhook_url: str,
        alert_name: str,
        entity: str,
        metric: str,
        current_value: float,
        threshold: float,
        operator: str,
    ) -> bool:
        try:
            payload = {
                "text": f"🚨 *GeoAnalytica Alert: {alert_name}*",
                "attachments": [
                    {
                        "color": "#f85149",
                        "fields": [
                            {"title": "Entity", "value": entity, "short": True},
                            {"title": "Metric", "value": metric.replace("_", " ").title(), "short": True},
                            {"title": "Condition", "value": f"{operator} {threshold}", "short": True},
                            {"title": "Current Value", "value": f"*{current_value:.2f}*", "short": True},
                        ],
                        "footer": "GeoAnalytica — Global data, decoded.",
                        "ts": int(datetime.now(timezone.utc).timestamp()),
                    }
                ],
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                if resp.status_code == 200:
                    logger.info("alert_slack_sent", alert=alert_name)
                    return True
                else:
                    logger.error("alert_slack_failed", status=resp.status_code)
                    return False
        except Exception as e:
            logger.error("alert_slack_error", error=str(e))
            return False


alert_service = AlertService()
