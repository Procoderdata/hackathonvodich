from __future__ import annotations

import argparse
import html
import re
import subprocess
from pathlib import Path

import markdown


PROJECT_DIR = Path(__file__).resolve().parent
CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def render_mermaid_to_svg(mermaid_text: str, out_svg: Path) -> None:
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    temp_mmd = out_svg.with_suffix('.mmd')
    temp_mmd.write_text(mermaid_text.strip() + '\n', encoding='utf-8')
    run([
        'npx', '-y', '@mermaid-js/mermaid-cli',
        '-i', str(temp_mmd),
        '-o', str(out_svg),
    ])


def replace_mermaid_blocks(md_text: str, md_path: Path) -> str:
    pattern = re.compile(r'```mermaid\s*\n(.*?)```', re.IGNORECASE | re.DOTALL)
    idx = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal idx
        idx += 1
        mermaid_code = match.group(1)
        svg_name = f"{md_path.stem}.diagram-{idx}.svg"
        svg_path = md_path.parent / svg_name
        render_mermaid_to_svg(mermaid_code, svg_path)
        # Inject as HTML block for precise sizing in print CSS.
        return (
            "\n<div class=\"diagram-wrap\">"
            f"<img src=\"{html.escape(svg_name)}\" alt=\"Diagram {idx}\" />"
            "</div>\n"
        )

    return pattern.sub(repl, md_text)


def build_html(md_text: str, orientation: str, max_diagram_height_mm: int, base_dir: Path) -> str:
    page_css = (
        '@page { size: A4 landscape; margin: 20mm; }'
        if orientation == 'landscape'
        else '@page { size: A4 portrait; margin: 20mm; }'
    )

    css = f"""
{page_css}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: #111;
  font-family: "Aptos", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  line-height: 1.42;
}}
h1, h2, h3, h4 {{
  break-after: avoid-page;
  page-break-after: avoid;
}}
h1 {{ font-size: 26px; margin: 0 0 8px; }}
h2 {{ font-size: 18px; margin: 18px 0 8px; border-bottom: 1px solid #d9d9d9; padding-bottom: 4px; }}
h3 {{ font-size: 14px; margin: 14px 0 6px; }}
p, li {{ font-size: 11px; margin: 0 0 7px; }}
ul, ol {{ margin: 0 0 8px 18px; }}
blockquote {{
  margin: 10px 0;
  padding: 8px 12px;
  border-left: 4px solid #0c8f73;
  background: #f4fbf9;
}}
code, pre {{ font-family: "JetBrains Mono", Consolas, "SFMono-Regular", monospace; }}
pre {{
  font-size: 9.6px;
  line-height: 1.4;
  background: #f7f7f7;
  border: 1px solid #e2e2e2;
  border-radius: 6px;
  padding: 10px;
  overflow: hidden;
  white-space: pre-wrap;
}}
code {{ font-size: 9.6px; }}
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0 12px;
  font-size: 9.8px;
}}
th, td {{
  border: 1px solid #cfcfcf;
  padding: 5px 7px;
  vertical-align: top;
}}
th {{ background: #f0f0f0; }}
img {{ max-width: 100%; }}
.diagram-wrap {{
  margin: 10px 0 14px;
  padding: 8px;
  border: 1px solid #dddddd;
  border-radius: 6px;
  background: #fff;
  text-align: center;
  break-inside: avoid-page;
  page-break-inside: avoid;
}}
.diagram-wrap img {{
  display: block;
  margin: 0 auto;
  width: auto;
  max-width: 100%;
  height: auto;
  max-height: {max_diagram_height_mm}mm;
}}
"""

    html_body = markdown.markdown(
        md_text,
        extensions=['extra', 'fenced_code', 'tables', 'sane_lists']
    )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <base href="file://{base_dir.as_posix()}/" />
  <style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>
"""


def export_pdf(md_path: Path, orientation: str, max_diagram_height_mm: int) -> Path:
    raw_md = md_path.read_text(encoding='utf-8')
    with_diagrams = replace_mermaid_blocks(raw_md, md_path)

    html_text = build_html(
        md_text=with_diagrams,
        orientation=orientation,
        max_diagram_height_mm=max_diagram_height_mm,
        base_dir=md_path.parent,
    )

    html_path = md_path.with_suffix('.render.html')
    pdf_path = md_path.with_suffix('.pdf')
    html_path.write_text(html_text, encoding='utf-8')

    run([
        str(CHROME),
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--allow-file-access-from-files',
        '--virtual-time-budget=8000',
        '--no-pdf-header-footer',
        '--print-to-pdf-no-header',
        f'--print-to-pdf={pdf_path.as_posix()}',
        f'file://{html_path.as_posix()}',
    ])

    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description='Export markdown files with Mermaid to clean PDF.')
    parser.add_argument('md_file', nargs='*', help='Markdown file path(s).')
    args = parser.parse_args()

    if args.md_file:
        md_files = [Path(p).resolve() for p in args.md_file]
    else:
        md_files = [
            PROJECT_DIR / 'ATLAS_ORRERY_SYSTEM_PIPELINE_PDF.md',
            PROJECT_DIR / 'ATLAS_ORRERY_TECHNICAL_ARCHITECTURE_PDF.md',
        ]

    settings = {
        'ATLAS_ORRERY_SYSTEM_PIPELINE_PDF.md': ('landscape', 140),
        'ATLAS_ORRERY_TECHNICAL_ARCHITECTURE_PDF.md': ('portrait', 220),
        'SYSTEM_PIPELINE.md': ('landscape', 140),
        'filemoi.md': ('portrait', 220),
    }

    for md in md_files:
        if not md.exists():
            print(f'Skip missing: {md}')
            continue
        orientation, max_h = settings.get(md.name, ('portrait', 210))
        out_pdf = export_pdf(md, orientation, max_h)
        print(f'Created: {out_pdf}')


if __name__ == '__main__':
    main()
