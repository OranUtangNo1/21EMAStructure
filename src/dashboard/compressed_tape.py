from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


SCHEMA_VERSION = "tape-v1.0.1"
FLAG_ORDER = ("G+", "G-", "!", "A", "D", "U", "R")


@dataclass(frozen=True, slots=True)
class CompressedTapeConfig:
    """Configuration for v1.0 compressed tape generation."""

    t0_days: int = 15
    t1_days: int = 50
    events_lookback_days: int = 50
    volume_window: int = 50
    max_events: int = 8

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "CompressedTapeConfig":
        data = payload or {}
        return cls(
            t0_days=max(1, int(data.get("t0_days", 15))),
            t1_days=max(1, int(data.get("t1_days", 50))),
            events_lookback_days=max(1, int(data.get("events_lookback_days", 50))),
            volume_window=max(1, int(data.get("volume_window", 50))),
            max_events=max(1, int(data.get("max_events", 8))),
        )


@dataclass(frozen=True, slots=True)
class CompressedTapeDocument:
    ticker: str
    text: str
    end_date: pd.Timestamp
    path: Path | None = None
    row_count: int = 0
    tier: str = "T0"

    @property
    def filename(self) -> str:
        return f"tape_{self.ticker}_{self.end_date.strftime('%Y%m%d')}.md"


@dataclass(frozen=True, slots=True)
class CompressedTapeExportResult:
    output_dir: Path
    documents: list[CompressedTapeDocument]
    missing: dict[str, str]
    manifest_path: Path


class CompressedTapeError(ValueError):
    """Raised when source data cannot produce a spec-compliant tape."""


