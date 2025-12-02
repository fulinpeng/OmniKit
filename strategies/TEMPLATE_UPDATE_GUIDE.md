# Word模板更新指南

## 问题说明
当前程序直接操作XML会破坏Word文档中的复选框等控件元素。

## 解决方案
需要将Word模板中的占位符从 `--` 格式改为 `{数字}` 格式。

## 具体修改步骤

### 当前模板格式：
```
Payment Date: --
Employee Name: --
Position / Department: --
Total Amount: $    --
Receiving wallet address: --
Date: --
```

### 需要改为：
```
Payment Date: {0}
Employee Name: {1}
Position / Department: {2}
Total Amount: $    {3}
Receiving wallet address: {4}
Date: {5}
```

## 修改说明
- `{0}` 对应 J列（Payment Date）
- `{1}` 对应 E列（Employee Name）
- `{2}` 对应 D列（Position / Department）
- `{3}` 对应 O列（Total Amount）
- `{4}` 对应 M列（Receiving wallet address）
- `{5}` 对应 J列（Date）

## 优势
- 完全保护复选框等控件不被破坏
- 使用docxtemplater库的标准方式
- 更安全、更可靠

## 如果不想修改模板
也可以继续使用当前的 `--` 格式，但复选框控件可能会被破坏。
