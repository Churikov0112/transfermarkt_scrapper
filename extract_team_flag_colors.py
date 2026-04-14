#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image


DEFAULT_FLAGS_DIR = "team_flags"
DEFAULT_OUTPUT_JSON = "team_flag_colors.json"


def quantize_channel(value: int, bin_size: int) -> int:
    return value // bin_size


def bin_to_hex_color(r_bin: int, g_bin: int, b_bin: int, bin_size: int) -> str:
    center_shift = bin_size // 2
    r = min(r_bin * bin_size + center_shift, 255)
    g = min(g_bin * bin_size + center_shift, 255)
    b = min(b_bin * bin_size + center_shift, 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def extract_palette(image_path: Path, decode_size: int, bin_size: int, max_colors: int) -> list[dict]:
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img = img.resize((decode_size, decode_size))
        pixels = list(img.getdata())

    total_pixels = len(pixels)
    if total_pixels == 0:
        return []

    histogram: Counter[tuple[int, int, int]] = Counter()
    for r, g, b in pixels:
        r_bin = quantize_channel(r, bin_size)
        g_bin = quantize_channel(g, bin_size)
        b_bin = quantize_channel(b, bin_size)
        histogram[(r_bin, g_bin, b_bin)] += 1

    palette = []
    for (r_bin, g_bin, b_bin), count in histogram.most_common(max_colors):
        palette.append(
            {
                "hex": bin_to_hex_color(r_bin, g_bin, b_bin, bin_size),
                "weight": round(count / total_pixels, 6),
            }
        )

    return palette


def sort_key(path: Path):
    stem = path.stem
    return (0, int(stem)) if stem.isdigit() else (1, stem)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract dominant colors for each team flag and save as JSON (id -> colors).",
    )
    parser.add_argument("--flags-dir", default=DEFAULT_FLAGS_DIR, help="Directory with team flag images.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_JSON, help="Output JSON file path.")
    parser.add_argument("--decode-size", type=int, default=48, help="Resize each image to N x N before extraction.")
    parser.add_argument("--bin-size", type=int, default=32, help="RGB quantization bin size.")
    parser.add_argument("--max-colors", type=int, default=8, help="Max number of colors per flag.")
    args = parser.parse_args()

    flags_dir = Path(args.flags_dir)
    output_path = Path(args.output)

    if not flags_dir.exists() or not flags_dir.is_dir():
        raise FileNotFoundError(f"Flags directory does not exist: {flags_dir}")

    image_files = sorted(
        [p for p in flags_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}],
        key=sort_key,
    )

    result: dict[str, list[dict]] = {}
    skipped: list[str] = []

    for image_path in image_files:
        team_id = image_path.stem
        try:
            result[team_id] = extract_palette(
                image_path=image_path,
                decode_size=args.decode_size,
                bin_size=args.bin_size,
                max_colors=args.max_colors,
            )
        except Exception:
            skipped.append(image_path.name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved: {output_path}")
    print(f"Processed: {len(result)}")
    if skipped:
        print(f"Skipped: {len(skipped)}")
        print(", ".join(skipped[:20]))


if __name__ == "__main__":
    main()
