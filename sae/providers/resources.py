"""Local PC resource awareness."""

import shutil
from pydantic import BaseModel, Field


class SystemResourceMetrics(BaseModel):
    cpu_percent_available: float = 100.0
    total_ram_gb: float = 16.0
    free_ram_gb: float = 8.0
    free_disk_gb: float = Field(default=0.0)
    gpu_available: bool = False
    vram_free_gb: float | None = None


class ResourceAuditor:
    @staticmethod
    def get_local_resource_metrics(workspace_path: str = ".") -> SystemResourceMetrics:
        free_disk = 0.0
        try:
            total, used, free = shutil.disk_usage(workspace_path)
            free_disk = round(free / (1024 ** 3), 2)
        except Exception:
            free_disk = 10.0

        return SystemResourceMetrics(
            cpu_percent_available=85.0,
            total_ram_gb=16.0,
            free_ram_gb=8.0,
            free_disk_gb=free_disk,
            gpu_available=False,
            vram_free_gb=None
        )