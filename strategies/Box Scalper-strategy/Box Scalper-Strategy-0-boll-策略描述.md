# Box Scalper 策略描述（BOLL版本）

## 策略概述

Box Scalper（箱体剥头皮策略）是一个基于多个技术指标组合的短线交易策略。本版本使用**布林带（BOLL）代替Box**，通过SSL通道、QQE动量指标、ADX趋势强度指标和布林带突破指标的综合判断，在趋势明确时进行快速进出场交易。

---

## 核心指标

### 1. ADX (Average Directional Index) - 平均趋向指标

**作用**：衡量趋势强度，过滤震荡市场中的假信号

**参数设置**：
- `ADX_Length`：ADX计算周期，默认14
- `ADX_Smooth`：ADX平滑周期，默认14
- `ADX_Range`：震荡市场阈值，默认25（未在代码中使用）
- `ADX_Trend`：趋势市场阈值，默认50

**应用逻辑**：
- 当 `ADX > ADX_Trend` 时，表示市场处于强趋势状态
- 在周末交易时，如果 `ADX > ADX_Trend`，仍然允许交易

---

### 2. SSL (SSL Channel) - SSL通道指标

**作用**：判断趋势方向，作为入场的基础条件

**计算公式**：
```
HH = HMA(high, length)  // 高点的Hull移动平均
LL = HMA(low, length)   // 低点的Hull移动平均
HLV = close > HH ? 1 : close < LL ? -1 : HLV[1]  // 趋势方向
SSL = HLV < 0 ? HH : LL  // SSL线
```

**参数设置**：
- `SSL_Length`：SSL计算周期，默认55

**应用逻辑**：
- 当 `close > SSL` 时，表示多头趋势
- 当 `close < SSL` 时，表示空头趋势
- SSL颜色：`close > SSL` 为青色（#00c3ff），`close < SSL` 为红色（#ff0062）

---

### 3. BOX (Squeeze Box) - 布林带箱体

**作用**：识别价格突破，提供额外的入场信号

**计算公式**：
```
BOX_basis = SMA(close, BOX_Period)  // 布林带中轨
BOX_dev = BOX_Deviation * STDEV(close, BOX_Period)  // 标准差
BOX_bh = BOX_basis + BOX_dev  // 布林带上轨（Box High）
BOX_bl = BOX_basis - BOX_dev  // 布林带下轨（Box Low）
```

**参数设置**：
- `BOX_Period`：布林带周期，默认24
- `BOX_Deviation`：标准差倍数，默认3
- `BOX_Threshold`：阈值，默认50（未在代码中使用）

**应用逻辑**：
- 当 `close > BOX_basis` 时，Box填充为绿色
- 当 `close < BOX_basis` 时，Box填充为红色
- 价格上穿 `BOX_bl` 可作为做多信号
- 价格下穿 `BOX_bh` 可作为做空信号

---

### 4. QQE (Quantitative Qualitative Estimation) - 定量定性估计指标

**作用**：识别动量变化，判断趋势转折点

**参数设置**：
- `QQE_Length`：RSI周期，默认14
- `QQE_Mtf`：多时间框架倍数，默认5
- `QQE_Smooth`：RSI平滑周期，默认8
- `QQE_Mult`：QQE倍数，默认4.3

**信号定义**：
- `QQE_up`：QQE上涨信号（`dn_ema > dn[1] and dn_ema[1] <= dn[2]`）
- `QQE_dn`：QQE下跌信号（`up_ema < up[1] and up_ema[1] >= up[2]`）
- `QQE_direction`：QQE方向（1=上涨，-1=下跌）

**强制信号检测**：
- `qqe_was_force_up`：强制上涨信号（QQE下跌时，RSI上穿时间晚于QQE上涨时间）
- `qqe_was_force_dn`：强制下跌信号（QQE上涨时，RSI下穿时间晚于QQE下跌时间）

**参数设置（QQE ZONE）**：
- `ZON_Length`：RSI周期，默认5
- `ZON_Upper`：RSI上阈值，默认75
- `ZON_Lower`：RSI下阈值，默认22

---

### 5. ZigZag - 锯齿线

**作用**：识别关键支撑和阻力位

**计算逻辑**：
- 基于 `QQE_direction` 计算ZigZag转折点
- 当 `QQE_up` 时，记录低点
- 当 `QQE_dn` 时，记录高点

**支撑阻力**：
- `zz_top`：阻力位（基于ZigZag高点和当前高点）
- `zz_bot`：支撑位（基于ZigZag低点和当前低点）

