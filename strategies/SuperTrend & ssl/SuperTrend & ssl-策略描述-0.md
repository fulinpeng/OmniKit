# SuperTrend & SSL 策略描述

## 策略概述

SuperTrend & SSL 策略是一个多指标组合的趋势跟踪策略，结合了 SuperTrend、SSL通道、Range Filter、WaveTrend、机器学习分类等多个技术指标，通过多重确认机制识别趋势突破点，并采用动态止盈止损管理仓位。

---

## 核心指标

### 1. Range Filter - 范围过滤器

**作用**：过滤震荡市场，识别趋势方向

**参数设置**：
- `rng_src`：数据源，默认 `close`
- `rng_per`：周期，默认60
- `rng_qty`：倍数，默认2.5

**计算逻辑**：
- 计算自适应通道（AC）：基于价格变化的EMA平滑
- 生成过滤线（filt）：动态调整的平滑价格线
- 方向判断：`fdir`（1=上涨，-1=下跌）

**应用**：
- `upward`：上涨方向（`fdir == 1`）
- `downward`：下跌方向（`fdir == -1`）
- 用于入场条件的确认

---

### 2. SuperTrend - 超级趋势指标

**作用**：识别趋势方向和趋势反转点

**参数设置**：
- `Periods`：ATR周期，默认9
- `src`：数据源，默认 `hl2`
- `Multiplier`：ATR乘数，默认12
- `changeATR`：切换ATR计算方法，默认true

**计算逻辑**：
```
up = src - Multiplier * atr  // 上升趋势线
dn = src + Multiplier * atr  // 下降趋势线
trend = 1（上升）或 -1（下降）
```

**趋势判断**：
- `trend == 1`：上升趋势（价格在上升趋势线上方）
- `trend == -1`：下降趋势（价格在下降趋势线下方）

**应用**：
- 作为入场条件的基础判断
- 用于止盈止损的触发条件

---

### 3. SSL (SSL Channel) - SSL通道

**作用**：判断趋势方向，识别价格突破

**参数设置**：
- `period`：SSL周期，默认200（未使用）
- `len`：WMA长度，默认200

**计算逻辑**：
```
smaHigh = WMA(high, len)  // 高点WMA
smaLow = WMA(low, len)    // 低点WMA
Hlv = close > smaHigh ? 1 : close < smaLow ? -1 : Hlv[1]  // 趋势方向
sslDown = Hlv < 0 ? smaHigh : smaLow  // SSL下轨
sslUp = Hlv < 0 ? smaLow : smaHigh     // SSL上轨
```

**应用**：
- `maxSSL = max(sslUp, sslDown)`：SSL上轨
- `minSSL = min(sslUp, sslDown)`：SSL下轨
- 用于入场条件的价格位置判断

---

### 4. SSL2 - SSL通道（长周期版本）

**作用**：识别长期趋势方向

**参数设置**：
- `period2 = period * 3`：SSL周期（原值的3倍）
- `len2 = len * 3`：WMA长度（原值的3倍，默认600）

**特点**：
- 周期更长，更平滑
- 适合识别长期趋势
- 使用蓝色和橙色区分于原SSL

---

### 5. WaveTrend - 波动趋势指标

**作用**：识别超买超卖区域，辅助入场判断

**参数设置**：
- `n1`：通道长度，默认10
- `n2`：平均长度，默认21
- `midLevelHigh`：看空门槛线，默认+50
- `midLevelLow`：看多门槛线，默认-50

**计算逻辑**：
```
ap = hlc3
esa = EMA(ap, n1)
d = EMA(|ap - esa|, n1)
ci = (ap - esa) / (0.015 * d)
tci = EMA(ci, n2)
wt1 = tci
wt2 = SMA(wt1, 4)
```

**应用**：
- `wt1 < midLevelLow and wt2 < midLevelLow`：看多条件（超卖区域）
- `wt1 > midLevelHigh and wt2 > midLevelHigh`：看空条件（超买区域）

