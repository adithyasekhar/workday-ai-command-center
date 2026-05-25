import os
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class NotificationRouter:
    """
    Routes alerts to all configured channels simultaneously.
    Every channel fires at the same time when a failure occurs.
    Humans receive the alert and take action in Workday.
    AI never takes action itself.
    """

    def __init__(self):
        # Load all channel configs from env
        self.channels = {
            "slack":   self._config_slack(),
            "teams":   self._config_teams(),
            "email":   self._config_email(),
            "outlook": self._config_outlook(),
            "zoom":    self._config_zoom(),
        }
        active = [k for k, v in self.channels.items() if v.get("enabled")]
        print(f"[Notifier] Active channels: {active if active else 'none configured'}")

    # Channel configs
    def _config_slack(self) -> dict:
        webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        return {"enabled": bool(webhook) and not webhook.startswith("https://hooks.slack.com/YOUR"), "webhook": webhook}

    def _config_teams(self) -> dict:
        webhook = os.getenv("TEAMS_WEBHOOK_URL", "")
        return {"enabled": bool(webhook) and not webhook.startswith("https://your"), "webhook": webhook}

    def _config_email(self) -> dict:
        host = os.getenv("EMAIL_SMTP_HOST", "")
        return {
            "enabled": bool(host),
            "smtp_host": host,
            "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
            "username": os.getenv("EMAIL_USERNAME", ""),
            "password": os.getenv("EMAIL_PASSWORD", ""),
            "from": os.getenv("EMAIL_FROM", ""),
            "to": [r.strip() for r in os.getenv("EMAIL_TO", "").split(",") if r.strip()],
        }

    def _config_outlook(self) -> dict:
        host = os.getenv("OUTLOOK_SMTP_HOST", "smtp.office365.com")
        user = os.getenv("OUTLOOK_USERNAME", "")
        return {
            "enabled": bool(user),
            "smtp_host": host,
            "smtp_port": int(os.getenv("OUTLOOK_SMTP_PORT", "587")),
            "username": user,
            "password": os.getenv("OUTLOOK_PASSWORD", ""),
            "from": user,
            "to": [r.strip() for r in os.getenv("OUTLOOK_TO", "").split(",") if r.strip()],
        }

    def _config_zoom(self) -> dict:
        webhook = os.getenv("ZOOM_WEBHOOK_URL", "")
        return {"enabled": bool(webhook) and not webhook.startswith("https://your"), "webhook": webhook, "token": os.getenv("ZOOM_VERIFICATION_TOKEN", "")}

    # Main send method
    def send_alert(self, failure: dict, diagnosis: str, urgency: str = "HIGH") -> dict:
        print("\n[Notifier] Sending to all channels...")

        name = (failure.get("integration_name") or failure.get("name") or failure.get("app_name", "Unknown"))
        module = failure.get("module", "workday").upper()
        error = (failure.get("error_message") or failure.get("error", "No details"))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subject = f"[{urgency}] Workday {module} Failure: {name}"
        short = self._short_message(name, module, error, urgency, timestamp)
        full = self._full_message(name, module, error, diagnosis, urgency, timestamp)

        results = {}

        if self.channels["slack"]["enabled"]:
            results["slack"] = self._send_slack(name, module, error, diagnosis, urgency, timestamp)
        if self.channels["teams"]["enabled"]:
            results["teams"] = self._send_teams(name, module, error, diagnosis, urgency, timestamp)
        if self.channels["email"]["enabled"]:
            results["email"] = self._send_email(subject, full, self.channels["email"]) 
        if self.channels["outlook"]["enabled"]:
            results["outlook"] = self._send_email(subject, full, self.channels["outlook"], channel_name="Outlook")
        if self.channels["zoom"]["enabled"]:
            results["zoom"] = self._send_zoom(short)

        sent = [k for k, v in results.items() if v]
        failed = [k for k, v in results.items() if not v]

        print(f"[Notifier] Sent to: {sent}")
        if failed:
            print(f"[Notifier] Failed: {failed}")

        return {"sent": sent, "failed": failed, "results": results}

    def send_all_clear(self) -> dict:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results = {}
        if self.channels["slack"]["enabled"]:
            results["slack"] = self._send_slack_clear(timestamp)
        if self.channels["teams"]["enabled"]:
            results["teams"] = self._send_teams_clear(timestamp)
        if self.channels["email"]["enabled"]:
            results["email"] = self._send_email("Workday Systems — All Clear", f"All Workday systems healthy as of {timestamp}.\n\nNo action required.", self.channels["email"]) 
        print(f"[Notifier] All-clear sent to: {list(results.keys())}")
        return results

    # Slack
    def _send_slack(self, name, module, error, diagnosis, urgency, timestamp) -> bool:
        try:
            color = {"HIGH": "#FF0000", "MEDIUM": "#FFA500", "LOW": "#36A64F"}.get(urgency, "#FF0000")
            emoji = {"HIGH": ":red_circle:", "MEDIUM": ":large_yellow_circle:", "LOW": ":large_green_circle:"}.get(urgency, ":red_circle:")
            payload = {
                "text": f"{emoji} *Workday {module} Alert — {name}*",
                "attachments": [{
                    "color": color,
                    "blocks": [
                        {"type": "section", "fields": [
                            {"type": "mrkdwn", "text": f"*System:*\n{module} — {name}"},
                            {"type": "mrkdwn", "text": f"*Urgency:*\n{urgency}"},
                            {"type": "mrkdwn", "text": f"*Detected:*\n{timestamp}"},
                            {"type": "mrkdwn", "text": f"*Error:*\n{error[:200]}"},
                        ]},
                        {"type": "divider"},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"*AI Diagnosis:*\n{diagnosis[:500]}"}},
                        {"type": "context", "elements": [{"type": "mrkdwn", "text": (":lock: *AI is read-only.* Human action required in Workday.")}]}
                    ]
                }]}
            r = requests.post(self.channels["slack"]["webhook"], json=payload, timeout=10)
            success = r.status_code == 200
            print(f"[Slack] {'Sent' if success else 'Failed'}: {r.status_code}")
            return success
        except Exception as e:
            print(f"[Slack] Error: {e}")
            return False

    def _send_slack_clear(self, timestamp) -> bool:
        try:
            payload = {"text": (f":large_green_circle: *Workday — All Systems Healthy*\nChecked: {timestamp} — No action required.")}
            r = requests.post(self.channels["slack"]["webhook"], json=payload, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print(f"[Slack] Clear error: {e}")
            return False

    # Teams
    def _send_teams(self, name, module, error, diagnosis, urgency, timestamp) -> bool:
        try:
            color = {"HIGH": "FF0000", "MEDIUM": "FFA500", "LOW": "00CC00"}.get(urgency, "FF0000")
            emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(urgency, "🔴")
            card = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color,
                "summary": f"Workday {module} Failure: {name}",
                "sections": [
                    {"activityTitle": f"{emoji} Workday {module} Failure", "activitySubtitle": f"Detected at {timestamp}", "facts": [{"name": "System", "value": f"{module} — {name}"}, {"name": "Urgency", "value": urgency}, {"name": "Error", "value": error[:300]}], "markdown": True},
                    {"activityTitle": "🤖 AI Diagnosis", "text": diagnosis[:600], "markdown": True},
                    {"activityTitle": "⚠️ Action Required", "text": ("AI is read-only. Please log into Workday and take action."), "markdown": True}
                ]
            }
            r = requests.post(self.channels["teams"]["webhook"], json=card, headers={"Content-Type": "application/json"}, timeout=10)
            success = r.status_code == 200
            print(f"[Teams] {'Sent' if success else 'Failed'}: {r.status_code}")
            return success
        except Exception as e:
            print(f"[Teams] Error: {e}")
            return False

    def _send_teams_clear(self, timestamp) -> bool:
        try:
            card = {"@type": "MessageCard", "@context": "http://schema.org/extensions", "themeColor": "00CC00", "summary": "Workday — All Systems Healthy", "sections": [{"activityTitle": "✅ All Workday Systems Healthy", "activitySubtitle": f"Last checked: {timestamp}", "text": "No failures detected. No action required.", "markdown": True}]}
            r = requests.post(self.channels["teams"]["webhook"], json=card, headers={"Content-Type": "application/json"}, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print(f"[Teams] Clear error: {e}")
            return False

    # Email / Outlook
    def _send_email(self, subject: str, body: str, config: dict, channel_name: str = "Email") -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = config["from"]
            msg["To"] = ", ".join([r for r in config.get("to", []) if r])
            msg.attach(MIMEText(body, "plain"))
            html_body = self._build_html_email(subject, body)
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
                server.starttls()
                server.login(config.get("username", ""), config.get("password", ""))
                server.sendmail(config["from"], [r for r in config.get("to", []) if r], msg.as_string())
            print(f"[{channel_name}] Email sent successfully")
            return True
        except Exception as e:
            print(f"[{channel_name}] Email error: {e}")
            return False

    def _build_html_email(self, subject: str, body: str) -> str:
        lines = body.replace("\n", "<br>")
        return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:600px; margin:0 auto;padding:20px;color:#333;">
  <div style="background:#f8f8f8;border-left:4px solid #cc0000; padding:16px;border-radius:4px;margin-bottom:20px;">
    <h2 style="margin:0;color:#cc0000;font-size:18px;">{subject}</h2>
  </div>
  <div style="line-height:1.8;font-size:14px;">{lines}</div>
  <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
  <p style="font-size:12px;color:#999;">This alert was generated by Workday AI Command Center.<br>AI is read-only. All actions must be taken in Workday by a human.</p>
</body>
</html>
"""

    # Zoom
    def _send_zoom(self, message: str) -> bool:
        try:
            payload = {"content": {"head": {"text": "Workday Alert"}, "body": [{"type": "message", "text": message}]}}
            headers = {"Content-Type": "application/json", "Authorization": self.channels["zoom"].get("token", "")}
            r = requests.post(self.channels["zoom"]["webhook"], json=payload, headers=headers, timeout=10)
            success = r.status_code in [200, 201]
            print(f"[Zoom] {'Sent' if success else 'Failed'}: {r.status_code}")
            return success
        except Exception as e:
            print(f"[Zoom] Error: {e}")
            return False

    # Message builders
    def _short_message(self, name, module, error, urgency, timestamp) -> str:
        return (f"[{urgency}] Workday {module} Alert\nSystem: {name}\nTime: {timestamp}\nError: {error[:150]}\nAction: Human required in Workday")

    def _full_message(self, name, module, error, diagnosis, urgency, timestamp) -> str:
        return f"""
WORKDAY {module} ALERT — {urgency} PRIORITY
{'='*50}
System    : {name}
Detected  : {timestamp}
Urgency   : {urgency}
{'='*50}

ERROR DETAILS:
{error}

{'='*50}
AI DIAGNOSIS:
{diagnosis}

{'='*50}
ACTION REQUIRED:
AI has read-only access to Workday.
A human must log in and resolve this issue.
AI cannot make any changes.

Generated by: Workday AI Command Center
"""
