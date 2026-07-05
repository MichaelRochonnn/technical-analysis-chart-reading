# Technical Analysis Chart Reading Skill

`technical-analysis-chart-reading` is a Codex Skill for Murphy-style technical analysis across stocks, crypto, futures, ETFs, FX, commodities, and any OHLCV/OHLCVI market data.

It is designed for chart reading, indicator synthesis, and scenario-based trade planning. It does not provide deterministic predictions or financial advice.

## What It Does

The skill analyzes market evidence in this order:

1. Market context and timeframe
2. Higher-timeframe trend
3. Price structure, support, resistance, trendlines, and channels
4. Chart patterns and breakout/retest behavior
5. Volume and open-interest confirmation when available
6. Moving averages, momentum, oscillators, divergence, and volatility
7. Bullish/bearish scenarios, invalidation levels, and risk notes

Core principle:

> Read price structure first, indicators second. Define risk before direction.

## Supported Analysis Methods

- Dow Theory trend classification
- Multi-timeframe analysis
- Support and resistance
- Trendlines and price channels
- Gaps and key reversal bars
- Reversal patterns: head-and-shoulders, double top/bottom, triple top/bottom, rounding formations
- Continuation patterns: triangles, rectangles, flags, pennants, wedges
- Volume and OBV analysis
- Open interest interpretation for futures/options data
- Moving averages: SMA/EMA and crossover context
- Donchian-style price channels
- RSI, MACD, stochastic/KD/KDJ-style momentum interpretation
- ROC and momentum
- ATR volatility/risk framing
- Divergence analysis
- Fibonacci retracements/extensions
- Point-and-figure logic
- Elliott Wave and cycle context, used conservatively
- Scenario planning and invalidation levels

## Repository Structure

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── analysis_template.md
│   ├── indicator_playbook.md
│   ├── murphy_knowledge_graph.json
│   └── patterns_and_structure.md
└── scripts/
    └── ta_signals.py
```

## Resources

- `SKILL.md`: Main skill instructions and trigger description.
- `references/murphy_knowledge_graph.json`: Condensed knowledge graph derived from John J. Murphy's technical-analysis framework.
- `references/indicator_playbook.md`: Indicator interpretation guide.
- `references/patterns_and_structure.md`: Price structure and chart-pattern guide.
- `references/analysis_template.md`: Output templates for chart reports and trade plans.
- `scripts/ta_signals.py`: Standard-library Python script for OHLCV/OHLCVI indicator calculation.

## OHLCV Script Usage

The script expects a CSV with at least a close column. It works better with open, high, low, close, volume, and open_interest.

```bash
python scripts/ta_signals.py data.csv
python scripts/ta_signals.py data.csv --json
python scripts/ta_signals.py data.csv --lookback 120 --json
```

Accepted column aliases include:

- `date`, `time`, `timestamp`, `datetime`
- `open`, `o`
- `high`, `h`
- `low`, `l`
- `close`, `c`, `adj_close`, `adjclose`, `last`, `price`
- `volume`, `vol`, `v`
- `open_interest`, `openinterest`, `oi`, `open_int`

The script calculates:

- SMA 20/50/200
- EMA 12/26
- RSI 14
- Stochastic %K/%D
- MACD, signal, histogram
- ROC 10
- ATR 14
- OBV
- 20-period high/low channel
- Recent pivots
- Basic open-interest interpretation when OI exists

## Example Prompt

```text
Use $technical-analysis-chart-reading to analyze this BTC hourly chart with trend, support/resistance, volume, RSI, MACD, KDJ, ATR, and scenario planning.
```

```text
Use $technical-analysis-chart-reading to analyze this OHLCV CSV and produce bullish, bearish, and invalidation scenarios.
```

## Output Style

A good analysis should include:

- Instrument and timeframe
- Data freshness
- Trend and market structure
- Key support/resistance
- Pattern candidate, if any
- Volume or OI confirmation
- Indicator evidence
- Conflicting evidence
- Bullish and bearish triggers
- Invalidation level
- Risk note

## Risk Notice

This repository is for technical-analysis workflow support. It is not investment advice.

Technical analysis can fail, especially in event-driven, illiquid, manipulated, or regime-shifting markets. Indicator signals should not be used without price structure, timeframe context, and risk management.
