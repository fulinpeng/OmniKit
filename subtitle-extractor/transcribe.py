import argparse
import json
import os
from pathlib import Path
from typing import Iterable, List, Dict, Any

from faster_whisper import WhisperModel


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(segments: Iterable[Any], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}\n")
            f.write(seg.text.strip() + "\n\n")


def write_txt(segments: Iterable[Any], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg.text.strip() + "\n")


def write_json(segments: Iterable[Any], info: Any, output_path: Path) -> None:
    data: Dict[str, Any] = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": [],
    }
    for seg in segments:
        data["segments"].append(
            {
                "id": seg.id,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "avg_logprob": seg.avg_logprob,
                "no_speech_prob": seg.no_speech_prob,
            }
        )
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="使用 faster-whisper 提取视频/音频字幕")
    parser.add_argument("--input", required=True, help="输入视频或音频文件路径")
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="输出目录（将自动创建），默认: outputs",
    )
    parser.add_argument(
        "--model",
        default="small",
        help="模型名，例如 tiny/base/small/medium/large-v3，默认: small",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="推理设备，默认: auto",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="计算类型，例如 int8/float16/float32，默认: int8",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="语言代码（如 zh/en），不传则自动识别",
    )
    parser.add_argument(
        "--task",
        default="transcribe",
        choices=["transcribe", "translate"],
        help="任务类型：transcribe 或 translate，默认: transcribe",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="beam size，默认: 5",
    )
    parser.add_argument(
        "--vad-filter",
        action="store_true",
        help="启用 VAD 过滤静音片段",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem
    srt_path = output_dir / f"{stem}.srt"
    txt_path = output_dir / f"{stem}.txt"
    json_path = output_dir / f"{stem}.json"

    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
    )

    segments_iter, info = model.transcribe(
        str(input_path),
        language=args.language,
        task=args.task,
        beam_size=args.beam_size,
        vad_filter=args.vad_filter,
    )

    segments: List[Any] = list(segments_iter)

    write_srt(segments, srt_path)
    write_txt(segments, txt_path)
    write_json(segments, info, json_path)

    print(f"完成: {input_path}")
    print(f"语言识别: {info.language} (prob={info.language_probability:.3f})")
    print(f"SRT: {srt_path}")
    print(f"TXT: {txt_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
