# mkslides_tools

Shared, plain-Python helpers for building [mkslides](https://github.com/MartenBE/mkslides)
(reveal.js) slide decks from plot/video outputs, and for bundling a built
deck into a single self-contained `.html` file. Extracted from duplicated
code across `norri_stochastic_generative_2026` and `Video_Lick_Monitoring`
so future deck-building scripts in either (or other) projects have one place
to import this mechanics from, instead of copy-pasting it forward again.

This is a **plain scripts/library folder, not an installable package** — no
`pyproject.toml`/src-layout. Reference it from a sibling project via
`sys.path`/`PYTHONPATH` (see below).

## Prerequisites

- `pip install mkslides` — requires **Python >= 3.12**. If your project's own
  environment is older, install mkslides into a separate venv/conda env and
  point calling scripts' `--mkslides` flag (or the `$MKSLIDES_TOOLS_BIN` env
  var — see `mkslides_bin.py`) at that env's `mkslides` binary, rather than
  relying on a bare `mkslides` on `PATH`.
- Optional: `pip install pillow` — enables `inline_html.py`'s image
  downscaling/recompression (`--image-format jpeg/png`), which can shrink a
  bundled deck considerably (one deck went from 34.7MB to 9.6MB just from
  `--image-max-width 800 --image-format jpeg --image-quality 75`).

## Files

| File | Purpose |
|---|---|
| `inline_html.py` | Bundle a built mkslides site (`index.html` + local `<link>`/`<script>`/`<img>`/`<video>` refs) into one self-contained HTML file. Also runnable standalone: `python inline_html.py in.html out.html`. |
| `slugify.py` | `make_valid_identifier()` (arbitrary string -> MATLAB/Python-identifier-safe id) and `slugify()` (identifier -> HTML-id-safe slide anchor). |
| `mkslides_bin.py` | `resolve_mkslides_bin()` — find the mkslides executable to invoke (explicit arg > `$MKSLIDES_TOOLS_BIN` > `PATH` > a documented conda-env fallback). |
| `mkslides_config.py` | `build_mkslides_config()` — render an `mkslides.yml` string (canvas size, `-v-` vertical-slide separator, optional `extra_css`). |
| `markdown_deck.py` | `slide()`/`slide_v()`/`img_tag()`/`video_tag()`/`paginate_toc()` — markdown-assembly primitives for a deck's `slides.md`. |
| `build_deck.py` | `build_slide_deck()` — write `slides.md`+`mkslides.yml`, run `mkslides build`, optionally bundle via `inline_html`. |
| `include_in_config.txt` | Base `<img>` CSS rule (scale-to-fit, centered) — pass as `extra_css`/copy into the slides dir for decks that want image sizing beyond mkslides' defaults. |
| `css/landscape_pair.css` | Extra CSS for laying out 2 images side-by-side per slide (`.landscape-pair` wrapper div) — use alongside `include_in_config.txt`, not instead of it. |

## Referencing this repo from another project

No install step — add this directory to `sys.path` (or set `PYTHONPATH`)
before importing:

```python
import sys
from pathlib import Path
sys.path.insert(0, "/media/bigdata/projects/hamilos_lab/mkslides_tools")

from markdown_deck import slide, slide_v, img_tag, video_tag, paginate_toc
from mkslides_config import build_mkslides_config
from build_deck import build_slide_deck
from mkslides_bin import resolve_mkslides_bin
from slugify import make_valid_identifier, slugify
```

or:

```bash
PYTHONPATH=/media/bigdata/projects/hamilos_lab/mkslides_tools python my_build_script.py
```

## Worked example 1: auto-discovery deck (one slide per item found on disk)

Style used by norri's per-dataset surrogate-opt decks: discover items by
globbing a run directory, build a paginated table of contents, then one
slide per item.

```python
from pathlib import Path
from slugify import slugify
from markdown_deck import paginate_toc
from mkslides_config import build_mkslides_config
from build_deck import build_slide_deck

run_dir = Path("plots/my_run")
dataset_ids = sorted(p.stem for p in run_dir.glob("*_heatmap.png"))

toc_entries = [(did, slugify(did)) for did in dataset_ids]
lines = ["# My deck", "", "---", ""]
lines += paginate_toc(toc_entries, rows_per_subslide=10)

for did in dataset_ids:
    anchor = slugify(did)
    lines += [
        "---", "",
        f'<!-- .slide: id="{anchor}" -->',
        f"## {did}", "",
        f'<img src="{did}_heatmap.png" width="90%"/>', "",
    ]

slides_dir = run_dir.parent / f"slides_{run_dir.name}"
# ... copy each did's PNG into slides_dir here ...
build_slide_deck(
    slides_dir,
    "\n".join(lines),
    mkslides_yml=build_mkslides_config(width=1920, height=1200),
)
```

## Worked example 2: hand-written-slide-list deck (one fixed narrative)

Style used by Video_Lick_Monitoring's project-summary decks: a fixed
sequence of `slide()`/`slide_v()` calls, ending with a bundled single-file
HTML deliverable.

```python
from pathlib import Path
from markdown_deck import slide, slide_v, img_tag, video_tag
from mkslides_config import build_mkslides_config
from build_deck import build_slide_deck

IMG_SRC = Path("slide_images")
slides_dir = Path("data/my_project/slides")

parts = ["# My project summary", ""]
parts.append(slide(
    "## What question is this answering?", "",
    img_tag("headline_result.png", width=70, src_dir=IMG_SRC),
))
parts.append(slide(
    "## Method", "",
    video_tag("demo_clip.mp4", width=60, src_dir=IMG_SRC),
    slide_v("### More detail", "", "- extra context here"),
))

# ... copy IMG_SRC's referenced files into slides_dir here ...
build_slide_deck(
    slides_dir,
    "\n".join(parts),
    mkslides_yml=build_mkslides_config(width=1920, height=1350),
    bundle_to=Path("my_project_summary.html"),
)
```

## Side-by-side image layout

For slides laying out 2 images side by side (e.g. comparing two metrics for
the same dataset), wrap them in `<div class="landscape-pair">...</div>` and
load both CSS files:

```python
build_slide_deck(
    slides_dir,
    slides_md,
    mkslides_yml=build_mkslides_config(extra_css=["include_in_config.txt", "landscape_pair.css"]),
    extra_files={
        "include_in_config.txt": Path("include_in_config.txt").read_text(),
        "landscape_pair.css": Path("css/landscape_pair.css").read_text(),
    },
)
```

Otherwise, `include_in_config.txt` alone (or mkslides' own default styling)
is enough for single-image-per-slide decks.

## Out of scope (left in each project)

Project-specific narrative/data-discovery logic — e.g. which datasets to
include, what each slide's prose says, how source images are laid out on
disk — stays in each project's own build script. This repo only holds the
shared mechanics: markdown assembly, mkslides config, running the build, and
bundling the result.
