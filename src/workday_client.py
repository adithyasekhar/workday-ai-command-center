from __future__ import annotations
from typing import Any


class WorkdayClient:
    def ping(self) -> str:
        return 'Workday client connected'

    def get_integration_runs(self) -> list[dict[str, Any]]:
        return []

    def get_prism_pipelines(self) -> list[dict[str, Any]]:
        return []

    def get_extend_apps(self) -> list[dict[str, Any]]:
        return []
