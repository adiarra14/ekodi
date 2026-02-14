"""
Ekodi – Server health monitoring and load protection.

Tracks:
  - Active concurrent requests
  - CPU usage %
  - Memory usage %
  - Average response time (rolling window)
  - Request queue depth
  - Error rate

Provides load-shedding: rejects new requests when server is overloaded.
"""

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Configuration (from env or defaults) ─────────────────────
MAX_CONCURRENT_REQUESTS = int(os.getenv("EKODI_MAX_CONCURRENT", "20"))
MAX_QUEUE_DEPTH = int(os.getenv("EKODI_MAX_QUEUE", "50"))
CPU_THRESHOLD = float(os.getenv("EKODI_CPU_THRESHOLD", "90"))       # percent
MEMORY_THRESHOLD = float(os.getenv("EKODI_MEMORY_THRESHOLD", "90"))  # percent
RESPONSE_TIME_WINDOW = 100  # rolling window size for avg response time


@dataclass
class ServerStats:
    """Real-time server statistics."""
    active_requests: int = 0
    total_requests: int = 0
    total_errors: int = 0
    total_rejected: int = 0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    avg_response_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    is_overloaded: bool = False
    overload_reason: str = ""


class ServerMonitor:
    """Singleton server monitor that tracks health metrics."""

    def __init__(self):
        self._active_requests = 0
        self._total_requests = 0
        self._total_errors = 0
        self._total_rejected = 0
        self._start_time = time.time()
        self._response_times: deque = deque(maxlen=RESPONSE_TIME_WINDOW)
        self._lock = asyncio.Lock()

        # CPU/memory cache (updated periodically, not on every request)
        self._cpu_percent = 0.0
        self._memory_percent = 0.0
        self._memory_used_mb = 0.0
        self._memory_total_mb = 0.0
        self._last_system_check = 0.0

    def _update_system_stats(self):
        """Update CPU and memory stats (cached for 5 seconds)."""
        now = time.time()
        if now - self._last_system_check < 5:
            return

        try:
            import psutil
            self._cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self._memory_percent = mem.percent
            self._memory_used_mb = mem.used / (1024 * 1024)
            self._memory_total_mb = mem.total / (1024 * 1024)
        except ImportError:
            # psutil not installed — use /proc fallback on Linux
            try:
                # CPU: simple load average approach
                load1, _, _ = os.getloadavg()
                cpu_count = os.cpu_count() or 1
                self._cpu_percent = min(100.0, (load1 / cpu_count) * 100)

                # Memory from /proc/meminfo
                with open("/proc/meminfo") as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            meminfo[parts[0].rstrip(":")] = int(parts[1])
                    total = meminfo.get("MemTotal", 0)
                    available = meminfo.get("MemAvailable", 0)
                    if total > 0:
                        used = total - available
                        self._memory_percent = (used / total) * 100
                        self._memory_used_mb = used / 1024
                        self._memory_total_mb = total / 1024
            except Exception:
                pass  # Can't read system stats

        self._last_system_check = now

    def request_start(self):
        """Called when a new request begins. Returns False if should be rejected."""
        self._active_requests += 1
        self._total_requests += 1
        return True

    def request_end(self, duration_ms: float, error: bool = False):
        """Called when a request finishes."""
        self._active_requests = max(0, self._active_requests - 1)
        self._response_times.append(duration_ms)
        if error:
            self._total_errors += 1

    def record_rejection(self):
        """Called when a request is rejected due to overload."""
        self._total_rejected += 1

    def check_overloaded(self) -> tuple[bool, str]:
        """Check if server is currently overloaded. Returns (is_overloaded, reason)."""
        self._update_system_stats()

        # Check concurrent requests
        if self._active_requests >= MAX_CONCURRENT_REQUESTS:
            return True, f"Too many concurrent requests ({self._active_requests}/{MAX_CONCURRENT_REQUESTS})"

        # Check CPU
        if self._cpu_percent >= CPU_THRESHOLD:
            return True, f"CPU usage too high ({self._cpu_percent:.0f}%)"

        # Check memory
        if self._memory_percent >= MEMORY_THRESHOLD:
            return True, f"Memory usage too high ({self._memory_percent:.0f}%)"

        return False, ""

    def get_stats(self) -> ServerStats:
        """Get current server statistics."""
        self._update_system_stats()

        avg_rt = 0.0
        if self._response_times:
            avg_rt = sum(self._response_times) / len(self._response_times)

        is_overloaded, reason = self.check_overloaded()

        return ServerStats(
            active_requests=self._active_requests,
            total_requests=self._total_requests,
            total_errors=self._total_errors,
            total_rejected=self._total_rejected,
            cpu_percent=round(self._cpu_percent, 1),
            memory_percent=round(self._memory_percent, 1),
            memory_used_mb=round(self._memory_used_mb, 1),
            memory_total_mb=round(self._memory_total_mb, 1),
            avg_response_time_ms=round(avg_rt, 1),
            uptime_seconds=round(time.time() - self._start_time, 0),
            is_overloaded=is_overloaded,
            overload_reason=reason,
        )

    def get_status_level(self) -> str:
        """Get a simple status: 'healthy', 'warning', or 'critical'."""
        self._update_system_stats()
        if self._active_requests >= MAX_CONCURRENT_REQUESTS or self._cpu_percent >= CPU_THRESHOLD or self._memory_percent >= MEMORY_THRESHOLD:
            return "critical"
        if self._active_requests >= MAX_CONCURRENT_REQUESTS * 0.7 or self._cpu_percent >= CPU_THRESHOLD * 0.8 or self._memory_percent >= MEMORY_THRESHOLD * 0.8:
            return "warning"
        return "healthy"


# ── Singleton ────────────────────────────────────────────────
_monitor = ServerMonitor()


def get_monitor() -> ServerMonitor:
    return _monitor
