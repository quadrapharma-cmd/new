"""Dossier Builder engine — P0: rule packs, profile, requirement resolver."""
__version__ = "0.1.0"

import re as _re

# The reading rules build many small patterns from their label lists. With the standard cache (512 patterns) every pass over a
# document compiled them again: most of the reading time, and ten times more inside the browser. A larger cache compiles each once.
try:
    _re._MAXCACHE = max(getattr(_re, '_MAXCACHE', 512), 8192)
except Exception:                                                  # pragma: no cover
    pass