---

### 6. Fibonacci Bollinger Bands - 斐波那契布林带

**作用**：识别价格极值区域，用于止盈判断

**参数设置**：
- `fbb_length`：周期，默认200
- `fbb_src`：数据源，默认 `hlc3`
- `mult`：倍数，默认3.0

**计算逻辑**：
```
fbb_basis = VWMA(fbb_src, fbb_length)
fbb_dev = mult * STDEV(fbb_src, fbb_length)
upper_6 = fbb_basis + 1.0 * fbb_dev
upper_7 = fbb_basis + 1.414 * fbb_dev
lower_6 = fbb_basis - 1.0 * fbb_dev
lower_7 = fbb_basis - 1.414 * fbb_dev
```

**应用**：
- 用于止盈保护：当价格达到 `upper_7` 或 `lower_7` 时，触发更高比例的止盈保护

---

### 7. DEMA - 双指数移动平均线

**作用**：趋势跟踪辅助指标

**参数设置**：
- `length_short`：短周期，默认20
- `length_log`：长周期，默认144

**计算逻辑**：
```
e1 = EMA(src, length)
e2 = EMA(e1, length)
DEMA = 2 * e1 - e2
```

**应用**：
- 长周期DEMA用于识别长期趋势
- 同时显示SMA(169)作为参考

---

### 8. GMMA - 顾比移动平均线组

**作用**：识别趋势强度和方向（可选显示）

**参数设置**：
- 12条EMA线：3, 5, 8, 10, 12, 15, 30, 35, 40, 45, 50, 60
- 短期组（绿色）：EMA1-6
- 长期组（红色）：EMA7-12

**应用**：
- 通过开关控制是否显示
- 用于趋势确认和可视化

---

### 9. 其他辅助指标

- **Nadaraya-Watson Envelope**：核回归包络线（可选）
- **Machine Learning: Lorentzian Classification**：机器学习分类（可选）
- **Bollinger Bands**：布林带（可选）
- **Anchored VWAP**：锚定VWAP（可选）
- **Swing Highs-Lows & Candle Patterns**：摆动高低点和K线形态（可选）

---

## 交易规则

### ====== 做多规则 ======

#### 入场条件

**条件组合**：`section3Up = section3Up1 and section3Up2`

**section3Up1（价格突破条件）**：
- `trend == 1`（SuperTrend为上升趋势）
- `bool(upward)`（Range Filter为上涨方向）
- `close > open`（当前K线为阳线）
- `close > maxSSL`（收盘价在SSL上轨上方）
- `math.min(low, low[1]) <= maxSSL`（当前或前一根K线的最低价触及或下穿SSL上轨）

**section3Up2（SSL斜率条件）**：
- `(maxSSL - math.max(smaHigh[2], smaLow[2])) / math.max(smaHigh[2], smaLow[2]) > sslRateUp`
- 即：SSL上轨相对于2根K线前的WMA值的上涨幅度 > `sslRateUp`（默认-0.00004）
- 表示SSL通道正在向上倾斜

**开仓条件**：
- 当前无持仓（`not isHoldingPosition`）
- `section3Up = true`

#### 开仓设置

- **开仓价**：当前收盘价（`close`）
- **订单ID**：`'buy'`
- **订单类型**：市价单（`strategy.entry()` 无 `limit` 参数）
- **注释**：`'多'`

#### 止损

**无固定止损**：策略中没有设置初始止损，完全依赖动态止盈止损逻辑

#### 止盈

**止盈触发条件**（`closeUp1`）：

1. **SuperTrend反转止盈**：
   - `close <= minSuper`（收盘价下穿SuperTrend下降趋势线）
   - 或 `upArrivedProfit >= arriveStopProfitCount and high >= maxSuper`（达到指定次数且价格触及SuperTrend上升趋势线）

2. **移动止损触发**：
   - `bool(buystopLossPrice) and close < buystopLossPrice`（价格下穿移动止损价）

