# SuperTrend & SSL 策略描述

## 策略概述

SuperTrend & SSL 策略是一个多指标组合的趋势跟踪策略，结合了 SuperTrend、SSL通道、Range Filter、WaveTrend、机器学习分类等多个技术指标，通过多重确认机制识别趋势突破点，并采用动态止盈止损管理仓位。

* 基于 SuperTrend & ssl-策略描述-6.md
* 加了保本，发现效果并不好，跟 策略描述5 差不多，甚至比策略5还差点
    * 可能是短周期，而且止盈1:1而已嘛，所以很容止盈
    * 移动止损的位置很容被回调给触碰到，所以加了保本更容易止损，得不偿失
    * ★还是去掉了保本逻辑★
* ★按盈利比例设置移动止损也去掉★
    * 不好用
* ★★★★很多平台或者统计平台的数据都有点差，所以加上容差机制
    * 在容差范围内均可认为达到目标，不需要等待精确值
    * 容差范围：[目标价格*(1-容差配置), 目标价格*(1+容差配置)]
* ★★★★重大升级
    * 当前代码为：@version=6版本
* 加入了 SMC Structures
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
- `Periods`：ATR周期，默认48
- `src`：数据源，默认 `hl2`
- `Multiplier`：ATR乘数，默认12
- `changeATR`：切换ATR计算方法，默认true

**计算逻辑**：
```
lowerBand = src - Multiplier * atr  // 上升趋势的下轨（支撑线），当 trend == 1 时使用
upperBand = src + Multiplier * atr  // 下降趋势的上轨（阻力线），当 trend == -1 时使用
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
sslDown = Hlv < 0 ? smaHigh : smaLow  // minSSL
sslUp = Hlv < 0 ? smaLow : smaHigh     // maxSSL
```

**应用**：
- `maxSSL = max(sslUp, sslDown)`：maxSSL
- `minSSL = min(sslUp, sslDown)`：minSSL
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

### 7. GMMA - 顾比移动平均线组

**作用**：识别趋势强度和方向（可选显示）

**参数设置**：
- 12条EMA线：3, 5, 8, 10, 12, 15, 30, 35, 40, 45, 50, 60
- 短期组（绿色）：EMA1-6
- 长期组（红色）：EMA7-12

**应用**：
- 通过开关控制是否显示
- 用于趋势确认和可视化

---

### 8. SMC Structures (BOS/CHoCH) - 市场结构分析

**作用**：识别市场结构变化，标记趋势突破点（BOS）和趋势反转点（CHoCH）

**参数设置**：
- `is_enable_BosChoch_section`：启用 BOS/CHoCH 功能，默认true
- `isStructBodyCandleBreak`：是否使用K线实体突破，默认true
- `structureLookback`：结构计算的回看周期，默认10
- `structHistoryNbr`：显示的结构数量，默认10
- `currentStructLineWidth`：当前结构线宽度，默认1

**计算逻辑**：
```
1. 计算结构高低点：
   - 使用指定回看周期（默认10）计算最高点和最低点
   - structureHigh：当前结构的高点
   - structureLow：当前结构的低点
   - structureDirection：结构方向（0=未定义, 1=看跌, 2=看涨）

2. 判断结构突破：
   - 低点突破：价格跌破结构低点（可使用K线实体或影线）
   - 高点突破：价格突破结构高点（可使用K线实体或影线）
   - 需要连续3根K线确认突破

3. 标记结构变化：
   - BOS (Break of Structure)：同方向的结构突破
   - CHoCH (Change of Character)：反方向的结构变化
```

**BOS (Break of Structure) 判断**：
- 当结构方向为看跌（1）且低点被突破时，标记为看跌BOS
- 当结构方向为看涨（2）且高点被突破时，标记为看涨BOS

**CHoCH (Change of Character) 判断**：
- 当结构方向为看涨（2）且低点被突破时，标记为看跌CHoCH（趋势反转）
- 当结构方向为看跌（1）且高点被突破时，标记为看涨CHoCH（趋势反转）

**应用**：
- 用于识别市场结构变化
- 辅助判断趋势方向和反转点
- 可视化显示在图表上，便于分析

**可视化**：
- BOS线：银色（看涨/看跌）
- CHoCH线：黄色（看涨/看跌）
- 当前结构线：蓝色（显示当前结构的高低点）

---

### 9. FVG (Fair Value Gap) - 公允价值缺口（多时间框架）

**作用**：识别价格跳空区域，标记市场中的不平衡区域，这些区域通常会被价格回填