class CompressedTapeGenerator:
    """Generate compressed tape markdown from daily OHLCV histories."""

    def __init__(self, config: CompressedTapeConfig | None = None) -> None:
        self.config = config or CompressedTapeConfig()

    def build_t0(self, ticker: str, history: pd.DataFrame, *, last_close: float | None = None) -> CompressedTapeDocument:
        return self.build(ticker, history, days=self.config.t0_days, tier="T0", last_close=last_close)

    def build_t1(self, ticker: str, history: pd.DataFrame, *, last_close: float | None = None) -> CompressedTapeDocument:
        return self.build(ticker, history, days=self.config.t1_days, tier="T1", last_close=last_close)

    def build(
        self,
        ticker: str,
        history: pd.DataFrame,
        *,
        days: int,
        tier: str,
        last_close: float | None = None,
    ) -> CompressedTapeDocument:
        symbol = str(ticker).strip().upper()
        if not symbol:
            raise CompressedTapeError("ticker is required")

        prepared, adjusted = self._prepare_history(history)
        if len(prepared) < 2:
            raise CompressedTapeError(f"{symbol}: at least two source rows are required")

        metrics = self._add_metrics(prepared)
        tape_rows = metrics.tail(max(1, int(days))).copy()
        if tape_rows.empty:
            raise CompressedTapeError(f"{symbol}: no rows available for tape")
        if tape_rows["cc_text"].isna().any():
            raise CompressedTapeError(f"{symbol}: previous close is unavailable for a tape row")

        self._validate_rows(symbol, tape_rows, metrics, last_close=last_close)
        text = self._render(tape_rows, metrics, adjusted=adjusted)
        return CompressedTapeDocument(
            ticker=symbol,
            text=text,
            end_date=pd.Timestamp(tape_rows.index[-1]),
            row_count=len(tape_rows),
            tier=tier,
        )

    def _prepare_history(self, history: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
        if history is None or history.empty:
            raise CompressedTapeError("price history is empty")

        frame = history.copy()
        frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
        if "adj_close" in frame.columns and "adjusted_close" not in frame.columns:
            frame = frame.rename(columns={"adj_close": "adjusted_close"})
        if "date" in frame.columns:
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame = frame.set_index("date")
        frame.index = pd.to_datetime(frame.index, errors="coerce")
        frame = frame.loc[frame.index.notna()].copy()
        if getattr(frame.index, "tz", None) is not None:
            frame.index = frame.index.tz_localize(None)

        required = ["open", "high", "low", "close", "volume"]
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise CompressedTapeError(f"missing required columns: {', '.join(missing)}")

        for column in required + (["adjusted_close"] if "adjusted_close" in frame.columns else []):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = frame.sort_index()
        frame = frame.loc[~frame.index.duplicated(keep="last")].copy()

        adjusted = "adjusted_close" in frame.columns
        if adjusted:
            close_for_ratio = frame["close"].where(frame["close"] != 0)
            ratio = frame["adjusted_close"] / close_for_ratio
            for column in ("open", "high", "low", "close"):
                frame[column] = frame[column] * ratio

        frame = frame.dropna(subset=required).copy()
        if frame.empty:
            raise CompressedTapeError("price history has no complete OHLCV rows")
        return frame[required], adjusted

    def _add_metrics(self, frame: pd.DataFrame) -> pd.DataFrame:
        metrics = frame.copy()
        previous_close = metrics["close"].shift(1)
        metrics["cc"] = (metrics["close"] / previous_close - 1.0) * 100.0
        rounded_open = metrics["open"].map(lambda value: self._round_half_up(float(value), 2))
        rounded_high = metrics["high"].map(lambda value: self._round_half_up(float(value), 2))
        rounded_low = metrics["low"].map(lambda value: self._round_half_up(float(value), 2))
        rounded_close = metrics["close"].map(lambda value: self._round_half_up(float(value), 2))
        rounded_range = rounded_high - rounded_low
        rounded_pos = (rounded_close - rounded_low) / rounded_range.where(rounded_range != 0) * 100.0
        metrics["pos"] = rounded_pos.map(lambda value: 50 if pd.isna(value) else int(self._round_half_up(float(value), 0))).astype(int)
        metrics["open_text"] = rounded_open.map(lambda value: f"{value:.2f}")
        metrics["high_text"] = rounded_high.map(lambda value: f"{value:.2f}")
        metrics["low_text"] = rounded_low.map(lambda value: f"{value:.2f}")
        metrics["close_text"] = rounded_close.map(lambda value: f"{value:.2f}")
        volume_sma = metrics["volume"].rolling(self.config.volume_window, min_periods=self.config.volume_window).mean()
        metrics["volume_sma"] = volume_sma
        v_values = metrics["volume"] / volume_sma.where(volume_sma != 0) * 100.0
        metrics["v"] = v_values.map(lambda value: pd.NA if pd.isna(value) else int(self._round_half_up(float(value), 0)))
        metrics["cc_text"] = metrics["cc"].map(self._format_signed_one_decimal)
        metrics["v_text"] = metrics["v"].map(lambda value: "NA" if pd.isna(value) else str(int(value)))
        metrics["flags"] = [self._flags_for_position(metrics, position) for position in range(len(metrics))]
        return metrics

    def _flags_for_position(self, frame: pd.DataFrame, position: int) -> str:
        row = frame.iloc[position]
        flags: list[str] = []
        if position > 0:
            previous = frame.iloc[position - 1]
            if float(row["open"]) > float(previous["high"]):
                flags.append("G+")
            if float(row["open"]) < float(previous["low"]):
                flags.append("G-")
        v_value = row["v"]
        has_volume_value = pd.notna(v_value)
        if has_volume_value and float(v_value) >= 180.0:
            flags.append("!")
        if has_volume_value and int(row["pos"]) >= 80 and float(v_value) >= 140.0:
            flags.append("A")
        if has_volume_value and int(row["pos"]) <= 20 and float(v_value) >= 140.0:
            flags.append("D")
        if position >= 10:
            prior_low = float(frame["low"].iloc[position - 10 : position].min())
            if float(row["low"]) < prior_low and float(row["close"]) > prior_low:
                flags.append("U")
        if position > 0:
            previous = frame.iloc[position - 1]
            if float(row["high"]) > float(previous["high"]) and float(row["close"]) < float(previous["close"]) and int(row["pos"]) <= 30:
                flags.append("R")
        return "".join(flags)

    def _render(self, tape_rows: pd.DataFrame, metrics: pd.DataFrame, *, adjusted: bool) -> str:
        start = pd.Timestamp(tape_rows.index[0])
        end = pd.Timestamp(tape_rows.index[-1])
        date_format = "%Y-%m-%d" if start.year != end.year else "%m%d"
        v50_last = tape_rows["volume_sma"].iloc[-1]
        v50_text = "NA" if pd.isna(v50_last) else str(int(self._round_half_up(v50_last, 0)))
        lines = [
            f"## TAPE ({SCHEMA_VERSION})",
            f"PERIOD: {start.strftime('%Y-%m-%d')}..{end.strftime('%Y-%m-%d')} ({len(tape_rows)}d) ADJ={'Y' if adjusted else 'N'} V50_LAST={v50_text}",
            "MMDD|O|H|L|C|cc|pos|v|flags",
        ]
        for idx, row in tape_rows.iterrows():
            lines.append(
                "|".join(
                    [
                        pd.Timestamp(idx).strftime(date_format),
                        str(row["open_text"]),
                        str(row["high_text"]),
                        str(row["low_text"]),
                        str(row["close_text"]),
                        str(row["cc_text"]),
                        str(int(row["pos"])),
                        str(row["v_text"]),
                        str(row["flags"]),
                    ]
                )
            )
        lines.extend(["", "## EVENTS_50D"])
        lines.extend(self._event_lines(metrics, tape_start=start))
        return "\n".join(lines) + "\n"

    def _event_lines(self, metrics: pd.DataFrame, *, tape_start: pd.Timestamp) -> list[str]:
        event_scope = metrics.tail(self.config.events_lookback_days)
        event_scope = event_scope.loc[event_scope.index < tape_start].copy()
        rows: list[dict[str, object]] = []
        for idx, row in event_scope.iterrows():
            flags = str(row["flags"])
            v_value = row["v"]
            is_event = (pd.notna(v_value) and float(v_value) >= 180.0) or ("A" in flags) or ("D" in flags) or ("U" in flags)
            if not is_event:
                continue
            rows.append(
                {
                    "date": pd.Timestamp(idx),
                    "v": -1 if pd.isna(v_value) else int(v_value),
                    "line": f"{pd.Timestamp(idx).strftime('%m%d')} v{row['v_text']} {flags} C={row['close_text']} cc={row['cc_text']}",
                }
            )
        if not rows:
            return ["none"]
        rows = sorted(rows, key=lambda item: item["date"], reverse=True)
        if len(rows) > self.config.max_events:
            rows = sorted(rows, key=lambda item: item["v"], reverse=True)[: self.config.max_events]
            rows = sorted(rows, key=lambda item: item["date"], reverse=True)
        return [str(row["line"]) for row in rows]

    def _validate_rows(self, ticker: str, tape_rows: pd.DataFrame, metrics: pd.DataFrame, *, last_close: float | None) -> None:
        if not tape_rows.index.is_monotonic_increasing or tape_rows.index.has_duplicates:
            raise CompressedTapeError(f"{ticker}: dates must be unique and ascending")
        for idx, row in tape_rows.iterrows():
            low = float(row["low"])
            high = float(row["high"])
            open_ = float(row["open"])
            close = float(row["close"])
            if low > min(open_, close) or high < max(open_, close):
                raise CompressedTapeError(f"{ticker}: invalid OHLC ordering at {pd.Timestamp(idx).date()}")
            rendered = {
                "open": float(row["open_text"]),
                "high": float(row["high_text"]),
                "low": float(row["low_text"]),
                "close": float(row["close_text"]),
            }
            expected_pos = 50 if rendered["high"] == rendered["low"] else int(self._round_half_up((rendered["close"] - rendered["low"]) / (rendered["high"] - rendered["low"]) * 100.0, 0))
            if expected_pos != int(row["pos"]):
                raise CompressedTapeError(f"{ticker}: pos validation failed at {pd.Timestamp(idx).date()}")
            if str(row["v_text"]) == "NA" and metrics.index.get_loc(idx) + 1 >= self.config.volume_window:
                raise CompressedTapeError(f"{ticker}: v=NA after enough source rows at {pd.Timestamp(idx).date()}")
            self._validate_flag_order(ticker, str(row["flags"]), pd.Timestamp(idx))

        if len(tape_rows) != len(pd.Index(tape_rows.index)):
            raise CompressedTapeError(f"{ticker}: row count mismatch")
        if last_close is not None:
            latest_close = self._round_half_up(float(tape_rows["close"].iloc[-1]), 2)
            expected_close = self._round_half_up(float(last_close), 2)
            if latest_close != expected_close:
                raise CompressedTapeError(f"{ticker}: latest close does not match snapshot last_close")

    def _validate_flag_order(self, ticker: str, flags: str, idx: pd.Timestamp) -> None:
        remaining = flags
        parsed: list[str] = []
        while remaining:
            matched = next((flag for flag in FLAG_ORDER if remaining.startswith(flag)), None)
            if matched is None:
                raise CompressedTapeError(f"{ticker}: undefined flag at {idx.date()}")
            parsed.append(matched)
            remaining = remaining[len(matched) :]
        order_positions = [FLAG_ORDER.index(flag) for flag in parsed]
        if order_positions != sorted(order_positions):
            raise CompressedTapeError(f"{ticker}: flag order invalid at {idx.date()}")

    def _format_price(self, value: object) -> str:
        rounded = self._round_half_up(float(value), 2)
        return f"{rounded:.2f}"

    def _format_signed_one_decimal(self, value: object) -> str | None:
        if pd.isna(value):
            return None
        number = float(value)
        if -0.05 <= number <= 0.05:
            return "0.0"
        rounded = self._round_half_up(number, 1)
        return f"{rounded:+.1f}"

    def _round_half_up(self, value: float, digits: int) -> float:
        quantizer = Decimal("1") if digits == 0 else Decimal("1").scaleb(-digits)
        return float(Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP))
