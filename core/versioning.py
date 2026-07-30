import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT_DIR / "versionado" / "version.txt"


def obtener_version(default="0.0.0"):
    version_files = [VERSION_FILE]
    if getattr(sys, "frozen", False):
        version_files.insert(0, Path(sys.executable).resolve().parent / "versionado" / "version.txt")

    for version_file in version_files:
        try:
            version = version_file.read_text(encoding="utf-8").strip()
            if version:
                return version
        except OSError:
            continue

    return default
