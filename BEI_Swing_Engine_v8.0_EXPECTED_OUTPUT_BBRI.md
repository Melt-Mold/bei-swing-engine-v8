# BBRI Technical Analysis Report

**Expected Output from BEI Swing Engine v8.0 — Fixture Test BBRI 2026-08-21**

---

## Executive Summary

| Field | Value |
|---|---|
| **Ticker** | BBRI |
| **Analysis Date** | 2026-08-21 |
| **Data Cutoff** | 2026-08-21 |
| **Period** | [start] to 2026-08-21 ([N] bars) |
| **Horizon** | SWING (1 day – 4 weeks) |
| **Direction Parameter** | BOTH |
| **Position Status** | UNKNOWN |
| **Modal** | Rp 10,000,000 |
| **Risk** | 2% |
| **Last Close** | 3,230 |

| Field | Value |
|---|---|
| **Decision (Top-level)** | WAIT |
| **Reason** | UNKNOWN position — branches differ; confirm position status to collapse. |
| **Thesis** | BULLISH |
| **Thesis Basis** | Structure bullish; Close > EMA9/SMA20/SMA50; ADX > 25; +DI > -DI. |
| **Evidence State** | Alignment |
| **Confluence State** | HIGH (11/16 bullish factors) |
| **Primary Setup** | Continuation / Breakout — TRIGGERED |
| **Setup Direction** | LONG |
| **Tradeability** | TRADEABLE_WITH_WARNING |
| **Warnings** | SMA200 acts as long-term resistance (3,422); Weinstein Stage 4 (weekly declining); R/R marginal. |

---

## 1. Market Context

| Instrument | Regime | Reason |
|---|---|---|
| IHSG / JKSE | N/A | No IHSG/JKSE data uploaded. Stock-specific decision is unaffected. |

---

## 2. Market Structure

| Element | Value |
|---|---|
| **Trend State** | Uptrend (daily) |
| **Protected Low** | Latest HL at ~3,000 (hypothetical) |
| **Protected High** | Latest LH invalidated |
| **BOS** | Bullish BOS active — Close > protected high |
| **CHoCH** | None |
| **Swing Structure** | HH/HL sequence intact |

---

## 3. Technical Indicators

> **Badge Legend:** ✓ = Bullish Confluence | ✗ = Bearish Confluence | ○ = Neutral | ⚡ Div = Divergence Alert | (no badge) = Not a Confluence Factor

