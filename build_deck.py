"""
Drive the "write slides.md + mkslides.yml (+ optional extra files), run
`mkslides build`, optionally bundle the built site into one self-contained
HTML file" mechanics shared by every deck-building script -- the part that
was previously copy-pasted near-identically into each script's main().

Callers are responsible for discovering/copying source images (or videos)
into `slides_dir` themselves before calling build_slide_deck() -- that part
is genuinely project-specific (auto-discovered by dataset id vs. a fixed
hand-written list) and stays out of this module.
"""

import subprocess
import sys
from pathlib import Path

from inline_html import inline_html
from mkslides_bin import resolve_mkslides_bin
from mkslides_config import build_mkslides_config


def build_slide_deck(
    slides_dir: Path,
    slides_md: str,
    *,
    site_dir: Path | None = None,
    mkslides_yml: str | None = None,
    extra_files: dict[str, str] | None = None,
    mkslides_bin: str | None = None,
    bundle_to: Path | None = None,
    image_max_width: int | None = None,
    image_format: str = "keep",
    image_quality: int = 85,
) -> Path:
    """Write `slides_md` to slides_dir/slides.md, `mkslides_yml` (default:
    build_mkslides_config()) to slides_dir/mkslides.yml, and any
    `extra_files` (e.g. {"custom.css": CUSTOM_CSS}) into slides_dir. Then
    run `mkslides build` and, if `bundle_to` is given, bundle
    site_dir/index.html into a single self-contained HTML file via
    inline_html().

    site_dir defaults to a SIBLING of slides_dir (f"{slides_dir.name}_site"),
    not a subdirectory -- mkslides re-scans its source path for markdown
    files, and a nested output dir gets picked up as extra "pages" (e.g. its
    own bundled theme docs), turning a single deck into a multi-page index.

    Raises RuntimeError (with captured stderr) on a nonzero mkslides exit.
    Returns site_dir.
    """
    slides_dir = Path(slides_dir)
    slides_dir.mkdir(parents=True, exist_ok=True)
    site_dir = Path(site_dir) if site_dir is not None else slides_dir.parent / f"{slides_dir.name}_site"

    (slides_dir / "slides.md").write_text(slides_md)

    config_path = slides_dir / "mkslides.yml"
    config_path.write_text(mkslides_yml if mkslides_yml is not None else build_mkslides_config())

    for filename, content in (extra_files or {}).items():
        (slides_dir / filename).write_text(content)

    resolved_bin = resolve_mkslides_bin(mkslides_bin)
    # Pass -f explicitly rather than relying on mkslides.yml auto-discovery:
    # auto-discovery silently swallows config parse errors and falls back to
    # defaults with no warning at all. With -f, a broken config fails the
    # build loudly instead.
    result = subprocess.run(
        [resolved_bin, "build", str(slides_dir), "-f", str(config_path), "-d", str(site_dir)],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"mkslides build failed (exit {result.returncode}): {result.stderr}")

    if bundle_to is not None:
        bundled = inline_html(
            site_dir / "index.html",
            image_max_width=image_max_width,
            image_format=image_format,
            image_quality=image_quality,
        )
        bundle_to = Path(bundle_to)
        bundle_to.write_text(bundled)
        print(f"Wrote self-contained HTML: {bundle_to} ({bundle_to.stat().st_size / 1e6:.1f} MB)")

    return site_dir
