import os
import sys
import sysconfig

from PyInstaller import log as logging

logger = logging.getLogger(__name__)


def pre_find_module_path(hook_api):
    candidates = []

    stdlib = sysconfig.get_paths().get("stdlib")
    if stdlib:
        candidates.append(stdlib)

    base_prefix = getattr(sys, "base_prefix", None)
    if base_prefix:
        candidates.append(os.path.join(base_prefix, "Lib"))

    resolved = []
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        tkinter_dir = os.path.join(candidate, "tkinter")
        if not os.path.isdir(tkinter_dir):
            continue
        key = os.path.normcase(os.path.abspath(candidate))
        if key in seen:
            continue
        seen.add(key)
        resolved.append(candidate)

    if resolved:
        hook_api.search_dirs = resolved
        logger.info("Custom tkinter hook activo | search_dirs=%s", resolved)
