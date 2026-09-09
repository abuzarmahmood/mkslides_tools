"""
Build an mkslides.yml config string, replacing the several hand-copied
MKSLIDES_CONFIG string constants that had drifted slightly across projects
(different revealjs canvas sizes, one with an extra `plugins: - extra_css:`
block).
"""

DEFAULT_SEPARATOR_VERTICAL = r"^\s*-v-\s*$"


def build_mkslides_config(
    width: int = 1920,
    height: int = 1200,
    *,
    separator_vertical: str = DEFAULT_SEPARATOR_VERTICAL,
    extra_css: list[str] | None = None,
    extra_javascript: list[str] | None = None,
) -> str:
    """Render an mkslides.yml YAML string.

    - Larger-than-default width/height gives Reveal.js's canvas more layout
      room (it scales to fit the viewport, so this affects layout headroom,
      not perceived font size).
    - separator_vertical is emitted single-quoted: double-quoting it in YAML
      lets YAML interpret `\\s` as a C-style escape, which silently disables
      '-v-' vertical-slide splitting (mkslides' own config auto-discovery
      swallows the resulting parse error and falls back to defaults with no
      warning -- pass -f explicitly when calling `mkslides build`, see
      build_deck.build_slide_deck).
    - extra_css/extra_javascript filenames (paths relative to the slides
      source dir, e.g. "custom.css") must be emitted nested under
      `plugins:` as ONE list entry with both as sibling keys
      (`plugins: - extra_css: [...] extra_javascript: [...]`), NOT as
      top-level keys and NOT as separate list items -- mkslides/config.py's
      Plugin dataclass only reads extra_css/extra_javascript from entries
      under `plugins`; a top-level `extra_css:` key raises ConfigKeyError.
    """
    lines = [
        "revealjs:",
        f"  width: {width}",
        f"  height: {height}",
        "",
        "slides:",
        f"  separator_vertical: '{separator_vertical}'",
    ]
    if extra_css or extra_javascript:
        plugin_lines = []
        if extra_css:
            plugin_lines.append("extra_css:")
            plugin_lines += [f"  - {css}" for css in extra_css]
        if extra_javascript:
            plugin_lines.append("extra_javascript:")
            plugin_lines += [f"  - {js}" for js in extra_javascript]
        lines += ["", "plugins:", f"  - {plugin_lines[0]}"]
        lines += [f"    {line}" for line in plugin_lines[1:]]
    return "\n".join(lines) + "\n"
