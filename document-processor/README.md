# Excel转Word/PDF自动化程序

将Excel表格中的数据自动填充到Word模板，并为每一行数据生成独立的Word文档或PDF文件。

## 功能说明

- 读取Excel文件中的数据
- 将数据填充到Word模板的占位符位置
- 为每个员工生成独立的Word文档或PDF文件
- 支持中文编码处理
- 支持Word控件保护

## 文件说明

- `index.js` - 主程序（处理Excel转Word/PDF）
- `index_new.js` - 新版本程序（使用已翻译的Excel文件）
- `README_ORIGINAL.md` - 原始README（Excel转Word详细说明，使用`--`占位符）
- `README_WORD.md` - Word版本详细说明（使用`{0}`占位符）
- `INSTALL_GUIDE.md` - 安装指南
- `LIBREOFFICE_INSTALL.md` - LibreOffice安装指南（用于PDF转换）

## 使用方法

### 从项目根目录运行：

```bash
# 运行主程序
npm start

# 或运行新版本
npm run start:new
```

### 输入输出路径

程序使用以下路径（相对于项目根目录）：
- 输入文件：`./input/a.xlsx`（Excel数据）和 `./input/b.docx`（Word模板）
- 输出文件：`./output/`（生成的Word或PDF文档）

## 依赖库

- `xlsx` - 读取Excel文件
- `docxtemplater` - 处理Word模板
- `pizzip` - 处理docx文件的zip结构
- `puppeteer` - 用于PDF转换
- `mammoth` - Word文档处理
- `officegen` - Office文档生成
- `archiver` - 文件压缩

## 注意事项

- 确保在项目根目录运行脚本
- 确保 `input/` 和 `output/` 文件夹存在
- Excel文件路径和工作表名称需要正确配置
- 详细说明请参考 `README.md` 和 `README_WORD.md`
