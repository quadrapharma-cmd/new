"""YAML read with the C parser where this build of PyYAML has one (the desktop's, the server's and the browser edition's all do):
the same safe loader and the same objects, at about ten times the speed of the pure-Python parser. The rule packs are read at
every start, and in the browser edition that was most of the time between «starting the engine» and the first screen."""
import yaml

_LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


def load(src):
    """`yaml.safe_load`, faster. `src`: text, bytes or an open file."""
    return yaml.load(src, Loader=_LOADER)