**移动止损逻辑**：

1. **第一次触发SuperTrend上升趋势线**：
   - 当 `high >= math.max(up, dn)` 时，`upArrivedProfit += 1`
   - 如果 `upArrivedProfit == 1`，设置移动止损：
     - `buystopLossPrice = entry_price + abs(high - entry_price) * profitProtectRatio`
     - 默认保留10%利润（`profitProtectRatio = 0.1`）

2. **达到Fibonacci上轨**：
   - 当 `high >= upper_7 and upArrivedProfit >= 1` 时，设置移动止损：
     - `buystopLossPrice = entry_price + abs(high - entry_price) * 0.9`
     - 保留90%利润

**平仓注释**：
- `close > entry_price`：`'止盈平多'`
- `close <= entry_price`：`'止损平多'`

---

### ====== 做空规则 ======

#### 入场条件

**条件组合**：`section3Down = section3Down1 and section3Down2`

**section3Down1（价格突破条件）**：
- `trend == -1`（SuperTrend为下降趋势）
- `bool(downward)`（Range Filter为下跌方向）
- `close < open`（当前K线为阴线）
- `close < minSSL`（收盘价在SSL下轨下方）
- `math.max(high, high[1]) >= minSSL`（当前或前一根K线的最高价触及或上穿SSL下轨）

**section3Down2（SSL斜率条件）**：
- `(maxSSL - math.max(smaHigh[2], smaLow[2])) / math.max(smaHigh[2], smaLow[2]) < sslRateDown`
- 即：SSL上轨相对于2根K线前的WMA值的下跌幅度 < `sslRateDown`（默认-0.00008）
- 表示SSL通道正在向下倾斜

**开仓条件**：
- 当前无持仓（`not isHoldingPosition`）
- `section3Down = true`

#### 开仓设置

- **开仓价**：当前收盘价（`close`）
- **订单ID**：`'sell'`
- **订单类型**：市价单（`strategy.entry()` 无 `limit` 参数）
- **注释**：`'空'`

#### 止损

**无固定止损**：策略中没有设置初始止损，完全依赖动态止盈止损逻辑

#### 止盈

**止盈触发条件**（`closeDown1`）：

1. **SuperTrend反转止盈**：
   - `close >= maxSuper`（收盘价上穿SuperTrend上升趋势线）
   - 或 `downArrivedProfit >= arriveStopProfitCount and low <= minSuper`（达到指定次数且价格触及SuperTrend下降趋势线）

2. **移动止损触发**：
   - `bool(sellstopLossPrice) and close > sellstopLossPrice`（价格上穿移动止损价）

**移动止损逻辑**：

1. **第一次触发SuperTrend下降趋势线**：
   - 当 `low <= math.min(up, dn)` 时，`downArrivedProfit += 1`
   - 如果 `downArrivedProfit == 1`，设置移动止损：
     - `sellstopLossPrice = entry_price - abs(low - entry_price) * profitProtectRatio`
     - 默认保留10%利润（`profitProtectRatio = 0.1`）

2. **达到Fibonacci下轨**：
   - 当 `low <= lower_7 and downArrivedProfit >= 1` 时，设置移动止损：
     - `sellstopLossPrice = entry_price - abs(low - entry_price) * 0.9`
     - 保留90%利润

**平仓注释**：
- `close < entry_price`：`'止盈平空'`
- `close >= entry_price`：`'止损平空'`

---

## 参数设置

### Range Filter参数
- **Swing Source**：数据源，默认 `close`
- **Swing Period**：周期，默认60
- **Swing Multiplier**：倍数，默认2.5

### SuperTrend参数
- **SuperTrend ATR 周期**：默认9
- **SuperTrend数据源**：默认 `hl2`
- **SuperTrend ATR 乘数**：默认12
- **切换 ATR 计算方法**：默认true
- **ssl斜率-up**：默认-0.00004
- **ssl斜率-down**：默认-0.00008

