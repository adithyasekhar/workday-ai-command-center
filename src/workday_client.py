# READ ONLY Workday API client
# This file can ONLY make GET requests
# Any attempt to write to Workday raises a hard error

import requests
import os
from typing import Any

# ─── Read Only Enforcement ────────────────────────────────
ALLOWED_HTTP_METHODS = ["GET"]


class WorkdayClient:
    """
    Read-only Workday API client.
    Permanently restricted to GET requests only.
    Cannot create, update, delete or approve anything.
    Cannot initiate any business process.
    """

    def __init__(self):
        self.token_url = os.getenv("WORKDAY_TOKEN_URL")
        self.client_id = os.getenv("WORKDAY_CLIENT_ID")
        self.client_secret = os.getenv("WORKDAY_CLIENT_SECRET")
        self.refresh_token = os.getenv("WORKDAY_REFRESH_TOKEN")
        self.report_url = os.getenv("WORKDAY_REPORT_URL")
        self.base_url = os.getenv("WORKDAY_BASE_URL")
        self._access_token = None

    def _safe_request(self, method: str, url: str, **kwargs):
        """
        Governance enforcer.
        Every single Workday API call goes through here.
        If the method is not GET — hard stop, error raised.
        This is not a warning. It is a hard block.
        """
        method = method.upper()

        if method not in ALLOWED_HTTP_METHODS:
            error_msg = (
                f"\n{'='*55}\n"
                f"GOVERNANCE VIOLATION BLOCKED\n"
                f"{'='*55}\n"
                f"Attempted method : {method}\n"
                f"Target URL       : {url}\n"
                f"Allowed methods  : {ALLOWED_HTTP_METHODS}\n"
                f"Reason           : This client is READ-ONLY by design.\n"
                f"                   AI cannot write to Workday.\n"
                f"                   No exceptions.\n"
                f"{'='*55}\n"
            )
            raise PermissionError(error_msg)

        return requests.request(method, url, **kwargs)

    def get_access_token(self):
        """
        Get OAuth2 token from Workday.
        Note: The token endpoint requires POST — this is
        authentication only, not a Workday data write.
        Token is read-only scoped by the API client config.
        """
        print("[Workday] Getting access token...")
        # If token endpoint or credentials are missing, avoid making a POST
        if not self.token_url or not self.refresh_token or not self.client_id or not self.client_secret:
            print("[Workday] Missing OAuth configuration — skipping token request")
            return None

        try:
            # Token endpoint uses POST for OAuth2 standard
            # This is authentication — not a data write operation
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=30,
            )
            if response.status_code == 200:
                self._access_token = response.json().get("access_token")
                print("[Workday] Token obtained — read-only scope.")
                return self._access_token
            else:
                print(f"[Workday] Token error: {response.status_code}")
                return None
        except Exception as e:
            print(f"[Workday] Connection error: {e}")
            return None

    def _get_headers(self):
        token = self.get_access_token()
        if not token:
            return None
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def _mask_sensitive_fields(self, record: dict) -> dict:
        """
        Remove or mask sensitive fields before
        passing any data to AI models.
        """
        sensitive = [
            "social_security_number",
            "ssn",
            "national_id_number",
            "national_id",
            "bank_account_number",
            "bank_account",
            "date_of_birth",
            "dob",
            "personal_email",
            "personal_phone",
            "medical_information",
            "immigration_status",
            "tax_identification_number",
            "passport_number",
            "salary",
        ]
        masked = record.copy()
        for field in sensitive:
            if field in masked:
                masked[field] = "***MASKED_BY_GOVERNANCE***"
        return masked

    # ─── Read Operations ─────────────────────────────────

    def get_integration_runs(self):
        """
        READ ONLY — Fetch integration run history.
        Returns failed, warning, and all statuses.
        """
        headers = self._get_headers()
        if not headers:
            print("[Workday] No token — using demo data")
            return self._demo_integrations()

        try:
            if not self.report_url:
                print("[Workday] No report URL configured — returning demo integration data")
                return self._demo_integrations()
            # GET only — safe_request enforces this
            response = self._safe_request("GET", self.report_url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"[Workday] Report error: {response.status_code}")
                return self._demo_integrations()

            runs = []
            for entry in response.json().get("Report_Entry", []):
                run = {
                    "integration_name": entry.get("Integration_System_Name", "Unknown"),
                    "status": entry.get("Integration_Status", "Unknown"),
                    "initiated_on": entry.get("Initiated_On", ""),
                    "completed_on": entry.get("Completed_On", ""),
                    "error_message": entry.get("Error_Message", ""),
                    "module": "integration",
                }
                # Mask before returning
                runs.append(self._mask_sensitive_fields(run))

            print(f"[Workday] READ: {len(runs)} integration run(s) retrieved")
            return runs

        except PermissionError as e:
            print(e)
            return []
        except Exception as e:
            print(f"[Workday] Error: {e}")
            return self._demo_integrations()

    def get_prism_pipelines(self):
        """READ ONLY — Fetch Prism dataset status."""
        headers = self._get_headers()
        if not headers:
            return self._demo_prism()
        try:
            if not self.base_url:
                print("[Workday] No base URL configured — returning demo Prism data")
                return self._demo_prism()
            url = f"{self.base_url}/prism/v1/datasets"
            response = self._safe_request(
                "GET", url, headers=headers, timeout=30
            )
            if response.status_code == 200:
                datasets = response.json().get("data", [])
                masked = [self._mask_sensitive_fields(d)
                          for d in datasets]
                print(f"[Workday] READ+MASKED: {len(masked)} Prism dataset(s)")
                return masked
            return self._demo_prism()
        except PermissionError as e:
            print(e)
            return []
        except Exception:
            return self._demo_prism()

    def get_extend_apps(self):
        """READ ONLY — Fetch Extend app status."""
        headers = self._get_headers()
        if not headers:
            return self._demo_extend()
        try:
            if not self.base_url:
                print("[Workday] No base URL configured — returning demo Extend data")
                return self._demo_extend()
            url = f"{self.base_url}/apps/v1/applications"
            response = self._safe_request(
                "GET", url, headers=headers, timeout=30
            )
            if response.status_code == 200:
                apps = response.json().get("data", [])
                masked = [self._mask_sensitive_fields(a)
                          for a in apps]
                print(f"[Workday] READ+MASKED: {len(masked)} Extend app(s)")
                return masked
            return self._demo_extend()
        except PermissionError as e:
            print(e)
            return []
        except Exception:
            return self._demo_extend()

    # ─── Demo Data ───────────────────────────────────────
    # Used when no credentials configured
    # Safe to use for testing and demos

    def _demo_integrations(self):
        print("[Workday] Using demo integration data")
        return [
            {
                "integration_name": "Benefits_Feed_ADP",
                "status": "Failed",
                "initiated_on": "2026-05-24T02:13:00",
                "completed_on": "2026-05-24T02:14:33",
                "error_message": "SFTP connection refused at host 10.0.0.45:22",
                "module": "integration",
            },
            {
                "integration_name": "Payroll_Export_ADP",
                "status": "Completed",
                "initiated_on": "2026-05-24T01:00:00",
                "completed_on": "2026-05-24T01:04:22",
                "error_message": "",
                "module": "integration",
            },
            {
                "integration_name": "Org_Chart_Sync",
                "status": "Warning",
                "initiated_on": "2026-05-24T03:00:00",
                "completed_on": "2026-05-24T03:02:15",
                "error_message": "3 records skipped — missing manager field",
                "module": "integration",
            },
        ]

    def _demo_prism(self):
        print("[Workday] Using demo Prism data")
        return [
            {
                "name": "Headcount_Analytics",
                "status": "Active",
                "last_refresh": "2026-05-24T00:00:00",
                "module": "prism",
            },
            {
                "name": "Compensation_Benchmark",
                "status": "Failed",
                "error": "Schema mismatch — column Grade_Level not found",
                "module": "prism",
            },
        ]

    def _demo_extend(self):
        print("[Workday] Using demo Extend data")
        return [
            {
                "app_name": "Equipment_Request_App",
                "status": "Active",
                "version": "2.1",
                "module": "extend",
            },
            {
                "app_name": "Travel_Request_App",
                "status": "Error",
                "error": "Orchestration timeout on approval step",
                "module": "extend",
            },
        ]