| Category | Indicator | Value | Signal | Interpretation | Standard / Reference |
|---|---|---:|---|---|---|
| Trend | MA Alignment | Mixed | — | EMA9>SMA20>SMA50 but <SMA200; intermediate bullish, long-term resistance | Bullish alignment requires all MAs stacked |
| Trend | Trend Classification | Uptrend | ✓ | Price above EMA9/SMA20/SMA50 with rising structure | Higher highs & higher lows = uptrend |
| Trend | Multi-TF Monthly | Up | — | Monthly close trend positive | Monthly context |
| Trend | Multi-TF Weekly | Sideways | — | Weekly consolidation around MA30w | Weekly context |
| Trend | Multi-TF Daily | Up | — | Daily higher highs / higher lows | Daily context |
| Trend | Weinstein Stage | Stage 4 (Declining) | ✗ | Close < MA30w, slope -2.48% | Stage 2 = bullish, Stage 4 = bearish |
| Trend | EMA9 | 3,121.87 | ✓ | Close > EMA9 | Price > EMA9 = short-term bullish |
| Trend | SMA20 | 3,056.50 | ✓ | Close > SMA20 | Price > SMA20 = primary swing bullish |
| Trend | SMA50 | 2,943.60 | ✓ | Close > SMA50 | Price > SMA50 = intermediate bullish |
| Trend | SMA200 | 3,422.15 | ✗ | Close < SMA200 | Price < SMA200 = long-term resistance |
| Trend | ADX(14) | 25.49 | — | Trend strength present (>25) | ADX > 25 = stronger trend reference |
| Trend | +DI(14) | 35.26 | — | Bullish directional pressure dominant | +DI > -DI = bullish pressure |
| Trend | -DI(14) | 13.74 | — | Bearish directional pressure weak | -DI < +DI = bearish pressure weak |
| Trend | Supertrend(10,3) | 3,020.00 | — | Bullish (Close > Supertrend) | Close > Supertrend = uptrend |
| Trend | Parabolic SAR | 3,010.00 | — | SAR below price | SAR below price = bullish |
| Momentum | RSI(14) | 67.30 | ✓ | Momentum bullish, approaching overbought | RSI > 50 = positive momentum |
| Momentum | MACD(12,26,9) | 59.34 vs 51.32 | ✓ | MACD Line > Signal, histogram positive | Line > Signal = bullish momentum |
| Momentum | Stochastic %K(14,3) | 72.50 | — | Stochastic in upper zone | >80 overbought reference |
| Momentum | Stochastic %D(14,3) | 68.20 | — | %D below %K | Bearish short-term crossover reference |
| Momentum | ROC(20) | +8.03% | ✓ | Strong positive 20-bar momentum | ROC > +5% = strong positive |
| Momentum | MFI(14) | 67.15 | — | Money flow positive | 0–100 range |
| Volatility | ATR(14) | 70.79 | — | Normal volatility | ATR measures price range |
| Volatility | ATR% | 2.19% | ○ | Normal regime (1.5%–4.0%) | ATR% = (ATR/Close)×100 |
| Volatility | BB Upper(20,2σ) | 3,350.00 | — | Upper band resistance | Mid + 2σ |
| Volatility | BB Mid(20,2σ) | 3,100.00 | — | 20-day average | SMA20 |
| Volatility | BB Lower(20,2σ) | 2,850.00 | — | Lower band support | Mid − 2σ |
| Volume | Volume vs MA20 | 1.84× | ✓ | Volume well above 20-day average | >1.0× = elevated interest |
| Volume | OBV 20-bar chg | +7.03% | ✓ | OBV rising over 20 bars | Rising OBV = accumulation flow |
| Volume | CMF(20) | +0.1771 | ✓ | Strong buying pressure | CMF > +0.10 = accumulation |
| Volume | Volume Synthesis | Accumulation (Medium) | ✓ | OBV Rising + CMF>+0.10 + ratio_up=1.10× | ratio_up>1.0 = accumulation medium |
| Structure | Ichimoku Tenkan(9) | 3,080.00 | — | Short-term Ichimoku line | (HH9+LL9)/2 |
| Structure | Ichimoku Kijun(26) | 3,020.00 | — | Medium-term Ichimoku line | (HH26+LL26)/2 |
| Structure | Ichimoku Senkou A | 3,050.00 | — | Leading span A | (Tenkan+Kijun)/2 |
| Structure | Ichimoku Senkou B(52) | 2,980.00 | — | Leading span B | (HH52+LL52)/2 |
| Structure | Ichimoku Chikou | 3,230.00 | — | Lagging span at close | Close shifted -26 |
| Structure | Divergence Scan | None | — | No significant divergence detected | Divergence = alert, not signal |
| Structure | Candlestick (Tier 1) | Bullish Marubozu | — | Strong bullish close on last bar | Single-bar pattern |
| Structure | Chart Patterns (Tier 2) | Ascending Triangle (Developing) | — | Higher lows, flat resistance | Pattern context |
| Weekly | MA20 Weekly | 3,150.00 | — | Weekly short-term MA | SMA20 weekly close |
| Weekly | MA50 Weekly | 3,200.00 | — | Weekly intermediate MA | SMA50 weekly close |
| Weekly | RSI Weekly | 48.50 | — | Weekly RSI near midpoint | Weekly momentum |
| Weekly | MACD Weekly | -5.20 vs -8.10 | — | Weekly MACD above signal but negative | Weekly momentum improving |

---

## 4. Key Levels

### 4.1 Pivot Points (Classic)

*Last completed bar: 2026-08-20 (H=3,140; L=3,090; C_prev=3,080)*

| Level | Price | Type |
|---|---:|---|
| R3 | 3,166.67 | Resistance 3 |
| R2 | 3,133.33 | Resistance 2 |
| R1 | 3,116.67 | Resistance 1 |
| PP | 3,103.33 | Pivot Point |
| S1 | 3,086.67 | Support 1 |
| S2 | 3,070.00 | Support 2 |
| S3 | 3,036.67 | Support 3 |

### 4.2 Structural Support / Resistance

| Level | Price | Type | Source |
|---|---:|---|---|
| R2 | 3,422 | Long-term resistance | SMA200 |
| R1 | 3,350 | Near-term resistance | BB Upper |
| — | 3,230 | Current close | — |
| S1 | 3,090 | Near-term support | Last completed low |
| S2 | 3,056 | Swing support | SMA20 |
| S3 | 2,944 | Intermediate support | SMA50 |

### 4.3 Fibonacci

*Hypothetical anchor: Low 2,944 (SMA50) → High 3,350 (BB Upper)*

| Level | Price |
|---|---:|
| 38.2% | 3,194.92 |
| 50.0% | 3,147.00 |
| 61.8% | 3,099.08 |
| Extension 127.2% | 3,460.32 |
| Extension 161.8% | 3,606.48 |

---

## 5. Pattern & Divergence Alerts

