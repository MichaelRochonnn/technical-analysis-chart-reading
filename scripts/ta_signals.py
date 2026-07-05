#!/usr/bin/env python3
import argparse
import csv
import json
import math
from pathlib import Path


ALIASES = {
    "date": ["date", "time", "timestamp", "datetime"],
    "open": ["open", "o"],
    "high": ["high", "h"],
    "low": ["low", "l"],
    "close": ["close", "c", "adj_close", "adjclose", "last", "price"],
    "volume": ["volume", "vol", "v"],
    "open_interest": ["open_interest", "openinterest", "oi", "open int", "open_int"],
}


def normalize(name):
    return "".join(ch for ch in name.strip().lower() if ch.isalnum() or ch == "_")


def to_float(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in {"nan", "null", "none", "-"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def round_or_none(value, digits=6):
    if value is None:
        return None
    return round(value, digits)


def load_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row")
        normalized = {normalize(name): name for name in reader.fieldnames}
        columns = {}
        for canonical, aliases in ALIASES.items():
            for alias in aliases:
                key = normalize(alias)
                if key in normalized:
                    columns[canonical] = normalized[key]
                    break

        if "close" not in columns:
            raise SystemExit("CSV must contain a close column")

        rows = []
        for raw in reader:
            item = {}
            for canonical, original in columns.items():
                if canonical == "date":
                    item[canonical] = raw.get(original, "")
                else:
                    item[canonical] = to_float(raw.get(original))
            if item.get("close") is not None:
                rows.append(item)
    if not rows:
        raise SystemExit("CSV has no usable close values")
    return rows, columns


def series(rows, field, fallback=None):
    values = []
    for row in rows:
        value = row.get(field)
        if value is None and fallback is not None:
            value = row.get(fallback)
        values.append(value)
    return values


def sma(values, period):
    out = [None] * len(values)
    window = []
    total = 0.0
    for i, value in enumerate(values):
        if value is None:
            window.append(None)
        else:
            window.append(value)
            total += value
        if len(window) > period:
            old = window.pop(0)
            if old is not None:
                total -= old
        if len(window) == period and all(v is not None for v in window):
            out[i] = total / period
    return out


def ema(values, period):
    out = [None] * len(values)
    alpha = 2.0 / (period + 1.0)
    seed = None
    for i, value in enumerate(values):
        if value is None:
            continue
        if seed is None:
            if i + 1 >= period and all(v is not None for v in values[i + 1 - period : i + 1]):
                seed = sum(values[i + 1 - period : i + 1]) / period
                out[i] = seed
        else:
            seed = alpha * value + (1 - alpha) * seed
            out[i] = seed
    return out


def rsi_wilder(closes, period=14):
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = []
    losses = []
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def true_range(highs, lows, closes):
    out = []
    for i, close in enumerate(closes):
        high = highs[i] if highs[i] is not None else close
        low = lows[i] if lows[i] is not None else close
        if i == 0:
            out.append(high - low)
        else:
            prev_close = closes[i - 1]
            out.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return out


def atr(highs, lows, closes, period=14):
    tr = true_range(highs, lows, closes)
    out = [None] * len(tr)
    if len(tr) < period:
        return out
    value = sum(tr[:period]) / period
    out[period - 1] = value
    for i in range(period, len(tr)):
        value = (value * (period - 1) + tr[i]) / period
        out[i] = value
    return out


def stochastic(highs, lows, closes, k_period=14, d_period=3):
    k = [None] * len(closes)
    for i in range(len(closes)):
        if i + 1 < k_period:
            continue
        window_high = [v for v in highs[i + 1 - k_period : i + 1] if v is not None]
        window_low = [v for v in lows[i + 1 - k_period : i + 1] if v is not None]
        if len(window_high) != k_period or len(window_low) != k_period:
            continue
        highest = max(window_high)
        lowest = min(window_low)
        if highest == lowest:
            k[i] = 50.0
        else:
            k[i] = 100.0 * (closes[i] - lowest) / (highest - lowest)
    d = sma(k, d_period)
    return k, d


def macd(closes, fast=12, slow=26, signal=9):
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    line = [None] * len(closes)
    for i, (fast_value, slow_value) in enumerate(zip(fast_ema, slow_ema)):
        if fast_value is not None and slow_value is not None:
            line[i] = fast_value - slow_value
    signal_line = ema(line, signal)
    hist = [None if a is None or b is None else a - b for a, b in zip(line, signal_line)]
    return line, signal_line, hist


def roc(closes, period=10):
    out = [None] * len(closes)
    for i in range(period, len(closes)):
        base = closes[i - period]
        if base:
            out[i] = 100.0 * (closes[i] - base) / base
    return out


def obv(closes, volumes):
    if not volumes or all(v is None for v in volumes):
        return [None] * len(closes)
    out = [0.0] * len(closes)
    for i in range(1, len(closes)):
        vol = volumes[i] or 0.0
        if closes[i] > closes[i - 1]:
            out[i] = out[i - 1] + vol
        elif closes[i] < closes[i - 1]:
            out[i] = out[i - 1] - vol
        else:
            out[i] = out[i - 1]
    return out


def rolling_extreme(values, period, mode):
    out = [None] * len(values)
    for i in range(len(values)):
        if i + 1 < period:
            continue
        window = [v for v in values[i + 1 - period : i + 1] if v is not None]
        if len(window) == period:
            out[i] = max(window) if mode == "max" else min(window)
    return out


def recent_pivots(highs, lows, closes, left=2, right=2, limit=5):
    highs_out = []
    lows_out = []
    for i in range(left, len(closes) - right):
        high = highs[i] if highs[i] is not None else closes[i]
        low = lows[i] if lows[i] is not None else closes[i]
        left_highs = [(highs[j] if highs[j] is not None else closes[j]) for j in range(i - left, i)]
        right_highs = [(highs[j] if highs[j] is not None else closes[j]) for j in range(i + 1, i + 1 + right)]
        left_lows = [(lows[j] if lows[j] is not None else closes[j]) for j in range(i - left, i)]
        right_lows = [(lows[j] if lows[j] is not None else closes[j]) for j in range(i + 1, i + 1 + right)]
        if high > max(left_highs + right_highs):
            highs_out.append({"index": i, "value": high})
        if low < min(left_lows + right_lows):
            lows_out.append({"index": i, "value": low})
    return highs_out[-limit:], lows_out[-limit:]


def last_non_none(values):
    for value in reversed(values):
        if value is not None:
            return value
    return None


def slope(values, period=5):
    valid = [v for v in values if v is not None]
    if len(valid) < period + 1:
        return None
    return valid[-1] - valid[-1 - period]


def classify_rsi(value):
    if value is None:
        return "unavailable"
    if value >= 70:
        return "overbought_or_strong_trend"
    if value <= 30:
        return "oversold_or_strong_downtrend"
    if value >= 55:
        return "bullish_momentum"
    if value <= 45:
        return "bearish_momentum"
    return "neutral"


def oi_interpretation(rows):
    if len(rows) < 2 or rows[-1].get("open_interest") is None or rows[-2].get("open_interest") is None:
        return None
    price_delta = rows[-1]["close"] - rows[-2]["close"]
    oi_delta = rows[-1]["open_interest"] - rows[-2]["open_interest"]
    if price_delta > 0 and oi_delta > 0:
        meaning = "new money supports the advance"
    elif price_delta > 0 and oi_delta < 0:
        meaning = "advance may be driven by short covering/liquidation"
    elif price_delta < 0 and oi_delta > 0:
        meaning = "new shorts support the decline"
    elif price_delta < 0 and oi_delta < 0:
        meaning = "decline may be driven by long liquidation"
    else:
        meaning = "mixed or unchanged"
    return {"price_delta": price_delta, "open_interest_delta": oi_delta, "meaning": meaning}


def build_report(rows, columns):
    closes = series(rows, "close")
    highs = series(rows, "high", "close")
    lows = series(rows, "low", "close")
    volumes = series(rows, "volume")

    ma20 = sma(closes, 20)
    ma50 = sma(closes, 50)
    ma200 = sma(closes, 200)
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    rsi14 = rsi_wilder(closes, 14)
    atr14 = atr(highs, lows, closes, 14)
    stoch_k, stoch_d = stochastic(highs, lows, closes, 14, 3)
    macd_line, macd_signal, macd_hist = macd(closes)
    roc10 = roc(closes, 10)
    obv_values = obv(closes, volumes)
    vol20 = sma(volumes, 20) if any(v is not None for v in volumes) else [None] * len(rows)
    ch_high20 = rolling_extreme(highs, 20, "max")
    ch_low20 = rolling_extreme(lows, 20, "min")
    pivot_highs, pivot_lows = recent_pivots(highs, lows, closes)

    last_close = closes[-1]
    latest = rows[-1].copy()
    latest["date"] = latest.get("date") or None

    latest_ma20 = ma20[-1]
    latest_ma50 = ma50[-1]
    latest_ma200 = ma200[-1]
    trend_state = "insufficient_data"
    if latest_ma20 is not None and latest_ma50 is not None:
        if last_close > latest_ma20 > latest_ma50 and (latest_ma200 is None or latest_ma50 > latest_ma200):
            trend_state = "bullish_trend_alignment"
        elif last_close < latest_ma20 < latest_ma50 and (latest_ma200 is None or latest_ma50 < latest_ma200):
            trend_state = "bearish_trend_alignment"
        elif last_close > latest_ma50:
            trend_state = "constructive_but_mixed"
        elif last_close < latest_ma50:
            trend_state = "weak_but_mixed"
        else:
            trend_state = "range_or_transition"

    interpretations = []
    if trend_state != "insufficient_data":
        interpretations.append(f"Trend state: {trend_state}.")

    if latest_ma20 is not None:
        if last_close > latest_ma20:
            interpretations.append("Close is above the 20-period average.")
        elif last_close < latest_ma20:
            interpretations.append("Close is below the 20-period average.")

    rsi_value = rsi14[-1]
    interpretations.append(f"RSI state: {classify_rsi(rsi_value)}.")

    if macd_hist[-1] is not None and len(macd_hist) > 1 and macd_hist[-2] is not None:
        if macd_hist[-1] > 0 and macd_hist[-1] > macd_hist[-2]:
            interpretations.append("MACD histogram is positive and improving.")
        elif macd_hist[-1] < 0 and macd_hist[-1] < macd_hist[-2]:
            interpretations.append("MACD histogram is negative and deteriorating.")

    if vol20[-1] is not None and volumes[-1] is not None:
        ratio = volumes[-1] / vol20[-1] if vol20[-1] else None
        if ratio is not None:
            if ratio >= 1.5:
                interpretations.append("Latest volume is meaningfully above its 20-period average.")
            elif ratio <= 0.7:
                interpretations.append("Latest volume is meaningfully below its 20-period average.")

    if len(ch_high20) >= 2 and ch_high20[-2] is not None and last_close > ch_high20[-2]:
        interpretations.append("Close broke above the prior 20-period channel high.")
    if len(ch_low20) >= 2 and ch_low20[-2] is not None and last_close < ch_low20[-2]:
        interpretations.append("Close broke below the prior 20-period channel low.")

    oi = oi_interpretation(rows)
    if oi:
        interpretations.append(f"Open interest: {oi['meaning']}.")

    output = {
        "metadata": {
            "rows": len(rows),
            "columns_used": columns,
            "latest_date": latest.get("date"),
        },
        "latest_bar": {k: round_or_none(v) if isinstance(v, float) else v for k, v in latest.items()},
        "indicators": {
            "sma20": round_or_none(latest_ma20),
            "sma50": round_or_none(latest_ma50),
            "sma200": round_or_none(latest_ma200),
            "ema12": round_or_none(ema12[-1]),
            "ema26": round_or_none(ema26[-1]),
            "rsi14": round_or_none(rsi_value),
            "stochastic_k14": round_or_none(stoch_k[-1]),
            "stochastic_d3": round_or_none(stoch_d[-1]),
            "macd": round_or_none(macd_line[-1]),
            "macd_signal": round_or_none(macd_signal[-1]),
            "macd_histogram": round_or_none(macd_hist[-1]),
            "roc10_pct": round_or_none(roc10[-1]),
            "atr14": round_or_none(atr14[-1]),
            "obv": round_or_none(obv_values[-1]),
            "volume_sma20": round_or_none(vol20[-1]),
            "channel_high20": round_or_none(ch_high20[-1]),
            "channel_low20": round_or_none(ch_low20[-1]),
        },
        "structure": {
            "trend_state": trend_state,
            "ma20_slope_5": round_or_none(slope(ma20, 5)),
            "ma50_slope_5": round_or_none(slope(ma50, 5)),
            "recent_pivot_highs": [{"index": p["index"], "value": round_or_none(p["value"])} for p in pivot_highs],
            "recent_pivot_lows": [{"index": p["index"], "value": round_or_none(p["value"])} for p in pivot_lows],
            "open_interest_interpretation": oi,
        },
        "interpretations": interpretations,
        "caveats": [
            "Indicators are secondary to price structure and timeframe context.",
            "Script output is not financial advice and needs risk/invalidation planning.",
        ],
    }
    return output


def main():
    parser = argparse.ArgumentParser(description="Calculate Murphy-style technical-analysis indicators from OHLCV/OHLCVI CSV data.")
    parser.add_argument("csv_path", help="CSV file with OHLCV data")
    parser.add_argument("--lookback", type=int, default=None, help="Use only the last N rows")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    rows, columns = load_rows(args.csv_path)
    if args.lookback:
        rows = rows[-args.lookback :]
    report = build_report(rows, columns)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print(f"Rows: {report['metadata']['rows']}")
    print(f"Latest date: {report['metadata']['latest_date']}")
    print(f"Trend state: {report['structure']['trend_state']}")
    print("Key indicators:")
    for key, value in report["indicators"].items():
        print(f"  {key}: {value}")
    print("Interpretations:")
    for item in report["interpretations"]:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
