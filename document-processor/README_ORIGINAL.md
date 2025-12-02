# Excel转Word自动化程序

将Excel表格中的数据自动填充到Word模板，并为每一行数据生成独立的Word文档。

## 功能说明

- 读取Excel文件中的数据（`数据总表Wallet` 工作表）
- 将数据填充到Word模板的占位符位置
- 为每个员工生成独立的Word文档，文件名为员工姓名

## 文件结构

```
document-processor/
├── index.js           # 主程序
├── index_new.js       # 新版本程序
└── README*.md         # 说明文档

项目根目录/
├── input/              # 输入文件夹
│   ├── a.xlsx         # Excel数据源
│   └── b.docx         # Word模板
├── output/            # 输出文件夹（生成的Word文档）
└── package.json       # 依赖配置
```

## 字段映射

Word模板中的占位符使用 `--`（两个中划线），程序会按以下顺序依次替换：

| 替换顺序 | Excel列 | 说明 |
|---------|---------|------|
| 第1个 `--` | J列 | Payment Date（付款日期） |
| 第2个 `--` | E列 | Employee Name（员工姓名） |
| 第3个 `--` | D列 | Position / Department（职位/部门） |
| 第4个 `--` | O列 | Total Amount（总金额） |
| 第5个 `--` | M列 | Receiving wallet address（收款钱包地址） |
| 第6个 `--` | J列 | Date（日期） |

## 安装步骤

1. 确保已安装 Node.js（建议 v14 或更高版本）

2. 安装依赖：
```bash
npm install
```

## 使用方法

1. 将Excel数据文件放到 `input/a.xlsx`
2. 将Word模板文件放到 `input/b.docx`
3. 确保Word模板中有6个 `--` 占位符（按顺序对应上表）
4. 运行程序：
```bash
npm start
```

5. 生成的Word文档将保存在 `output/` 文件夹中

## 注意事项

- Excel文件必须包含名为 `数据总表Wallet` 的工作表
- Word模板中需要有6个 `--` 占位符，程序会按顺序依次替换
- 生成的文件名为员工姓名（E列），格式为 `.docx`
- 如果某行数据的员工姓名为空，将跳过该行

## 依赖库

- `xlsx` - 读取Excel文件
- `docxtemplater` - 处理Word模板
- `pizzip` - 处理docx文件的zip结构

## 问题排查

如果程序运行出错，请检查：

1. Excel文件路径和工作表名称是否正确
2. Word模板文件是否存在
3. Word模板中是否有6个 `--` 占位符
4. Excel数据列是否对应正确（J、E、D、O、M、J列）

## 许可证

MIT

