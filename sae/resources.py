"""Dynamic system resource detection, threshold monitoring, and VRAM/RAM reservation leasing."""

import asyncio
import os
import shutil
from typing import Any
import psutil
from pydantic import BaseModel, Field


class SystemMetrics(BaseModel):
    cpu_percent: float
    total_ram_gb: float
    free_ram_gb: float
    total_vram_gb: float
    free_vram_gb: float
    free_disk_gb: float


class ResourceLease(BaseModel):
    lease_id: str
    task_id: str
    reserved_vram_gb: float
    reserved_ram_gb: float
    active: bool = True


class ResourceManager:
    def __init__(
        self,
        min_free_ram_gb: float = 0.5,
        min_free_vram_gb: float = 0.5,
        min_free_disk_gb: float = 1.0
    ):
        self.min_free_ram_gb = min_free_ram_gb
        self.min_free_vram_gb = min_free_vram_gb
        self.min_free_disk_gb = min_free_disk_gb
        self._active_leases: dict[str, ResourceLease] = {}
        self._lock = asyncio.Lock()

    def get_metrics(self) -> SystemMetrics:
        vm = psutil.virtual_memory()
        total_ram = round(vm.total / (1024 ** 3), 2)
        free_ram = round(vm.available / (1024 ** 3), 2)

        total_vram = 8.0
        free_vram = 8.0
        try:
            import torch
            if torch.cuda.is_available():
                total_vram = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
                allocated = torch.cuda.memory_allocated(0)
                free_vram = round(total_vram - (allocated / (1024 ** 3)), 2)
        except Exception:
            pass

        disk = shutil.disk_usage(os.getcwd())
        free_disk = round(disk.free / (1024 ** 3), 2)

        leased_vram = sum(l.reserved_vram_gb for l in self._active_leases.values() if l.active)
        leased_ram = sum(l.reserved_ram_gb for l in self._active_leases.values() if l.active)

        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=None),
            total_ram_gb=total_ram,
            free_ram_gb=max(0.0, round(free_ram - leased_ram, 2)),
            total_vram_gb=total_vram,
            free_vram_gb=max(0.0, round(free_vram - leased_vram, 2)),
            free_disk_gb=free_disk
        )

    def can_accommodate(self, required_vram_gb: float, required_ram_gb: float) -> bool:
        metrics = self.get_metrics()
        if (metrics.free_vram_gb + 0.1) < required_vram_gb:
            return False
        if (metrics.free_ram_gb + 0.1) < required_ram_gb:
            return False
        return True

    async def reserve(self, task_id: str, vram_gb: float, ram_gb: float) -> ResourceLease | None:
        async with self._lock:
            if not self.can_accommodate(vram_gb, ram_gb):
                return None

            import uuid
            lease = ResourceLease(
                lease_id=f"lease_{uuid.uuid4().hex[:6]}",
                task_id=task_id,
                reserved_vram_gb=vram_gb,
                reserved_ram_gb=ram_gb,
                active=True
            )
            self._active_leases[lease.lease_id] = lease
            return lease

    async def release(self, lease_id: str) -> bool:
        async with self._lock:
            if lease_id in self._active_leases:
                self._active_leases[lease_id].active = False
                del self._active_leases[lease_id]
                return True
            return False