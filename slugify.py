"""
Two related, but distinct, string-to-safe-identifier helpers used across
mkslides-deck-building scripts. Kept as two separate functions (not merged)
because they serve different pipeline stages -- see each docstring.
"""

import re


def make_valid_identifier(s: str) -> str:
    """Mimics MATLAB's matlab.lang.makeValidName closely enough for use as
    a filename-safe, MATLAB-identifier-safe id (e.g. a dataset id derived
    from an arbitrary source filename/path component, upstream of any slide
    deck). From norri_stochastic_generative_2026/src/extras/parse_datasets.py.
    """
    s = re.sub(r"[^0-9a-zA-Z_]", "_", s)
    if not s or not s[0].isalpha():
        s = "d_" + s
    return s


def slugify(dataset_id: str) -> str:
    """Turn an already-valid identifier into an HTML-id-safe reveal.js slide
    anchor (used in `<!-- .slide: id="..." -->` and `#/anchor` TOC links).
    A dataset_id produced by make_valid_identifier() is already a valid HTML
    id, but this is kept separate/explicit in case that assumption ever
    changes. From build_surrogate_opt_slides.py.
    """
    return re.sub(r"[^0-9a-zA-Z_-]", "-", dataset_id)