**参数设置**：
- `is_enable_fvg_section`：启用 FVG 功能，默认true
- `bullishFvgColor`：看涨FVG颜色，默认绿色（透明度60%）
- `bearishFvgColor`：看跌FVG颜色，默认红色（透明度60%）
- `mitigatedFvgColor`：已回填FVG颜色，默认灰色（透明度70%）
- `isMitigatedFvgToReduce`：是否缩小已回填FVG区域，默认true
- `fvgTFDistance`：FVG时间框架距离，默认10（控制不同时间框架FVG之间的间距）
- `ltf_hide`：是否隐藏低于启用时间框架的FVG，默认true
- `isAddBarIndex`：是否显示FVG BarIndex，默认false
- `fvgHistoryNbr`：每个时间框架的最大活跃FVG数量，默认8

**多时间框架配置**（TF1-TF8）：
- 每个时间框架包含：
  - `tfX_show`：是否显示该时间框架的FVG
  - `tfX`：时间框架设置（如"15", "60", "240", "D", "W"等）
  - `tfX_label`：时间框架标签（如"15", "1H", "4H", "1D"等）
  - `tfX_fvg_limit`：该时间框架的最大FVG数量（默认：TF1=6, 其他=4）

**计算逻辑**：
```
1. FVG识别：
   - 看涨FVG：high[3] < low[1]（第三根K线的高点低于第一根K线的低点）
   - 看跌FVG：low[3] > high[1]（第三根K线的低点高于第一根K线的高点）

2. FVG管理：
   - 自动检测重复FVG，避免重复绘制
   - 当FVG数量超过限制时，自动删除最旧的FVG
   - 实时更新FVG框的右边界，跟随当前价格

3. FVG回填检测：
   - 看涨FVG：当价格跌破FVG底部时，标记为完全回填并删除
   - 看跌FVG：当价格突破FVG顶部时，标记为完全回填并删除
   - 部分回填：价格进入FVG区域但未完全回填时，改变颜色并可选缩小区域
```

**应用**：
- 识别价格跳空区域，这些区域通常会被价格回填
- 多时间框架分析，从不同周期识别FVG
- 辅助判断潜在的支撑和阻力位
- 可视化显示在图表上，便于分析

**可视化**：
- 看涨FVG：绿色半透明框
- 看跌FVG：红色半透明框
- 已回填FVG：灰色半透明框（可配置缩小区域）
- 每个FVG显示对应时间框架的标签

---

### 10. Structure Fibonacci - 结构斐波那契回撤

**作用**：在当前结构的高低点之间绘制斐波那契回撤线，识别潜在的支撑和阻力位

**参数设置**：
- `is_enable_structfib_section`：启用结构斐波那契功能，默认false
- 5个斐波那契级别（Fibo1-Fibo5），每个包含：
  - `isFiboXToShow`：是否显示该级别，默认true
  - `fiboXValue`：斐波那契值（默认：0.786, 0.705, 0.618, 0.5, 0.382）
  - `fiboXColor`：线条颜色
  - `fiboXStyleOption`：线条样式（实线/虚线/点线）
  - `fiboXLineWidth`：线条宽度，默认1

**计算逻辑**：
```
1. 计算结构范围：
   - structureRange = |structureHigh - structureLow|

2. 根据结构方向计算斐波那契价格：
   - 看涨结构（structureDirection != 1）：
     fiboPrice = structureLow + (structureRange - structureRange * fiboValue)
   - 看跌结构（structureDirection == 1）：
     fiboPrice = structureHigh - (structureRange - structureRange * fiboValue)

3. 确定起始点：
   - 看涨结构：从structureLowStartIndex开始
   - 看跌结构：从structureHighStartIndex开始
```

**应用**：
- 在当前结构的高低点之间绘制斐波那契回撤线
- 识别潜在的支撑和阻力位
- 辅助判断价格回调的目标位
- 与BOS/CHoCH结构分析结合使用

**可视化**：
- 每个斐波那契级别显示为一条水平线
- 线条颜色和样式可自定义
- 标签显示斐波那契值和对应的价格
- 实时更新，跟随当前结构的变化

---

### 辅助指标