---

## 交易规则

### ====== 做多规则 ======

#### 入场条件

**条件1（主要条件）**：
- `close > SSL`（价格在SSL通道上方）
- `QQE_up = true`（QQE上涨信号）
- `not qqe_was_force_dn`（不是强制下跌信号）
- `(week != 7 and week != 1 or ADX > ADX_Trend)`（不是周末，或ADX > 趋势阈值）

**条件2（突破条件）**：
- `close > SSL`（价格在SSL通道上方）
- `ta.crossover(close, BOX_bl)`（价格上穿布林带下轨）

**开仓条件**：
- 当前无持仓或持空仓（`strategy.position_size <= 0`）
- 允许做多（`PS_Expect != 'SHORT'`）
- 在回测时间窗口内（`window = true`）

#### 开仓设置

- **开仓价**：当前收盘价（`close`）
- **仓位大小**：
  - 如果 `PS_Mode == 'Capital'`：`(strategy.initial_capital / close) * (PS_Initial / 100)`
  - 如果 `PS_Mode == 'Equity'`：`(strategy.equity / close) * (PS_Initial / 100)`
- **止损价**：`close * (100 - TSL_SL2) / 100`
- **止盈目标价**：`strategy.position_avg_price * (1 + TP_Ts2/100)`

#### 止损

- **固定止损**：通过 `strategy.exit()` 设置，止损价为开仓价的 `(100 - TSL_SL2)%`
- **止损订单ID**：`'CL-L'`

#### 止盈

**止盈目标价格**：`L_TP = strategy.position_avg_price * (1 + TP_Ts2/100)`

**止盈条件**：

1. **趋势止盈**（优先）：
   - `close > L_TP`（价格超过止盈目标价）
   - `moveHigh = true`（收盘价下穿最近20个周期内最高枢轴点的99%）
   - 平仓注释：`"多头趋势止盈"`

2. **保护性止盈**（备选）：
   - `close > L_TP`（价格超过止盈目标价）
   - `L_reversal = true`（收盘价下穿止盈目标价）
   - 平仓注释：`"多头趋势不明显保护性止盈"`

**枢轴点计算**：
- `pivotsizing = 20`（查找周期数）
- `pivotLookup = 1`（枢轴点左右K线数）
- `highest = ta.highest(top, pivotsizing)`（最近20个周期内的最高枢轴点）
- `moveHigh = ta.crossunder(close, highest*0.99)`（价格下穿最高点的99%）

#### 反向平仓

- 当 `PS_Expect == 'LONG'` 且 `BEAR` 信号出现时，立即平仓
- 平仓注释：`'CL-L'`

---

### ====== 做空规则 ======

#### 入场条件

**条件1（主要条件）**：
- `close < SSL`（价格在SSL通道下方）
- `QQE_dn = true`（QQE下跌信号）
- `not qqe_was_force_up`（不是强制上涨信号）
- `(week != 7 and week != 1 or ADX > ADX_Trend)`（不是周末，或ADX > 趋势阈值）

**条件2（突破条件）**：
- `close < SSL`（价格在SSL通道下方）
- `ta.crossunder(close, BOX_bh)`（价格下穿布林带上轨）

**开仓条件**：
- 当前无持仓或持多仓（`strategy.position_size >= 0`）
- 允许做空（`PS_Expect != 'LONG'`）
- 在回测时间窗口内（`window = true`）

#### 开仓设置

- **开仓价**：当前收盘价（`close`）
- **仓位大小**：
  - 如果 `PS_Mode == 'Capital'`：`(strategy.initial_capital / close) * (PS_Initial / 100)`
  - 如果 `PS_Mode == 'Equity'`：`(strategy.equity / close) * (PS_Initial / 100)`
- **止损价**：`close * (100 + TSL_SL2) / 100`
- **止盈目标价**：`strategy.position_avg_price * (1 - TP_Ts2/100)`

#### 止损

- **固定止损**：通过 `strategy.exit()` 设置，止损价为开仓价的 `(100 + TSL_SL2)%`
- **止损订单ID**：`'CL-S'`

#### 止盈

**止盈目标价格**：`S_TP = strategy.position_avg_price * (1 - TP_Ts2/100)`

**止盈条件**：

1. **趋势止盈**（优先）：
   - `close < S_TP`（价格低于止盈目标价）
   - `moveBottom = true`（收盘价上穿最近20个周期内最低枢轴点的99%）
   - 平仓注释：`"空头趋势止盈"`

