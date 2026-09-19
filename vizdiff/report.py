"""HTML and terminal report generators for vizdiff."""

from __future__ import annotations
import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageFont


def _pil_font(size: int):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def terminal_report(result: "DiffResult") -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("  VIZDIFF -- Visual Regression Report")
    lines.append("=" * 60)
    lines.append(f"  Image A: {result.image_a}")
    lines.append(f"  Image B: {result.image_b}")
    lines.append(f"  Size:    {result.width}x{result.height}")
    lines.append(f"  Status:  {result.status}")
    lines.append(f"  Similarity: {result.similarity * 100:.2f}%")
    lines.append(f"  Diff pixels: {result.diff_pixels:,} / {result.width * result.height:,}")
    lines.append("")
    if result.regions:
        lines.append(f"  Diff regions: {len(result.regions)}")
        for i, r in enumerate(result.regions[:20], 1):
            sev = r.severity.upper()
            lines.append(f"    [{i}] {sev:>6}  area={r.area:,}px  box={r.box}")
        if len(result.regions) > 20:
            lines.append(f"    ... and {len(result.regions) - 20} more regions")
    else:
        lines.append("  No significant diff regions found")
    lines.append("")
    verdict = "PASS" if result.passed else "FAIL"
    lines.append(f"  Verdict: {verdict}")
    lines.append("=" * 60)
    return "\n".join(lines)


def html_report(result: "DiffResult", output_path: Path | str | None = None) -> str:
    def b64(img: Image.Image) -> str:
        buf = BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    img_b64 = b64(result.side_by_side) if result.side_by_side else ""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sev_colors = {
        "low": "#FFD166",
        "medium": "#EF476F",
        "high": "#D62828",
    }

    all_rows = ""
    for i, r in enumerate(result.regions[:50], 1):
        c = sev_colors.get(r.severity, "#FFD166")
        bx = f"{r.box[0]}, {r.box[1]} to {r.box[2]}, {r.box[3]}"
        all_rows += f'<tr><td>{i}</td><td style="color:{c}">{r.severity.upper()}</td><td>{r.area:,}</td><td>{bx}</td></tr>\n'

    verdict_span = 'pass' if result.passed else 'fail'
    status_text = result.status
    verdict_text = 'PASS' if result.passed else 'FAIL'

    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Vizdiff Report</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:900px;margin:40px auto;padding:0 20px;color:#264653}}
h1{{font-size:24px;margin-bottom:4px}}
.meta{{color:#666;font-size:13px;margin-bottom:20px}}
.card{{background:#f8f9fa;border-radius:8px;padding:16px;margin:12px 0;border:1px solid #e9ecef}}
.pass{{background:#d4edda;color:#155724;padding:4px 12px;border-radius:4px;display:inline-block;font-weight:bold}}
.fail{{background:#f8d7da;color:#721c24;padding:4px 12px;border-radius:4px;display:inline-block;font-weight:bold}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:12px 0}}
.stat{{background:white;padding:12px;border-radius:6px;text-align:center;border:1px solid #dee2e6}}
.stat .value{{font-size:28px;font-weight:bold;color:#007BA7}}
.stat .label{{font-size:12px;color:#666}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}}
th{{background:#264653;color:white;padding:8px;text-align:left}}
td{{padding:6px 8px;border-bottom:1px solid #dee2e6}}
img{{max-width:100%;border-radius:6px;border:1px solid #dee2e6}}
.footer{{margin-top:30px;color:#999;font-size:12px}}
</style></head><body>
<h1>Vizdiff Report</h1>
<div class="meta">{timestamp}</div>
<div class="stats">
<div class="stat"><div class="value">{result.similarity*100:.2f}%</div><div class="label">Similarity</div></div>
<div class="stat"><div class="value">{result.width}x{result.height}</div><div class="label">Image Size</div></div>
<div class="stat"><div class="value">{result.diff_pixels:,}</div><div class="label">Diff Pixels</div></div>
<div class="stat"><div class="value">{len(result.regions)}</div><div class="label">Regions</div></div>
</div>
<div class="card">
<strong>Status:</strong> <span class="{verdict_span}">{status_text}</span><br>
<strong>Verdict:</strong> <span class="{verdict_span}">{verdict_text}</span>
</div>
<div class="card">
<h3>Side-by-Side Comparison</h3>
<img src="data:image/png;base64,{img_b64}" alt="Side-by-side diff">
<p style="font-size:12px;color:#666;margin-top:8px">Left: BEFORE - Right: AFTER with diff highlights</p>
</div>
{"<div class='card'><h2>Diff Regions</h2><table><thead><tr><th>#</th><th>Severity</th><th>Area</th><th>Bounding Box</th></tr></thead><tbody>"+all_rows+"</tbody></table></div>" if result.regions else ""}
<div class="footer">Generated by vizdiff</div>
</body></html>'''

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(html)
    return html
