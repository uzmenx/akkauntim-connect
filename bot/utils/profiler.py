"""
Institutional Loop Profiler & Performance Bottleneck Analyzer.

TradingBot'dagi 5-daqiqalik va har bir symbol bo'yicha run_cycle loop'larining
barcha bosqichlarini yuqori aniqlikda (high-resolution timer) va cProfile bilan
o'lchaydi, qayerda vaqt yo'qotilayotganini (bottleneck) aniqlaydi.
"""

import time
import cProfile
import pstats
import io
import threading
import logging
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def get_memory_usage_mb() -> float:
    """Joriy jarayonning RSS xotira sarfini MB o'lchovida hisoblash."""
    try:
        import psutil
        process = psutil.Process()
        return round(process.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        try:
            import resource
            rusage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == 'darwin':
                return round(rusage / (1024 * 1024), 2)
            return round(rusage / 1024, 2)
        except Exception:
            return 0.0


@dataclass
class StepStats:
    name: str
    count: int = 0
    total_time_sec: float = 0.0
    min_time_sec: float = float('inf')
    max_time_sec: float = 0.0

    @property
    def avg_time_ms(self) -> float:
        if self.count == 0:
            return 0.0
        return (self.total_time_sec / self.count) * 1000.0

    @property
    def total_time_ms(self) -> float:
        return self.total_time_sec * 1000.0

    @property
    def min_time_ms(self) -> float:
        if self.min_time_sec == float('inf'):
            return 0.0
        return self.min_time_sec * 1000.0

    @property
    def max_time_ms(self) -> float:
        return self.max_time_sec * 1000.0


class StepTimerContext:
    """Context manager for timing individual code steps."""

    def __init__(self, profiler: "LoopProfiler", step_name: str):
        self.profiler = profiler
        self.step_name = step_name
        self.start_time: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time
        self.profiler.record_step(self.step_name, elapsed)


class LoopProfiler:
    """
    Thread-safe High-Resolution Loop Profiler.
    
    Har bir bosqich davomiyligi, o'rtacha vaqt, min/maks va foiziy
    ulushini hisoblab beradi.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._lock = threading.Lock()
        self._stats: Dict[str, StepStats] = {}
        self._cycle_start_time: Optional[float] = None
        self._last_cycle_duration: float = 0.0
        self.cycle_count: int = 0

    def start_cycle(self):
        """Yangi loop sikli boshlanishini belgilash."""
        with self._lock:
            self._cycle_start_time = time.perf_counter()
            self.cycle_count += 1

    def end_cycle(self) -> float:
        """Loop siklini yakunlash va umumiy vaqtni qaytarish (sekundda)."""
        with self._lock:
            if self._cycle_start_time is not None:
                self._last_cycle_duration = time.perf_counter() - self._cycle_start_time
                self._cycle_start_time = None
            return self._last_cycle_duration

    def track(self, step_name: str) -> StepTimerContext:
        """Bosqich vaqtini o'lchash uchun context manager."""
        return StepTimerContext(self, step_name)

    def record_step(self, step_name: str, elapsed_sec: float):
        """Bosqich vaqtini saqlash."""
        if not self.enabled:
            return
        with self._lock:
            if step_name not in self._stats:
                self._stats[step_name] = StepStats(name=step_name)
            stat = self._stats[step_name]
            stat.count += 1
            stat.total_time_sec += elapsed_sec
            if elapsed_sec < stat.min_time_sec:
                stat.min_time_sec = elapsed_sec
            if elapsed_sec > stat.max_time_sec:
                stat.max_time_sec = elapsed_sec

    def reset(self):
        """Profil ko'rsatkichlarini tozalash."""
        with self._lock:
            self._stats.clear()
            self._cycle_start_time = None
            self._last_cycle_duration = 0.0
            self.cycle_count = 0

    def get_summary(self) -> Dict[str, Any]:
        """Barcha o'lchov statistikasini lug'at shaklida olish."""
        return self.get_stats_dict()

    def get_stats_dict(self) -> Dict[str, Any]:
        """Barcha o'lchov statistikasini lug'at shaklida olish."""
        with self._lock:
            total_recorded_sec = sum(s.total_time_sec for s in self._stats.values())
            items = []
            for name, stat in self._stats.items():
                pct = (stat.total_time_sec / total_recorded_sec * 100.0) if total_recorded_sec > 0 else 0.0
                items.append({
                    "step": name,
                    "count": stat.count,
                    "total_ms": round(stat.total_time_ms, 2),
                    "avg_ms": round(stat.avg_time_ms, 2),
                    "min_ms": round(stat.min_time_ms, 2),
                    "max_ms": round(stat.max_time_ms, 2),
                    "share_pct": round(pct, 1)
                })
            # Eng ko'p vaqt olgan tartibda saralash (Bottlenecks)
            items.sort(key=lambda x: x["total_ms"], reverse=True)
            return {
                "cycle_count": self.cycle_count,
                "last_cycle_sec": round(self._last_cycle_duration, 3),
                "total_recorded_sec": round(total_recorded_sec, 3),
                "memory_rss_mb": get_memory_usage_mb(),
                "steps": items
            }

    def format_report(self) -> str:
        """Profiling natijalarini chiroyli jadval va matn ko'rinishida shakllantirish."""
        summary = self.get_stats_dict()
        steps = summary["steps"]

        lines = []
        lines.append("==========================================================================")
        lines.append("⏱️  TRADING BOT MAIN LOOP PROFILER REPORT (Ishlash Tezligi & Xotira Tahlili)")
        lines.append("==========================================================================")
        lines.append(f"📊 Jami o'tkazilgan sikllar: {summary['cycle_count']}")
        lines.append(f"⏳ So'nggi sikl umumiy vaqti: {summary['last_cycle_sec']} sek")
        lines.append(f"⚡ O'lchangan barcha qadamlar vaqti: {summary['total_recorded_sec']} sek")
        lines.append(f"💾 Joriy xotira sarfi (RSS): {summary['memory_rss_mb']} MB")
        lines.append("--------------------------------------------------------------------------")
        lines.append(f"{'Bosqich Nomi':<40} | {'Soni':<5} | {'Jami (ms)':<10} | {'O`rtacha':<9} | {'Ulush':<6}")
        lines.append("--------------------------------------------------------------------------")

        for item in steps:
            lines.append(
                f"{item['step']:<40} | {item['count']:<5} | {item['total_ms']:<10.1f} | "
                f"{item['avg_ms']:<9.1f} ms | {item['share_pct']:<5.1f}%"
            )

        lines.append("==========================================================================")
        if steps:
            top_bottleneck = steps[0]
            lines.append(
                f"🔥 ENG KATTA BOTTLENECK: [{top_bottleneck['step']}] — "
                f"{top_bottleneck['total_ms']:.1f}ms ({top_bottleneck['share_pct']}%)"
            )
        lines.append("==========================================================================")

        return "\n".join(lines)

    def log_summary(self, log_level: int = logging.INFO, verbose: bool = False):
        """Profil va xotira sarfi hisobotini logger orqali chiqarish."""
        if not self.enabled:
            return
        summary = self.get_stats_dict()
        top = summary["steps"][0] if summary["steps"] else {"step": "N/A", "total_ms": 0.0}
        
        # Qisqa 1 qatorlik xulosa (INFO level uchun)
        concise_msg = (
            f"⏱️ Loop #{summary['cycle_count']} yakunlandi ({summary['last_cycle_sec']}s) | "
            f"💾 Xotira: {summary['memory_rss_mb']} MB | "
            f"🔥 Top Bottleneck: {top['step']} ({top['total_ms']:.1f}ms)"
        )
        logger.log(log_level, concise_msg)
        
        # To'liq jadval verbose=True bo'lganda yoki DEBUG rejimida chiqariladi
        if verbose or logger.isEnabledFor(logging.DEBUG):
            report = self.format_report()
            logger.debug(f"\n{report}")


def run_cprofile_analysis(func, *args, top_n: int = 25, **kwargs) -> str:
    """
    cProfile yordamida funksiya yoki siklning pastki darajadagi (low-level) call tree
    statisitikasini o'lchash va matn shaklida qaytarish.
    """
    pr = cProfile.Profile()
    pr.enable()
    
    res = None
    try:
        res = func(*args, **kwargs)
    finally:
        pr.disable()
        
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(top_n)
    
    header = f"=== cProfile Call Tree Breakdown (Top {top_n} Cumulative Functions) ===\n"
    return header + s.getvalue()
