"""Build a single-file standalone bundle of the Pulse viewer.

Reads viewer/index.html and inlines:
  - viewer/styles.css         -> <style>
  - viewer/data.js            -> <script>
  - all viewer/*.jsx imports  -> <script type="text/babel">

Writes viewer/Pulse_Dashboard_Standalone.html.

Usage:
  python -m app.viewer.bundle
  python -m app.viewer.bundle --output viewer/Pulse_Dashboard_Standalone.html
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


VIEWER_DIR = Path(__file__).resolve().parents[2] / "viewer"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_standalone(index_path: Path, output_path: Path) -> None:
    html = _read(index_path)

    # Inline styles.css (use lambda to avoid backref interpretation of \u, etc.)
    css = _read(VIEWER_DIR / "styles.css")
    html = re.sub(
        r'<link rel="stylesheet" href="styles\.css"\s*/?>',
        lambda _m: f"<style>\n{css}\n</style>",
        html,
        count=1,
    )

    # Inline data.js
    data_js = _read(VIEWER_DIR / "data.js")
    html = re.sub(
        r'<script src="data\.js"></script>',
        lambda _m: f"<script>\n{data_js}\n</script>",
        html,
        count=1,
    )

    # Inline every <script type="text/babel" src="X.jsx"></script>
    def _inline_jsx(match: re.Match) -> str:
        src = match.group(1)
        body = _read(VIEWER_DIR / src)
        return f'<script type="text/babel">\n{body}\n</script>'

    html = re.sub(
        r'<script type="text/babel" src="([^"]+\.jsx)"></script>',
        _inline_jsx,
        html,
    )

    output_path.write_text(html, encoding="utf-8")
    size_kb = output_path.stat().st_size // 1024
    print(f"  Wrote {output_path}  ({size_kb} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build standalone Pulse HTML")
    parser.add_argument(
        "--index",
        default=str(VIEWER_DIR / "index.html"),
        help="Path to viewer/index.html",
    )
    parser.add_argument(
        "--output",
        default=str(VIEWER_DIR / "Pulse_Dashboard_Standalone.html"),
        help="Path for the standalone bundle",
    )
    args = parser.parse_args()
    build_standalone(Path(args.index), Path(args.output))


if __name__ == "__main__":
    main()