| Type | Status | Detail |
|---|---|---|
| Divergence (RSI) | None | No price/RSI divergence |
| Divergence (MACD) | None | No price/MACD divergence |
| Divergence (OBV) | None | No price/OBV divergence |
| Ascending Triangle | Developing | Higher lows, resistance near 3,350 |

---

## 6. Confluence & Conflict Analysis

### Bullish Evidence Dimensions
1. **Structure:** HH/HL intact, bullish BOS.
2. **Trend:** Close > EMA9/SMA20/SMA50; ADX > 25; +DI > -DI.
3. **Momentum:** RSI > 50; MACD Line > Signal; ROC > +5%.
4. **Participation:** Volume 1.84×; OBV rising; CMF +0.1771; Volume Synthesis Accumulation.
5. **Price Location:** Close above key MAs; near support zone.

### Bearish / Caution Evidence
1. **Long-term Trend:** Close < SMA200 (3,422).
2. **Weekly Context:** Weinstein Stage 4, weekly slope -2.48%.
3. **Overbought Proximity:** RSI 67.30 near 70.

### Conclusion
- **Confluence State:** HIGH
- **Evidence State:** Alignment with caution
- **Technical Thesis:** BULLISH
- **Caveat:** Long-term resistance at SMA200 and weekly Stage 4 require careful risk management.

---

## 7. Setup Status

| Field | Value |
|---|---|
| **Primary Setup** | Continuation / Breakout — TRIGGERED |
| **Direction** | LONG |
| **Trigger Date** | 2026-08-21 |
| **Trigger Price** | 3,230 |
| **Candidate Date** | 2026-08-18 |
| **Confirmation Date** | 2026-08-20 |
| **Invalidation Price** | 3,088 (ATR-based SL) / structural HL ~3,000 |
| **Basis** | Structure, Momentum, Participation |
| **Warnings** | Near SMA200 resistance; weekly Stage 4 |

---

## 8. Trading Plan

| Component | Value |
|---|---:|
| **Direction** | LONG |
| **Entry** | 3,230 |
| **Stop Loss** | 3,088 |
| **SL Basis** | Entry − 2×ATR14 = 3,230 − 141.58 |
| **TP1** | 3,450 |
| **TP1 Basis** | Structural resistance cluster (SMA200 + Fib 127.2%) |
| **TP2** | 3,606 |
| **TP2 Basis** | Fibonacci 161.8% extension |
| **R/R** | 1.55 |
| **R/R Status** | VALID |
| **Lots** | 14 |
| **Final Shares** | 1,400 |
| **Modal Terpakai** | Rp 4,522,000 |
| **Risk Budget** | Rp 200,000 |
| **Actual Risk** | Rp 198,800 |
| **Actual Risk %** | 1.99% |
| **Invalidation** | Close < 3,088 or violation of structural HL |

---

## 9. Decision Trace

| Gate | Result | Detail |
|---|---|---|
| G0 Data | OK | 250 bars received, sufficient for all indicators |
| G1 Direction | OK | BOTH permits LONG setup |
| G2 Structural Veto | Pass | No active structural invalidation vs LONG |
| G3 Setup Actionability | OK | Continuation/Breakout TRIGGERED |
| G4 Evidence Sufficiency | OK | ≥2 dimensions (Structure + Momentum + Participation) |
| G5 Tradeability | WITH_WARNING | R/R 1.55 valid; warnings: SMA200 resistance, Stage 4 |
| G6 Position Mapping | UNKNOWN | Branches differ |

### Branch Outputs

| Branch | Decision | Reason |
|---|---|---|
| **If NO_POSITION** | BUY (BUY-02) | Triggered setup + strong confluence + valid R/R |
| **If EXISTING_POSITION** | HOLD (HOLD-02) | Thesis intact, no exit trigger, warnings present |

### Top-Level Resolution

> **WAIT (UNKNOWN position)** — If you hold no position, this is a BUY candidate (BUY-02). If you already hold a LONG position aligned with the bullish thesis, HOLD (HOLD-02). Please confirm your position status to collapse this branch.

**Reason Codes:** BUY-02, HOLD-02, WAIT-01
**Warnings:** SMA200 resistance, Weinstein Stage 4, RSI near overbought
**Vetoes Triggered:** None

---

## 10. Disclaimer

> Analisa ini bersifat edukatif untuk pembelajaran analisis teknikal, BUKAN rekomendasi investasi atau ajakan untuk membeli/menjual efek. Keputusan investasi dan risiko sepenuhnya menjadi tanggung jawab pengguna. Hasil masa lalu tidak menjamin hasil di masa depan.

---

**END OF EXPECTED OUTPUT — BBRI 2026-08-21**
