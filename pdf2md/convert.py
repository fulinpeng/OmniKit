import argparse
import sys
from pathlib import Path

import pymupdf4llm


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "input"
DEFAULT_OUTPUT = ROOT / "output"


def find_pdfs(input_dir: Path) -> list[Path]:
    return sorted(input_dir.rglob("*.pdf"))


def convert_pdf(pdf_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    md_text = pymupdf4llm.to_markdown(str(pdf_path))
    output_path.write_text(md_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="将 input 目录中的 PDF 批量转为 Markdown")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"PDF 输入目录，默认: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown 输出目录，默认: {DEFAULT_OUTPUT}",
    )
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.is_dir():
        print(f"输入目录不存在: {input_dir}", file=sys.stderr)
        return 1

    pdfs = find_pdfs(input_dir)
    if not pdfs:
        print(f"未在 {input_dir} 中找到 PDF 文件")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, 0

    for pdf_path in pdfs:
        rel = pdf_path.relative_to(input_dir)
        out_path = output_dir / rel.with_suffix(".md")
        try:
            convert_pdf(pdf_path, out_path)
            print(f"OK  {rel} -> {out_path.relative_to(output_dir)}")
            ok += 1
        except Exception as exc:
            print(f"FAIL {rel}: {exc}", file=sys.stderr)
            failed += 1

    print(f"\n完成: 成功 {ok}，失败 {failed}，输出目录 {output_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
