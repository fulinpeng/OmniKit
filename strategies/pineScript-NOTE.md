##### 仓位止损失败问题
```js
// 【下面这一段代码千万不能放开，这会导致仓位不能止损，暂时不明原因】
// 如果当前没有持仓，确保状态变量被重置
// if strategy.position_size == 0
//     longEntryPrice := na
//     longCurrentStopLoss := na
//     longInitialTakeProfit := na
//     longEntryBarLow := na
//     longMovedToBreakeven := false
//     longFvgWindowActive := false
//     longFvgWindowStart := na
//     shortEntryPrice := na
//     shortCurrentStopLoss := na
//     shortInitialTakeProfit := na
//     shortEntryBarHigh := na
//     shortMovedToBreakeven := false
//     shortFvgWindowActive := false
//     shortFvgWindowStart := na
// 关键问题：strategy.position_size 的更新延迟
// 在 Pine Script 中，strategy.position_size 的更新可能有延迟：
// 当 strategy.close() 执行后，strategy.position_size 不会立即变为 0
// 它可能在下一个 bar 或更晚才更新
// 如果在这期间重置 currentStopLoss := na，会影响 strategy.exit() 的执行
```