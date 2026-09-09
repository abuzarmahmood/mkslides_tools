"""
Resolve the mkslides executable to invoke.

mkslides (https://github.com/MartenBE/mkslides) requires Python >=3.12, so a
project whose own environment is older often needs to point at a dedicated
conda/venv env's mkslides binary rather than relying on a bare "mkslides" on
PATH.
"""

import os
import shutil

# Documented, machine/user-specific fallback -- kept only because existing
# scripts in Video_Lick_Monitoring hardcode exactly this path. Not assumed to
# exist on other machines; resolve_mkslides_bin() only uses it if it's
# actually present on disk.
FALLBACK_CONDA_MKSLIDES = "/home/abuzarmahmood/anaconda3/envs/mkslides_env/bin/mkslides"

ENV_VAR = "MKSLIDES_TOOLS_BIN"


def resolve_mkslides_bin(explicit: str | None = None) -> str:
    """Resolution order:
    1. `explicit` (e.g. a caller's own --mkslides CLI flag), if given.
    2. $MKSLIDES_TOOLS_BIN environment variable, if set.
    3. `shutil.which("mkslides")` (bare "mkslides" already on PATH).
    4. FALLBACK_CONDA_MKSLIDES, only if that path exists on disk.
    5. Bare "mkslides" -- let subprocess raise FileNotFoundError loudly if
       nothing above resolved, rather than silently guessing further.
    """
    if explicit:
        return explicit
    if os.environ.get(ENV_VAR):
        return os.environ[ENV_VAR]
    on_path = shutil.which("mkslides")
    if on_path:
        return on_path
    if os.path.isfile(FALLBACK_CONDA_MKSLIDES):
        return FALLBACK_CONDA_MKSLIDES
    return "mkslides"