### SSL参数
- **SSL Period**：默认200（未使用）
- **SSL WMA Length**：默认200

### SSL2参数
- **自动计算**：`period2 = period * 3`，`len2 = len * 3`

### WaveTrend参数
- **WT Channel Length**：默认10
- **WT Average Length**：默认21
- **看空门槛线 (+50)**：默认50
- **看多门槛线 (-50)**：默认-50

### Fibonacci Bollinger Bands参数
- **fbb_length**：默认200
- **fbb_Source**：默认 `hlc3`
- **fbb_mult**：默认3.0

### DEMA参数
- **短周期 DEMA 长度**：默认20
- **长周期 DEMA 长度**：默认144
- **DEMA数据源**：默认 `hl2`

### GMMA参数
- **启用GMMA指标**：默认false
- **12个EMA周期**：3, 5, 8, 10, 12, 15, 30, 35, 40, 45, 50, 60

### 止盈止损参数
- **止盈保留利润比例**：默认0.1（10%）
- **第几次触发superTrend止盈**：默认3

### 其他可选指标参数
- **showNadarayaWatsonEnvelope**：默认true
- **showBB**：默认false
- **vwap_showVwap**：默认false
- **showSwingPatterns**：默认false

---

## 特殊逻辑

### 仓位管理

- **单次持仓**：策略使用 `isHoldingPosition` 变量确保同时只持有一个方向的仓位
- **无加仓**：开仓后不会在同一方向再次开仓

### 移动止损机制

**做多移动止损**：
1. **第一次保护**：当价格首次触及SuperTrend上升趋势线时，设置移动止损保留10%利润
2. **深度保护**：当价格达到Fibonacci上轨（`upper_7`）时，设置移动止损保留90%利润

**做空移动止损**：
1. **第一次保护**：当价格首次触及SuperTrend下降趋势线时，设置移动止损保留10%利润
2. **深度保护**：当价格达到Fibonacci下轨（`lower_7`）时，设置移动止损保留90%利润

### 止盈计数机制

- **upArrivedProfit**：记录做多时价格触及SuperTrend上升趋势线的次数
- **downArrivedProfit**：记录做空时价格触及SuperTrend下降趋势线的次数
- 当达到指定次数（默认3次）且价格触及趋势线时，触发止盈

### 可视化

- **交易框**：平仓时绘制矩形框标记交易区间
  - 盈利交易：蓝色框
  - 亏损交易：黄色框

---

## 策略特点

### 优点

1. **多重确认**：结合SuperTrend、SSL、Range Filter等多个指标，提高信号可靠性
2. **趋势跟踪**：SuperTrend和SSL通道确保在趋势明确时交易
3. **动态止盈**：基于SuperTrend和Fibonacci布林带的移动止损，能够保护利润
4. **突破确认**：价格必须突破SSL通道并满足斜率条件，减少假突破
5. **灵活配置**：包含多个可选指标，可根据需要启用

### 风险提示

1. **无初始止损**：策略没有设置固定止损，完全依赖动态止损，可能面临较大回撤
2. **趋势依赖**：在震荡市场中可能产生较多假信号
3. **参数敏感**：多个指标参数需要根据市场和时间周期调整
4. **延迟入场**：需要价格突破SSL通道，可能错过最佳入场点

---

## 使用建议

1. **参数优化**：根据交易品种和时间周期调整各指标参数
2. **市场选择**：更适合趋势明显的市场，震荡市场需谨慎
3. **时间周期**：建议在15分钟及以上周期使用
4. **风险控制**：建议根据账户大小和风险承受能力调整 `profitProtectRatio`
5. **回测验证**：使用前务必进行充分回测，验证策略有效性
6. **指标组合**：可根据需要启用GMMA、Swing Patterns等辅助指标

---

## 版本说明

- **版本**：SuperTrend & ssl.pine
- **Pine Script版本**：v5
- **策略类型**：趋势跟踪策略
- **交易频率**：中等（基于突破信号）

