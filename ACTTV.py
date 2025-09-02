"""Loader shim for Assetto Corsa (Python 3.3 compatible).

Makes this module act as a package and imports ``app.py``.
No debug file logging to keep things clean.
"""

import os
import sys
import types
from importlib import import_module


def _load_impl():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    pkg_name = os.path.basename(base_dir)
    parent = os.path.abspath(os.path.dirname(base_dir))

    if parent and parent not in sys.path:
        sys.path.insert(0, parent)

    # Ensure the current module acts as a package
    current_mod = sys.modules.get(__name__)
    try:
        current_mod.__path__ = [base_dir]
        current_mod.__file__ = os.path.join(base_dir, "__init__.py")
        current_mod.__package__ = pkg_name
    except Exception:
        pass

    # Alias the package name to this module object
    sys.modules[pkg_name] = current_mod

    # Try exact case first, then alternate case
    candidates = [pkg_name]
    if pkg_name.lower() != pkg_name:
        candidates.append(pkg_name.lower())
    if pkg_name.upper() != pkg_name:
        candidates.append(pkg_name.upper())

    last_exc = None
    for name in candidates:
        try:
            # Map alias to the same package module to satisfy import
            sys.modules[name] = sys.modules[pkg_name]
            impl = import_module("%s.app" % name)
            return impl
        except Exception as ex:
            last_exc = ex
    if last_exc:
        raise last_exc
    raise ImportError("acttv.py: no candidate package names")


try:
    _impl = _load_impl()
except Exception:
    def acMain(ac_version):  # type: ignore
        return "ACTTV"

    def acUpdate(deltaT):  # type: ignore
        return

    def acShutdown():  # type: ignore
        return
else:
    def acMain(ac_version):  # type: ignore
        try:
            return _impl.acMain(ac_version)
        except Exception:
            return "ACTTV"

    def acUpdate(deltaT):  # type: ignore
        try:
            return _impl.acUpdate(deltaT)
        except Exception:
            return

    def acShutdown():  # type: ignore
        try:
            if hasattr(_impl, "acShutdown"):
                return _impl.acShutdown()
        except Exception:
            pass
        return
