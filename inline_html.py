"""
Bundle a static HTML file (with local <link>/<script>/<img>/<video>/<source>
references, and CSS files with local @import/url() references) into a single
self-contained .html file with everything inlined -- no external files
needed, so it can be emailed/shared as one file and opened directly in a
browser. <video>/<source> are embedded as-is (base64), with no
downscale/recompression step (unlike <img>) -- keep source clips small.

This only handles LOCAL (relative, on-disk) references. Remote (http(s)://)
URLs and already-inlined data: URIs are left untouched.

<img> references are optionally downscaled/recompressed before embedding
(requires Pillow) -- source images are often exported at a much higher
resolution than their actual display size, so embedding them as-is bloats
the bundle far more than necessary.

Usage:
    python inline_html.py <input.html> <output.html> [--image-max-width PX]
        [--image-format {keep,jpeg,png}] [--image-quality Q]
"""

import argparse
import base64
import io
import mimetypes
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

# mimetypes' built-in table is missing/inconsistent for some web font types
# across Python versions.
EXTRA_MIME_TYPES = {
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".otf": "font/otf",
    ".svg": "image/svg+xml",
}


def guess_mime(path: Path) -> str:
    if path.suffix.lower() in EXTRA_MIME_TYPES:
        return EXTRA_MIME_TYPES[path.suffix.lower()]
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def to_data_uri(path: Path) -> str:
    mime = guess_mime(path)
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def to_image_data_uri(path: Path, max_width: int | None, fmt: str, quality: int) -> str:
    """Like to_data_uri, but for raster images: optionally downscale to
    max_width and re-encode as jpeg/png. fmt='keep' skips recompression
    entirely (falls back to to_data_uri)."""
    if fmt == "keep" or Image is None or path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"):
        return to_data_uri(path)

    im = Image.open(path)
    if max_width and im.width > max_width:
        new_height = round(im.height * max_width / im.width)
        im = im.resize((max_width, new_height), Image.LANCZOS)

    buf = io.BytesIO()
    if fmt == "jpeg":
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:  # fmt == "png"
        im.save(buf, format="PNG", optimize=True)
        mime = "image/png"

    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{data}"


def is_local_ref(ref: str) -> bool:
    ref = ref.strip().strip("'\"")
    return bool(ref) and not ref.startswith(("http://", "https://", "//", "data:", "#"))


CSS_URL_RE = re.compile(r"url\(\s*([^)]+?)\s*\)")
CSS_IMPORT_RE = re.compile(r"@import\s+url\(\s*([^)]+?)\s*\)\s*;")


def inline_css(css_path: Path, _seen: set | None = None) -> str:
    """Recursively inline @import url(...) and url(...) references in a CSS
    file, resolving relative paths against css_path's own directory."""
    if _seen is None:
        _seen = set()
    css_path = css_path.resolve()
    if css_path in _seen:
        return ""  # avoid infinite @import loops
    _seen.add(css_path)

    content = css_path.read_text()
    base_dir = css_path.parent

    def replace_import(m: re.Match) -> str:
        ref = m.group(1).strip("'\"")
        if not is_local_ref(ref):
            return m.group(0)
        return inline_css(base_dir / ref, _seen)

    content = CSS_IMPORT_RE.sub(replace_import, content)

    def replace_url(m: re.Match) -> str:
        ref = m.group(1).strip("'\"")
        if not is_local_ref(ref):
            return m.group(0)
        # strip any trailing query/fragment (e.g. "file.eot?#iefix")
        clean_ref = ref.split("?")[0].split("#")[0]
        target = base_dir / clean_ref
        if not target.is_file():
            print(f"Warning: CSS url() target not found, leaving as-is: {target}", file=sys.stderr)
            return m.group(0)
        return f"url({to_data_uri(target)})"

    content = CSS_URL_RE.sub(replace_url, content)
    return content


LINK_CSS_RE = re.compile(r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*\bhref=["\']([^"\']+)["\'][^>]*/?>')
SCRIPT_SRC_RE = re.compile(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*></script>')
IMG_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'][^>]*/?>)')
# Matches both <video src="..."> and <source src="..."> (the latter as a
# <video> child, e.g. <video controls><source src="clip.mp4"></video>) --
# same src="..." attribute shape as <img>, so one regex covers both tags.
VIDEO_SRC_RE = re.compile(r'(<(?:video|source)\b[^>]*\bsrc=["\'])([^"\']+)(["\'][^>]*/?>)')


def inline_html(html_path: Path, image_max_width: int | None = None,
                 image_format: str = "keep", image_quality: int = 85) -> str:
    html_path = html_path.resolve()
    base_dir = html_path.parent
    html = html_path.read_text()

    # Order matters: <img>/<link> are processed before <script> is inlined,
    # so these regexes only ever scan the original markup -- never text
    # that's already-embedded JS (which can contain template-literal
    # strings like `<img src="${e}">` that would otherwise false-match).

    def replace_img(m: re.Match) -> str:
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if not is_local_ref(src):
            return m.group(0)
        target = base_dir / src
        if not target.is_file():
            print(f"Warning: image not found, leaving as-is: {target}", file=sys.stderr)
            return m.group(0)
        return f"{prefix}{to_image_data_uri(target, image_max_width, image_format, image_quality)}{suffix}"

    html = IMG_SRC_RE.sub(replace_img, html)

    def replace_video(m: re.Match) -> str:
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if not is_local_ref(src):
            return m.group(0)
        target = base_dir / src
        if not target.is_file():
            print(f"Warning: video not found, leaving as-is: {target}", file=sys.stderr)
            return m.group(0)
        return f"{prefix}{to_data_uri(target)}{suffix}"

    html = VIDEO_SRC_RE.sub(replace_video, html)

    def replace_link(m: re.Match) -> str:
        href = m.group(1)
        if not is_local_ref(href):
            return m.group(0)
        target = base_dir / href
        if not target.is_file():
            print(f"Warning: stylesheet not found, leaving as-is: {target}", file=sys.stderr)
            return m.group(0)
        return f"<style>\n{inline_css(target)}\n</style>"

    html = LINK_CSS_RE.sub(replace_link, html)

    def replace_script(m: re.Match) -> str:
        src = m.group(1)
        if not is_local_ref(src):
            return m.group(0)
        target = base_dir / src
        if not target.is_file():
            print(f"Warning: script not found, leaving as-is: {target}", file=sys.stderr)
            return m.group(0)
        return f"<script>\n{target.read_text()}\n</script>"

    html = SCRIPT_SRC_RE.sub(replace_script, html)

    return html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_html", type=Path)
    parser.add_argument("output_html", type=Path)
    parser.add_argument(
        "--image-max-width", type=int, default=None,
        help="Downscale images wider than this (px) before embedding. Omit to keep original resolution.",
    )
    parser.add_argument(
        "--image-format", choices=["keep", "jpeg", "png"], default="keep",
        help="'keep' embeds the source file as-is; 'jpeg'/'png' re-encode (requires Pillow).",
    )
    parser.add_argument(
        "--image-quality", type=int, default=85,
        help="JPEG quality (1-100) when --image-format=jpeg. Ignored otherwise.",
    )
    args = parser.parse_args()

    if not args.input_html.is_file():
        sys.exit(f"Not a file: {args.input_html}")
    if args.image_format != "keep" and Image is None:
        sys.exit("--image-format requires Pillow (pip install pillow)")

    bundled = inline_html(args.input_html, args.image_max_width, args.image_format, args.image_quality)
    args.output_html.write_text(bundled)
    print(f"Wrote self-contained HTML: {args.output_html} ({args.output_html.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