2. **保护性止盈**（备选）：
   - `close < S_TP`（价格低于止盈目标价）
   - `S_reversal = true`（收盘价上穿止盈目标价）
   - 平仓注释：`"空头趋势不明显保护性止盈"`

**枢轴点计算**：
- `pivotsizing = 20`（查找周期数）
- `pivotLookup = 1`（枢轴点左右K线数）
- `bottomst = ta.lowest(bottom, pivotsizing)`（最近20个周期内的最低枢轴点）
- `moveBottom = ta.crossunder(close, bottomst*0.99)`（价格上穿最低点的99%）

#### 反向平仓

- 当 `PS_Expect == 'SHORT'` 且 `BULL` 信号出现时，立即平仓
- 平仓注释：`'CL-S'`

---

## 参数设置

### ADX参数
- **Length**：ADX计算周期，默认14
- **Smooth**：ADX平滑周期，默认14
- **Range**：震荡市场阈值，默认25（未使用）
- **Trend**：趋势市场阈值，默认50

### SSL参数
- **Length**：SSL计算周期，默认55

### BOX参数（布林带）
- **Periods**：布林带周期，默认24
- **Deviation**：标准差倍数，默认3
- **Threshold**：阈值，默认50（未使用）

### QQE参数
- **RSI Length**：RSI周期，默认14
- **MTF Mult**：多时间框架倍数，默认5
- **RSI Smooth**：RSI平滑周期，默认8
- **QQE Mult**：QQE倍数，默认4.3

### QQE ZONE参数
- **Length**：RSI周期，默认5
- **Upper**：RSI上阈值，默认75
- **Lower**：RSI下阈值，默认22

### 仓位管理参数
- **Expect**：交易方向，选项：`'BOTH'`（双向）、`'LONG'`（仅做多）、`'SHORT'`（仅做空），默认`'BOTH'`
- **Mode**：仓位计算模式，选项：`'Capital'`（基于初始资金）、`'Equity'`（基于当前权益），默认`'Capital'`
- **Initial(%)**：初始仓位百分比，默认100

### 止损参数
- **Stop Loss Max(%)**：最大止损百分比，默认9.9%

### 止盈参数
- **Profit Target 2(%)**：止盈目标百分比，默认1.0%

### 回测参数
- **Start**：回测开始时间，默认2020-01-01
- **Finish**：回测结束时间，默认2030-12-31

---

## 特殊逻辑

### 周末过滤

- 默认情况下，周末（`week == 7` 或 `week == 1`）不交易
- 但如果 `ADX > ADX_Trend`（强趋势），周末仍然允许交易

### 强制信号过滤

- `qqe_was_force_up`：当QQE下跌信号出现时，如果RSI上穿时间晚于QQE上涨时间，则认为是强制上涨信号，做空时需排除
- `qqe_was_force_dn`：当QQE上涨信号出现时，如果RSI下穿时间晚于QQE下跌时间，则认为是强制下跌信号，做多时需排除

### 枢轴点止盈

- 使用 `ta.pivothigh()` 和 `ta.pivotlow()` 识别局部高点和低点
- 跟踪最近20个周期内的最高/最低枢轴点
- 当价格突破止盈目标价后，如果价格回撤到枢轴点的99%，则触发趋势止盈

---

## 策略特点

### 优点

1. **多指标确认**：结合SSL、QQE、ADX和布林带，提高信号可靠性
2. **趋势过滤**：通过ADX过滤震荡市场，只在强趋势时交易
3. **灵活入场**：提供两种入场方式（QQE信号和布林带突破）
4. **智能止盈**：基于枢轴点的趋势止盈，能够捕捉更多利润
5. **周末保护**：默认周末不交易，避免低流动性风险

### 风险提示

1. **短线策略**：止盈目标较小（默认1%），适合短线交易
2. **止损较大**：默认止损9.9%，单笔亏损可能较大
3. **参数敏感**：多个指标参数需要根据市场调整
4. **震荡市场**：在震荡市场中可能产生较多假信号

---

## 使用建议

1. **参数优化**：根据交易品种和时间周期调整各指标参数
2. **风险控制**：建议根据账户大小调整止损和仓位百分比
3. **市场选择**：更适合趋势明显的市场，震荡市场需谨慎
4. **时间周期**：建议在15分钟及以上周期使用，避免噪音干扰
5. **回测验证**：使用前务必进行充分回测，验证策略有效性

---

## 版本说明

- **版本**：Box Scalper-Strategy-0-boll.pine
- **特点**：使用布林带（BOLL）代替Box指标
- **Pine Script版本**：v5