- **Nadaraya-Watson Envelope**：核回归包络线（可选）
- **Swing Highs-Lows & Candle Patterns**：摆动高低点和K线形态（可选）
- **QQEMOD**：QQE修改版指标，用于入场条件判断
- **TrendSpeed**：趋势速度分析器（可选显示）
- **GMMA**：顾比移动平均线组（可选显示）
- **Fibonacci Bollinger Bands**：斐波那契布林带
- **Range Filter**：范围过滤器
- **SSL & SSL2**：SSL通道（标准版和长周期版）
- **WaveTrend**：波动趋势指标
- **SMC Structures (BOS/CHoCH)**：市场结构分析（可选显示）
- **FVG (Fair Value Gap)**：公允价值缺口，多时间框架分析（可选显示）
- **Structure Fibonacci**：结构斐波那契回撤线（可选显示）

---

## 交易规则
* 容差范围：[目标价格*(1-容差配置), 目标价格*(1+容差配置)]
    * 容差配置默认：0.0005
    * 例如SuperTrend上轨加上容差机制,多单情况下:
        * maxSuper的容差范围: [maxSuper*(1-容差配置), maxSuper*(1+容差配置)]
        * 如果 close > min(maxSuper*(1-容差配置), maxSuper*(1+容差配置)) or low < min(maxSuper*(1-容差配置), maxSuper*(1+容差配置))
### ====== 做多规则 ======

#### 入场条件

**条件组合**：`section3Up = (section3Up1 or section3Up2 or section3Up3)`

**section3Up1**：
- 满足所有条件可以SSL入场
    - maxSSL > minSSL2（确定上升趋势）
    - `trend == 1`
    - 最近三根K线 qqe柱子是红色 and 拐头向上 and 最近三个qqe柱子的最小值 < -5 
    - `close > maxSSL`（收盘价在maxSSL上方）
    - minSSL > minSSL2 and maxSSL > maxSSL2 and `math.min(low, low[1]) <= maxSSL`（当前或前一根K线的最低价触及或下穿maxSSL）
    - SSL斜率条件： `(maxSSL - math.max(smaHigh[21], smaLow[21])) / math.max(smaHigh[21], smaLow[21]) > sslRateUp`，补充说明
        - 即：maxSSL相对于21(21可配置)根K线前的WMA值的上涨幅度 > `sslRateUp`（默认0.00008）
        - 表示SSL通道正在向上倾斜

**section3Up2**：
- 满足所有条件可以SSL2入场
    - maxSSL > minSSL2（确定上升趋势）
    - `trend == 1`
    - 最近三根K线 qqe柱子是红色 and 拐头向上 and 最近三个qqe柱子的最小值 < -15
    - close > maxSSL2（收盘价在maxSSL上方）
    - minSSL > minSSL2 and maxSSL > maxSSL2 and `math.min(low, low[1]) <= maxSSL2`（当前或前一根K线的最低价触及或下穿maxSSL2）
    - SSL2斜率条件： `(maxSSL2 - math.max(smaHigh2[21], smaLow2[21])) / math.max(smaHigh2[21], smaLow2[21]) > ssl2RateUp`，补充说明
        - 即：maxSSL2相对于21(21可配置)根K线前的WMA值的上涨幅度 > `ssl2RateUp`（默认0.00001）
        - 表示SSL2通道正在向上倾斜

**section3Up3**：
- 满足所有条件可以ADX入场
    - minSSL > maxSSL2（确定上升趋势）
    - `trend == 1`
    - close > maxSSL2（收盘价在maxSSL2上方）
    - ADX， DIPlus 形成金叉 and ADX > ADX[1] > ADX[2]
    - DIPlus > 20 and DIMinus < 20 and 20 < ADX < 40 (20 40可配置)
    - 最近10根k线不能有 close > upper_6

**开仓条件**：
- 当前无持仓（`not isHoldingPosition`）
- `section3Up = true`

#### 开仓设置

- **开仓价**：当前收盘价（`close`）
- **订单ID**：`'buy'`
- **订单类型**：市价单（`strategy.entry()` 无 `limit` 参数）
- **注释**：`'多'`

#### 止损
1. 使用SuperTrend下轨为限价止损位
2. close < 当前SuperTrend下轨立即平仓全部仓位

#### 移动止损（默认关闭移动止损，多空使用同一个开关）
1. 
2. qqe柱子值 > 30 (-30可配置)
    * 移动一次止损位置到 max(订单的当前限价止损价, preLow)

#### 止盈
1. 固定止盈 1:3（3可配置）作为限价止盈位，全部平仓
2. 指标止盈（可配置，默认关闭）（到达一次指标止盈位计数加1，随后5根k线之内如果再次满足该条件不要计数超过5根k线再次到达的需要增加一次计数），并移动一次止损位置到 max(订单的当前限价止损价, preLow)
    * close > SuperTrend上轨（SuperTrend上轨加上容差机制）
    * close > Fibonacci上轨（Fibonacci上轨加上容差机制）
