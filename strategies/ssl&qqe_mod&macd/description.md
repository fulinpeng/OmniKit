
// ==========================================================================================
//                                     策略说明
// ==========================================================================================
// SSL + QQE MOD + MACD 组合策略，支持做多与做空（不能同时持有多单和空单）。
//
// 一、方向开关
// ----------------------------------------------------------
// - 启用做多(enableLong) 为 true 时，允许按“多头逻辑”入场。
// - 启用做空(enableShort) 为 true 时，允许按“空头逻辑”入场。
// - 无论多空，所有入场都要求当前无持仓：strategy.position_size == 0 且 strategy.opentrades == 0。
//   因此不会同时存在多单和空单。
//
// 二、趋势过滤：SuperTrend & 准备状态
// ----------------------------------------------------------
// 使用 SuperTrend 判断大趋势：
// - stTrend == 1 视为多头趋势；stTrend == -1 视为空头趋势。
// 定义两个准备状态：
// - readyBuy  ：大趋势为多头时置为 true，空头时为 false；
// - readySell：大趋势为空头时置为 true，多头时为 false；
// 因此 readyBuy 与 readySell 互斥，多空的“准备做单状态”同时由 SuperTrend 控制。
//
// 三、多单入场条件（Long Entry）
// ----------------------------------------------------------
// longEntryCondition 需满足：
// 0）基础条件：
//    - enableLong == true；
//    - 当前无持仓；
//    - readyBuy == true；
//    - ssl1Down 与 ssl2Down 有效（非 na）。
//
// 1）结构性多头 (entryBaseConditionLong)：
//    - SSL2 上轨连续三根抬高：ssl2Up >= ssl2Up[1] 且 ssl2Up[1] >= ssl2Up[2]；
//    - SSL1 上轨 >= SSL2 下轨：ssl1Up >= ssl2Down；
//    - SuperTrend 下沿参与约束：
//        * 如 ssl1Down > ssl2Down，则直接通过；
//        * 否则要求 ssl2Down >= stLower（SSL2 下轨不得跌破 SuperTrend 下沿）。
//
// 2）QQE 回调 + 企稳 (callbackConditionLong)：
//    - 方案一 callbackCondition1：
//        * 取最近三根 qqeValue ，找到三者最小值 minValue；
//        * 要求 minValue <= 0（至少有一根柱子在 0 以下”）；
//        * 白线 whiteLine 满足：
//            a) 拐头向上：(whiteLine2 > whiteLine1 且 whiteLine1 < whiteLine0)，或
//            b) 连续增大且仍处于 20 以下：(whiteLine2 < whiteLine1 < whiteLine0 < 20)。
//    - 方案二 callbackCondition2：
//        * K 线收盘价向上突破 SSL2 上轨：ta.crossover(close, ssl2Up)；
//        * qqeValue 最近两根继续增大，且当前值 > -20；
//        * 白线最近两根也在增大。
//    - callbackConditionLong = callbackCondition1 or callbackCondition2。
//
// 3）MACD 动能 (macdConditionLong)：
//    - 使用自定义 MA 类型计算 MACD 与信号线；
//    - 条件：
//        a) macdHist[2] < macdHist[1] < macdHist （三根递增），或
//        b) macdHist[2] > macdHist[1] 且 macdHist[1] < macdHist （V 型反转）。
//
// 以上 0）+ 1）+ 2）+ 3）全部满足时，执行：strategy.entry("Long", strategy.long)。
//
// 四、多单的初始止损 / 固定止盈 / 可视化
// ----------------------------------------------------------
// 开多当根：longEntryPrice = close；并初始化：
//
// 1）初始止损 longInitialStopLoss & longStopLoss：
//    - 优先取 SSL1/SSL2 下轨中较小者；
//    - 如该价无效（na）或 >= 开仓价：
//        * 若 stLower 有效且 < 开仓价，则用 stLower；
//        * 否则，放弃这一单
//    - 若风险 longRisk = longEntryPrice - longInitialStopLoss <= 0，则放弃这一单
//
// 2）固定止盈 longTakeProfit：
//    - longTakeProfit = longEntryPrice + longRisk * riskRewardRatio；
//    - 如 <= 开仓价，放弃这一单。
//
// 3）画框：若 longStopLoss < longEntryPrice 且 longTakeProfit > longEntryPrice，
//    以这两个价位绘制一个白色矩形框，用于观察风险与目标区间。
//
// 五、多单资金管理与移动止损（四阶段，含两次分批止盈）
// ----------------------------------------------------------
// 公共参数：
// - principalRR：第一阶段触发 R 阈值（到此先减仓 + 止损抬到保本）；
// - RR_forOpenExitCondition：第二阶段触发 R 阈值（锁定“高盈利阶段”状态）；
// - riskRewardRatio：最终固定 R:R 止盈；
// - longBreakevenFactor：保本系数，breakevenSL = entry * factor (>1)。
// - 多单状态变量：
//   longReachedPrincipalRRState, longReachedExitRRState,
//   longTP1Executed, longTP2Executed。
//
// 触发逻辑（仅在 strategy.position_size > 0 且 longEntryExecuted 为 true 时）：
// 定义：
// - initialRiskAmount = longEntryPrice - longInitialStopLoss；
// - currentProfitHigh = high - longEntryPrice；
// - currentRRHigh     = currentProfitHigh / initialRiskAmount（若风险<=0则记为 0）；
// - breakevenSL       = longEntryPrice * longBreakevenFactor。
//
// 1）第一阶段：达到 principalRR
//    - 若 currentRRHigh >= principalRR：
//        * longReachedPrincipalRRState := true；
//    - 若 longReachedPrincipalRRState 且 longTP1Executed == false：
//        * strategy.close("Long", qty_percent=33, comment="Long TP1 principalRR")；
//        * longTP1Executed := true；
//    - 同时：如 breakevenSL > longStopLoss，则 longStopLoss := breakevenSL；
//      相当于止损抬到保本上方一点。
//    - 并保证 longStopLoss >= longInitialStopLoss（止损永远不比初始更差）。
//
// 2）第二阶段：达到 RR_forOpenExitCondition（锁定“高盈利阶段”）
//    - 若 currentRRHigh >= RR_forOpenExitCondition：
//        * longReachedExitRRState := true；
//    - 在 longReachedExitRRState == true 期间：
//        * trailBase = breakevenSL；
//        * 若 stLower 有效，则 trailBase = max(trailBase, stLower)；
//        * 如 trailBase > longStopLoss，则 longStopLoss := trailBase；
//        * 即止损价始终不低于保本价与 SuperTrend 下沿中更高的一个，实现趋势拖尾。
//    - 再次保证 longStopLoss >= longInitialStopLoss。
//
// 3）第三阶段：指标止盈触发第二次分批（TP2）
//    定义多单的指标平仓条件：
//    - exitCondition1Long（若开启开关1）：收盘价 < stLower；
//    - exitCondition2Long（若开启开关2）：ssl1Up < ssl2Down；
//    - exitCondition3Long（若开启开关3）：收盘价 < ssl2Down；
//    - exitCondition4Long（若开启开关4）：QQE 白线在较高区出现拐头向下或动能减弱
//      (whiteLineTurningDown or whiteLineReduce)；
//    - anyExitConditionLong = 上述任意为 true。
//    当 anyExitConditionLong 为 true 时：
//    - 用 close 重新计算 currentRRClose；
//    - 若 longReachedExitRRState == true 且 currentRRClose >= RR_forOpenExitCondition
//      且 longTP2Executed == false：
//        * strategy.close("Long", qty_percent=33, comment="Long TP2 indicator")；
//        * longTP2Executed := true；
//    - 剩余约 34% 仓位继续由 longStopLoss（拖尾） + longTakeProfit（固定 TP）决定最终出场价。
//
// 4）最终止盈 / 止损：
//    - 对剩余多单挂统一 exit：
//        strategy.exit("Long SLTP", from_entry="Long", stop=longStopLoss, limit=longTakeProfit)。
//    - 可能结果：
//        * 被拖尾止损打掉（锁定一部分浮盈）；
//        * 或击中固定止盈 longTakeProfit（达到设定 R:R）。
//
// 六、空单逻辑（Short）
// ----------------------------------------------------------
// 空单完全独立一套变量，逻辑与多单镜像，但方向相反：
// - 仅在 enableShort == true 且 readySell == true 且 当前无持仓 时才允许开空。
// - entry / SL / TP / 移动止损 / 分批止盈 与多单采用同一套参数，
//   只是价格方向全部反转。
//
// 1）空单入场条件（shortEntryCondition）
// 0）基础条件：
//    - enableShort == true；
//    - 当前无持仓；
//    - readySell == true（SuperTrend 空头）；
//    - ssl1Up 与 ssl2Up 有效（非 na）。
//
// 1）结构性空头 (entryBaseConditionShort)：
//    - SSL2 下轨连续三根走低：ssl2Down <= ssl2Down[1] 且 ssl2Down[1] <= ssl2Down[2]；
//    - SSL1 下轨 <= SSL2 上轨：ssl1Down <= ssl2Up；
//    - SuperTrend 上沿参与约束：
//        * 如 ssl1Up < ssl2Up，则直接通过；
//        * 否则要求 ssl2Up <= stUpper（SSL2 上轨不得突破 SuperTrend 上沿）。
//
// 2）QQE 回调 + 转弱 (callbackConditionShort)：
不需要使用镜像数据啊，qqe的柱子值还是使用qqeValue0、qqeValue1、qqeValue2，白线还是使用whiteLine0、whiteLine1、whiteLine2
//    - 方案一 shortCallback1：
//        * 取最近三根 qqeValue0/1/2，找最大值 sMaxValue；
//        * 要求 sMaxValue >= 0（至少一次“上侧回调”，也就是超买）；
//        * 白线 whiteLine 满足：
//            a) 拐头向下：(whiteLine2 < whiteLine1 且 whiteLine1 > whiteLine0)，或
//            b) 连续减小且仍处于 -20 以下：(whiteLine2 > whiteLine1 > whiteLine0 > -20)。
//    - 方案二 shortCallback2：
//        * 收盘价向下跌破 SSL2 下轨：ta.crossunder(close, ssl2Down)；
//        * qqeValue 最近两根在变小且当前值 < 20；
//        * whiteLine 最近两根在变小。
//    - callbackConditionShort = shortCallback1 or shortCallback2。
//
// 3）MACD 动能 (macdConditionShort)：
//    - 寻找“持续变弱或顶部 A 型反转”：
//        a) macdHist[2] > macdHist[1] > macdHist（三根递减），或
//        b) macdHist[2] < macdHist[1] 且 macdHist[1] > macdHist（顶部 A 型）。
//
// 条件 0）+ 1）+ 2）+ 3）全部满足，则：strategy.entry("Short", strategy.short)。
//
// 2）空单初始止损 / 固定止盈
// - shortEntryPrice = close；
// - 初始止损 shortInitialStopLoss / shortStopLoss：
//   * 优先取 SSL1/SSL2 上轨中的较大者（在价格上方）；
//   * 若无效或 <= 开仓价，则尝试使用 stUpper（且 stUpper > 开仓价）；
//   * 再不行，就放弃这一单；
//   * shortRisk = shortInitialStopLoss - shortEntryPrice，如 <=0 则 放弃这一单；
// - 固定止盈 shortTakeProfit：
//   * shortTakeProfit = shortEntryPrice - shortRisk * riskRewardRatio；
//   * 如 >= 开仓价，放弃这一单。
//
// 3）空单移动止损与分批止盈
// 定义（仅在 strategy.position_size < 0 且 shortEntryExecuted 为 true 时生效）：
// - initialRiskAmountShort = shortInitialStopLoss - shortEntryPrice；
// - currentProfitLow = shortEntryPrice - low（向下的最佳浮盈）；
// - currentRRShortHigh = currentProfitLow / initialRiskAmountShort；
// - breakevenSLShort   = shortEntryPrice * shortBreakevenFactor（略高于开仓价）。
//
// 第一阶段：currentRRShortHigh >= principalRR：
// - shortReachedPrincipalRRState := true；
// - 如未执行 TP1，则平掉 33% 空单；
// - 如 breakevenSLShort < shortStopLoss，则 shortStopLoss := breakevenSLShort；
// - 并保证 shortStopLoss <= shortInitialStopLoss（空单的“止损永远不比初始更高”）。
//
// 第二阶段：currentRRShortHigh >= RR_forOpenExitCondition：
// - shortReachedExitRRState := true；
// - 在该状态下：
//   * shortTrailBase = breakevenSLShort；
//   * 若 stUpper 有效，则 shortTrailBase = min(shortTrailBase, stUpper)；
//   * 如 shortTrailBase < shortStopLoss，则 shortStopLoss := shortTrailBase；
//   * 即止损价始终不高于 stUpper 与保本价中更低的那个，实现上方面对价格的拖尾保护。
//
// 第三阶段：指标触发第二次分批 TP2（空单）：
// - 定义空单版指标条件：
//   * exitCondition1Short：收盘价 > stUpper；
//   * exitCondition2Short：ssl1Down > ssl2Up；
//   * exitCondition3Short：收盘价 > ssl2Up；
//   * exitCondition4Short：QQE 白线在低位出现拐头向上或动能增强;
//   * anyExitConditionShort 为上述任意真。
// - 当 anyExitConditionShort 为真且 shortReachedExitRRState == true 时：
//   * 用 close 计算 currentRRShortClose；
//   * 若 currentRRShortClose >= RR_forOpenExitCondition 且 shortTP2Executed == false：
//       strategy.close("Short", qty_percent=33, comment="Short TP2 indicator")。
//   * 剩余约 34% 空单继续由 shortStopLoss + shortTakeProfit 控制。
//
// 最终空单止盈/止损：
// - strategy.exit("Short SLTP", from_entry="Short", stop=shortStopLoss, limit=shortTakeProfit)。
//
// 七、仓位结束后的状态重置
// ----------------------------------------------------------
// - 当上一根有持仓、本根无持仓（无论多单还是空单），统一重置：
//   * long / short 的 EntryPrice / StopLoss / InitialStopLoss / TakeProfit；
//   * longReachedPrincipalRRState / longReachedExitRRState / longTP1Executed / longTP2Executed；
//   * shortReachedPrincipalRRState / shortReachedExitRRState / shortTP1Executed / shortTP2Executed；
//   * longEntryExecuted / shortEntryExecuted。
// ==========================================================================================
