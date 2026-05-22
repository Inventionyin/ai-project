import asyncio
import psutil
import time
from typing import Dict, List

class SystemMonitor:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.is_running = False
        self.stats: List[Dict] = []

    async def start(self):
        self.is_running = True
        self.stats = []
        asyncio.create_task(self._monitor_loop())

    async def stop(self):
        self.is_running = False

    async def _monitor_loop(self):
        while self.is_running:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_io_counters()
            
            self.stats.append({
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "disk_read_mb": disk.read_bytes / (1024 * 1024) if disk else 0,
                "disk_write_mb": disk.write_bytes / (1024 * 1024) if disk else 0,
            })
            await asyncio.sleep(self.interval)

    def generate_report(self) -> Dict:
        if not self.stats:
            return {"message": "No data collected"}
        
        cpu_percents = [s["cpu_percent"] for s in self.stats]
        mem_percents = [s["memory_percent"] for s in self.stats]
        
        return {
            "duration_seconds": self.stats[-1]["timestamp"] - self.stats[0]["timestamp"],
            "cpu": {
                "avg": sum(cpu_percents) / len(cpu_percents),
                "max": max(cpu_percents),
                "min": min(cpu_percents),
            },
            "memory": {
                "avg": sum(mem_percents) / len(mem_percents),
                "max": max(mem_percents),
                "min": min(mem_percents),
            },
            "sample_count": len(self.stats)
        }