3. 指标止盈计数大于等于3，立即全部平仓（3可以配置）
4. 首次达到指标止盈平仓50%，剩余仓位博弈更多的可能（50%可以配置）
    * 如果配置为0不执行平仓逻辑，认为是关闭了分批止盈

**平仓注释**：
- `close > entry_price`：`'止盈平多'`
- `close <= entry_price`：`'止损平多'`

---

### ====== 做空规则 ======

#### 入场条件

**条件组合**：`section3Down = (section3Down1 or section3Down2 or section3Down3)`

**section3Down1**：
- 满足所有条件可以SSL入场
    - minSSL < maxSSL2（确定为下降趋势）
    - `trend == -1`
    - 最近三根K线 qqe柱子是绿色 and 拐头向下 and 最近三个qqe柱子的最大值 > 5
    - `close < minSSL`（收盘价在minSSL下方）
    - minSSL < minSSL2 and maxSSL < maxSSL2 and `math.max(high, high[1]) >= minSSL`（当前或前一根K线的最高价触及或上穿minSSL）
    - SSL斜率条件： `(maxSSL - math.max(smaHigh[21], smaLow[21])) / math.max(smaHigh[21], smaLow[21]) < sslRateDown`，补充说明
        - 即：maxSSL相对于21(21可配置)根K线前的WMA值的下跌幅度 < `sslRateDown`（默认-0.00006）
        - 表示SSL通道正在向下倾斜

**section3Down2**：
- 满足所有条件可以SSL2入场
    - minSSL < maxSSL2（确定为下降趋势）
    - `trend == -1`
    - 最近三根K线 qqe柱子是绿色 and 拐头向下 and 最近三个qqe柱子的最大值 > 15
    - close < minSSL2（收盘价在minSSL下方）
    - minSSL < minSSL2 and maxSSL < maxSSL2 and `math.max(high, high[1]) >= minSSL2`（当前或前一根K线的最高价触及或上穿minSSL2）
    - SSL2斜率条件： `(maxSSL2 - math.max(smaHigh2[21], smaLow2[21])) / math.max(smaHigh2[21], smaLow2[21]) < ssl2RateDown`，补充说明
        - 即：maxSSL2相对于21(21可配置)根K线前的WMA值的下跌幅度 < `ssl2RateDown`（默认-0.00001）
        - 表示SSL2通道正在向下倾斜

**section3Down3**：
- 满足所有条件可以ADX入场
    - maxSSL < minSSL2（确定下降趋势）
    - `trend == -1`
    - close < minSSL2（收盘价在minSSL2下方）
    - ADX， DIMinus 形成金叉 and ADX > ADX[1] > ADX[2]
    - DIMinus > 20 and DIPlus < 20 and 20 < ADX < 40 (20 40可配置)
    - 最近10根k线不能有 close < lower_6

**开仓条件**：
- 当前无持仓（`not isHoldingPosition`）
- `section3Down = true`

#### 开仓设置

- **开仓价**：当前收盘价（`close`）
- **订单ID**：`'sell'`
- **订单类型**：市价单（`strategy.entry()` 无 `limit` 参数）
- **注释**：`'空'`

#### 止损 达到任何位置都可以止损
1. 使用当前SuperTrend上轨为限价止损位
2. 趋势反转立即平仓（不要这个条件）
3. close > 当前SuperTrend上轨立即平仓全部仓位

#### 移动止损（默认关闭移动止损，多空使用同一个开关）
2. qqe柱子值 < -30 (-30可配置)
    * 移动一次止损位置到 min(订单的当前限价止损价, preHigh)

#### 止盈
1. 固定止盈 1:3（3可配置）作为限价止盈位
2. 指标止盈（可配置，默认关闭）（到达一次指标止盈位计数加1，随后5根k线之内如果再次满足该条件不要计数超过5根k线再次到达的需要增加一次计数），并移动一次止损位置到 min(订单的当前限价止损价, preHigh)
    * close < SuperTrend下轨（SuperTrend下轨加上容差机制）
    * close < Fibonacci下轨（Fibonacci下轨加上容差机制）
3. 指标止盈计数大于等于3，立即全部平仓（3可以配置）
4. 首次达到指标止盈平仓50%，剩余仓位博弈更多的可能（50%可以配置）
    * 如果配置为0不执行平仓逻辑，认为是关闭了分批止盈

**平仓注释**：
- `close < entry_price`：`'止盈平空'`
- `close >= entry_price`：`'止损平空'`
