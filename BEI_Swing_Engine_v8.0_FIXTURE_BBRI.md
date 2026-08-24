# Fixture Test: BBRI 2026-08-21

**Purpose:** Validate BEI Swing Engine v8.0 draft prompt against known reference values.  
**Ticker:** BBRI  
**Analysis Date:** 2026-08-21  
**Data Cutoff:** 2026-08-21 (last bar)  
**Last Completed Bar for Pivot:** 2026-08-20  
**Horizon:** SWING  
**Direction:** BOTH  
**Position:** UNKNOWN  
**Modal:** Rp 10,000,000  
**Risk:** 2%  
**IHSG:** None (not uploaded)  

---

## Input Parameters

```
MODE=A
HORIZON=SWING
DIRECTION=BOTH
POSITION=UNKNOWN
MODAL=10000000
RISK=2
OUTPUT=Chat
IHSG=None
```

---

## Reference Values (from SwingFlow v7)

### Price Data
- **Close:** 3,230
- **Last Completed Bar (2026-08-20):** H=3,140 | L=3,090 | C_prev (Aug 19 close)=3,080

### Trend Indicators
- **EMA9:** 3,121.87
- **SMA20:** 3,056.50
- **SMA50:** 2,943.60
- **SMA200:** 3,422.15
- **ADX(14):** 25.49
- **+DI:** 35.26
- **-DI:** 13.74

### Momentum Indicators
- **RSI(14):** 67.30
- **MACD Line:** 59.34
- **MACD Signal:** 51.32
- **Stochastic %K:** — (not provided)
- **Stochastic %D:** — (not provided)
- **ROC(20):** +8.03%
- **MFI(14):** 67.15

### Volume Indicators
- **Volume vs MA20:** 1.84×
- **OBV 20-bar change:** +7.03%
- **CMF(20):** +0.1771
- **Volume Synthesis:** Accumulation (Medium)
- **ratio_up:** 1.10×
- **ratio_down:** — (not provided)

### Volatility
- **ATR(14):** 70.79
- **ATR%:** 2.19%
- **BB Upper / Mid / Lower:** — (not provided)

### Weekly / Weinstein
- **Weekly MA30w:** 3,237.33
- **Weekly Slope:** -2.48%
- **Weinstein Stage:** Stage 4 (Declining)

### 3M Return
- **+6.95%**

### Pivot Points
- **PP:** 3,103.33
- **R1:** 3,116.67
- **R2:** 3,133.33
- **R3:** 3,166.67
- **S1:** 3,086.67
- **S2:** 3,070.00
- **S3:** 3,036.67

### Expected Confluence
- **11/16 bullish factors**
- **Confluence Quality:** HIGH
- **Technical Bias / Thesis:** Bullish

### Expected Setup (Hypothetical)
- **Setup Type:** Continuation or Breakout
- **Setup Status:** TRIGGERED
- **Direction:** LONG
- **Entry:** 3,230 (current close)
- **SL:** 3,088 (Entry − 2×ATR14 = 3,230 − 141.58)
- **TP1:** 3,166.67 (R3 pivot) or nearest structural resistance
- **TP2:** next major resistance
- **R/R:** depends on TP1

### Position Sizing
- **Risk Budget:** Rp 200,000 (10jt × 2%)
- **Risk per Share:** 142
- **Raw Shares:** 1,408.45
- **Lots:** 14
- **Final Shares:** 1,400
- **Actual Risk:** Rp 198,800 (1.988%)

---

## Acceptance Criteria

### AC1: Format Compliance
- [ ] Output contains exactly 42 indicator rows.
- [ ] Each row has exactly 6 columns.
- [ ] Column headers match: `| Category | Indicator | Value | Signal | Interpretation | Standard / Reference |`

### AC2: Badge Compliance
- [ ] Exactly 16 confluence factors have badges.
- [ ] ADX, +DI, -DI, Supertrend, SAR, Stochastic %K, Stochastic %D, MFI, ATR, BB Upper/Mid/Lower, Ichimoku rows, Candlestick, Chart Patterns, Weekly rows have NO badge.
- [ ] RSI, MACD, OBV rows include `⚡ Div` only if divergence detected.

### AC3: Calculation Accuracy
- [ ] EMA9 = 3,121.87 (±0.01)
- [ ] SMA20 = 3,056.50 (±0.01)
- [ ] SMA50 = 2,943.60 (±0.01)
- [ ] SMA200 = 3,422.15 (±0.01)
- [ ] ADX = 25.49 (±0.05)
- [ ] +DI = 35.26 (±0.05)
- [ ] -DI = 13.74 (±0.05)
- [ ] RSI = 67.30 (±0.05)
- [ ] MACD Line = 59.34 (±0.05)
- [ ] MACD Signal = 51.32 (±0.05)
- [ ] ROC = +8.03% (±0.05%)
- [ ] CMF = +0.1771 (±0.0005)
- [ ] OBV chg = +7.03% (±0.05%)
- [ ] Volume vs MA20 = 1.84× (±0.01)
- [ ] ATR = 70.79 (±0.05)
- [ ] ATR% = 2.19% (±0.05%)
- [ ] Weinstein Stage = Stage 4
- [ ] 3M return = +6.95% (±0.05%)
- [ ] Pivot PP = 3,103.33 (±0.01)
- [ ] Pivot R3 = 3,166.67 (±0.01)
- [ ] Volume Synthesis = Accumulation (Medium)

### AC4: Decision Logic
- [ ] Thesis = BULLISH (structure bullish, Close > EMA9/SMA20/SMA50, ADX > 25, +DI > -DI).
- [ ] Evidence state = Alignment or Complementary (not Conflict).
- [ ] Confluence state = Strong or Moderate.
- [ ] Setup = Continuation or Breakout, TRIGGERED.
- [ ] Tradeability = TRADEABLE or TRADEABLE_WITH_WARNING.
- [ ] Decision for NO_POSITION branch = BUY.
- [ ] Decision for EXISTING_POSITION branch = HOLD.
- [ ] Top-level decision for UNKNOWN position = WAIT + dual-branch detail.

### AC5: Risk & Trade Plan
- [ ] SL = 3,088 (Entry − 2×ATR14).
- [ ] SL < Entry.
- [ ] TP1 > Entry.
- [ ] R/R computed correctly.
- [ ] Position sizing: 14 lots, 1,400 shares, actual risk ~Rp 198,800 (1.99%).

### AC6: Anti-Fabrication
- [ ] No values invented.
- [ ] Every number traceable to input or formula.
- [ ] N/A includes reason where applicable.

### AC7: Output Rules
- [ ] No BUY/SELL/HOLD as final investment advice language.
- [ ] Disclaimer included.
- [ ] IHSG section = N/A with reason if no IHSG data.
- [ ] Market Regime does not alter stock decision.

---

## Notes

- This fixture assumes the uploaded CSV actually produces the reference values above.
- If the uploaded CSV differs, the output will differ accordingly — this is expected and correct behavior.
- The key validation is that the prompt **correctly calculates** from the CSV and **logically derives** decision states, not that it matches these reference values regardless of input.

---

**END OF FIXTURE**
