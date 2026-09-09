"""
Shared markdown-assembly primitives for building an mkslides (reveal.js)
deck's slides.md, for both the "hand-written slide list" style (a fixed
sequence of slide()/slide_v() calls describing one project) and the
"auto-discovery" style (one slide per item found on disk, with a paginated
table of contents).
"""

import sys
from pathlib import Path


def slide(*lines: str) -> str:
    """Join lines as one mkslides markdown slide, preceded by a '---'
    horizontal separator."""
    return "\n".join(["---", ""] + list(lines) + [""])


def slide_v(*lines: str) -> str:
    """Like slide(), but as a '-v-' vertical sub-slide nested under the
    previous slide (down-arrow navigation), for detail that expands on the
    slide above without disrupting the main left-right narrative flow."""
    return "\n".join(["-v-", ""] + list(lines) + [""])


def img_tag(name: str, width: int = 90, src_dir: Path | None = None,
            display_name: str | None = None) -> str:
    """Build an <img> tag referencing `name` inside `src_dir` (or the
    current directory if src_dir is None). Warns to stderr and returns ''
    (skips the image, does not raise) if the file doesn't exist, so a deck
    build can proceed with an intentionally-missing image rather than
    crashing partway through.

    `display_name` overrides the emitted `src=` filename -- needed when two
    source dirs' images share a basename after being flattened into one
    slides dir (copy the file in under `display_name`, then reference it
    with the same `display_name` here).
    """
    src_dir = src_dir or Path(".")
    src = src_dir / name
    if not src.is_file():
        print(f"Warning: missing image, skipping: {src}", file=sys.stderr)
        return ""
    return f'<img src="{display_name or name}" width="{width}%"/>'


def video_tag(name: str, width: int = 70, src_dir: Path | None = None) -> str:
    """Like img_tag(), but for a <video controls> tag. Same missing-file
    warn-and-skip behavior."""
    src_dir = src_dir or Path(".")
    src = src_dir / name
    if not src.is_file():
        print(f"Warning: missing video, skipping: {src}", file=sys.stderr)
        return ""
    return f'<video src="{name}" width="{width}%" controls></video>'


def paginate_toc(
    entries: list[tuple[str, str]],
    rows_per_subslide: int = 10,
    heading: str = "Table of contents",
    extra_first_page_lines: list[str] | None = None,
) -> list[str]:
    """Build a '-v-'-paginated table-of-contents block, as a list of markdown
    lines (not yet joined) to splice into a larger slides.md.

    `entries` is a list of (display_text, anchor) pairs, each rendered as
    '- [display_text](#/anchor)'. Plain markdown lists overflowing a single
    slide don't reflow (CSS multi-column/inline-block layouts both overlap
    badly under reveal.js's markdown plugin) -- chunking across reveal's own
    vertical-slide pagination is native and needs no custom CSS.

    `extra_first_page_lines` (e.g. a single '- [Summary](#/summary)' link)
    are inserted at the top of the first page only.
    """
    n_chunks = -(-len(entries) // rows_per_subslide)  # ceil division
    lines: list[str] = []
    for chunk_i in range(n_chunks):
        chunk = entries[chunk_i * rows_per_subslide:(chunk_i + 1) * rows_per_subslide]
        if chunk_i > 0:
            lines.append("-v-")
            lines.append("")
        lines.append(f"## {heading} ({chunk_i + 1}/{n_chunks})")
        lines.append("")
        if chunk_i == 0 and extra_first_page_lines:
            lines.extend(extra_first_page_lines)
        for display_text, anchor in chunk:
            lines.append(f"- [{display_text}](#/{anchor})")
        lines.append("")
    return lines
