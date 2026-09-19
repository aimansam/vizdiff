"""CLI interface for vizdiff -- spot-the-difference visual regression tool."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from .differ import compute_diff
from .report import terminal_report, html_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vizdiff",
        description="Visual regression CLI: compare two images or screenshot directories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  vizdiff before.png after.png
  vizdiff before.png after.png --html report.html
  vizdiff screenshots/before/ screenshots/after/ --html report.html
  vizdiff before.png after.png --threshold 50 --min-region 100
  vizdiff before.png after.png --passed   # exit 0 if similar, 1 if different
""",
    )
    parser.add_argument("image_a", help="First image or directory of screenshots")
    parser.add_argument("image_b", help="Second image or directory of screenshots")
    parser.add_argument("--html", "-H", metavar="FILE", help="Write HTML report to FILE")
    parser.add_argument("--threshold", "-t", type=int, default=30,
                        help="Pixel difference threshold 0-255 (default: 30)")
    parser.add_argument("--min-region", "-m", type=int, default=50,
                        help="Minimum region area in pixels (default: 50)")
    parser.add_argument("--passed", action="store_true",
                        help="Exit 0 if images are similar (>=98%%), 1 otherwise")

    args = parser.parse_args(argv)

    a_path = Path(args.image_a)
    b_path = Path(args.image_b)

    if a_path.is_dir() and b_path.is_dir():
        files_a = sorted(f for f in a_path.iterdir() if f.is_file() and _is_image(f))
        files_b = {f.name: f for f in b_path.iterdir() if f.is_file() and _is_image(f)}

        if not files_a:
            print(f"Error: no images found in {a_path}", file=sys.stderr)
            return 1

        all_results = []
        for fa in files_a:
            if fa.name in files_b:
                fb = files_b[fa.name]
                result = compute_diff(fa, fb, args.threshold, args.min_region)
                all_results.append(result)
                print(terminal_report(result))
                print()
                if args.html:
                    html_report(result, args.html)
            else:
                print(f"Warning: {fa.name} not found in {b_path}", file=sys.stderr)

        if not all_results:
            print("No matching files to compare", file=sys.stderr)
            return 1

        overall = sum(r.similarity for r in all_results) / len(all_results)
        print(f"Overall similarity: {overall * 100:.2f}% across {len(all_results)} images")
        return 0 if not args.passed or overall >= 0.98 else 1

    elif a_path.is_file() and b_path.is_file():
        result = compute_diff(a_path, b_path, args.threshold, args.min_region)
        print(terminal_report(result))
        if args.html:
            html_report(result, args.html)
        return 0 if not args.passed or result.passed else 1

    else:
        print("Error: both inputs must be files or both directories", file=sys.stderr)
        return 1


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff")


if __name__ == "__main__":
    sys.exit(main())
