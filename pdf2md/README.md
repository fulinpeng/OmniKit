# PDF 转 Markdown

将项目 `input/` 目录下所有 PDF 转为 Markdown，输出到 `output/`（保持相对路径结构）。

## 安装

在 `pdf2md` 目录执行：

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

## 使用

在项目根目录或 `pdf2md` 目录均可运行：

```bash
python pdf2md/convert.py
```

指定目录：

```bash
python pdf2md/convert.py --input-dir "E:/tradingview-stratagys/input" --output-dir "E:/tradingview-stratagys/output"
```

## 说明

- 递归处理 `input` 下所有 `.pdf` 文件
- 每个 PDF 生成同名 `.md`，子目录结构会同步到 `output`
- 适用于可选中文字的 PDF；扫描版（纯图片）需 OCR，本工具不做 OCR
