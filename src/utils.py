from __future__ import annotations

import hashlib
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import numpy as np
import pandas as pd


def percent_rank(series: pd.Series) -> pd.Series:
    """Return 0-100 percentile ranks while preserving missing values."""
    non_null = series.dropna()
    if non_null.empty:
        return pd.Series(np.nan, index=series.index, dtype=float)
    ranks = non_null.rank(method="average", pct=True) * 100.0
    result = pd.Series(np.nan, index=series.index, dtype=float)
    result.loc[ranks.index] = ranks
    return result


def normalize_series(series: pd.Series, method: str = "percentile", neutral: float = 50.0) -> pd.Series:
    """Normalize a series to an approximate 0-100 scale."""
    if method == "percentile":
        return percent_rank(series)
    if method == "zscore":
        non_null = series.dropna()
        if non_null.empty:
            return pd.Series(np.nan, index=series.index, dtype=float)
        std = float(non_null.std(ddof=0))
        if std == 0:
            return pd.Series(neutral, index=series.index, dtype=float)
        zscore = (series - float(non_null.mean())) / std
        return (zscore * 15.0 + neutral).clip(0.0, 100.0)
    if method == "clipped_rank":
        lower = series.quantile(0.05)
        upper = series.quantile(0.95)
        return percent_rank(series.clip(lower=lower, upper=upper))
    raise ValueError(f"Unsupported normalization method: {method}")


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """Compute a safe weighted mean."""
    mask = values.notna() & weights.notna()
    if not mask.any():
        return float("nan")
    usable_values = values.loc[mask].astype(float)
    usable_weights = weights.loc[mask].astype(float)
    weight_sum = usable_weights.sum()
    if weight_sum == 0:
        return float(usable_values.mean())
    return float(np.average(usable_values, weights=usable_weights))


def weighted_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Compute a simple weighted moving average."""
    weights = np.arange(1, window + 1, dtype=float)
    return series.rolling(window).apply(lambda values: np.dot(values, weights) / weights.sum(), raw=True)


def deterministic_seed(text: str) -> int:
    """Create a stable pseudo-random seed from a string."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def coalesce_strings(values: Iterable[str | None], fallback: str = "Unknown") -> str:
    """Return the first non-empty string."""
    for value in values:
        if value:
            return value
    return fallback


class StartupTimer:
    """Append coarse startup milestone timings to a local log and stdout."""

    def __init__(self, name: str, log_path: str | Path, *, run_id: str | None = None) -> None:
        self.name = str(name)
        self.log_path = Path(log_path)
        self.run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
        self._started = time.perf_counter()
        self._last = self._started
        self.mark("timer.start")

    def mark(self, milestone: str, **fields: object) -> None:
        now = time.perf_counter()
        elapsed = now - self._started
        delta = now - self._last
        self._last = now
        timestamp = datetime.now().isoformat(timespec="seconds")
        parts = [
            "[startup-timing]",
            f"ts={timestamp}",
            f"run_id={self.run_id}",
            f"name={self.name}",
            f"milestone={milestone}",
            f"elapsed_s={elapsed:.3f}",
            f"delta_s={delta:.3f}",
        ]
        for key, value in fields.items():
            parts.append(f"{key}={self._format_value(value)}")
        line = " ".join(parts)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass

    @contextmanager
    def step(self, milestone: str, **fields: object):
        step_started = time.perf_counter()
        self.mark(f"{milestone}.start", **fields)
        try:
            yield
        except Exception as exc:
            self.mark(
                f"{milestone}.error",
                duration_s=f"{time.perf_counter() - step_started:.3f}",
                error_type=type(exc).__name__,
            )
            raise
        else:
            self.mark(f"{milestone}.end", duration_s=f"{time.perf_counter() - step_started:.3f}")

    def _format_value(self, value: object) -> str:
        text = str(value).replace("\n", " ").replace("\r", " ").strip()
        return text.replace(" ", "_") if text else "-"
